# CORDA Deliberation Platform

CORDA v1 is a two-app monorepo:

- `apps/api`: FastAPI backend, Telegram webhook handling, transcript capture, and summarization
- `apps/web`: Next.js website for the active topic and public results

The platform routes Telegram users into least-full forum topics inside one Telegram supergroup, stores thread transcripts in Postgres, and publishes per-group summaries after the deliberation closes.

## Architecture

- Frontend: Next.js on Vercel
- Backend: FastAPI on Railway
- Database: Neon Postgres
- Bot integration: Telegram Bot API via `python-telegram-bot`
- Summarization: Anthropic API

## Local setup

1. Install Python dependencies:

   ```bash
   uv sync
   ```

2. Install web dependencies:

   ```bash
   pnpm install
   ```

3. Copy `.env.example` to `.env` and set all required values.

4. Apply the database schema:

   ```bash
   make apply_schema
   ```

5. Run the backend:

   ```bash
   uv run uvicorn main:app --app-dir apps/api --reload
   ```

6. Run the website:

   ```bash
   pnpm --dir apps/web dev
   ```

## API surface

- `GET /health`
- `GET /topics/active`
- `GET /topics/{topic_id}/summaries`
- `POST /webhook/telegram`
- `POST /admin/topics`
- `POST /admin/summarize/{topic_id}`

Admin endpoints require the `X-Admin-Key` header.

## Quality gates

Run the full required checks from the repo root:

```bash
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest
cd apps/web && ./node_modules/.bin/eslint .
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
```

## Deployment notes

- Neon project: `CORDA deliberation` (`delicate-cake-88112071`)
- Railway project: `clever-radiance`
- Vercel hosts `apps/web` and must define `PUBLIC_API_BASE_URL` and `TELEGRAM_BOT_USERNAME`

Operational setup details are documented in [docs/operations/deployment.md](/Users/kevinblin/Code/corda_massively_scalable_deliberative_processes/docs/operations/deployment.md).
