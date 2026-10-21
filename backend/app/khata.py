"""Khata (shop credit) rules. Balance = what the customer owes the shop = sum of ledger entries."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models

# Khata orders in these states are not in the ledger yet but will be if delivered, so they count against the limit.
PENDING_STATUSES = ("PENDING_PRESCRIPTION_REVIEW", "PLACED", "ACCEPTED", "READY", "OUT_FOR_DELIVERY")


def get_account(db: Session, store_id: int, customer_id: int) -> models.KhataAccount | None:
    return db.scalar(select(models.KhataAccount).where(models.KhataAccount.store_id == store_id, models.KhataAccount.customer_id == customer_id))


def balance(db: Session, account_id: int) -> int:
    return db.scalar(select(func.coalesce(func.sum(models.KhataEntry.amount_paise), 0)).where(models.KhataEntry.account_id == account_id))


def pending_exposure(db: Session, store_id: int, customer_id: int) -> int:
    return db.scalar(
        select(func.coalesce(func.sum(models.Order.total_paise), 0)).where(
            models.Order.store_id == store_id, models.Order.customer_id == customer_id,
            models.Order.payment_method == "khata", models.Order.status.in_(PENDING_STATUSES),
        )
    )


def available_credit(db: Session, account: models.KhataAccount) -> int:
    return account.credit_limit_paise - balance(db, account.id) - pending_exposure(db, account.store_id, account.customer_id)


def post_delivered_sales(db: Session, orders: list[models.Order]) -> None:
    """Add a SALE entry for each delivered khata order. Safe to call twice (unique per order)."""
    for o in orders:
        if o.payment_method != "khata" or o.status != "DELIVERED":
            continue
        acct = get_account(db, o.store_id, o.customer_id)
        if not acct:
            continue
        exists = db.scalar(select(models.KhataEntry.id).where(models.KhataEntry.order_id == o.id, models.KhataEntry.kind == "SALE"))
        if not exists:
            db.add(models.KhataEntry(account_id=acct.id, kind="SALE", amount_paise=o.total_paise, order_id=o.id, note=f"Bill {o.id}"))
