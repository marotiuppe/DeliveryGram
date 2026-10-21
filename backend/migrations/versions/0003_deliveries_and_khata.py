"""deliveries (one rider per checkout, many shop orders) and khata ledger

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# Columns that move from orders to deliveries.
MOVED = ("idempotency_key", "delivery_fee_paise", "lat", "lon", "rider_id", "delivery_code", "delivery_code_required")
DELIVERY_STATUS = {"DELIVERED": "DELIVERED", "OUT_FOR_DELIVERY": "OUT_FOR_DELIVERY", "FAILED": "FAILED", "REJECTED": "CANCELLED", "CANCELLED": "CANCELLED"}


def upgrade() -> None:
    op.create_table(
        "deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("placed_by_id", sa.Integer(), nullable=False),
        sa.Column("contact_phone", sa.String(length=15), nullable=False),
        sa.Column("village_id", sa.Integer(), nullable=False),
        sa.Column("ward_id", sa.Integer(), nullable=True),
        sa.Column("landmark", sa.String(length=200), nullable=False),
        sa.Column("address_details", sa.Text(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("delivery_fee_paise", sa.Integer(), nullable=False),
        sa.Column("delivery_code", sa.String(length=4), nullable=False),
        sa.Column("delivery_code_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rider_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["placed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["village_id"], ["villages.id"]),
        sa.ForeignKeyConstraint(["ward_id"], ["wards.id"]),
        sa.ForeignKeyConstraint(["rider_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_deliveries_idempotency_key"),
    )
    op.create_index("ix_deliveries_customer_id", "deliveries", ["customer_id"])
    op.create_index("ix_deliveries_rider_id", "deliveries", ["rider_id"])
    op.create_index("ix_deliveries_status", "deliveries", ["status"])

    op.create_table(
        "khata_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("credit_limit_paise", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "customer_id", name="uq_khata_store_customer"),
    )
    op.create_index("ix_khata_accounts_store_id", "khata_accounts", ["store_id"])
    op.create_index("ix_khata_accounts_customer_id", "khata_accounts", ["customer_id"])

    op.create_table(
        "khata_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["khata_accounts.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "kind", name="uq_khata_order_kind"),
    )
    op.create_index("ix_khata_entries_account_id", "khata_entries", ["account_id"])

    with op.batch_alter_table("orders") as b:
        b.add_column(sa.Column("delivery_id", sa.Integer(), nullable=True))

    # Backfill: every existing order becomes its own single-shop delivery.
    conn = op.get_bind()
    deliveries = sa.table(
        "deliveries", *[sa.column(c) for c in (
            "idempotency_key", "customer_id", "placed_by_id", "contact_phone", "village_id", "ward_id", "landmark", "address_details",
            "lat", "lon", "delivery_fee_paise", "delivery_code", "delivery_code_required", "rider_id", "status", "created_at")]
    )
    rows = conn.execute(sa.text(
        "SELECT id, idempotency_key, customer_id, placed_by_id, contact_phone, village_id, ward_id, landmark, address_details, lat, lon, "
        "delivery_fee_paise, delivery_code, delivery_code_required, rider_id, status, created_at FROM orders"
    )).mappings().all()
    for r in rows:
        conn.execute(deliveries.insert().values(
            idempotency_key=r["idempotency_key"], customer_id=r["customer_id"], placed_by_id=r["placed_by_id"], contact_phone=r["contact_phone"],
            village_id=r["village_id"], ward_id=r["ward_id"], landmark=r["landmark"], address_details=r["address_details"], lat=r["lat"], lon=r["lon"],
            delivery_fee_paise=r["delivery_fee_paise"], delivery_code=r["delivery_code"], delivery_code_required=r["delivery_code_required"],
            rider_id=r["rider_id"], status=DELIVERY_STATUS.get(r["status"], "OPEN"), created_at=r["created_at"],
        ))
        new_id = conn.execute(sa.text("SELECT id FROM deliveries WHERE idempotency_key = :k"), {"k": r["idempotency_key"]}).scalar_one()
        conn.execute(sa.text("UPDATE orders SET delivery_id = :d WHERE id = :o"), {"d": new_id, "o": r["id"]})

    op.drop_index("ix_orders_rider_id", table_name="orders")
    with op.batch_alter_table("orders") as b:
        b.drop_constraint("fk_orders_rider", type_="foreignkey")
    with op.batch_alter_table("orders") as b:
        for col in MOVED:
            b.drop_column(col)
        b.alter_column("delivery_id", existing_type=sa.Integer(), nullable=False)
        b.create_foreign_key("fk_orders_delivery", "deliveries", ["delivery_id"], ["id"])
        b.create_index("ix_orders_delivery_id", ["delivery_id"])


def downgrade() -> None:
    with op.batch_alter_table("orders") as b:
        b.add_column(sa.Column("idempotency_key", sa.String(length=64), nullable=True))
        b.add_column(sa.Column("delivery_fee_paise", sa.Integer(), nullable=True))
        b.add_column(sa.Column("lat", sa.Float(), nullable=True))
        b.add_column(sa.Column("lon", sa.Float(), nullable=True))
        b.add_column(sa.Column("rider_id", sa.Integer(), nullable=True))
        b.add_column(sa.Column("delivery_code", sa.String(length=4), nullable=True))
        b.add_column(sa.Column("delivery_code_required", sa.Boolean(), nullable=False, server_default=sa.false()))

    conn = op.get_bind()
    # The delivery fee and the checkout key go on the first order of each delivery; other orders get a derived key and fee 0.
    conn.execute(sa.text(
        "UPDATE orders SET "
        "idempotency_key = (SELECT d.idempotency_key FROM deliveries d WHERE d.id = orders.delivery_id) || "
        "  CASE WHEN orders.id = (SELECT MIN(o2.id) FROM orders o2 WHERE o2.delivery_id = orders.delivery_id) THEN '' ELSE '-' || orders.id END, "
        "delivery_fee_paise = CASE WHEN orders.id = (SELECT MIN(o2.id) FROM orders o2 WHERE o2.delivery_id = orders.delivery_id) "
        "  THEN (SELECT d.delivery_fee_paise FROM deliveries d WHERE d.id = orders.delivery_id) ELSE 0 END, "
        "lat = (SELECT d.lat FROM deliveries d WHERE d.id = orders.delivery_id), "
        "lon = (SELECT d.lon FROM deliveries d WHERE d.id = orders.delivery_id), "
        "rider_id = (SELECT d.rider_id FROM deliveries d WHERE d.id = orders.delivery_id), "
        "delivery_code = (SELECT d.delivery_code FROM deliveries d WHERE d.id = orders.delivery_id), "
        "delivery_code_required = (SELECT d.delivery_code_required FROM deliveries d WHERE d.id = orders.delivery_id)"
    ))

    op.drop_index("ix_orders_delivery_id", table_name="orders")
    with op.batch_alter_table("orders") as b:
        b.drop_constraint("fk_orders_delivery", type_="foreignkey")
    with op.batch_alter_table("orders") as b:
        b.drop_column("delivery_id")
        b.alter_column("idempotency_key", existing_type=sa.String(length=64), nullable=False)
        b.alter_column("delivery_fee_paise", existing_type=sa.Integer(), nullable=False)
        b.alter_column("delivery_code", existing_type=sa.String(length=4), nullable=False)
        b.create_unique_constraint("uq_orders_idempotency_key", ["idempotency_key"])
        b.create_foreign_key("fk_orders_rider", "users", ["rider_id"], ["id"])
        b.create_index("ix_orders_rider_id", ["rider_id"])

    op.drop_index("ix_khata_entries_account_id", table_name="khata_entries")
    op.drop_table("khata_entries")
    op.drop_index("ix_khata_accounts_customer_id", table_name="khata_accounts")
    op.drop_index("ix_khata_accounts_store_id", table_name="khata_accounts")
    op.drop_table("khata_accounts")
    op.drop_index("ix_deliveries_status", table_name="deliveries")
    op.drop_index("ix_deliveries_rider_id", table_name="deliveries")
    op.drop_index("ix_deliveries_customer_id", table_name="deliveries")
    op.drop_table("deliveries")
