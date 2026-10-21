from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.db import get_db

router = APIRouter(prefix="/merchant", tags=["merchant"])


class PriceUpdate(BaseModel):
    price_paise: int = Field(gt=0, le=100_000_000)
    available: bool = True


class CustomItem(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    price_paise: int = Field(gt=0, le=100_000_000)


class OpenUpdate(BaseModel):
    is_open: bool


def _own_store(db: Session, user: models.User, store_id: int) -> models.Store:
    store = db.get(models.Store, store_id)
    if not store or store.deleted_at is not None or (user.role != "admin" and store.owner_id != user.id):
        raise HTTPException(404, "Store not found")
    return store


@router.get("/stores", response_model=list[schemas.StoreOut])
def my_stores(user: models.User = Depends(security.require_roles("merchant", "admin")), db: Session = Depends(get_db)):
    stmt = select(models.Store).where(models.Store.deleted_at.is_(None))
    if user.role != "admin":
        stmt = stmt.where(models.Store.owner_id == user.id)
    return db.scalars(stmt).all()


@router.patch("/stores/{store_id}/open", response_model=schemas.StoreOut)
def set_open(store_id: int, body: OpenUpdate, user: models.User = Depends(security.require_roles("merchant", "admin")), db: Session = Depends(get_db)):
    store = _own_store(db, user, store_id)
    store.is_open = body.is_open
    db.commit()
    return store


@router.put("/stores/{store_id}/catalog/{catalog_item_id}", response_model=schemas.StoreItemOut)
def set_catalog_item(
    store_id: int, catalog_item_id: int, body: PriceUpdate,
    user: models.User = Depends(security.require_roles("merchant", "admin")), db: Session = Depends(get_db),
):
    """List a master-catalog item at the shop's own price, or toggle its availability."""
    store = _own_store(db, user, store_id)
    ci = db.get(models.CatalogItem, catalog_item_id)
    if not ci or not ci.active:
        raise HTTPException(404, "Catalog item not found")
    if ci.store_type_id != store.store_type_id:
        raise HTTPException(422, "This item belongs to a different kind of store")
    si = db.scalar(select(models.StoreItem).where(models.StoreItem.store_id == store.id, models.StoreItem.catalog_item_id == ci.id))
    if not si:
        si = models.StoreItem(store_id=store.id, catalog_item_id=ci.id, price_paise=body.price_paise)
        db.add(si)
    si.price_paise, si.available = body.price_paise, body.available
    db.commit()
    return _out(si, ci)


@router.post("/stores/{store_id}/custom-items", response_model=schemas.StoreItemOut, status_code=201)
def add_custom_item(
    store_id: int, body: CustomItem, user: models.User = Depends(security.require_roles("merchant", "admin")), db: Session = Depends(get_db)
):
    store = _own_store(db, user, store_id)
    si = models.StoreItem(store_id=store.id, custom_name=body.name, price_paise=body.price_paise)
    db.add(si)
    db.commit()
    return _out(si, None)


@router.patch("/stores/{store_id}/items/{item_id}", response_model=schemas.StoreItemOut)
def update_item(
    store_id: int, item_id: int, body: PriceUpdate, user: models.User = Depends(security.require_roles("merchant", "admin")), db: Session = Depends(get_db)
):
    store = _own_store(db, user, store_id)
    si = db.get(models.StoreItem, item_id)
    if not si or si.store_id != store.id:
        raise HTTPException(404, "Item not found")
    si.price_paise, si.available = body.price_paise, body.available
    db.commit()
    return _out(si, si.catalog_item)


def _out(si: models.StoreItem, ci: models.CatalogItem | None) -> schemas.StoreItemOut:
    return schemas.StoreItemOut(
        id=si.id, store_id=si.store_id, catalog_item_id=si.catalog_item_id,
        name=si.custom_name or (ci.name if ci else "Item"), name_hi=ci.name_hi if ci else None,
        price_paise=si.price_paise, available=si.available,
        requires_prescription=bool(ci and ci.requires_prescription), image_path=ci.image_path if ci else None,
    )
