# Trust Reviews Website (Coolify / Docker)

This is a small Next.js site for viewing CommonTrust user reviews stored in PocketBase.

## Local dev

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

Then open http://localhost:3000

## PocketBase requirements

The website reads from PocketBase collections:

- `members`
- `reviews` (with `expand=reviewer_id,reviewee_id,deal_id`)
- `reputation`

You have 2 options:

1) Public-read collections (recommended for a public reviews site)
- Configure PocketBase API rules to allow read access for these collections.

2) Private collections with a server-only token
- Set `POCKETBASE_API_TOKEN` in container environment (do not use `NEXT_PUBLIC_*`).
- Keep collections private.

## Run with Docker Compose (same container stack)

From repository root:

```bash
docker-compose up -d --build
```

Services:
- Website: http://localhost:3000
- PocketBase: http://localhost:8090

The `web` service is configured to talk to PocketBase over the internal Docker network (`http://pocketbase:8090`).

## Deploy on Coolify

Use this repo as a Docker Compose deployment in Coolify.

1) Create a new **Docker Compose** resource in Coolify.
2) Point it to this repository.
3) Set environment variables in Coolify (from `.env` + web vars below):
- `POCKETBASE_URL` (for public links/sitemap; external URL recommended in production)
- Optional: `POCKETBASE_API_TOKEN` for private-read mode
- `POCKETBASE_ADMIN_TOKEN` for admin pages/actions
- `ADMIN_PASSWORD` and `ADMIN_COOKIE_SECRET` to enable `/admin`
4) Expose the `web` service on your desired domain (e.g. `trust.yourdomain.com`).
5) Deploy.

## Admin Page

There is a password-protected admin page at `/admin`.

It uses:
- `ADMIN_PASSWORD`
- `ADMIN_COOKIE_SECRET`

Without both env vars, `/admin` will not be accessible.

## Review Responses

If you want the reviewee to respond publicly on the ledger website, configure:
- `REVIEW_RESPONSE_SECRET` (shared with the bot; used to sign response links)

The bot will DM the reviewee a private response link after a review is filed.
