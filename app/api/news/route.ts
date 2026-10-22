import { NextRequest, NextResponse } from 'next/server';
import { db, ensureSchema, rows } from '@/lib/db';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
type News = { id: number; consulta: string; titulo: string; link: string; fonte: string | null; publicado: string | null; detectado_em: string };

export async function GET(request: NextRequest) {
  try {
    await ensureSchema();
    const p = request.nextUrl.searchParams;
    const consulta = p.getAll('consulta');
    const fonte = p.getAll('fonte');
    const busca = (p.get('busca') || '').trim();
    const inicio = p.get('inicio');
    const fim = p.get('fim');
    const where: string[] = [];
    const args: (string | number)[] = [];
    if (consulta.length) { where.push(`consulta IN (${consulta.map(() => '?').join(',')})`); args.push(...consulta); }
    if (fonte.length) { where.push(`COALESCE(NULLIF(fonte, ''), 'Fonte não identificada') IN (${fonte.map(() => '?').join(',')})`); args.push(...fonte); }
    if (busca) { where.push('titulo LIKE ? COLLATE NOCASE'); args.push(`%${busca}%`); }
    if (inicio) { where.push('(publicado IS NULL OR date(publicado) IS NULL OR date(publicado) >= date(?))'); args.push(inicio); }
    if (fim) { where.push('(publicado IS NULL OR date(publicado) IS NULL OR date(publicado) <= date(?))'); args.push(fim); }
    const clause = where.length ? `WHERE ${where.join(' AND ')}` : '';
    const result = await db.execute({ sql: `SELECT id, consulta, titulo, link, COALESCE(NULLIF(fonte, ''), 'Fonte não identificada') AS fonte, publicado, detectado_em FROM noticias ${clause} ORDER BY id DESC LIMIT 5000`, args });
    const news = rows<News>(result);
    const facets = await db.execute('SELECT DISTINCT consulta FROM noticias ORDER BY consulta');
    const sources = await db.execute(`SELECT DISTINCT COALESCE(NULLIF(fonte, ''), 'Fonte não identificada') AS fonte FROM noticias ORDER BY fonte`);
    return NextResponse.json({ news, consultas: rows<{consulta: string}>(facets).map(x => x.consulta), fontes: rows<{fonte: string}>(sources).map(x => x.fonte), total: news.length });
  } catch (error) {
    console.error('GET /api/news', error);
    return NextResponse.json({ error: 'Não foi possível consultar as notícias. Verifique a configuração do banco de dados.' }, { status: 500 });
  }
}
