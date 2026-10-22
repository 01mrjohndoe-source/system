# Lule Robot — Next.js + SQLite

Migração do dashboard Streamlit e do monitor RSS Python para Next.js, React e Node.js.

## Funcionalidades migradas

- Dashboard de notícias com filtros por consulta, veículo, título e período.
- Indicadores, gráficos por veículo/consulta e evolução temporal.
- Tabela com links para as matérias e exportação CSV UTF-8.
- Comparador de declarações com formulário, validação de URLs, pesquisa, filtros por status e exportação CSV.
- Coleta dos seis termos configurados no Google News RSS e inserção sem duplicar a combinação consulta/link.
- Endpoint para executar coleta manual e relatório por consulta.
- Preservação do banco SQLite original (`data/monitor.db`).

## Requisitos

- Node.js 20.9+ (Node 22 recomendado).
- npm.

## Rodar localmente

```bash
cp .env.example .env.local
npm install
npm run db:check
npm run dev
```

Abra http://localhost:3000.

O arquivo original `data/monitor.db` está incluído para desenvolvimento local. Faça backup antes de executar migrações ou alterar os dados.

## API

- `GET /api/news` — notícias; aceita parâmetros repetidos `consulta`, `fonte`, além de `busca`, `inicio` e `fim`.
- `GET /api/declarations` — declarações; aceita `status` repetido e `busca`.
- `POST /api/declarations` — cria uma declaração.
- `POST /api/monitor` — executa a coleta RSS. Se `MONITOR_API_SECRET` estiver configurado, envie `Authorization: Bearer <segredo>`.

## Deploy Vercel e persistência

**Não use o SQLite do disco local da função Vercel como banco de produção.** O filesystem da função não é um armazenamento persistente e pode ser recriado entre execuções. O app aceita a API SQLite compatível do Turso/libSQL:

1. Crie um banco Turso/libSQL persistente.
2. Configure `TURSO_DATABASE_URL` e `TURSO_AUTH_TOKEN` nas Environment Variables da Vercel.
3. Importe o conteúdo de `data/monitor.db` para o banco remoto antes do primeiro deploy ou execute o script de importação documentado na seção de migração abaixo.
4. Configure um `MONITOR_API_SECRET` forte para proteger a coleta manual e/ou `CRON_SECRET` para o agendador.
5. Faça o deploy e teste os endpoints.

O arquivo `vercel.json` agenda uma chamada a cada 15 minutos. A coleta é protegida por `CRON_SECRET` (padrão da Vercel) ou `MONITOR_API_SECRET`. Confira se a duração máxima disponível no seu plano é suficiente para consultar todos os feeds; se houver timeout, dividiremos a coleta em lotes menores.

A Vercel Cron pode acionar `POST /api/monitor`? Por padrão, Cron chama URLs HTTP com GET; para agendamento, crie um endpoint GET dedicado protegido por segredo e configure `vercel.json`, ou use um serviço de agendamento que faça POST. A coleta das seis consultas pode ultrapassar os limites de duração do plano; monitore os tempos e considere dividir as consultas em lotes.

## Importação de dados para Turso

O banco local incluído contém 754 notícias e a tabela de declarações vazia no momento da migração. Não aponte a aplicação local para um banco remoto vazio antes de importar os dados.

Para migrar, configure `TURSO_DATABASE_URL` e `TURSO_AUTH_TOKEN` localmente e execute `npm run db:migrate:turso`. O script cria as tabelas e copia os registros preservando IDs e campos, ignorando duplicatas. Confira as contagens mostradas pelo script e mantenha o arquivo original como backup. Execute apenas depois de confirmar que o destino é o banco correto; o script não apaga registros existentes.

## Notas de migração

- O projeto Python original também contém `tests/monitor.robot`, que automatiza pesquisa na interface web do Google. Ele é distinto do monitor RSS do dashboard e não foi convertido para Node.js neste primeiro corte; pode continuar sendo executado separadamente com Robot Framework, se ainda for necessário.
- A coleta atual usa feeds RSS públicos do Google News, não scraping do navegador.
- O dashboard limita a resposta da API de notícias a 5.000 registros por consulta para evitar respostas muito grandes. Ajuste paginação caso o acervo cresça significativamente.
- Para segurança, este projeto não implementa login/autorização do dashboard. Se ele for público, configure proteção antes de inserir declarações privadas ou permitir escrita pública.

npm run db:check