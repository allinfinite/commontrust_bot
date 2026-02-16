# Open Trust Credit

Federated mutual-credit system for Telegram:
- `commontrust_credit_bot`: Telegram bot for credit commands (`/pay`, `/balance`, `/transactions`, admin ops)
- `commontrust_api`: FastAPI ledger + identity + optional hub proxy routing
- PocketBase schema in `pb_schema.json`

## Quick Start

1. Create env file:
```bash
cp .env.example .env
```

2. Set required variables in `.env`:
- `COMMONTRUST_API_TOKEN`
- `CREDIT_TELEGRAM_BOT_TOKEN`
- `POCKETBASE_URL`
- PocketBase auth (`POCKETBASE_ADMIN_TOKEN` preferred, or email/password)

3. Run locally:
```bash
python3 -m pip install -e ".[dev]"
python3 -m commontrust_api.main
python3 -m commontrust_credit_bot.main
```

## Coolify Deployment (Git Auto Deploy)

Use `docker-compose.coolify.yml` as the compose file in Coolify.

Services:
- `pocketbase`
- `api`
- `credit-bot`

Enable "Auto Deploy on Push" in Coolify so new commits on your selected Git branch redeploy automatically.

## Federation Modes

- `LEDGER_MODE=local` (default): bot uses local ledger in this deployment.
- `LEDGER_MODE=hub`: supports per-group remote ledger routing via:
  - `/setledger <base_url> <token>`
  - `/clearledger`

For hub mode, set:
- `HUB_REMOTE_TOKEN_ENCRYPTION_KEY` (Fernet key)

## Tests

```bash
python3 -m pytest -q
```

