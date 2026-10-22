import { createClient } from '@libsql/client';
import path from 'node:path';

// Local development can use the existing SQLite file. In production, configure
// TURSO_DATABASE_URL/TURSO_AUTH_TOKEN to use a persistent SQLite-compatible database.
const databaseUrl = process.env.TURSO_DATABASE_URL || `file:${path.join(process.cwd(), 'data', 'monitor.db')}`;
export const db = createClient({
  url: databaseUrl,
  authToken: process.env.TURSO_AUTH_TOKEN || undefined,
});

let initialized: Promise<void> | undefined;
export function ensureSchema() {
  if (!initialized) {
    initialized = (async () => {
      await db.batch([
        `CREATE TABLE IF NOT EXISTS noticias (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          consulta TEXT NOT NULL,
          titulo TEXT NOT NULL,
          link TEXT NOT NULL,
          fonte TEXT,
          publicado TEXT,
          detectado_em TEXT NOT NULL,
          UNIQUE(consulta, link)
        )`,
        `CREATE TABLE IF NOT EXISTS declaracoes (
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
        )`
      ], 'write');
    })();
  }
  return initialized;
}

export function rows<T>(result: { rows: unknown[] }): T[] {
  return result.rows as T[];
}
