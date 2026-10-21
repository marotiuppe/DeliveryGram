# DeliveryGram backend

FastAPI + SQLAlchemy 2 + Alembic. Postgres on Render, SQLite locally.

## Local
```
cd backend
pip install -r requirements-dev.txt
python -m alembic upgrade head      # creates deliverygram.db
python -m app.seed                  # store types + 251 catalog items (idempotent)
python -m uvicorn app.main:app --reload
python -m pytest
```
Run the same tests on Postgres (needs Docker; needs a psycopg build for your Python, e.g. `pip install "psycopg[binary]"`):
```
docker run -d --name dg-pg -e POSTGRES_PASSWORD=test -e POSTGRES_DB=dg -p 55432:5432 postgres:16-alpine
docker exec dg-pg psql -U postgres -tAc "create database dg_tests;"
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:test@localhost:55432/dg_tests"
python -m pytest        # ~1 min; verified 2026-10-21: all tests pass on Postgres 16
$env:DATABASE_URL = "postgres://postgres:test@localhost:55432/dg"; python -m alembic upgrade head   # migrations up/down verified too
```
API docs: http://localhost:8000/docs

## Env vars
| Var | Default | Notes |
|---|---|---|
| DATABASE_URL | sqlite:///./deliverygram.db | Render injects Postgres; `postgres://` is normalised |
| ENV | development | `production` refuses the dev SECRET_KEY and never logs OTP codes |
| SECRET_KEY | dev value | signs login tokens; required in production |
| ADMIN_EMAIL | empty | `python -m app.seed` makes this email an admin; log in with an emailed OTP |
| BREVO_API_KEY + MAIL_FROM | empty | email through Brevo's HTTP API (works on Render's free plan). MAIL_FROM must be a sender verified in Brevo |
| SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD | empty | SMTP fallback (blocked on Render's free plan). With no email configured in development, OTP codes are logged to the console |
| MAIL_BACKEND | empty | `memory` collects emails in memory (tests) |
| KEEPALIVE_SECONDS / KEEPALIVE_URL | 300 / `RENDER_EXTERNAL_URL` | the API calls its own public `/health` this often on Render; `0` turns it off; does nothing locally |
| ALLOWED_ORIGINS | http://localhost:5173 | comma-separated CORS origins |
| DELIVERY_FEE_PAISE | 2000 | default fee; village row can override |
| MIN_ORDER_PAISE | 10000 | minimum subtotal |
| DELIVERY_CODE_THRESHOLD_PAISE | 200000 | UPI, prescription and orders at/above this need the 4-digit delivery code at handover |
| IMAGES_DIR | ../assets/catalog-images | served at /images |

## Roles
customer, merchant, rider, agent (village helper), admin. Self-registration (email OTP) always creates a customer;
staff roles are created by an admin. See [docs/OTP_AND_IDENTITY_RESEARCH.md](../docs/OTP_AND_IDENTITY_RESEARCH.md).

## Implemented
- Auth: email OTP (hashed, 10 min, 5 attempts, 3 requests/window), phone + PIN login with lockout, assisted
  registration by staff with forced PIN change, signed tokens.
- Catalog, stores, villages/wards, **cross-shop item search** (cheapest first).
- Merchant: price/availability editing, custom items, open/close, **khata book** (give credit with a limit, record
  counter sales and payments, see dues).
- **Checkout** `POST /api/checkout`: a cart from one or many shops becomes one Delivery with one Order (bill) per shop.
  Idempotent, prescription rule, whole-cart minimum, per-shop commission/tax snapshot, per-shop payment method
  (cod | upi | khata) with credit-limit check, delivery fee and delivery code once per delivery.
- Pickup at the shop: per-shop `fulfillment` (delivery | pickup); pickup bills carry no delivery fee and are handed over by the shop.
- Orders (bills): merchant accept/ready/reject, customer or agent cancel, pharmacist review for prescriptions.
- Rider view: deliveries carry shop names/phones, village/ward, creation time; the rider list is open jobs plus the rider's own history.
- Deliveries: rider claims when every live bill is READY, completes with the delivery code (when required),
  or fails it; delivery completion posts khata sales to each shop's ledger.
- Village helpers (agents): look up a phone, register a villager with a temporary PIN, order on behalf of a villager (phone/WhatsApp source).
- Admin (`/api/admin/*`, admin role only): stats, people (list/search/disable/reset PIN), shops (list/edit/disable, per-shop commission override), shop-type commission/tax rates, villages and wards. Roles cannot be changed through the API; an admin cannot disable themselves.
- Admin: create staff users and stores (medical stores need a drug licence number).

## Key endpoints
`GET /api/stores`, `/api/stores/{id}/items`, `/api/search/items?q=`, `POST /api/checkout`, `GET /api/deliveries`,
`POST /api/deliveries/{id}/claim|complete|fail`, `GET /api/orders`, `POST /api/orders/{id}/status`,
`GET /api/khata`, `PUT /api/merchant/stores/{id}/khata/{phone}`, `POST /api/merchant/stores/{id}/khata/{customer_id}/entries`.

## Not yet (next)
Prescription image upload, rider COD cash settlement, operator UI, WhatsApp/SMS channels, PIN reset flow,
per-IP rate limiting, khata reminders, the web app.
