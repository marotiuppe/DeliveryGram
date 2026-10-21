"""auth users otp and order workflow

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "otp_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("code_hash", sa.String(length=100), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_otp_codes_email", "otp_codes", ["email"])

    with op.batch_alter_table("users") as b:
        b.add_column(sa.Column("email", sa.String(length=120), nullable=True))
        b.add_column(sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))
        b.add_column(sa.Column("pin_hash", sa.String(length=200), nullable=True))
        b.add_column(sa.Column("pin_must_change", sa.Boolean(), nullable=False, server_default=sa.false()))
        b.add_column(sa.Column("failed_pin_attempts", sa.Integer(), nullable=False, server_default="0"))
        b.add_column(sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
        b.alter_column("phone", existing_type=sa.String(length=15), nullable=True)
        b.create_unique_constraint("uq_users_email", ["email"])

    # New NOT NULL order columns: add nullable, backfill any existing rows, then tighten.
    with op.batch_alter_table("orders") as b:
        b.add_column(sa.Column("placed_by_id", sa.Integer(), nullable=True))
        b.add_column(sa.Column("contact_phone", sa.String(length=15), nullable=True))
        b.add_column(sa.Column("rider_id", sa.Integer(), nullable=True))
        b.add_column(sa.Column("delivery_code", sa.String(length=4), nullable=True))
        b.add_column(sa.Column("delivery_code_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE orders SET placed_by_id = customer_id WHERE placed_by_id IS NULL")
    op.execute("UPDATE orders SET contact_phone = '0000000000' WHERE contact_phone IS NULL")
    op.execute("UPDATE orders SET delivery_code = '0000' WHERE delivery_code IS NULL")
    with op.batch_alter_table("orders") as b:
        b.alter_column("placed_by_id", existing_type=sa.Integer(), nullable=False)
        b.alter_column("contact_phone", existing_type=sa.String(length=15), nullable=False)
        b.alter_column("delivery_code", existing_type=sa.String(length=4), nullable=False)
        b.create_foreign_key("fk_orders_placed_by", "users", ["placed_by_id"], ["id"])
        b.create_foreign_key("fk_orders_rider", "users", ["rider_id"], ["id"])
        b.create_index("ix_orders_rider_id", ["rider_id"])


def downgrade() -> None:
    with op.batch_alter_table("orders") as b:
        b.drop_index("ix_orders_rider_id")
        b.drop_constraint("fk_orders_rider", type_="foreignkey")
        b.drop_constraint("fk_orders_placed_by", type_="foreignkey")
        for col in ("delivery_code_required", "delivery_code", "rider_id", "contact_phone", "placed_by_id"):
            b.drop_column(col)

    # Users created without a phone (email-only) cannot satisfy the old NOT NULL phone column.
    op.execute("DELETE FROM users WHERE phone IS NULL")
    with op.batch_alter_table("users") as b:
        b.drop_constraint("uq_users_email", type_="unique")
        b.alter_column("phone", existing_type=sa.String(length=15), nullable=False)
        for col in ("locked_until", "failed_pin_attempts", "pin_must_change", "pin_hash", "active", "email"):
            b.drop_column(col)

    op.drop_index("ix_otp_codes_email", table_name="otp_codes")
    op.drop_table("otp_codes")
