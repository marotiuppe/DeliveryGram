"""Owner/admin tools: dashboard numbers, people, shops, commission rates, villages and wards."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import config, keepalive, mailer, models, schemas, security
from app.db import get_db

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(security.require_roles("admin"))])

IST = timedelta(hours=5, minutes=30)
PHONE = r"^[6-9]\d{9}$"


# ---------- dashboard ----------

class StatsOut(BaseModel):
    orders_today: int
    orders_by_status: dict[str, int]
    delivered_sales_paise: int  # value of today's bills that were delivered
    commission_paise: int  # platform commission on those delivered bills
    delivery_fees_paise: int  # fees on today's delivered deliveries
    open_deliveries: int
    khata_outstanding_paise: int  # what villagers owe shops, all time
    shops: int
    riders: int
    villagers: int


def ist_day_start_utc(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    ist_now = now + IST
    start_ist = ist_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_ist - IST  # aware-or-naive follows `now`


@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    start = ist_day_start_utc()  # "today" is the Indian calendar day
    today = models.Order.created_at >= start
    by_status = dict(db.execute(select(models.Order.status, func.count()).where(today).group_by(models.Order.status)).all())
    delivered = db.execute(
        select(func.coalesce(func.sum(models.Order.total_paise), 0), func.coalesce(func.sum(models.Order.commission_paise), 0))
        .where(today, models.Order.status == "DELIVERED")
    ).one()
    fees = db.scalar(select(func.coalesce(func.sum(models.Delivery.delivery_fee_paise), 0)).where(models.Delivery.created_at >= start, models.Delivery.status == "DELIVERED"))
    return StatsOut(
        orders_today=sum(by_status.values()), orders_by_status=by_status,
        delivered_sales_paise=delivered[0], commission_paise=delivered[1], delivery_fees_paise=fees,
        open_deliveries=db.scalar(select(func.count()).select_from(models.Delivery).where(models.Delivery.status.in_(("OPEN", "OUT_FOR_DELIVERY")))),
        khata_outstanding_paise=db.scalar(select(func.coalesce(func.sum(models.KhataEntry.amount_paise), 0))),
        shops=db.scalar(select(func.count()).select_from(models.Store).where(models.Store.deleted_at.is_(None))),
        riders=db.scalar(select(func.count()).select_from(models.User).where(models.User.role == "rider", models.User.active.is_(True))),
        villagers=db.scalar(select(func.count()).select_from(models.User).where(models.User.role == "customer")),
    )


# ---------- system status (what to look at when something does not work on Render) ----------

class SystemOut(BaseModel):
    version: str
    environment: str
    database: str  # kind only (postgresql / sqlite), never the connection string
    email_backend: str
    email_configured: bool
    last_email_error: str
    keepalive_enabled: bool
    keepalive_url: str
    keepalive_last_ok: bool | None
    keepalive_last_error: str


@router.get("/system", response_model=SystemOut)
def system(db: Session = Depends(get_db)):
    return SystemOut(
        version="0.4.0", environment=config.ENV, database=db.get_bind().dialect.name,
        email_backend=mailer.backend(), email_configured=mailer.configured(), last_email_error=mailer.last_error,
        keepalive_enabled=keepalive.status["enabled"], keepalive_url=keepalive.status["url"],
        keepalive_last_ok=keepalive.status["last_ok"], keepalive_last_error=keepalive.status["last_error"],
    )


# ---------- people ----------

class PersonOut(schemas.ORM):
    id: int
    role: str
    name: str | None
    phone: str | None
    email: str | None
    active: bool
    has_pin: bool = False


class PersonPatch(BaseModel):
    active: bool | None = None
    name: str | None = Field(default=None, max_length=80)
    temp_pin: str | None = Field(default=None, pattern=r"^\d{4,6}$")


def _person(u: models.User) -> PersonOut:
    return PersonOut(id=u.id, role=u.role, name=u.name, phone=u.phone, email=u.email, active=u.active, has_pin=bool(u.pin_hash))


@router.get("/users", response_model=list[PersonOut])
def list_users(
    role: str | None = Query(default=None, pattern=r"^(customer|merchant|rider|agent|admin)$"),
    q: str | None = Query(default=None, max_length=60),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(models.User).order_by(models.User.role, models.User.name, models.User.id).limit(limit)
    if role:
        stmt = stmt.where(models.User.role == role)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(models.User.name.ilike(like), models.User.phone.ilike(like), models.User.email.ilike(like)))
    return [_person(u) for u in db.scalars(stmt).all()]


@router.patch("/users/{user_id}", response_model=PersonOut)
def patch_user(user_id: int, body: PersonPatch, admin: models.User = Depends(security.current_user), db: Session = Depends(get_db)):
    """Disable/enable, rename, or set a new temporary PIN. Roles cannot be changed here (no privilege escalation)."""
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == admin.id and body.active is False:
        raise HTTPException(409, "You cannot disable your own account")
    if body.active is not None:
        user.active = body.active
    if body.name is not None:
        user.name = body.name or None
    if body.temp_pin:
        user.pin_hash, user.pin_must_change = security.hash_pin(body.temp_pin), True
        user.failed_pin_attempts, user.locked_until = 0, None
    db.commit()
    return _person(user)


# ---------- shops ----------

class AdminStoreOut(BaseModel):
    id: int
    name: str
    store_type_id: int
    store_type_name: str
    village_id: int
    village_name: str
    owner_id: int | None
    owner_phone: str | None
    phone: str | None
    address_text: str | None
    is_open: bool
    fssai_no: str | None
    drug_licence_no: str | None
    commission_bps: int | None  # this shop's own rate; None = use the shop type's rate
    effective_commission_bps: int
    active: bool


class StorePatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, pattern=PHONE)
    address_text: str | None = Field(default=None, max_length=300)
    fssai_no: str | None = Field(default=None, max_length=20)
    drug_licence_no: str | None = Field(default=None, max_length=40)
    commission_bps: int | None = Field(default=None, ge=0, le=5000)  # send null to go back to the shop type's rate
    is_open: bool | None = None
    active: bool | None = None


def _store_out(db: Session, s: models.Store) -> AdminStoreOut:
    owner = db.get(models.User, s.owner_id) if s.owner_id else None
    village = db.get(models.Village, s.village_id)
    return AdminStoreOut(
        id=s.id, name=s.name, store_type_id=s.store_type_id, store_type_name=s.store_type.name, village_id=s.village_id, village_name=village.name,
        owner_id=s.owner_id, owner_phone=owner.phone if owner else None, phone=s.phone, address_text=s.address_text, is_open=s.is_open,
        fssai_no=s.fssai_no, drug_licence_no=s.drug_licence_no, commission_bps=s.commission_bps,
        effective_commission_bps=s.commission_bps if s.commission_bps is not None else s.store_type.commission_bps, active=s.deleted_at is None,
    )


@router.get("/stores", response_model=list[AdminStoreOut])
def list_stores(db: Session = Depends(get_db)):
    return [_store_out(db, s) for s in db.scalars(select(models.Store).order_by(models.Store.village_id, models.Store.name)).all()]


@router.patch("/stores/{store_id}", response_model=AdminStoreOut)
def patch_store(store_id: int, body: StorePatch, db: Session = Depends(get_db)):
    s = db.get(models.Store, store_id)
    if not s:
        raise HTTPException(404, "Store not found")
    sent = body.model_fields_set  # distinguishes "not sent" from an explicit null
    for field in ("name", "phone", "address_text", "fssai_no", "is_open"):
        if field in sent and getattr(body, field) is not None:
            setattr(s, field, getattr(body, field))
    if "drug_licence_no" in sent:
        if s.store_type.needs_prescription and not body.drug_licence_no:
            raise HTTPException(422, "A drug licence number is required for medical stores")
        s.drug_licence_no = body.drug_licence_no or None
    if "commission_bps" in sent:
        s.commission_bps = body.commission_bps
    if body.active is not None:
        s.deleted_at = None if body.active else datetime.now(timezone.utc)
    db.commit()
    return _store_out(db, s)


# ---------- commission and tax rates (per shop type) ----------

class RateOut(schemas.ORM):
    id: int
    code: str
    name: str
    name_hi: str | None
    needs_prescription: bool
    has_time_slots: bool
    commission_bps: int
    tax_bps: int
    safety_notice: str | None


class RatePatch(BaseModel):
    commission_bps: int | None = Field(default=None, ge=0, le=5000)
    tax_bps: int | None = Field(default=None, ge=0, le=2800)  # GST tops out at 28%
    safety_notice: str | None = Field(default=None, max_length=1000)


@router.get("/store-types", response_model=list[RateOut])
def list_rates(db: Session = Depends(get_db)):
    return db.scalars(select(models.StoreType).order_by(models.StoreType.id)).all()


@router.patch("/store-types/{type_id}", response_model=RateOut)
def patch_rate(type_id: int, body: RatePatch, db: Session = Depends(get_db)):
    """New rates apply to orders placed from now on; existing bills keep the rate they were placed with."""
    st = db.get(models.StoreType, type_id)
    if not st:
        raise HTTPException(404, "Shop type not found")
    if body.commission_bps is not None:
        st.commission_bps = body.commission_bps
    if body.tax_bps is not None:
        st.tax_bps = body.tax_bps
    if "safety_notice" in body.model_fields_set:
        st.safety_notice = body.safety_notice or None
    db.commit()
    return st


# ---------- villages and wards ----------

class VillageCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=80)
    delivery_fee_paise: int | None = Field(default=None, ge=0, le=100_000)
    ward_count: int = Field(default=0, ge=0, le=100)  # creates wards 1..N


class VillagePatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=80)
    delivery_fee_paise: int | None = Field(default=None, ge=0, le=100_000)  # send null to use the default fee


class WardCreate(BaseModel):
    number: int = Field(ge=1, le=999)
    name: str | None = Field(default=None, max_length=80)


def village_out(v: models.Village) -> schemas.VillageOut:
    return schemas.VillageOut(
        id=v.id, name=v.name, district=v.district, state=v.state,
        wards=[schemas.WardOut.model_validate(w) for w in sorted(v.wards, key=lambda w: w.number)],
        delivery_fee_paise=v.delivery_fee_paise if v.delivery_fee_paise is not None else config.DELIVERY_FEE_PAISE,
        min_order_paise=config.MIN_ORDER_PAISE,
    )


@router.post("/villages", response_model=schemas.VillageOut, status_code=201)
def create_village(body: VillageCreate, db: Session = Depends(get_db)):
    if db.scalar(select(models.Village.id).where(func.lower(models.Village.name) == body.name.lower(), models.Village.district == body.district)):
        raise HTTPException(409, "This village already exists")
    v = models.Village(name=body.name, district=body.district, state=body.state, delivery_fee_paise=body.delivery_fee_paise,
                       wards=[models.Ward(number=n) for n in range(1, body.ward_count + 1)])
    db.add(v)
    db.commit()
    return village_out(v)


@router.patch("/villages/{village_id}", response_model=schemas.VillageOut)
def patch_village(village_id: int, body: VillagePatch, db: Session = Depends(get_db)):
    v = db.get(models.Village, village_id)
    if not v:
        raise HTTPException(404, "Village not found")
    for field in body.model_fields_set:
        value = getattr(body, field)
        if field == "name" and value is None:
            continue
        setattr(v, field, value)
    db.commit()
    return village_out(v)


@router.post("/villages/{village_id}/wards", response_model=schemas.VillageOut, status_code=201)
def add_ward(village_id: int, body: WardCreate, db: Session = Depends(get_db)):
    v = db.get(models.Village, village_id)
    if not v:
        raise HTTPException(404, "Village not found")
    if any(w.number == body.number for w in v.wards):
        raise HTTPException(409, f"Ward {body.number} already exists")
    v.wards.append(models.Ward(number=body.number, name=body.name))
    db.commit()
    return village_out(v)
