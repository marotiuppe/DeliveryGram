---
trigger: always_on
---

# Rule 5: Compliance & Safety Guardrails

- **Medicines:** prescription-required items cannot be checked out without an uploaded prescription verified by a licensed pharmacist; show safety disclaimers. Confirm current Indian regulations before launch.
- **Food:** restaurant/sweet/dairy stores must carry an FSSAI number field.
- **Fuel:** out of scope; do not build loose-fuel delivery.
- **Personal data:** store minimum PII (name, phone, address); never log phone numbers, prescriptions or addresses in plain logs.
- Any bulk data mutation or deletion requires explicit human approval first.
