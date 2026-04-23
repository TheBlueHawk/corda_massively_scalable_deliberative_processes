# CORDA Deliberation Platform — Technical README

> Grounding document for the coding agent. Read this before writing any code.

---

## Project Overview

A minimalist deliberation platform that:
1. Shows a topic on a website
2. Assigns users to parallel Telegram discussion groups (via forum topics)
3. Optionally summarizes each group's conversation and displays results on the website

No login. No cross-group idea routing. No complex NLP. Ship a working thing first.

---

## Tech Stack

| Layer         | Technology              | Host      |
| ------------- | ----------------------- | --------- |
| Frontend      | Next.js (TypeScript)    | Vercel    |
| Backend       | FastAPI (Python)        | Railway   |
| Database      | Neon Postgres           | Neon      |
| Bot           | python-telegram-bot v20 | Railway   |
| Summarization | Claude API              | Anthropic |

---

## Architecture

```
User → Next.js frontend
         ↓ deep link to Telegram bot
      Telegram Bot ←→ FastAPI backend ←→ Neon Postgres
                              ↓ (cron)
                       Summarization job → Claude API
                              ↓
                       Neon (summaries table)
                              ↑
                       Next.js /results page
```

### User Join Flow

```
1. User visits website → clicks "Join a Group"
2. Redirected to t.me/corda_bot?start=<topic_id>
3. Telegram opens the bot
4. Bot receives /start with topic_id
5. Bot upserts user in DB
6. Bot finds least-full forum topic for this deliberation topic
7. If all topics full → bot creates a new forum topic automatically
8. Bot sends user an invite link + welcome message
9. User joins the Telegram supergroup and participates in their thread
10. After closes_at → cron triggers summarization job
11. Results appear on /results page
```

---

## Database Schema (Neon Postgres)

Connect via standard Postgres connection string using `asyncpg`.

```sql
CREATE TABLE topics (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title       TEXT NOT NULL,
  description TEXT,
  status      TEXT DEFAULT 'active', -- active | closed
  closes_at   TIMESTAMPTZ,
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE groups (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  topic_id         UUID REFERENCES topics(id),
  thread_id        BIGINT UNIQUE NOT NULL, -- Telegram forum topic ID
  invite_link      TEXT NOT NULL,
  capacity         INT DEFAULT 8,
  member_count     INT DEFAULT 0           -- denormalized for fast assignment
);

CREATE TABLE users (
  telegram_user_id BIGINT PRIMARY KEY,
  username         TEXT,                   -- @handle, optional
  first_name       TEXT
);

CREATE TABLE memberships (
  telegram_user_id BIGINT REFERENCES users(telegram_user_id),
  group_id         UUID REFERENCES groups(id),
  joined_at        TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (telegram_user_id, group_id)
);

CREATE TABLE summaries (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  group_id   UUID REFERENCES groups(id) UNIQUE,
  content    TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

> No messages table. Messages are fetched from Telegram API at summarization time.
> The bot must be present in the supergroup from creation for history access to work.

---

## API Endpoints (FastAPI)

### Webhook (Telegram → Backend)
```
POST /webhook/telegram
```
Single entry point for all bot events. Handles:
- `/start <topic_id>` — upsert user, assign group, send invite link
- Chat member updates (user joined/left)

### Frontend-facing (public, read-only)
```
GET /topics/active
    → { id, title, description, closes_at }

GET /topics/{topic_id}/summaries
    → [{ group_id, content, created_at }, ...]
```

### Admin (protected by X-Admin-Key header)
```
POST /admin/summarize/{topic_id}
    → fetches Telegram history per group, calls Claude API, stores summaries
    → triggered by Railway cron or manually
