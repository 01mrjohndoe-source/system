// Copies the bundled/local SQLite database to a persistent Turso/libSQL database.
// Usage: TURSO_DATABASE_URL=libsql://... TURSO_AUTH_TOKEN=... node scripts/migrate-to-turso.mjs
import { createClient } from '@libsql/client';
import path from 'node:path';

if (!process.env.TURSO_DATABASE_URL || !process.env.TURSO_AUTH_TOKEN) {
  console.error('Configure TURSO_DATABASE_URL e TURSO_AUTH_TOKEN antes de executar.');
  process.exit(1);
}
if (process.env.TURSO_DATABASE_URL.startsWith('file:')) {
  console.error('TURSO_DATABASE_URL precisa apontar para o banco remoto, não para um arquivo local.');
  process.exit(1);
}
const source = createClient({ url: `file:${path.join(process.cwd(), 'data', 'monitor.db')}` });
const target = createClient({ url: process.env.TURSO_DATABASE_URL, authToken: process.env.TURSO_AUTH_TOKEN });
try {
  await target.batch([
    `CREATE TABLE IF NOT EXISTS noticias (id INTEGER PRIMARY KEY AUTOINCREMENT, consulta TEXT NOT NULL, titulo TEXT NOT NULL, link TEXT NOT NULL, fonte TEXT, publicado TEXT, detectado_em TEXT NOT NULL, UNIQUE(consulta, link))`,
    `CREATE TABLE IF NOT EXISTS declaracoes (id INTEGER PRIMARY KEY AUTOINCREMENT, pessoa TEXT NOT NULL, declaracao TEXT NOT NULL, data_declaracao TEXT, contexto TEXT, status TEXT NOT NULL DEFAULT 'Não verificado', justificativa TEXT, fonte_original TEXT, url_original TEXT, fonte_checagem TEXT, url_checagem TEXT, cadastrado_em TEXT DEFAULT CURRENT_TIMESTAMP)`
  ], 'write');
  for (const table of ['noticias', 'declaracoes']) {
    const result = await source.execute(`SELECT * FROM ${table} ORDER BY id`);
    const columns = result.columns;
    let copied = 0;
    for (let offset = 0; offset < result.rows.length; offset += 100) {
      const batch = result.rows.slice(offset, offset + 100).map(row => ({
        sql: `INSERT OR IGNORE INTO ${table} (${columns.map(c => `"${c}"`).join(', ')}) VALUES (${columns.map(() => '?').join(', ')})`,
        args: columns.map(c => row[c] ?? null),
      }));
      if (batch.length) {
        const responses = await target.batch(batch, 'write');
        copied += responses.reduce((sum, r) => sum + r.rowsAffected, 0);
      }
    }
    const count = await target.execute(`SELECT COUNT(*) AS total FROM ${table}`);
    console.log(`${table}: ${result.rows.length} registros locais; ${copied} inseridos; ${count.rows[0].total} no destino.`);
  }
} finally {
  await source.close();
  await target.close();
}
