import { NextRequest, NextResponse } from 'next/server';
import { db, ensureSchema, rows } from '@/lib/db';
import { DECLARATION_STATUSES } from '@/lib/queries';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    await ensureSchema();
    const p = request.nextUrl.searchParams;
    const status = p.getAll('status');
    const busca = (p.get('busca') || '').trim();
    const where: string[] = [];
    const args: string[] = [];
    if (status.length) { where.push(`status IN (${status.map(() => '?').join(',')})`); args.push(...status); }
    if (busca) { where.push(`(pessoa LIKE ? COLLATE NOCASE OR declaracao LIKE ? COLLATE NOCASE OR COALESCE(justificativa,'') LIKE ? COLLATE NOCASE OR COALESCE(contexto,'') LIKE ? COLLATE NOCASE)`); args.push(...Array(4).fill(`%${busca}%`)); }
    const clause = where.length ? `WHERE ${where.join(' AND ')}` : '';
    const result = await db.execute({ sql: `SELECT * FROM declaracoes ${clause} ORDER BY cadastrado_em DESC, id DESC`, args });
    return NextResponse.json({ declarations: rows<Record<string, unknown>>(result), statuses: DECLARATION_STATUSES });
  } catch (error) {
    console.error('GET /api/declarations', error);
    return NextResponse.json({ error: 'Não foi possível consultar as declarações.' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    await ensureSchema();
    const body = await request.json();
    const pessoa = typeof body.pessoa === 'string' ? body.pessoa.trim() : '';
    const declaracao = typeof body.declaracao === 'string' ? body.declaracao.trim() : '';
    if (!pessoa || !declaracao) return NextResponse.json({ error: 'Preencha a pessoa e o texto da declaração.' }, { status: 400 });
    const fields = ['url_original', 'url_checagem'] as const;
    for (const field of fields) {
      const value = typeof body[field] === 'string' ? body[field].trim() : '';
      if (value && !/^https?:\/\//i.test(value)) return NextResponse.json({ error: `${field === 'url_original' ? 'Link da declaração original' : 'Link da checagem'} deve começar com http:// ou https://.` }, { status: 400 });
    }
    const status = DECLARATION_STATUSES.includes(body.status) ? body.status : 'Não verificado';
    const result = await db.execute({
      sql: `INSERT INTO declaracoes (pessoa, declaracao, data_declaracao, contexto, status, justificativa, fonte_original, url_original, fonte_checagem, url_checagem) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      args: [pessoa, declaracao, body.data_declaracao || null, body.contexto?.trim() || '', status, body.justificativa?.trim() || '', body.fonte_original?.trim() || '', body.url_original?.trim() || '', body.fonte_checagem?.trim() || '', body.url_checagem?.trim() || ''],
    });
    return NextResponse.json({ ok: true, id: Number(result.lastInsertRowid) }, { status: 201 });
  } catch (error) {
    console.error('POST /api/declarations', error);
    return NextResponse.json({ error: 'Não foi possível salvar a declaração.' }, { status: 500 });
  }
}