```

> No user authentication. No JWT. Admin endpoints protected by a single
> X-Admin-KEY env variable checked as a request header.

---

## Telegram Bot Setup

### Prerequisites
- A regular Telegram account (no special account needed)
- python-telegram-bot==20.7

```bash
pip install python-telegram-bot==20.7
```

### One-time Setup Steps

**1. Create the bot via @BotFather**
- Open Telegram → search @BotFather → /newbot
- Save the token: looks like `7743920481:AAF_xK...`
- Run `/setprivacy` → Disabled (bot must read group messages)
- Run `/setjoingroups` → Enabled

**2. Create the Supergroup**
- Telegram → New Group → add one member (required, can remove after)
- Group Settings → Edit → enable **Topics** (converts to forum supergroup)
- Add your bot as Admin with permissions:
  - Manage topics ✅
  - Send messages ✅
  - Invite users via link ✅
  - Delete messages ✅

**3. Get the Supergroup ID**
- Add @userinfobot to the group temporarily — it prints the chat ID
- Looks like `-1001234567890` (note the negative sign)
- Remove @userinfobot after

**4. Register webhook (production)**
```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-app.railway.app/webhook/telegram"
```

### Environment Variables
```
TELEGRAM_BOT_TOKEN=7743920481:AAF_xK...
TELEGRAM_SUPERGROUP_ID=-1001234567890
DATABASE_URL=postgresql://...  # Neon connection string
CLAUDE_API_KEY=sk-ant-...
X_ADMIN_KEY=some-secret-string
```

### Bot Modes
- **Local dev**: use `app.run_polling()` — no public URL needed
- **Production**: use `app.run_webhook()` — requires Railway public URL

### Key Bot Logic

**Creating a forum topic (deliberation cell) programmatically:**
```python
topic = await bot.create_forum_topic(
    chat_id=TELEGRAM_SUPERGROUP_ID,
    name=f"Group {group_number}"
)
# topic.message_thread_id is your cell identifier — store this as thread_id
```

**Sending a message into a specific topic:**
```python
await bot.send_message(
    chat_id=TELEGRAM_SUPERGROUP_ID,
    message_thread_id=thread_id,
    text="Welcome! Your deliberation happens in this thread."
)
```

**Creating an invite link:**
```python
link = await bot.create_chat_invite_link(
    chat_id=TELEGRAM_SUPERGROUP_ID,
    member_limit=8
)
# Note: link lands user in supergroup generally, not directly in their topic
# Bot should immediately send a welcome message directing them to their thread
```

**Fetching message history for summarization:**
```python
# Use bot.get_chat_history or iterate updates filtered by message_thread_id
# Bot must have been present in the group since messages were sent
```

---

## Summarization Job

Triggered by cron (Railway) or `POST /admin/summarize/{topic_id}`:

1. Fetch all groups for topic from DB
2. For each group, fetch message history from Telegram API (filter by `thread_id`)
3. Call Claude API with prompt:
   ```
   Summarize the key points of agreement and disagreement from this deliberation.
   Be concise and neutral. Output in 3-5 bullet points.
   ```
4. Store result in `summaries` table
5. Frontend `/results` page reads from `summaries`

---

## Frontend Pages (Next.js)

| Route      | Purpose                                                     |
| ---------- | ----------------------------------------------------------- |
| `/`        | Show active topic, "Join a Group" button (deep link to bot) |
| `/results` | Show per-group summaries after deliberation closes          |

The join button is simply:
```
https://t.me/corda_bot?start=<topic_id>
```

No session, no cookies, no auth state on the frontend.

---

## Known Constraints & Decisions

| Constraint                                          | Decision                                                                        |
| --------------------------------------------------- | ------------------------------------------------------------------------------- |
| Bots can't create Telegram groups                   | Use supergroup with forum topics instead — fully automatable                    |
| Telegram Bot API has no getHistory                  | Bot must be present from group creation; fetch via updates                      |
| Invite links land in supergroup, not specific topic | Bot sends immediate welcome directing user to their thread                      |
| All forum topics visible in sidebar                 | Acceptable tradeoff for v1 — users can see other groups exist but not read them |
| No user authentication                              | Telegram user ID is the identity primitive — zero friction                      |
| Admin group creation                                | Topics (deliberation subjects) added manually via DB or admin endpoint          |

---

## Project Scope (v1)

**In scope:**
- Single active topic at a time
- Automatic group assignment via Telegram forum topics
- Optional end-of-deliberation summarization
- Public results page

**Explicitly out of scope for v1:**
- Cross-group idea routing or discursive stratification
- User profiles or authentication
- Real-time updates
- Multi-topic support
- Moderation tools