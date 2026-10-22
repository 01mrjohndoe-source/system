
import sqlite3
from pathlib import Path
import sqlite3 as sqlite_comparador
from datetime import date as data_atual
import subprocess
import sys

import pandas as pd
import plotly.express as px
import streamlit as st


# Configuração da página
st.set_page_config(
    page_title="Radar de Notícias",
    page_icon="📰",
    layout="wide",
)

# ============================================================
# BOTÃO PARA ATUALIZAR NOTÍCIAS
# ============================================================

MONITOR_PATH = Path(__file__).resolve().parent / "monitor.py"

st.subheader("Atualização das notícias")

if st.button(
    "🔄 Atualizar notícias agora",
    type="primary",
    width="stretch",
    key="atualizar_noticias_agora",
):
    if not MONITOR_PATH.exists():
        st.error(f"Arquivo do monitor não encontrado: {MONITOR_PATH}")
    else:
        try:
            with st.spinner(
                "Consultando os feeds e salvando novas notícias..."
            ):
                processo = subprocess.run(
                    [sys.executable, str(MONITOR_PATH), "--once"],
                    cwd=str(MONITOR_PATH.parent),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=240,
                    check=False,
                )

            if processo.returncode == 0:
                st.success("Coleta finalizada!")

                # Exibe o resumo produzido pelo monitor
                st.code(
                    processo.stdout[-12000:] or "Coleta concluída sem saída.",
                    language="text",
                )

                if processo.stderr.strip():
                    with st.expander("Avisos do processo"):
                        st.code(processo.stderr[-5000:], language="text")

                # Descarta os dados em cache para reler o SQLite
                st.cache_data.clear()
                st.rerun()

            else:
                st.error(
                    f"O monitor terminou com código {processo.returncode}."
                )

                if processo.stdout.strip():
                    st.code(processo.stdout[-8000:], language="text")

                if processo.stderr.strip():
                    st.code(processo.stderr[-8000:], language="text")

        except subprocess.TimeoutExpired:
            st.error(
                "A coleta ultrapassou 4 minutos e foi interrompida. "
                "Confira a conexão e os feeds RSS."
            )

        except Exception as erro:
            st.error(f"Não foi possível executar o monitor: {erro}")

# Localiza o banco a partir da pasta deste arquivo
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "monitor.db"
DB_COMPARADOR = Path(__file__).resolve().parent / "data" / "monitor.db"

@st.cache_data(ttl=60)
def carregar_noticias():
    if not DB_PATH.exists():
        return pd.DataFrame()

    with sqlite3.connect(DB_PATH) as conexao:
        df = pd.read_sql_query(
            """
            SELECT
                id,
                consulta,
                titulo,
                link,
                fonte,
                publicado,
                detectado_em
            FROM noticias
            ORDER BY id DESC
            """,
            conexao,
        )

    # Converte datas para permitir filtros e gráficos
    for coluna in ["publicado", "detectado_em"]:
        df[coluna] = pd.to_datetime(
            df[coluna], errors="coerce", utc=True
        )

    # Evita contar o mesmo link várias vezes nos indicadores
    df["link"] = df["link"].fillna("").astype(str)
    df["fonte"] = df["fonte"].fillna("Fonte não identificada")
    df["consulta"] = df["consulta"].fillna("Sem consulta")
    df["titulo"] = df["titulo"].fillna("Sem título")

    return df


st.title("📰 Radar de Notícias")
st.caption(
    "Monitoramento de notícias públicas. "
    "Consulte as fontes originais e confira o contexto."
)

df = carregar_noticias()

if df.empty:
    st.warning(
        "Nenhuma notícia encontrada. Confira se o banco existe em "
        "data/monitor.db e se contém registros."
    )
    st.stop()

# Sidebar: filtros
st.sidebar.header("Filtros")

consultas = sorted(df["consulta"].unique().tolist())
consulta_selecionada = st.sidebar.multiselect(
    "Termos de pesquisa",
    options=consultas,
    default=consultas,
)

fontes = sorted(df["fonte"].unique().tolist())
fontes_selecionadas = st.sidebar.multiselect(
    "Veículos",
    options=fontes,
    default=[],
    help="Deixe vazio para incluir todas as fontes.",
)

