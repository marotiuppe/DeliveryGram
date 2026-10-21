import hmac

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import khata, models, present, schemas, security
from app.db import get_db

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


def _get(db: Session, user: models.User, delivery_id: int) -> models.Delivery:
    d = present.load_delivery(db, delivery_id)
    if not d or not present.can_view_delivery(user, d):
        raise HTTPException(404, "Delivery not found")
    return d


@router.get("", response_model=list[schemas.DeliveryOut])
def list_deliveries(user: models.User = Depends(security.current_user), db: Session = Depends(get_db)):
    """Customers/agents: their deliveries. Riders: jobs ready for pickup plus their own. Admin: all."""
    if user.role == "merchant":
        raise HTTPException(403, "Merchants use /orders")
    stmt = select(models.Delivery).options(joinedload(models.Delivery.orders).joinedload(models.Order.items)).order_by(models.Delivery.id.desc()).limit(100)
    if user.role == "rider":
        stmt = stmt.where((models.Delivery.rider_id == user.id) | ((models.Delivery.status == "OPEN") & (models.Delivery.rider_id.is_(None))))
    elif user.role != "admin":
        stmt = stmt.where((models.Delivery.customer_id == user.id) | (models.Delivery.placed_by_id == user.id))
    rows = db.scalars(stmt).unique().all()
    if user.role == "rider":
        rows = [d for d in rows if d.rider_id == user.id or present.is_available_for_rider(d)]
    return [present.delivery_out(user, d) for d in rows]


@router.get("/{delivery_id}", response_model=schemas.DeliveryOut)
def get_delivery(delivery_id: int, user: models.User = Depends(security.current_user), db: Session = Depends(get_db)):
    return present.delivery_out(user, _get(db, user, delivery_id))


@router.post("/{delivery_id}/claim", response_model=schemas.DeliveryOut)
def claim(delivery_id: int, user: models.User = Depends(security.require_roles("rider")), db: Session = Depends(get_db)):
    """A rider takes the whole delivery once every live shop order is READY: one rider, all shops, one trip."""
    d = _get(db, user, delivery_id)
    if not present.is_available_for_rider(d):
        raise HTTPException(409, "This delivery is not ready for pickup (or already taken)")
    d.rider_id, d.status = user.id, "OUT_FOR_DELIVERY"
    for o in present.rider_orders(d):
        o.status = "OUT_FOR_DELIVERY"
    db.commit()
    return present.delivery_out(user, d)


def _own_active(d: models.Delivery, user: models.User) -> None:
    if d.status != "OUT_FOR_DELIVERY":
        raise HTTPException(409, f"Delivery is {d.status}")
    if user.role == "rider" and d.rider_id != user.id:
        raise HTTPException(404, "Delivery not found")


@router.post("/{delivery_id}/complete", response_model=schemas.DeliveryOut)
def complete(
    delivery_id: int, body: schemas.CompleteDelivery, user: models.User = Depends(security.require_roles("rider", "admin")), db: Session = Depends(get_db)
):
    """Handover at the door: every live bill is delivered; khata bills are posted to each shop's ledger."""
    d = _get(db, user, delivery_id)
    _own_active(d, user)
    if d.delivery_code_required and user.role != "admin":
        if not body.delivery_code or not hmac.compare_digest(body.delivery_code, d.delivery_code):
            raise HTTPException(422, "Delivery code is missing or wrong")
    carried = present.rider_orders(d)
    for o in carried:
        o.status = "DELIVERED"
    d.status = "DELIVERED"
    khata.post_delivered_sales(db, carried)
    db.commit()
    return present.delivery_out(user, d)


@router.post("/{delivery_id}/fail", response_model=schemas.DeliveryOut)
def fail(delivery_id: int, user: models.User = Depends(security.require_roles("rider", "admin")), db: Session = Depends(get_db)):
    """Customer not found / refused. Nothing is posted to khata."""
    d = _get(db, user, delivery_id)
    _own_active(d, user)
    for o in present.rider_orders(d):
        o.status = "FAILED"
    d.status = "FAILED"
    db.commit()
    return present.delivery_out(user, d)
