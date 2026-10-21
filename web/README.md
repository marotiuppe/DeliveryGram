# DeliveryGram web (PWA)

React 18 + Vite 6 + TypeScript + Tailwind 4 + vite-plugin-pwa. Hindi first, English toggle. Installable, works offline for
browsing saved data and filling the cart. Every role has screens: customer, shopkeeper, rider, village helper (agent) and admin.

## Run
```
cd backend && pip install -r requirements-dev.txt && python -m alembic upgrade head && python -m scripts.demo_data   # dev demo data
python -m uvicorn app.main:app --port 8000
cd web && npm install && npm run dev        # http://localhost:5173 (proxies /api and /images to :8000)
npm test        # cart logic + i18n unit tests
npm run build   # typecheck + production build (the service worker only exists in the build: use `npm run preview` to test offline)
```
Demo logins (PIN 1234): customer 9876543210, shopkeeper 9000000001 (Sharma Kirana), rider 9000000003, village helper 9000000005, admin 9000000009. Prices in demo data are made up.

## Screens
Village -> shop list (by shop type) -> shop items -> cart (several shops allowed) -> search across shops (cheapest first) ->
checkout (ward + landmark address, payment per shop: cash / UPI / khata) -> order page (one delivery code, one bill per shop,
cancel a bill before the shop accepts it) -> khata (what I owe each shop, history). Login by phone + PIN or email code.

Shopkeeper screens (`/merchant`): incoming orders (new / preparing / ready; beeps on a new order; accept, reject, ready, hand over
a pickup order; open/closed switch), items (edit price, in/out of stock, add from the master catalog or your own item), khata book
(give khata with a limit, record money received or a counter sale, history, WhatsApp/SMS reminder links).

Rider screens (`/rider`): jobs list (cash from today's deliveries, trips on the way, ready for pickup, done today; beeps on a
new job), trip page (shops to collect from with phone and items, village + ward + landmark to deliver to, cash to collect at the door,
delivery code entry when required, "could not deliver" with confirmation).

Village-helper screens (`/agent`): register a villager (phone, name, random temporary PIN to hand over; the villager must set their
own PIN on first login), take an order for a villager (browse shops, cart, then checkout with the villager's phone, phone or WhatsApp,
shop pickup/delivery and payment per shop; the helper sees the delivery code to read out), and the helper's own order list.

Admin screens (`/admin`): dashboard (orders today, delivered sales, commission, delivery fees, khata dues, counts; "today" is the Indian
calendar day), shops (add; per-shop commission override; disable), people (add shopkeeper/rider/helper/admin; reset PIN; disable), villages
(add with numbered wards and delivery fee; add wards; change fee) and rates (commission and tax per shop type; apply to new orders only).
In production the first admin comes from `ADMIN_EMAIL` and logs in with an emailed code.

## Rural-network behaviour
- Cart is saved on the phone and survives reloads and dropped connections.
- API responses are cached; shops/items show the last saved copy when offline (a banner says so).
- Checkout needs a connection. Each cart gets one stable idempotency key, so a retry never creates a second order.
- Each screen is a separate chunk; first load is about 62 KB of JavaScript (gzip).

## Config
`VITE_API_URL` (empty in dev). On Render the API and web are separate origins: set `VITE_API_URL` on the web service and
`ALLOWED_ORIGINS` on the API.

## Dev note (Windows)
`python -m uvicorn` on Python 3.14 starts a child process that keeps port 8000 open if you only kill the parent. When stopping the dev
API, also stop its `multiprocessing.spawn` child, or the next run will talk to the stale server.

## Known gaps
Prescription medicines cannot be ordered in the app yet (no upload); the UI tells the user to phone the shop.
Item names on bills are stored in English. No push notifications; the order page polls every 15 seconds.