busca = st.sidebar.text_input(
    "Buscar no título",
    placeholder="Digite uma palavra...",
)

# Aplica filtros
filtrado = df[df["consulta"].isin(consulta_selecionada)].copy()

if fontes_selecionadas:
    filtrado = filtrado[
        filtrado["fonte"].isin(fontes_selecionadas)
    ]

if busca.strip():
    filtrado = filtrado[
        filtrado["titulo"].str.contains(
            busca.strip(), case=False, na=False
        )
    ]

# Filtro de datas, quando há datas válidas
datas_validas = filtrado["publicado"].dropna()

if not datas_validas.empty:
    menor_data = datas_validas.min().date()
    maior_data = datas_validas.max().date()

    intervalo = st.sidebar.date_input(
        "Período de publicação",
        value=(menor_data, maior_data),
        min_value=menor_data,
        max_value=maior_data,
    )

    if isinstance(intervalo, (tuple, list)) and len(intervalo) == 2:
        inicio, fim = intervalo
        datas = filtrado["publicado"].dt.date
        filtrado = filtrado[
            filtrado["publicado"].isna()
            | ((datas >= inicio) & (datas <= fim))
        ]

# Métricas
links_unicos = filtrado[
    filtrado["link"].str.strip() != ""
]["link"].nunique()

fontes_ativas = filtrado["fonte"].nunique()

m1, m2, m3, m4 = st.columns(4)

m1.metric("Registros encontrados", f"{len(filtrado):,}")
m2.metric("Links únicos", f"{links_unicos:,}")
m3.metric("Veículos identificados", f"{fontes_ativas:,}")
m4.metric(
    "Termos de pesquisa",
    f"{filtrado['consulta'].nunique():,}",
)

st.divider()

# Gráficos
col1, col2 = st.columns(2)

