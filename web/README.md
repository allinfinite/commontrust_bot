# Trust Reviews Website (Vercel)

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
- Set `POCKETBASE_API_TOKEN` in Vercel env (do not use `NEXT_PUBLIC_*`).
- Keep collections private.

## Deploy to Vercel (trust.bigislandbulletin.com)

1) Create a new Vercel project and import this repo.
2) In the Vercel project settings set **Root Directory** to `web`.
3) Add env vars:
- `POCKETBASE_URL` = your PocketBase base URL (example: `https://pb.bigislandbulletin.com`)
- Optional: `POCKETBASE_API_TOKEN` if using private collections.
4) Deploy.
5) Add the custom domain `trust.bigislandbulletin.com` to the project in Vercel.
6) Update DNS for `bigislandbulletin.com`:
- Create a `CNAME` record for `trust` pointing to the target Vercel shows in the domain setup (often `cname.vercel-dns.com`).

## Admin Page

There is a password-protected admin page at `/admin`.

It uses:
- `ADMIN_PASSWORD` (set in Vercel env as sensitive)
- `ADMIN_COOKIE_SECRET` (random secret, set in Vercel env as sensitive)

Without both env vars, `/admin` will not be accessible.
