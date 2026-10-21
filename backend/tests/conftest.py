import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, security
from app.db import Base, get_db
from app.main import app
from app.seed import seed_store_types


@pytest.fixture()
def db():
    """SQLite in memory by default. Set TEST_DATABASE_URL=postgresql+psycopg://... to run the same tests on Postgres."""
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        engine = create_engine(url)
        Base.metadata.drop_all(engine)
    else:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield session
    session.close()
    if url:
        engine.dispose()


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def world(db):
    """A village with two wards, a kirana store and a pharmacy, each with items."""
    types = seed_store_types(db)
    kirana, medical = types["Kirana & Grocery"], types["Medical & Pharmacy"]
    village = models.Village(name="Rampur", district="Test", state="UP", wards=[models.Ward(number=1), models.Ward(number=2)])
    other = models.Village(name="Shyampur", wards=[models.Ward(number=1)])
    db.add_all([village, other])
    db.flush()
    users = {
        "customer": models.User(phone="9876543210", name="Ramesh", role="customer"),
        "customer2": models.User(phone="9876543211", name="Suresh", role="customer"),
        "merchant": models.User(phone="9000000001", role="merchant"),
        "merchant2": models.User(phone="9000000002", role="merchant"),
        "merchant3": models.User(phone="9000000006", role="merchant"),
        "rider": models.User(phone="9000000003", role="rider"),
        "rider2": models.User(phone="9000000004", role="rider"),
        "agent": models.User(phone="9000000005", role="agent"),
        "admin": models.User(email="admin@example.com", role="admin"),
    }
    db.add_all(users.values())
    db.flush()
    shop = models.Store(name="Sharma Kirana", store_type_id=kirana.id, village_id=village.id, owner_id=users["merchant"].id)
    pharmacy = models.Store(name="Gupta Medical", store_type_id=medical.id, village_id=village.id, drug_licence_no="X-1", owner_id=users["merchant2"].id)
    shop2 = models.Store(name="Verma General", store_type_id=kirana.id, village_id=village.id, owner_id=users["merchant3"].id)
    db.add_all([shop, pharmacy, shop2])
    atta = models.CatalogItem(code="DG0001", store_type_id=kirana.id, subcategory="Atta", name="Wheat Atta")
    para = models.CatalogItem(code="DG0900", store_type_id=medical.id, subcategory="OTC", name="Paracetamol")
    amox = models.CatalogItem(code="DG0901", store_type_id=medical.id, subcategory="Rx", name="Antibiotics", requires_prescription=True)
    db.add_all([atta, para, amox])
    db.flush()
    items = {
        "atta": models.StoreItem(store_id=shop.id, catalog_item_id=atta.id, price_paise=45000),  # Rs 450
        "para": models.StoreItem(store_id=pharmacy.id, catalog_item_id=para.id, price_paise=3000),
        "amox": models.StoreItem(store_id=pharmacy.id, catalog_item_id=amox.id, price_paise=12000),
        "out": models.StoreItem(store_id=shop.id, custom_name="Sold out thing", price_paise=20000, available=False),
        "atta2": models.StoreItem(store_id=shop2.id, catalog_item_id=atta.id, price_paise=42000),  # cheaper at the other shop
        "pickle": models.StoreItem(store_id=shop2.id, custom_name="Homemade pickle", price_paise=15000),
    }
    db.add_all(items.values())
    db.commit()
    return {"village": village, "other": other, "shop": shop, "pharmacy": pharmacy, "shop2": shop2, "items": items, "users": users,
            "auth": {k: {"Authorization": "Bearer " + security.create_token(u)} for k, u in users.items()}}


def shop_block(store, items, payment_method="cod", **over):
    """items: list of (StoreItem, quantity)."""
    return {"store_id": store.id, "payment_method": payment_method,
            "items": [{"store_item_id": si.id, "quantity": q} for si, q in items], **over}


def checkout_body(world, key="key-00000001", shops=None, **over):
    body = {
        "idempotency_key": key, "customer_phone": "9876543210", "customer_name": "Ramesh",
        "village_id": world["village"].id, "ward_id": world["village"].wards[0].id, "landmark": "Near Hanuman temple",
        "shops": shops or [shop_block(world["shop"], [(world["items"]["atta"], 2)])],
    }
    body.update(over)
    return body
