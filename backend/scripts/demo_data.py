"""DEV ONLY: a demo village with shops, prices and test accounts. Prices are made up. Never run against production.

    python -m scripts.demo_data      (from backend/, after `alembic upgrade head`)
Logins (PIN 1234): customer 9876543210, merchant 9000000001, rider 9000000003, agent 9000000005, admin 9000000009.
In production the admin is created from ADMIN_EMAIL and logs in with an emailed code.
"""
import random

from sqlalchemy import select

from app import config, models, security
from app.db import SessionLocal
from app.seed import DEFAULT_XLSX, ensure_admin, import_catalog

if config.ENV == "production":
    raise SystemExit("Refusing to create demo data in production")


def user(db, phone, role, name):
    u = db.scalar(select(models.User).where(models.User.phone == phone))
    if not u:
        u = models.User(phone=phone, role=role, name=name, active=True)
        db.add(u)
    u.pin_hash, u.pin_must_change = security.hash_pin("1234"), False
    db.flush()
    return u


def stock(db, store, names, rng, discount=1.0):
    ci = db.scalars(select(models.CatalogItem).where(models.CatalogItem.store_type_id == store.store_type_id, models.CatalogItem.name.in_(names))).all()
    for c in ci:
        if not db.scalar(select(models.StoreItem.id).where(models.StoreItem.store_id == store.id, models.StoreItem.catalog_item_id == c.id)):
            db.add(models.StoreItem(store_id=store.id, catalog_item_id=c.id, price_paise=int(rng.randint(20, 400) * 100 * discount)))


with SessionLocal() as db:
    import_catalog(db, DEFAULT_XLSX)
    ensure_admin(db)
    rng = random.Random(7)
    types = {t.code: t for t in db.scalars(select(models.StoreType)).all()}

    village = db.scalar(select(models.Village).where(models.Village.name == "Rampur"))
    if not village:
        village = models.Village(name="Rampur", district="Demo district", state="Demo state", wards=[models.Ward(number=n, name=f"Ward {n}") for n in range(1, 6)])
        db.add(village)
        db.flush()

    customer = user(db, "9876543210", "customer", "Ramesh")
    owners = [user(db, "9000000001", "merchant", "Sharma"), user(db, "9000000002", "merchant", "Gupta"), user(db, "9000000006", "merchant", "Verma")]
    user(db, "9000000003", "rider", "Bholu")
    user(db, "9000000005", "agent", "Sahayak")
    user(db, "9000000009", "admin", "Owner")

    specs = [
        (owners[0], "kirana", "Sharma Kirana", ["Wheat Atta", "Basmati Rice", "Toor Dal", "Moong Dal", "Sugar", "Salt", "Mustard Oil", "Tea Leaves (Chai Patti)", "Bathing Soap", "Detergent Powder", "Toothpaste", "Potato", "Onion", "Tomato"], 1.0),
        (owners[2], "kirana", "Verma General Store", ["Wheat Atta", "Regular Rice", "Chana Dal", "Sugar", "Mustard Oil", "Biscuits", "Glucose Biscuit", "Matchbox", "Candle", "Onion"], 0.95),
        (owners[1], "medical", "Gupta Medical", ["Paracetamol Tablets", "ORS Sachet", "Antacid", "Bandage", "Thermometer", "Antibiotics", "Diabetes Medicines"], 1.0),
    ]
    for owner, code, name, items, disc in specs:
        store = db.scalar(select(models.Store).where(models.Store.name == name))
        if not store:
            store = models.Store(name=name, owner_id=owner.id, store_type_id=types[code].id, village_id=village.id, phone=owner.phone,
                                 drug_licence_no="DEMO-0001" if code == "medical" else None)
            db.add(store)
            db.flush()
        stock(db, store, items, rng, disc)
    db.flush()

    sharma = db.scalar(select(models.Store).where(models.Store.name == "Sharma Kirana"))
    if not db.scalar(select(models.KhataAccount.id).where(models.KhataAccount.store_id == sharma.id, models.KhataAccount.customer_id == customer.id)):
        db.add(models.KhataAccount(store_id=sharma.id, customer_id=customer.id, credit_limit_paise=200000, enabled=True))
    db.commit()
    print("Demo data ready: village Rampur, 3 shops, customer 9876543210 PIN 1234")
