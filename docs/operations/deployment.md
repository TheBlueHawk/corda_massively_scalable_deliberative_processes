# Deployment Guide

## Neon

1. Set `DATABASE_URL` in Railway and local `.env`.
2. Apply the schema from [`apps/api/sql/schema.sql`](/Users/kevinblin/Code/corda_massively_scalable_deliberative_processes/apps/api/sql/schema.sql).
3. Confirm the tables exist:
   - `topics`
   - `groups`
   - `users`
   - `memberships`
   - `summaries`
   - `thread_messages`

## Railway

Deploy the FastAPI service from this repo with:

```bash
railway link
railway up
```

Use the start command from [`railway.toml`](/Users/kevinblin/Code/corda_massively_scalable_deliberative_processes/railway.toml). Set these variables in Railway:

- `DATABASE_URL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_SUPERGROUP_ID`
- `ANTHROPIC_API_KEY`
- `X_ADMIN_KEY`
- `TELEGRAM_BOT_USERNAME`
- `GROUP_CAPACITY`
- `SUMMARY_MODEL`

After deployment, register the Telegram webhook:

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://<railway-domain>/webhook/telegram"
```

For scheduled summarization, configure a Railway cron job to call:

```bash
curl -X POST -H "X-Admin-Key: ${X_ADMIN_KEY}" https://<railway-domain>/admin/summarize/<topic_id>
```

## Vercel

Deploy the web app from `apps/web`:

```bash
vercel --cwd apps/web
```

Set:

- `PUBLIC_API_BASE_URL`
- `TELEGRAM_BOT_USERNAME`

If the Vercel project is created from the repo root, set the root directory to `apps/web`.

## Telegram

1. Create a bot with BotFather.
2. Disable privacy mode.
3. Add the bot as admin to the forum-enabled supergroup.
4. Enable permissions to manage topics, send messages, and create invite links.
5. Create topics through the admin API or directly in Postgres.
