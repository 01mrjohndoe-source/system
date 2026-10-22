// Export a JSON snapshot from the local SQLite-compatible database for backup/migration.
import { createClient } from '@libsql/client';
import path from 'node:path';
import { writeFile } from 'node:fs/promises';
const url = process.env.TURSO_DATABASE_URL || `file:${path.join(process.cwd(), 'data', 'monitor.db')}`;
const db = createClient({ url, authToken: process.env.TURSO_AUTH_TOKEN || undefined });
const news = await db.execute('SELECT * FROM noticias ORDER BY id');
const declarations = await db.execute('SELECT * FROM declaracoes ORDER BY id');
await writeFile(path.join(process.cwd(), 'data-export.json'), JSON.stringify({ exportedAt: new Date().toISOString(), noticias: news.rows, declaracoes: declarations.rows }, null, 2));
console.log(`Exportado: ${news.rows.length} notícias e ${declarations.rows.length} declarações para data-export.json`);
await db.close();
