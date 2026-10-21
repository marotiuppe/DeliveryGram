from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import config, khata, models, present, schemas, security
from app.db import get_db

router = APIRouter(tags=["checkout"])

STAFF_ORDER_ROLES = ("agent", "merchant", "admin")  # may order on behalf of a villager


def _bps(amount: int, bps: int) -> int:
    """Integer basis-point share, rounded half up."""
    return (amount * bps + 5000) // 10000


def _existing(db: Session, key: str) -> models.Delivery | None:
    return db.scalar(select(models.Delivery.id).where(models.Delivery.idempotency_key == key))


@router.post("/checkout", response_model=schemas.DeliveryOut, status_code=201)
def checkout(body: schemas.CheckoutIn, response: Response, user: models.User = Depends(security.current_user), db: Session = Depends(get_db)):
    """One checkout, any number of shops: one order (bill) per shop, one delivery (rider, fee, code) for all."""
    if user.role == "customer":
        customer = user
    elif user.role in STAFF_ORDER_ROLES:
        customer = db.scalar(select(models.User).where(models.User.phone == body.customer_phone))
        if not customer:
            customer = models.User(phone=body.customer_phone, name=body.customer_name, role="customer", active=True)
            db.add(customer)
            db.flush()
        elif customer.role != "customer":
            raise HTTPException(409, "This phone belongs to a staff account")
    else:
        raise HTTPException(403, "Riders cannot place orders")

    prior_id = _existing(db, body.idempotency_key)
    if prior_id:  # retried request on a flaky network: return the original, never a second order
        prior = present.load_delivery(db, prior_id)
        if prior.placed_by_id != user.id:
            raise HTTPException(409, "Idempotency key already used")
        response.status_code = 200
        return present.delivery_out(user, prior)

    village = db.get(models.Village, body.village_id)
    if not village:
        raise HTTPException(422, "Unknown village")
    if body.ward_id is not None:
        ward = db.get(models.Ward, body.ward_id)
        if not ward or ward.village_id != village.id:
            raise HTTPException(422, "Ward does not belong to village")

    store_ids = [s.store_id for s in body.shops]
    if len(set(store_ids)) != len(store_ids):
        raise HTTPException(422, "Each shop can appear once; combine its items")

    orders, grand_subtotal, any_upi, any_rx = [], 0, False, False
    for shop in body.shops:
        store = db.get(models.Store, shop.store_id)
        if not store or store.deleted_at is not None:
            raise HTTPException(404, f"Store {shop.store_id} not found")
        if not store.is_open:
            raise HTTPException(409, f"{store.name} is closed")

        ids = [line.store_item_id for line in shop.items]
        if len(set(ids)) != len(ids):
            raise HTTPException(422, "Duplicate items; combine quantities")
        rows = db.scalars(select(models.StoreItem).options(joinedload(models.StoreItem.catalog_item)).where(models.StoreItem.id.in_(ids))).all()
        by_id = {r.id: r for r in rows}

        subtotal, needs_rx, lines = 0, False, []
        for line in shop.items:
            si = by_id.get(line.store_item_id)
            if not si or si.store_id != store.id:
                raise HTTPException(422, f"Item {line.store_item_id} is not sold by {store.name}")
            if not si.available:
                raise HTTPException(409, f"Item {line.store_item_id} is unavailable")
            ci = si.catalog_item
            needs_rx = needs_rx or bool(ci and ci.requires_prescription)
            subtotal += si.price_paise * line.quantity
            lines.append(models.OrderItem(store_item_id=si.id, name=si.custom_name or (ci.name if ci else "Item"), unit_price_paise=si.price_paise, quantity=line.quantity))
        if needs_rx and not shop.prescription_ref:
            raise HTTPException(422, f"A prescription is required for the medicines from {store.name}")

        stype = store.store_type
        tax = _bps(subtotal, stype.tax_bps)
        total = subtotal + tax
        if shop.payment_method == "khata":
            acct = khata.get_account(db, store.id, customer.id)
            if not acct or not acct.enabled:
                raise HTTPException(409, f"{store.name} has not given you khata")
            if total > khata.available_credit(db, acct):
                raise HTTPException(409, f"Over your khata limit at {store.name}")
        any_upi, any_rx = any_upi or shop.payment_method == "upi", any_rx or needs_rx
        grand_subtotal += subtotal
        orders.append(models.Order(
            customer_id=customer.id, placed_by_id=user.id, contact_phone=body.customer_phone, store_id=store.id,
            status="PENDING_PRESCRIPTION_REVIEW" if needs_rx else "PLACED", source=body.source, payment_method=shop.payment_method,
            fulfillment=shop.fulfillment,
            village_id=village.id, ward_id=body.ward_id, landmark=body.landmark, address_details=body.address_details,
            prescription_ref=shop.prescription_ref, subtotal_paise=subtotal, tax_paise=tax,
            commission_paise=_bps(subtotal, store.commission_bps if store.commission_bps is not None else stype.commission_bps),
            total_paise=total, items=lines,
        ))

    if grand_subtotal < config.MIN_ORDER_PAISE:  # minimum applies to the whole cart, not per shop
        raise HTTPException(422, f"Minimum order is {config.MIN_ORDER_PAISE // 100} rupees")

    any_delivery = any(s.fulfillment == "delivery" for s in body.shops)
    fee = (village.delivery_fee_paise if village.delivery_fee_paise is not None else config.DELIVERY_FEE_PAISE) if any_delivery else 0
    grand_total = sum(o.total_paise for o in orders) + fee
    delivery = models.Delivery(
        idempotency_key=body.idempotency_key, customer_id=customer.id, placed_by_id=user.id, contact_phone=body.customer_phone,
        village_id=village.id, ward_id=body.ward_id, landmark=body.landmark, address_details=body.address_details, lat=body.lat, lon=body.lon,
        delivery_fee_paise=fee, delivery_code=security.new_delivery_code(),
        delivery_code_required=any_upi or any_rx or grand_total >= config.DELIVERY_CODE_THRESHOLD_PAISE, orders=orders,
    )
    db.add(delivery)
    try:
        db.commit()
    except IntegrityError:  # concurrent retry with the same key
        db.rollback()
        prior_id = _existing(db, body.idempotency_key)
        prior = present.load_delivery(db, prior_id) if prior_id else None
        if prior and prior.placed_by_id == user.id:
            response.status_code = 200
            return present.delivery_out(user, prior)
        raise
    return present.delivery_out(user, delivery)
