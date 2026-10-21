---
trigger: always_on
---

# Rule 3: Rural Product Constraints

Every feature must hold up for low-literacy users on weak 3G with cheap Android phones.

- UI: Hindi/regional first, i18n keys for all strings, large touch targets, icons + photos over text.
- Network: offline-first cart, request retries with backoff, idempotency keys on order creation, small payloads.
- Address: Village + Ward + Landmark text always works without GPS. Map pins use OpenStreetMap only (no Google Maps/Geocoding).
- Payments: COD and UPI first.
- Shopkeepers: assume no digital inventory; support master-catalog toggles and photo/text orders.
- Keep the PWA bundle small (code-split per role, lazy images); justify every new dependency.
