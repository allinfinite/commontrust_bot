# CommonTrust

Reputation system for Telegram communities. Build trust through verified deals, peer reviews, and AI-assisted scam detection.

## Components

| Component | Description |
|---|---|
| `commontrust_bot` | Telegram bot — deals, reviews, reputation tracking, scam reports with AI triage |
| `commontrust_api` | FastAPI identity + reputation service |
| `web` | Next.js review/reputation website |
| PocketBase | Self-hosted database backend (schema in `pb_schema.json`) |

## Bot Commands

**Deals**
- `/newdeal description` — Create a private deal invite link (DM only; recommended)
- `/deal` (reply) `description` — Create a new deal in a group
- `/confirm deal_id` — Confirm a pending deal
- `/complete deal_id` — Mark a deal as completed
- `/review deal_id rating(1-5) [comment]` — Review a completed deal

**Reports**
- `/report @username` — Report a scammer (evidence collected in DM)
- `/report deal_id` — Report linked to a specific deal

**Reputation**
- `/reputation` — View your reputation stats
- `/mydeals` — List your deals

## Quick Start

1. Create env file:
```bash
cp .env.example .env
```

2. Set required variables in `.env`:
- `TELEGRAM_BOT_TOKEN` (reputation bot)
- `POCKETBASE_URL` + auth (`POCKETBASE_ADMIN_TOKEN` preferred, or email/password)
- `VENICE_API_KEY` (for AI report analysis)
- `COMMONTRUST_WEB_URL` (public website URL)
- `REVIEW_RESPONSE_SECRET` (generate with `openssl rand -hex 32`)

3. Run locally:
```bash
python3 -m pip install -e ".[dev]"

# Start PocketBase (port 8090)
# Import pb_schema.json via PocketBase admin UI

# Reputation bot
python3 -m commontrust_bot.main

# API server
python3 -m commontrust_api.main

# Web frontend
cd web && npm install && npm run dev
```

## Docker Deployment

`docker-compose.yml` runs all services:
- `pocketbase` (port 8090)
- `bot` (reputation bot)
- `api` (port 8000)
- `web` (port 3000)

```bash
docker compose up -d
```

### Coolify

Use `docker-compose.coolify.yml` as the compose file. Enable "Auto Deploy on Push" for continuous deployment.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | Reputation bot token from @BotFather |
| `POCKETBASE_URL` | Yes | PocketBase server URL (default: `http://localhost:8090`) |
| `POCKETBASE_ADMIN_TOKEN` | Yes* | PocketBase admin API token (preferred) |
| `POCKETBASE_ADMIN_EMAIL` | Alt* | PocketBase admin email (fallback auth) |
| `POCKETBASE_ADMIN_PASSWORD` | Alt* | PocketBase admin password (fallback auth) |
| `ADMIN_USER_IDS` | No | Telegram user IDs of bot admins (JSON list) |
| `VENICE_API_KEY` | No | Venice.ai API key for AI report analysis |
| `AI_MODEL` | No | Venice.ai model (default: `qwen3-next-80b`) |
| `COMMONTRUST_WEB_URL` | No | Public website URL for review links |
| `REVIEW_RESPONSE_SECRET` | No | HMAC secret for signed review response links |
| `COMMONTRUST_API_TOKEN` | No | API authentication token |

\* Either `POCKETBASE_ADMIN_TOKEN` or email/password pair required.

## Tests

```bash
python3 -m pytest -q
```
