import { NextRequest, NextResponse } from 'next/server';
import { runCollection } from '@/lib/monitor';
export const runtime = 'nodejs';
export const maxDuration = 60;
export const dynamic = 'force-dynamic';

async function handle(request: NextRequest) {
  const secret = process.env.MONITOR_API_SECRET || process.env.CRON_SECRET;
  if (process.env.NODE_ENV === 'production' && !secret) {
    return NextResponse.json({ error: 'Configure MONITOR_API_SECRET ou CRON_SECRET antes de habilitar a coleta em produção.' }, { status: 503 });
  }
  if (secret && request.headers.get('authorization') !== `Bearer ${secret}`) {
    return NextResponse.json({ error: 'Não autorizado.' }, { status: 401 });
  }
  try {
    const result = await runCollection();
    return NextResponse.json(result, { status: result.erros === result.consultas.length ? 502 : 200 });
  } catch (error) {
    console.error('monitor endpoint', error);
    return NextResponse.json({ error: 'Falha ao executar a coleta.' }, { status: 500 });
  }
}
export async function POST(request: NextRequest) { return handle(request); }
export async function GET(request: NextRequest) { return handle(request); }
