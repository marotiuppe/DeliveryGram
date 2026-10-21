"""pickup at the shop: per-order fulfillment

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as b:
        b.add_column(sa.Column("fulfillment", sa.String(length=10), nullable=False, server_default="delivery"))


def downgrade() -> None:
    with op.batch_alter_table("orders") as b:
        b.drop_column("fulfillment")
