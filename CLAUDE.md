# DeliveryGram

One hyperlocal marketplace app for **rural India**: villagers order from nearby local shops (kirana, footwear, general store, medical, sweet mart, cloth, restaurants, dairy, more). Big quick-commerce apps (Blinkit, Zepto, BigBasket) don't serve villages; this does. Sellers are local shopkeepers with little or no digital inventory.

Read [README.md](README.md), [docs/DEPLOY_RENDER.md](docs/DEPLOY_RENDER.md) and the notes under [docs/](docs/) before large changes. Agent rules live in [.agent/rules/](.agent/rules/). Early planning notes (a Flutter/Laravel/6amMart plan we dropped) are kept locally in `docs/archive/` and are deliberately not in git; if you find them, do not follow them.

## Components
1. **Customer app** (PWA): browse shops by category, order, track.
2. **Merchant app** (PWA): receive/accept/reject orders, toggle item availability and prices, mark ready.
3. **Delivery app** (PWA): batches, address/landmark, mark delivered, COD collection.
4. **Admin panel + API**: stores, commissions, zones, riders, operator-entered orders.

## Stack (decided 2026-10-20: build lean, nothing paid, all open source, deploy on Render)
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (SQLite locally) in [backend/](backend/).
- **Frontend ([web/](web/)):** one installable **PWA** (React + Vite + TypeScript + Tailwind, `vite-plugin-pwa`) with code-split role routes (customer, merchant, rider, admin). Chosen over native apps: no Play Store, shareable by WhatsApp link, offline cart via service worker + IndexedDB, one codebase.
- **Maps:** Leaflet / `react-leaflet` with OpenStreetMap data. The public OSM tile server is not for production traffic: use a tile provider or self-host, and set a real User-Agent.
- **Hosting:** Render via [render.yaml](render.yaml): API web service + static web app. **Database: Neon** (non-expiring free Postgres, `DATABASE_URL` env var), not Render's 30-day free Postgres. **Email: Brevo HTTP API** (`BREVO_API_KEY`, `MAIL_FROM`; Render's free plan blocks SMTP). **Keep-awake:** the API pings its own public `/health` every 5 minutes (`app/keepalive.py`). Pattern taken from the Program-Practice project. All credentials are environment variables; see docs/DEPLOY_RENDER.md.
- **Render free-tier facts (checked 2026-10-21 against Render's docs/changelog):** web services spin down after 15 min idle (about a minute to wake); free Postgres expires 30 days after creation (14-day grace, then deleted); **free web services block outbound SMTP (ports 25/465/587)**, so email login codes need an HTTPS email API (SendGrid/Mailgun/Postmark/Brevo etc.), not SMTP; the local filesystem is lost on spin-down, so uploads (prescriptions) need external storage. Move to paid instances before the pilot.
- Postgres compatibility verified locally with Docker (Postgres 16): migrations up/down/up, `alembic check` clean, full test suite passes. `psycopg[binary]==3.2.3` is pinned for Render's Python 3.12 (it has no wheel for Python 3.14 on dev PCs; install a newer psycopg locally).
- Third-party repos (6amMart copy, Grofresh) were audited and rejected: see [docs/REPO_AUDIT.md](docs/REPO_AUDIT.md). Do not vendor them.

## Domain model rules
- Generic **Store -> Catalog -> Order** model. Shop kinds are rows in a `store_type` config, not hardcoded verticals.
- Behaviour flags per store type: `needs_prescription`, `has_time_slots`, `catalog_mode` (structured | photo_or_text | fixed_menu), `commission_pct`, `tax_rule`.
- One checkout across stores; pharmacy items require prescription upload + pharmacist verification and show safety disclaimers.
- Fuel/petrol delivery is out of scope (regulated, unsafe) unless explicitly re-decided.

## Customer flow and money rules
- Customer picks a **shop**, sees only that shop's items, adds to cart. If an item is missing they **search** (`/api/search/items`) and can buy it from any open shop; the cart can hold several shops.
- **One checkout = one Delivery** (one rider, one address, one delivery fee, one handover code) containing **one Order (bill) per shop**. Each shop has its own bill, tax, commission and payment method (cod | upi | khata). Min order applies to the whole cart.
- A rider claims a delivery only when every live shop order is READY, then one handover completes all bills. Rejected/cancelled bills drop out; the rider sees `cash_to_collect_paise` (cod bills + delivery fee).
- **Pickup:** each shop bill is `delivery` (rider) or `pickup` (customer collects; the shop marks it handed over, with the delivery code if one is required). Delivery fee and cash-to-collect only count rider bills; a pickup-only cart pays no delivery fee.
- **Khata** (village credit book): per shop per customer account with a credit limit set by the shopkeeper; ledger of SALE (+) and PAYMENT (-) entries. Khata orders count against the limit (balance + pending khata orders) from placement, and are posted to the ledger only on delivery. The delivery fee is not on khata. Shopkeepers also record counter sales and payments, and send reminders as free WhatsApp/SMS tap-to-send links. Khata is between shop and customer; the platform does not guarantee it.

## Rural constraints (design drivers)
- **Language:** Hindi/regional first, i18n from day one, icon-heavy UI, minimal typing, voice search later.
- **Orders without the app:** WhatsApp/phone orders entered by an operator in the admin panel are a first-class flow.
- **Payments:** Cash on Delivery and UPI. No card-first flows.
- **Addresses:** Village + Ward + Landmark text is the source of truth; GPS pin is optional and may be inaccurate.
- **Network:** assume weak 3G. Offline cart caching, small payloads, retries with backoff, idempotent order submission.
- **Delivery:** scheduled batches per village cluster, zone/distance fee, minimum order value. Not 10-minute delivery.
- **Bundle size:** keep the PWA small (code-split per role, lazy-load images, WebP thumbnails, justify every dependency).

## Conventions
- Secrets only in `.env` (never committed); keep `.env.example` current.
- Money as integer paise, never floats. Timestamps in UTC, display in IST.
- Every migration reversible. Every public API change documented in `docs/`.
- Prefer small, reviewable changes; match surrounding code style.

## Commands
```
cd backend
pip install -r requirements-dev.txt
python -m alembic upgrade head && python -m app.seed
python -m uvicorn app.main:app --reload     # http://localhost:8000/docs
python -m pytest
```
Web: `cd web && npm install && npm run dev` (needs the API on :8000; `python -m scripts.demo_data` seeds a dev village). `npm test`, `npm run build`. See web/README.md.

## Current status
Done: master catalog (251 items, 182 images), data model + migrations 0001-0003, catalog/search/store APIs, auth (email OTP + phone/PIN + assisted registration), merchant inventory, multi-shop checkout with one delivery per cart, delivery code, khata ledger, 116 backend tests + 20 web unit tests, Render blueprint (API, web, Postgres). Customer and shopkeeper web screens built and browser-tested (Edge): shops, cart, cross-shop search, pickup/delivery, khata checkout, order page, offline; shopkeeper orders (with beep), items/prices, khata book with reminders; rider jobs and trip (pickup shops, drop address, cash to collect, delivery code, fail); village-helper (agent) screens (register a villager with a temporary PIN, order for a villager by phone/WhatsApp, helper's order list); admin screens (dashboard numbers, people, shops with per-shop commission, villages and wards with delivery fee, commission/tax rates per shop type).
Identity decision: OTP is email-only for now; most villagers lack email/WhatsApp, so staff-assisted PIN registration and staff-entered phone orders are first-class. See [docs/OTP_AND_IDENTITY_RESEARCH.md](docs/OTP_AND_IDENTITY_RESEARCH.md).
Next: first real deploy to Render (docs/DEPLOY_RENDER.md), rider cash settlement (what each rider owes the platform), prescription upload, delivery windows with order cut-offs, UPI link in khata reminders. See docs/SIMILAR_APPS.md.
Open decision: commission basis is chosen per shop ("order based" vs "customer based"); "customer based" is not yet defined, so only order-based commission exists in code.
Open risks: medicine-selling legality (needs legal advice), image attribution screen (CC BY), commission/tax rates in `app/seed.py` are placeholders (set the real ones in the admin Rates screen), Render free-tier limits and SMTP availability (verify).
