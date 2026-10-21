# Repo audit and base-code decision

Date: 2026-10-20. Repos cloned (shallow, read-only, never run) into `E:\Own-Projects\DeliveryGram-research\`, outside this project.

## 1. Kind-Unes/Flutter-6amMart-E-Commerce-Application
- **What it is:** a copy of the 6amMart **customer app only** (Flutter, GetX, 627 Dart files). No backend, no admin panel, no store app, no delivery app.
- **Licence:** none in the repo. The code is 6amTech's commercial product (CodeCanyon). A public GitHub copy is very likely unlicensed redistribution. Using it commercially risks takedown, and it comes with no support or updates. Last commit April 2024, app version 2.6.
- **Hard-wired to 6amTech's servers:** `lib/util/app_constants.dart` sets `baseUrl` to 6amTech's demo admin host. The app does nothing useful without a matching Laravel backend, which is not included.
- **Embedded third-party secrets:** Google Maps, Firebase and iOS API keys are committed (`android/app/google-services.json`, `AndroidManifest.xml`, `ios/.../AppDelegate.swift`). They belong to someone else. Do not reuse them, and do not copy these files into DeliveryGram.
- **Fit for DeliveryGram:** good feature coverage (modules incl. pharmacy and parcel, prescription handling in about 25 files, offline-capable cart via SharedPreferences, localization). Google Maps is used in about 34 files (`google_maps_flutter`, geolocator), so swapping to OSM means real work across address, checkout, store cards and registration.
- **Verdict:** do not use as the base.

## 2. sobol-sudo/grofresh
- **What it is:** a Next.js 15 / TypeScript / Redux Toolkit **web frontend demo** with 17 mock products and no backend. Not Flutter, not multi-vendor, not mobile-native.
- **Licence:** MIT (c) 2026 Alexander Kolesnik. Safe to read and borrow from.
- **Fit for DeliveryGram:** none as a base. Only the Feature-Sliced Design layout and the cart/checkout flow are useful as UI inspiration.
- **Verdict:** do not use as the base. Reference only.

## 3. What this means
Neither repo gives us the thing the PDF implied (a free, complete 4-app multi-vendor system). The real 6amMart is a **paid CodeCanyon product** that includes the Laravel backend + admin panel and source for the apps.

CodeCanyon prices seen in search snapshots (verify on the live page before buying; the sources disagreed):
- 6amMart main system: regular licence about USD 99; an extended licence was advertised at USD 399 (USD 199 on a 2024 promotion).
- Store app and delivery app appeared as separate add-ons (about USD 39-99 in snapshots).
Source: https://6amtech.com/blog/extended-license-50-percent-off-in-codecanyon/ and CodeCanyon listing snapshots.

Open-source alternatives checked (web search, not hands-on):
- **Nearby Shops** (open-source hyperlocal/grocery, self-hostable; repo deprecated in favour of a newer one): unverified for pharmacy and for current quality.
- **Enatega:** frontend open source, **backend proprietary** (paid).
- **Fleetbase Storefront:** open source but React Native, multi-vendor still in progress.
No free, complete, Flutter-based, multi-vendor, self-hosted system was found.

## 4. Options
| Option | Cost | Speed | Control | Main risk |
|---|---|---|---|---|
| **A. Buy 6amMart licence and customise** | about USD 100-400 plus add-ons (verify) | Fastest: all 4 components, pharmacy, parcel, payments, i18n | Full source of apps and backend; must replace Google Maps with OSM; Firebase dependency | Licence is per product/domain (read terms); upgrades overwrite customisations; heavy codebase |
| **B. Build lean ourselves** (Flutter + Laravel or Node + Postgres) | Dev time only | Slowest (months to MVP) | Total | Scope creep; reinventing payments, notifications, order lifecycle |
| **C. Hybrid: buy backend/admin only, build thin rural apps** | licence cost + dev time | Medium | Apps are exactly rural-fit | Must learn the 6amMart API |

## 5. Recommendation
**Option A**, after verifying on the live CodeCanyon page exactly what the licence includes (backend, admin, user/store/delivery app source) and its terms. For a solo, low-budget rural launch, buying a working system and adapting it beats rebuilding order management, pharmacy flow and payments. Plan the customisations in this order: (1) OSM maps + Ward/Landmark address, (2) Hindi-first UI and icons, (3) operator-entered WhatsApp/phone orders, (4) COD/UPI, (5) scheduled delivery batches.
Fall back to **B** if the licence terms do not allow the modifications we need, or if budget rules out any purchase.

## 6. Other findings that affect the plan
- **OSM:** the public OSM tile server is not meant for production traffic; use a tile provider (MapTiler, Carto, etc.) or self-host tiles. Set a real User-Agent / package name (generic ones get blocked). Nominatim also needs a User-Agent and rate limits, or self-host it. Source: https://docs.fleaflet.dev/tile-servers/using-openstreetmap-direct
- **Medicines:** online sale falls under the Drugs and Cosmetics Act 1940 / Rules 1945; a 2015 DCGI circular treats online and offline sale alike, so the seller needs a valid pharmacy licence. Draft e-pharmacy rules (2018) proposed registration, no narcotic/psychotropic/Schedule X sales, and data kept in India. I could not confirm whether final rules were notified. Get legal advice before launching the medical vertical. Sources: https://www.mondaq.com/india/food-and-drugs-law/747792 and https://indiacorplaw.in/2019/01/20/analyzing-draft-e-pharmacy-rules/
- **Cleanup:** delete `E:\Own-Projects\DeliveryGram-research\sixam` when done (it contains someone else's API keys and unlicensed code).

## 7. Decision (2026-10-20)
Owner chose to **build lean** with open-source tools only (Python backend, deployed on Render). See CLAUDE.md for the stack.
