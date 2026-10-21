from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import khata, models, schemas, security
from app.db import get_db

router = APIRouter(tags=["khata"])


def _out(db: Session, acct: models.KhataAccount) -> schemas.KhataAccountOut:
    store, customer = db.get(models.Store, acct.store_id), db.get(models.User, acct.customer_id)
    return schemas.KhataAccountOut(
        store_id=acct.store_id, store_name=store.name, customer_id=acct.customer_id, customer_name=customer.name,
        customer_phone=customer.phone, credit_limit_paise=acct.credit_limit_paise, enabled=acct.enabled,
        balance_paise=khata.balance(db, acct.id),
    )


def _own_store(db: Session, user: models.User, store_id: int) -> models.Store:
    store = db.get(models.Store, store_id)
    if not store or store.deleted_at is not None or (user.role != "admin" and store.owner_id != user.id):
        raise HTTPException(404, "Store not found")
    return store


# ---- customer: see what I owe each shop ----

@router.get("/khata", response_model=list[schemas.KhataAccountOut])
def my_khata(user: models.User = Depends(security.require_roles("customer")), db: Session = Depends(get_db)):
    accounts = db.scalars(select(models.KhataAccount).where(models.KhataAccount.customer_id == user.id)).all()
    return [_out(db, a) for a in accounts]


@router.get("/khata/{store_id}/entries", response_model=list[schemas.KhataEntryOut])
def my_khata_entries(store_id: int, user: models.User = Depends(security.require_roles("customer")), db: Session = Depends(get_db)):
    acct = khata.get_account(db, store_id, user.id)
    if not acct:
        raise HTTPException(404, "No khata with this shop")
    return db.scalars(select(models.KhataEntry).where(models.KhataEntry.account_id == acct.id).order_by(models.KhataEntry.id.desc()).limit(200)).all()


# ---- shopkeeper: run the khata book ----

@router.get("/merchant/stores/{store_id}/khata", response_model=list[schemas.KhataAccountOut])
def store_khata(store_id: int, user: models.User = Depends(security.require_roles("merchant", "admin")), db: Session = Depends(get_db)):
    _own_store(db, user, store_id)
    accounts = db.scalars(select(models.KhataAccount).where(models.KhataAccount.store_id == store_id)).all()
    return sorted((_out(db, a) for a in accounts), key=lambda a: -a.balance_paise)  # biggest dues first


@router.put("/merchant/stores/{store_id}/khata/{customer_phone}", response_model=schemas.KhataAccountOut)
def set_khata_account(
    store_id: int, customer_phone: str, body: schemas.KhataAccountIn,
    user: models.User = Depends(security.require_roles("merchant", "admin")), db: Session = Depends(get_db),
):
    """Give a villager khata at this shop (or change their limit / pause it). Creates the customer by phone if new."""
    _own_store(db, user, store_id)
    if not (len(customer_phone) == 10 and customer_phone.isdigit() and customer_phone[0] in "6789"):
        raise HTTPException(422, "Invalid phone number")
    customer = db.scalar(select(models.User).where(models.User.phone == customer_phone))
    if customer and customer.role != "customer":
        raise HTTPException(409, "This phone belongs to a staff account")
    if not customer:
        customer = models.User(phone=customer_phone, role="customer", active=True)
        db.add(customer)
        db.flush()
    acct = khata.get_account(db, store_id, customer.id)
    if not acct:
        acct = models.KhataAccount(store_id=store_id, customer_id=customer.id)
        db.add(acct)
    acct.credit_limit_paise, acct.enabled = body.credit_limit_paise, body.enabled
    db.commit()
    return _out(db, acct)


@router.get("/merchant/stores/{store_id}/khata/{customer_id}/entries", response_model=list[schemas.KhataEntryOut])
def store_khata_entries(store_id: int, customer_id: int, user: models.User = Depends(security.require_roles("merchant", "admin")), db: Session = Depends(get_db)):
    _own_store(db, user, store_id)
    acct = khata.get_account(db, store_id, customer_id)
    if not acct:
        raise HTTPException(404, "No khata for this customer")
    return db.scalars(select(models.KhataEntry).where(models.KhataEntry.account_id == acct.id).order_by(models.KhataEntry.id.desc()).limit(200)).all()


@router.post("/merchant/stores/{store_id}/khata/{customer_id}/entries", response_model=schemas.KhataAccountOut, status_code=201)
def add_khata_entry(
    store_id: int, customer_id: int, body: schemas.KhataEntryIn,
    user: models.User = Depends(security.require_roles("merchant", "admin")), db: Session = Depends(get_db),
):
    """Record a counter sale 'add to khata' (SALE) or money received from the customer (PAYMENT)."""
    _own_store(db, user, store_id)
    acct = khata.get_account(db, store_id, customer_id)
    if not acct:
        raise HTTPException(404, "No khata for this customer")
    owed = khata.balance(db, acct.id)
    if body.kind == "PAYMENT" and body.amount_paise > owed:
        raise HTTPException(422, f"Payment is more than the {owed / 100:.2f} rupees owed")
    amount = body.amount_paise if body.kind == "SALE" else -body.amount_paise
    db.add(models.KhataEntry(account_id=acct.id, kind=body.kind, amount_paise=amount, note=body.note, created_by_id=user.id))
    db.commit()
    return _out(db, acct)
