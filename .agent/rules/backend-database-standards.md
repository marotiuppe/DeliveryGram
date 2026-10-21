---
trigger: always_on
---

# Rule 4: Backend & Database Standards

- Stack: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Postgres. Pydantic models for all request/response bodies; type hints everywhere.
- Tests (pytest) for every endpoint rule, run before declaring work done.

- Generic Store -> Catalog -> Order model; store kinds are config rows (`store_type`) with flags: `needs_prescription`, `has_time_slots`, `catalog_mode`, `commission_pct`, `tax_rule`.
- Money in integer paise. UTC timestamps. Soft-delete stores/products.
- Migrations must be reversible; never edit a migration that has shipped.
- Index foreign keys and fields used in listing filters (store_type, village/ward, status).
- Validate all input server-side; authorize per role (customer, merchant, rider, admin).
- Secrets in `.env` only; keep `.env.example` current.
