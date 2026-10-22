
import argparse
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import feedparser
import requests

from config.urls import (
    SEARCH_QUERIES,
    POLL_INTERVAL_SECONDS,
    NEWS_LANGUAGE,
    NEWS_REGION,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "monitor.db"

FEED_URL = "https://news.google.com/rss/search"


def conectar_banco():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS noticias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consulta TEXT NOT NULL,
            titulo TEXT NOT NULL,
            link TEXT NOT NULL,
            fonte TEXT,
            publicado TEXT,
            detectado_em TEXT NOT NULL,
            UNIQUE(consulta, link)
        )
    """)

    conn.commit()
    return conn


def buscar_noticias(consulta):
    params = {
        "q": consulta,
        "hl": NEWS_LANGUAGE,
        "gl": NEWS_REGION,
        "ceid": f"{NEWS_REGION}:{NEWS_LANGUAGE}",
    }

    url = f"{FEED_URL}?{urlencode(params)}"

    response = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "PersonalNewsMonitor/1.0"},
    )
    response.raise_for_status()

    feed = feedparser.parse(response.content)

    if feed.bozo and not feed.entries:
        raise ValueError("O feed retornou conteúdo inválido.")

    return feed.entries


def salvar_noticia(conn, consulta, noticia):
    titulo = noticia.get("title", "").strip()
    link = noticia.get("link", "").strip()

    if not titulo or not link:
        return False

    fonte = noticia.get("source", {}).get("title", "")
    publicado = noticia.get("published", "")
    detectado_em = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO noticias
        (consulta, titulo, link, fonte, publicado, detectado_em)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            consulta,
            titulo,
            link,
            fonte,
            publicado,
            detectado_em,
        ),
    )

    conn.commit()

    if cursor.rowcount == 0:
        return False

    print(f"\n[NOVA NOTÍCIA] {consulta}")
    print(f"Título: {titulo}")
    print(f"Fonte: {fonte or 'Não identificada'}")
    print(f"Publicado: {publicado or 'Data indisponível'}")
    print(f"Link: {link}")

    return True


def executar_ciclo(conn):
    print("\n========== NOVO CICLO ==========")
    print(datetime.now().astimezone().isoformat(timespec="seconds"))

    total_novas = 0
    consultas_com_erro = 0

    for consulta in SEARCH_QUERIES:
        print(f"\n[CONSULTANDO] {consulta}")

        try:
            noticias = buscar_noticias(consulta)
            novas = 0

            for noticia in noticias:
                if salvar_noticia(conn, consulta, noticia):
                    novas += 1

            total_novas += novas

            print(
                f"[OK] {len(noticias)} resultados recebidos; "
                f"{novas} novos registros."
            )

        except requests.RequestException as erro:
            consultas_com_erro += 1
            print(f"[ERRO DE REDE] {consulta}: {erro}")

        except Exception as erro:
            consultas_com_erro += 1
            print(f"[ERRO] {consulta}: {erro}")

    print("\n========== CICLO CONCLUÍDO ==========")
    print(f"Novas notícias salvas: {total_novas}")
    print(f"Consultas com erro: {consultas_com_erro}")

    return total_novas, consultas_com_erro


def main():
    parser = argparse.ArgumentParser(
        description="Monitor de notícias do Google News RSS."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa uma única coleta e encerra.",
    )
    args = parser.parse_args()

    conn = conectar_banco()

    print("Monitor de notícias iniciado.")
    print(f"Consultas configuradas: {len(SEARCH_QUERIES)}")
    print(f"Banco de dados: {DB_PATH}")

    try:
        if args.once:
            print("Modo manual: será executado apenas um ciclo.")
            _, erros = executar_ciclo(conn)

            if erros:
                print(
                    "ATENÇÃO: uma ou mais consultas falharam. "
                    "Confira as mensagens acima."
                )
        else:
            print("Modo automático: pressione Ctrl+C para encerrar.")

            while True:
                executar_ciclo(conn)
                print(
                    f"\nPróxima coleta em "
                    f"{POLL_INTERVAL_SECONDS // 60} minutos."
                )
                time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nMonitor encerrado pelo usuário.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