with col1:
    st.subheader("Notícias por veículo")

    por_fonte = (
        filtrado.groupby("fonte")
        .size()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
        .head(10)
    )

    if not por_fonte.empty:
        fig = px.bar(
            por_fonte.sort_values("Quantidade"),
            x="Quantidade",
            y="fonte",
            orientation="h",
            labels={
                "fonte": "Veículo",
                "Quantidade": "Registros",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Resultados por consulta")

    por_consulta = (
        filtrado.groupby("consulta")
        .size()
        .reset_index(name="Quantidade")
        .sort_values("Quantidade", ascending=False)
    )

    if not por_consulta.empty:
        fig = px.bar(
            por_consulta,
            x="consulta",
            y="Quantidade",
            labels={
                "consulta": "Termo pesquisado",
                "Quantidade": "Registros",
            },
        )
        fig.update_layout(xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

# Evolução temporal
st.subheader("Publicações ao longo do tempo")

com_data = filtrado.dropna(subset=["publicado"]).copy()

if not com_data.empty:
    com_data["dia"] = com_data["publicado"].dt.date

    por_dia = (
        com_data.groupby("dia")
        .size()
        .reset_index(name="Quantidade")
    )

    fig = px.line(
        por_dia,
        x="dia",
        y="Quantidade",
        markers=True,
        labels={
            "dia": "Data de publicação",
            "Quantidade": "Registros",
        },
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Não há datas de publicação válidas para o gráfico.")

# Tabela de notícias
st.divider()
st.subheader("Notícias encontradas")
st.caption(
    "Abra a fonte original para conferir a matéria completa. "
    "Os resultados refletem os termos de pesquisa configurados."
)

colunas = [
    "publicado",
    "titulo",
    "fonte",
    "consulta",
    "link",
]

tabela = filtrado[colunas].copy()
tabela["publicado"] = tabela["publicado"].dt.strftime(
    "%d/%m/%Y %H:%M"
)

tabela = tabela.rename(
    columns={
        "publicado": "Publicação (UTC)",
        "titulo": "Título",
        "fonte": "Veículo",
        "consulta": "Consulta",
        "link": "Link",
    }
)

st.dataframe(
    tabela,
    column_config={
        "Link": st.column_config.LinkColumn(
            "Abrir matéria",
            display_text="Ler notícia",
        ),
    },
    use_container_width=True,
    hide_index=True,
)

# Exportação dos resultados filtrados
csv = filtrado[colunas].to_csv(
    index=False
).encode("utf-8-sig")

st.download_button(
    "Baixar resultados filtrados (CSV)",
    data=csv,
    file_name="noticias_filtradas.csv",
    mime="text/csv",
)


def criar_tabela_declaracoes():
    """Cria a tabela de checagens caso ela ainda não exista."""
    with sqlite_comparador.connect(DB_COMPARADOR) as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS declaracoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pessoa TEXT NOT NULL,
                declaracao TEXT NOT NULL,
                data_declaracao TEXT,
                contexto TEXT,
                status TEXT NOT NULL DEFAULT 'Não verificado',
                justificativa TEXT,
                fonte_original TEXT,
                url_original TEXT,
                fonte_checagem TEXT,
                url_checagem TEXT,
                cadastrado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conexao.commit()


def carregar_declaracoes():
    """Carrega as declarações registradas no banco."""
    with sqlite_comparador.connect(DB_COMPARADOR) as conexao:
        return pd.read_sql_query("""
            SELECT
                id,
                pessoa,
                declaracao,
                data_declaracao,
                contexto,
                status,
                justificativa,
                fonte_original,
                url_original,
                fonte_checagem,
                url_checagem,
                cadastrado_em
            FROM declaracoes
            ORDER BY cadastrado_em DESC, id DESC
        """, conexao)


def salvar_declaracao(dados):
    """Salva uma declaração sem alterar as notícias já existentes."""
    with sqlite_comparador.connect(DB_COMPARADOR) as conexao:
        conexao.execute("""
            INSERT INTO declaracoes (
                pessoa,
                declaracao,
                data_declaracao,
                contexto,
                status,
                justificativa,
                fonte_original,
                url_original,
                fonte_checagem,
                url_checagem
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, dados)
        conexao.commit()


criar_tabela_declaracoes()

st.divider()
st.header("🔎 Comparador de Declarações")
st.caption(
    "Registre declarações públicas e compare-as com fontes, "
    "documentos e checagens verificáveis."
)

# -------------------------
# Formulário para cadastro
# -------------------------

with st.expander("➕ Cadastrar uma declaração para verificação", expanded=False):
    with st.form("form_declaracao", clear_on_submit=True):

        pessoa = st.text_input(
            "Pessoa que fez a declaração",
            value="Flávio Bolsonaro"
        )

        declaracao = st.text_area(
            "O que foi dito? *",
            placeholder="Cole a declaração exata. Evite resumir de modo que altere o sentido.",
            height=120
        )

        data_fala = st.date_input(
            "Data da declaração (se conhecida)",
            value=None,
            format="DD/MM/YYYY"
        )

        contexto = st.text_area(
            "Contexto",
            placeholder="Em qual entrevista, discurso, publicação ou situação a fala ocorreu?"
        )

        status = st.selectbox(
            "Status da verificação",
            [
                "Não verificado",
                "Verdadeiro",
                "Falso",
                "Impreciso",
                "Enganoso",
                "Fora de contexto",
                "Inconclusivo"
            ],
            help=(
                "Use um veredito conclusivo somente quando houver evidências "
                "suficientes. Caso contrário, escolha 'Não verificado' ou 'Inconclusivo'."
            )
        )

        justificativa = st.text_area(
            "Justificativa e evidências",
            placeholder=(
                "Explique o que as fontes demonstram, o que não demonstram "
                "e quais limitações existem."
            ),
            height=150
        )

        st.markdown("**Fonte da declaração original**")

        fonte_original = st.text_input(
            "Nome da fonte original",
            placeholder="Ex.: entrevista, vídeo, publicação oficial"
        )

        url_original = st.text_input(
            "Link da declaração original",
            placeholder="https://..."
        )

        st.markdown("**Fonte independente de checagem (se disponível)**")

        fonte_checagem = st.text_input(
            "Nome da fonte de checagem",
            placeholder="Ex.: agência de checagem ou documento oficial"
        )

        url_checagem = st.text_input(
            "Link da checagem ou evidência",
            placeholder="https://..."
        )

        enviar = st.form_submit_button(
            "Salvar declaração",
            type="primary",
            width="stretch"
        )

        if enviar:
            if not pessoa.strip() or not declaracao.strip():
                st.error("Preencha a pessoa e o texto da declaração.")
            else:
                # Campos de URL são opcionais, mas, se preenchidos,
                # precisam ter formato de endereço web.
                urls = [
                    ("Link da declaração original", url_original),
                    ("Link da checagem", url_checagem),
                ]

                url_invalida = next(
                    (
                        nome for nome, url in urls
                        if url.strip()
                        and not url.strip().lower().startswith(("https://", "http://"))
                    ),
                    None
                )

                if url_invalida:
                    st.error(
                        f"{url_invalida}: informe um endereço iniciado por http:// ou https://."
                    )
                else:
                    salvar_declaracao((
                        pessoa.strip(),
                        declaracao.strip(),
                        data_fala.isoformat() if data_fala else None,
                        contexto.strip(),
                        status,
                        justificativa.strip(),
                        fonte_original.strip(),
                        url_original.strip(),
                        fonte_checagem.strip(),
                        url_checagem.strip()
                    ))

                    st.success("Declaração salva no banco de dados!")
                    st.rerun()


# -------------------------
# Consulta e filtros
# -------------------------

declaracoes = carregar_declaracoes()

st.subheader("Declarações cadastradas")

if declaracoes.empty:
    st.info(
        "Ainda não há declarações cadastradas. "
        "Abra o formulário acima para adicionar a primeira."
    )
else:
    col_filtro1, col_filtro2 = st.columns(2)

    with col_filtro1:
        filtro_status = st.multiselect(
            "Filtrar por status",
            options=sorted(declaracoes["status"].dropna().unique().tolist()),
            default=[]
        )

    with col_filtro2:
        busca = st.text_input(
            "Buscar nas declarações",
            placeholder="Digite uma palavra ou assunto..."
        )

    resultado = declaracoes.copy()

    if filtro_status:
        resultado = resultado[resultado["status"].isin(filtro_status)]

    if busca.strip():
        termo = busca.strip()
        mascara = (
            resultado["declaracao"].fillna("").str.contains(
                termo, case=False, regex=False
            )
            | resultado["pessoa"].fillna("").str.contains(
                termo, case=False, regex=False
            )
            | resultado["justificativa"].fillna("").str.contains(
                termo, case=False, regex=False
            )
            | resultado["contexto"].fillna("").str.contains(
                termo, case=False, regex=False
            )
        )
        resultado = resultado[mascara]

    # Indicadores do acervo cadastrado
    m1, m2, m3 = st.columns(3)

    m1.metric("Declarações encontradas", len(resultado))
    m2.metric(
        "Com veredito registrado",
        int((resultado["status"] != "Não verificado").sum())
    )
    m3.metric(
        "Com fonte de checagem",
        int(resultado["url_checagem"].fillna("").str.strip().ne("").sum())
    )

    colunas_exibicao = [
        "pessoa",
        "declaracao",
        "data_declaracao",
        "status",
        "justificativa",
        "fonte_original",
        "url_original",
        "fonte_checagem",
        "url_checagem"
    ]

    tabela = resultado[colunas_exibicao].rename(columns={
        "pessoa": "Pessoa",
        "declaracao": "Declaração",
        "data_declaracao": "Data da fala",
        "status": "Status",
        "justificativa": "Justificativa",
        "fonte_original": "Fonte original",
        "url_original": "Link original",
        "fonte_checagem": "Fonte de checagem",
        "url_checagem": "Link da checagem"
    })

    st.dataframe(
        tabela,
        column_config={
            "Link original": st.column_config.LinkColumn(
                "Link original",
                display_text="Abrir fonte"
            ),
            "Link da checagem": st.column_config.LinkColumn(
                "Link da checagem",
                display_text="Ver checagem"
            ),
        },
        hide_index=True,
        width="stretch"
    )

    csv_declaracoes = resultado.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "📥 Exportar declarações para CSV",
        data=csv_declaracoes,
        file_name="declaracoes_verificadas.csv",
        mime="text/csv",
        width="stretch"
    )

st.caption(
    "A classificação é um registro de análise, não uma conclusão automática. "
    "Confira a fala original, a metodologia e as evidências antes de aceitar um veredito."
)