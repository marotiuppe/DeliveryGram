from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.db import get_db

router = APIRouter(tags=["staff"])
PHONE = r"^[6-9]\d{9}$"


class CustomerRegister(BaseModel):
    phone: str = Field(pattern=PHONE)
    name: str | None = Field(default=None, max_length=80)
    temp_pin: str = Field(pattern=r"^\d{4,6}$")


class UserCreate(BaseModel):
    role: str = Field(pattern=r"^(merchant|rider|agent|admin)$")
    name: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, pattern=PHONE)
    email: str | None = Field(default=None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=120)
    temp_pin: str | None = Field(default=None, pattern=r"^\d{4,6}$")


class StoreCreate(BaseModel):
    owner_id: int
    store_type_code: str
    village_id: int
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, pattern=PHONE)
    address_text: str | None = None
    fssai_no: str | None = None
    drug_licence_no: str | None = None


class UserOut(schemas.ORM):
    id: int
    role: str
    name: str | None
    phone: str | None
    email: str | None


class CustomerLookup(BaseModel):
    registered: bool
    name: str | None = None
    has_pin: bool = False


@router.get("/staff/customers/{phone}", response_model=CustomerLookup)
def lookup_customer(
    phone: str, staff: models.User = Depends(security.require_roles("agent", "merchant", "admin")), db: Session = Depends(get_db)
):
    """Lets a helper check a phone number before registering or ordering for it (catches typos and staff numbers)."""
    if not (len(phone) == 10 and phone.isdigit() and phone[0] in "6789"):
        raise HTTPException(422, "Invalid phone number")
    user = db.scalar(select(models.User).where(models.User.phone == phone))
    if user and user.role != "customer":
        raise HTTPException(409, "This phone belongs to a staff account")
    return CustomerLookup(registered=bool(user), name=user.name if user else None, has_pin=bool(user and user.pin_hash))


@router.post("/staff/customers", response_model=UserOut, status_code=201)
def register_customer(
    body: CustomerRegister, staff: models.User = Depends(security.require_roles("agent", "merchant", "admin")), db: Session = Depends(get_db)
):
    """Assisted registration: a shopkeeper or village agent registers a villager with a temporary PIN."""
    user = db.scalar(select(models.User).where(models.User.phone == body.phone))
    if user and user.role != "customer":
        raise HTTPException(409, "This phone belongs to a staff account")
    if not user:
        user = models.User(phone=body.phone, role="customer")
        db.add(user)
    user.name = body.name or user.name
    user.pin_hash, user.pin_must_change = security.hash_pin(body.temp_pin), True
    user.failed_pin_attempts, user.locked_until = 0, None
    db.commit()
    return user


@router.post("/admin/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, _: models.User = Depends(security.require_roles("admin")), db: Session = Depends(get_db)):
    if not (body.phone or body.email):
        raise HTTPException(422, "Give a phone or an email")
    if body.phone and db.scalar(select(models.User).where(models.User.phone == body.phone)):
        raise HTTPException(409, "Phone already registered")
    if body.email and db.scalar(select(models.User).where(models.User.email == body.email.lower())):
        raise HTTPException(409, "Email already registered")
    user = models.User(role=body.role, name=body.name, phone=body.phone, email=body.email.lower() if body.email else None)
    if body.temp_pin:
        user.pin_hash, user.pin_must_change = security.hash_pin(body.temp_pin), True
    db.add(user)
    db.commit()
    return user


@router.post("/admin/stores", response_model=schemas.StoreOut, status_code=201)
def create_store(body: StoreCreate, _: models.User = Depends(security.require_roles("admin")), db: Session = Depends(get_db)):
    owner = db.get(models.User, body.owner_id)
    stype = db.scalar(select(models.StoreType).where(models.StoreType.code == body.store_type_code))
    if not owner or owner.role != "merchant":
        raise HTTPException(422, "owner_id must be a merchant user")
    if not stype or not db.get(models.Village, body.village_id):
        raise HTTPException(422, "Unknown store type or village")
    if stype.needs_prescription and not body.drug_licence_no:
        raise HTTPException(422, "A drug licence number is required for medical stores")
    store = models.Store(
        owner_id=owner.id, store_type_id=stype.id, village_id=body.village_id, name=body.name, phone=body.phone,
        address_text=body.address_text, fssai_no=body.fssai_no, drug_licence_no=body.drug_licence_no,
    )
    db.add(store)
    db.commit()
    return store
