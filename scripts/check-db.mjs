import { createClient } from '@libsql/client';
import path from 'node:path';
const url = process.env.TURSO_DATABASE_URL || `file:${path.join(process.cwd(), 'data', 'monitor.db')}`;
const db = createClient({ url, authToken: process.env.TURSO_AUTH_TOKEN || undefined });
for (const table of ['noticias', 'declaracoes']) {
  const result = await db.execute(`SELECT COUNT(*) AS total FROM ${table}`);
  console.log(`${table}: ${result.rows[0].total}`);
}
await db.close();
