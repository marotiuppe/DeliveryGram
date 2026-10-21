"""Shared view/permission helpers for deliveries and orders."""
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import models, schemas

DEAD_ORDER_STATUSES = ("REJECTED", "CANCELLED")


def live_orders(delivery: models.Delivery) -> list[models.Order]:
    return [o for o in delivery.orders if o.status not in DEAD_ORDER_STATUSES]


def rider_orders(delivery: models.Delivery) -> list[models.Order]:
    """Live bills a rider brings. Pickup bills are collected by the customer at the shop instead."""
    return [o for o in live_orders(delivery) if o.fulfillment == "delivery"]


def is_available_for_rider(delivery: models.Delivery) -> bool:
    carry = rider_orders(delivery)
    return delivery.status == "OPEN" and delivery.rider_id is None and bool(carry) and all(o.status == "READY" for o in carry)


def load_delivery(db: Session, delivery_id: int) -> models.Delivery | None:
    return db.scalar(
        select(models.Delivery).options(joinedload(models.Delivery.orders).joinedload(models.Order.items)).where(models.Delivery.id == delivery_id)
    )


def refresh_delivery_status(delivery: models.Delivery) -> None:
    """No live bills left -> cancelled. Pickup-only delivery whose bills were all handed over -> delivered."""
    if delivery.status != "OPEN":
        return
    live = live_orders(delivery)
    if not live:
        delivery.status = "CANCELLED"
    elif not rider_orders(delivery) and all(o.status == "DELIVERED" for o in live):
        delivery.status = "DELIVERED"


def can_see_code(user: models.User, delivery: models.Delivery) -> bool:
    return user.role == "admin" or user.id in (delivery.customer_id, delivery.placed_by_id)


def delivery_out(user: models.User, delivery: models.Delivery) -> schemas.DeliveryOut:
    out = schemas.DeliveryOut.model_validate(delivery)
    live, carry = live_orders(delivery), rider_orders(delivery)
    fee = delivery.delivery_fee_paise if carry else 0  # no fee if nothing is being delivered
    out.bills_total_paise = sum(o.total_paise for o in live)
    out.grand_total_paise = out.bills_total_paise + fee
    # What the rider collects at the door: cash bills they carry + the delivery fee. Pickup bills are paid at the shop.
    out.cash_to_collect_paise = (sum(o.total_paise for o in carry if o.payment_method == "cod") + fee) if carry else 0
    out.delivery_code = delivery.delivery_code if can_see_code(user, delivery) else None
    return out


def can_view_delivery(user: models.User, delivery: models.Delivery) -> bool:
    if user.role == "admin" or user.id in (delivery.customer_id, delivery.placed_by_id, delivery.rider_id):
        return True
    return user.role == "rider" and is_available_for_rider(delivery)
