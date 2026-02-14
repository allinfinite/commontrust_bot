# CommonTrust Bot

A Telegram bot for federated reputation and mutual credit systems with PocketBase backend.

## Features

- **Reputation System**: Build trust through verified deals and peer reviews
- **Mutual Credit**: Create community currencies within Telegram groups
- **Double-Entry Ledger**: Proper accounting with zero-sum verification
- **Admin Tools**: Sanctions, verification, and credit management

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (recommended)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone <repo-url>
cd rep-bot
```

2. Create environment file:
```bash
cp .env.example .env
```

3. Edit `.env` with your configuration:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
# Preferred: create a PocketBase API key / admin token and use it (avoid storing a password)
POCKETBASE_ADMIN_TOKEN=your_admin_token_or_api_key
# Fallback:
POCKETBASE_ADMIN_EMAIL=admin@example.com
POCKETBASE_ADMIN_PASSWORD=your_secure_password
ADMIN_USER_IDS=[your_telegram_user_id]
```

4. Start services:
```bash
docker-compose up -d
```

5. Initialize PocketBase schema:
```bash
# Create a PocketBase admin token (see scripts/pb_create_admin_token.py)
# Then create the collections defined in pb_schema.json:
python3 scripts/pb_setup_db.py
```

### Manual Installation

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -e .
```

3. Set up PocketBase:
   - Download from [pocketbase.io](https://pocketbase.io)
   - Run `./pocketbase serve`
   - Create admin account at http://localhost:8090/_/
   - Create the collections defined in `pb_schema.json`:
     - `python3 scripts/pb_setup_db.py`

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. Run the bot:
```bash
python -m commontrust_bot.main
```

## Commands

### Basic Commands
| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show all commands |

### Deal Commands
| Command | Description |
|---------|-------------|
| `/deal <description>` | Create a deal (reply to user) |
| `/confirm <deal_id>` | Confirm a pending deal |
| `/complete <deal_id>` | Mark a deal as completed |
| `/review <deal_id> <rating> [comment]` | Review a completed deal |
| `/cancel <deal_id> [reason]` | Cancel a deal |

### Credit Commands
| Command | Description |
|---------|-------------|
| `/pay <amount> [description]` | Send credits (reply to user) |
| `/balance` | Check your credit balance |
| `/transactions` | View recent transactions |

### Reputation Commands
| Command | Description |
|---------|-------------|
| `/reputation` | View your reputation |
| `/mydeals` | List your deals |
| `/stats` | View your statistics |
| `/pending` | View pending deals |
| `/active` | View active deals |

### Admin Commands
| Command | Description |
|---------|-------------|
| `/enable_credit [name] [symbol]` | Enable mutual credit in group |
| `/warn @user <reason>` | Warn a user |
| `/mute @user <hours> <reason>` | Mute a user |
| `/ban @user <reason>` | Ban a user |
| `/freeze @user <reason>` | Freeze credit account |
| `/verify @user` | Verify a member |
| `/setcredit @user <amount>` | Set user's credit limit |
| `/checkzero` | Verify zero-sum ledger |

## PocketBase Collections

The bot requires these collections (import `pb_schema.json`):

### members
- `telegram_id` (number, unique)
- `username` (text)
- `display_name` (text)
- `joined_at` (datetime)
- `verified` (bool)

### groups
- `telegram_id` (number, unique)
- `title` (text)
- `mc_enabled` (bool)

### deals
- `initiator_id` (relation to members)
- `counterparty_id` (relation to members)
- `group_id` (relation to groups)
- `description` (text)
- `initiator_offer` (text)
- `counterparty_offer` (text)
- `status` (select: pending, confirmed, in_progress, completed, cancelled, disputed)

### reviews
- `deal_id` (relation to deals)
- `reviewer_id` (relation to members)
- `reviewee_id` (relation to members)
- `rating` (number, 1-5)
- `comment` (text)
- `outcome` (select: positive, neutral, negative)

### reputation
- `member_id` (relation to members, unique)
- `verified_deals` (number)
- `avg_rating` (number)

### mc_groups
- `group_id` (relation to groups)
- `currency_name` (text)
- `currency_symbol` (text)

### mc_accounts
- `mc_group_id` (relation to mc_groups)
- `member_id` (relation to members)
- `balance` (number)
- `credit_limit` (number)

### mc_transactions
- `mc_group_id` (relation to mc_groups)
- `payer_id` (relation to members)
- `payee_id` (relation to members)
- `amount` (number)
- `description` (text)

### mc_entries
- `transaction_id` (relation to mc_transactions)
- `account_id` (relation to mc_accounts)
- `amount` (number)
- `balance_after` (number)

### sanctions
- `member_id` (relation to members)
- `group_id` (relation to groups)
- `type` (select: warning, mute, ban, freeze)
- `reason` (text)
- `expires_at` (datetime)
- `is_active` (bool)

## Website (Reviews Viewer)

There is a small Next.js website for browsing reviews at `web/` (designed for Vercel).

- Setup instructions: `web/README.md`

## How It Works

### Reputation System
1. Users create deals with other members
2. Counterparty confirms the deal
3. Both parties complete the deal
4. Each party can leave a review (1-5 stars)
5. Reputation is calculated from verified deals and average ratings

### Mutual Credit System
1. Admin enables credit in a group with `/enable_credit`
2. Users get a credit account with a base limit
3. Credit limit increases with verified deals
4. Users can pay each other with `/pay`
5. Double-entry ledger ensures zero-sum accounting

### Credit Limit Formula
```
credit_limit = base_limit + (verified_deals * credit_per_deal)
```

Default: `100 + (deals * 50)`

## Development

### Running Tests
```bash
pip install -e ".[dev]"
pytest
```

### Code Formatting
```bash
ruff format .
ruff check .
```

### Type Checking
```bash
mypy commontrust_bot
```

## Architecture

```
commontrust_bot/
├── __init__.py          # Package info
├── config.py            # Settings and configuration
├── main.py              # Bot entry point
├── pocketbase_client.py # Database client wrapper
├── handlers/            # Telegram command handlers
│   ├── __init__.py
│   ├── admin.py         # Admin commands
│   ├── basic.py         # /start, /help
│   ├── credit.py        # Credit commands
│   ├── deal.py          # Deal commands
│   └── reputation.py    # Reputation commands
└── services/            # Business logic
    ├── __init__.py
    ├── deal.py          # Deal management
    ├── mutual_credit.py # Credit system
    └── reputation.py    # Reputation calculations
```

## License

MIT License
