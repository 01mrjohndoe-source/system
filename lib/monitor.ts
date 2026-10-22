import Parser from 'rss-parser';
import { db, ensureSchema } from '@/lib/db';
import { NEWS_LANGUAGE, NEWS_REGION, SEARCH_QUERIES } from '@/lib/queries';

const parser = new Parser({ timeout: 25000, headers: { 'User-Agent': 'PersonalNewsMonitor/1.0' } });
export type MonitorResult = { consulta: string; recebidas: number; novas: number; erro?: string };

export async function runCollection(): Promise<{ novas: number; erros: number; consultas: MonitorResult[] }> {
  await ensureSchema();
  const results = await Promise.all(SEARCH_QUERIES.map(async (consulta): Promise<MonitorResult> => {
    try {
      const params = new URLSearchParams({ q: consulta, hl: NEWS_LANGUAGE, gl: NEWS_REGION, ceid: `${NEWS_REGION}:${NEWS_LANGUAGE}` });
      const feed = await parser.parseURL(`https://news.google.com/rss/search?${params.toString()}`);
      let novas = 0;
      for (const item of feed.items) {
        const titulo = (item.title || '').trim();
        const link = (item.link || '').trim();
        if (!titulo || !link) continue;
        const fonte = (item as typeof item & { source?: { title?: string } }).source?.title || '';
        const publicado = item.isoDate || item.pubDate || '';
        const detectadoEm = new Date().toISOString();
        const inserted = await db.execute({
          sql: `INSERT OR IGNORE INTO noticias (consulta, titulo, link, fonte, publicado, detectado_em) VALUES (?, ?, ?, ?, ?, ?)`,
          args: [consulta, titulo, link, fonte, publicado, detectadoEm],
        });
        novas += inserted.rowsAffected;
      }
      return { consulta, recebidas: feed.items.length, novas };
    } catch (error) {
      return { consulta, recebidas: 0, novas: 0, erro: error instanceof Error ? error.message : String(error) };
    }
  }));
  return { novas: results.reduce((n, r) => n + r.novas, 0), erros: results.filter(r => r.erro).length, consultas: results };
}
