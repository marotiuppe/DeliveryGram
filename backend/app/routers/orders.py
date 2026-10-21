from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

import hmac

from app import khata, models, present, schemas, security
from app.db import get_db

router = APIRouter(tags=["orders"])

# (from_status, to_status) -> roles allowed. Rider pickup/handover is per delivery (routers/deliveries.py); shop handover applies to pickup bills only.
TRANSITIONS: dict[tuple[str, str], set[str]] = {
    ("PENDING_PRESCRIPTION_REVIEW", "PLACED"): {"merchant", "admin"},  # pharmacist verified the prescription
    ("PENDING_PRESCRIPTION_REVIEW", "REJECTED"): {"merchant", "admin"},
    ("PLACED", "ACCEPTED"): {"merchant", "admin"},
    ("PLACED", "REJECTED"): {"merchant", "admin"},
    ("ACCEPTED", "READY"): {"merchant", "admin"},
    ("READY", "DELIVERED"): {"merchant", "admin"},  # pickup only: the shop hands the order to the customer
    ("PLACED", "CANCELLED"): {"customer", "agent", "admin"},
    ("PENDING_PRESCRIPTION_REVIEW", "CANCELLED"): {"customer", "agent", "admin"},
}


def _load(db: Session, order_id: int) -> models.Order | None:
    return db.scalar(select(models.Order).options(joinedload(models.Order.items), joinedload(models.Order.delivery)).where(models.Order.id == order_id))


def _can_view(db: Session, user: models.User, order: models.Order) -> bool:
    if user.role == "admin" or user.id in (order.customer_id, order.placed_by_id):
        return True
    if user.role == "merchant":
        store = db.get(models.Store, order.store_id)
        return bool(store and store.owner_id == user.id)
    return False


@router.get("/orders", response_model=list[schemas.OrderOut])
def my_orders(user: models.User = Depends(security.current_user), db: Session = Depends(get_db)):
    """Bills. Customers see their own, merchants see their shops', admin sees all. Riders use /deliveries."""
    if user.role == "rider":
        raise HTTPException(403, "Riders use /deliveries")
    stmt = select(models.Order).options(joinedload(models.Order.items)).order_by(models.Order.id.desc()).limit(100)
    if user.role == "merchant":
        stmt = stmt.join(models.Store, models.Store.id == models.Order.store_id).where(models.Store.owner_id == user.id)
    elif user.role != "admin":
        stmt = stmt.where((models.Order.customer_id == user.id) | (models.Order.placed_by_id == user.id))
    return db.scalars(stmt).unique().all()


@router.get("/orders/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, user: models.User = Depends(security.current_user), db: Session = Depends(get_db)):
    order = _load(db, order_id)
    if not order or not _can_view(db, user, order):
        raise HTTPException(404, "Order not found")
    return order


@router.post("/orders/{order_id}/status", response_model=schemas.OrderOut)
def change_status(order_id: int, body: schemas.StatusChange, user: models.User = Depends(security.current_user), db: Session = Depends(get_db)):
    order = _load(db, order_id)
    if not order or not _can_view(db, user, order):
        raise HTTPException(404, "Order not found")
    allowed = TRANSITIONS.get((order.status, body.status))
    if allowed is None:
        raise HTTPException(409, f"Cannot move an order from {order.status} to {body.status}")
    if user.role not in allowed:
        raise HTTPException(403, "Not allowed for your role")
    if user.role == "customer" and user.id != order.customer_id:
        raise HTTPException(403, "Not your order")
    if user.role == "agent" and user.id != order.placed_by_id:
        raise HTTPException(403, "Agents can only cancel orders they placed")
    delivery = present.load_delivery(db, order.delivery_id)
    if body.status == "DELIVERED":
        if order.fulfillment != "pickup":
            raise HTTPException(409, "Only pickup orders are handed over by the shop; a rider delivers the rest")
        if delivery.delivery_code_required and user.role != "admin":
            if not body.delivery_code or not hmac.compare_digest(body.delivery_code, delivery.delivery_code):
                raise HTTPException(422, "Delivery code is missing or wrong")
    order.status = body.status
    if body.status == "DELIVERED":
        khata.post_delivered_sales(db, [order])
    present.refresh_delivery_status(delivery)
    db.commit()
    return order
