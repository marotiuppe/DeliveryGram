# Deploying to Render (free plan) - what to set up and what to watch

Pattern copied from the Program-Practice project: Render free web service + **Neon** Postgres + **Brevo** email (HTTP API) +
a **self-ping** every 5 minutes. All secrets are environment variables, set in the Render dashboard, never in git.

## One-time setup
1. **Neon** (neon.tech, free): create a project and database, copy the connection string (`postgresql://...?sslmode=require`).
   Neon does not expire like Render's free Postgres (30 days). It may sleep when idle; the first request after that is a little slower.
2. **Brevo** (brevo.com, free, about 300 emails/day): create an API key (Settings -> SMTP & API) and **verify your sender address**
   (Senders, domains & dedicated IPs). An unverified sender is rejected.
3. **GitHub**: push this repo (`git init`, commit, create the repo, push). `.env`, `*.db` and `node_modules` are already ignored.
4. **Render**: New -> Blueprint -> pick the repo (it reads `render.yaml`). Fill the `sync: false` values:

| Variable | Service | Value |
|---|---|---|
| `DATABASE_URL` | API | the Neon connection string |
| `ADMIN_EMAIL` | API | your email; you log in with a code sent there, then create everyone else in the admin screens |
| `BREVO_API_KEY` | API | the Brevo API key |
| `MAIL_FROM` | API | verified sender, e.g. `DeliveryGram <orders@yourdomain.com>` |
| `ALLOWED_ORIGINS` | API | the web app URL (set after the web service has a URL) |
| `VITE_API_URL` | Web | the API URL, no trailing slash |
| `SECRET_KEY`, `ENV`, `PYTHON_VERSION`, `KEEPALIVE_SECONDS` | API | already in `render.yaml` |

5. Open the web app, log in as admin (email code), then check **Admin -> Dashboard -> System**: database should say `postgresql`,
   email should say `Brevo HTTP API, sending as ...` with no error, and keep-alive should say enabled.

## What each piece does
- `app/mailer.py`: Brevo HTTP API (works on the free plan), SMTP fallback (blocked on free Render), `MAIL_BACKEND=memory` for tests.
  The last email error is shown on the System card, so a wrong key or unverified sender is visible at once.
- `app/keepalive.py`: calls the API's own public `/health` every `KEEPALIVE_SECONDS` (default 300). `/health` does not touch the database,
  so Neon can still sleep. Local runs do nothing because `RENDER_EXTERNAL_URL` is only set on Render.

## Limits you must know (checked 2026-10-21)
- **750 free instance hours per workspace per month, shared by ALL free web services.** One always-awake service uses about 720-744
  hours, so it just fits. **A second always-awake free service in the same workspace (for example another project that also pings itself)
  pushes the total over 750 and Render suspends all free services until the next month.** Keep only one always-awake free service per
  workspace, use a separate Render account/workspace, or move this API to a paid instance (recommended for the real pilot).
- The self-ping only works while the service is awake. A deploy or restart still cold-starts it (about a minute).
- The free web service's disk is wiped on every restart. Do not store uploads on it (prescription upload will need external storage).
- Render's static site (the web app) does not sleep and does not use instance hours.
- Brevo's free plan caps emails per day; OTP emails count. Check the number against your expected logins.

## Backups
Neon keeps a short history (Branches -> Restore). For a real backup, dump the database regularly; the Program-Practice project has a
`tools/db_backup.py` (JSON dump and restore) that is worth porting once there is real data. Test one restore before relying on it.
