# DeliveryGram

One app for a whole village: order from nearby shops (kirana, medical, dairy, sweets, cloth, general stores) with home
delivery or pickup. Built for low-end phones, weak networks and first-time smartphone users.

Big quick-commerce apps do not serve villages. DeliveryGram lets local shops sell to their own village, with the things
village shops actually need: **khata** (credit), helpers who can order for people without smartphones, and a Hindi-first app
that still works when the network drops.

## What makes it different
- **Many shops, one delivery.** One cart can hold items from several shops. Each shop gets its own bill; one rider brings everything.
- **Khata (credit book).** Shops give villagers credit with a limit, record payments and counter sales, and send WhatsApp/SMS reminders as free tap-to-send links.
- **Pickup or delivery, per shop.** Pickup bills carry no delivery fee.
- **Built for villages.** Hindi first with an English toggle, ward + landmark addresses instead of exact GPS, offline cart, small downloads, large touch targets.
- **For people without smartphones too.** Village helpers register villagers (temporary PIN) and place orders by phone or WhatsApp.
- **Five roles.** Villager, shopkeeper, rider, village helper, admin: each with its own screens.
- **Safe handover.** A 4-digit delivery code is required for UPI, prescription and high-value orders; small cash orders skip it.

## Stack
| Part | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (SQLite for local development) |
| Web app | React 18, Vite, TypeScript, Tailwind 4, installable PWA with offline support |
| Hosting | Render (API + static web app), Neon (Postgres), Brevo (email over HTTPS) |
| Maps | OpenStreetMap / Leaflet (planned; addresses work without maps today) |

## Project layout
```
backend/   FastAPI app, migrations (Alembic), tests, dev demo data      -> backend/README.md
web/       React PWA: customer, shopkeeper, rider, helper, admin screens -> web/README.md
assets/    Catalog item images (WebP, credited in docs/IMAGE_CREDITS.md)
docs/      Master catalog, research notes, deployment guide, image credits
render.yaml  Render blueprint (API + web)
CLAUDE.md  Project notes and rules for contributors and AI assistants
```

## Run it locally (Windows PowerShell)
You need Python 3.12+ and Node 22+.
```powershell
# 1) Backend: install, create the database, load dev demo data, start the API on http://localhost:8000
cd backend
pip install -r requirements-dev.txt
$env:DATABASE_URL = "sqlite:///./demo.db"
python -m alembic upgrade head
python -m scripts.demo_data
python -m uvicorn app.main:app --reload --port 8000

# 2) Web app (second terminal): http://localhost:5173
cd web
npm install
npm run dev
```
Set `DATABASE_URL` in **every** terminal where you start the backend, or it will use a different, empty database.

Dev demo logins (PIN `1234`): villager `9876543210`, shopkeeper `9000000001`, rider `9000000003`, village helper `9000000005`, admin `9000000009`.
Prices in the demo data are made up. These accounts exist only after `scripts.demo_data` and must never be created in production.

## Tests
```powershell
cd backend; python -m pytest        # 116 tests (SQLite in memory; also verified on PostgreSQL 16, see backend/README.md)
cd web;     npm test                # 20 unit tests
cd web;     npm run build           # type-check + production build
```

## Deploy
See [docs/DEPLOY_RENDER.md](docs/DEPLOY_RENDER.md): Neon database, Brevo email, Render blueprint, environment variables and the
free-plan limits to watch. **No secret is ever stored in this repository**; keys and passwords are environment variables.

## Status
Backend and all five role screens are built and browser-tested.
**Not built yet:** prescription upload (so prescription medicines cannot be ordered in the app yet), rider cash settlement,
delivery windows with order cut-off times, UPI payment links, map-based address pin.
Selling medicines online has legal requirements in India; get advice before enabling that part.
Commission and tax rates in the seed data are placeholders: set the real ones in the admin **Rates** screen.

## Documentation
- [backend/README.md](backend/README.md) and [web/README.md](web/README.md): running, configuration, endpoints and screens
- [docs/DEPLOY_RENDER.md](docs/DEPLOY_RENDER.md): deployment checklist
- [docs/OTP_AND_IDENTITY_RESEARCH.md](docs/OTP_AND_IDENTITY_RESEARCH.md): login and OTP options for rural users
- [docs/SIMILAR_APPS.md](docs/SIMILAR_APPS.md): what we learned from similar apps
- [docs/REPO_AUDIT.md](docs/REPO_AUDIT.md): why existing open-source repos were not used as a base
- [docs/IMAGE_CREDITS.md](docs/IMAGE_CREDITS.md): attribution for catalog images (required by their licences)

## License
No licence has been chosen yet, so all rights are reserved. Catalog images come from Wikimedia Commons under their own licences
(see docs/IMAGE_CREDITS.md).
