from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.db import get_db

router = APIRouter(tags=["catalog"])


@router.get("/store-types", response_model=list[schemas.StoreTypeOut])
def list_store_types(db: Session = Depends(get_db)):
    return db.scalars(select(models.StoreType).order_by(models.StoreType.id)).all()


@router.get("/villages", response_model=list[schemas.VillageOut])
def list_villages(db: Session = Depends(get_db)):
    from app.routers.admin import village_out  # one place decides the effective fee and minimum

    villages = db.scalars(select(models.Village).options(joinedload(models.Village.wards)).order_by(models.Village.name)).unique().all()
    return [village_out(v) for v in villages]


@router.get("/catalog/items", response_model=list[schemas.CatalogItemOut])
def list_catalog_items(
    store_type: str | None = None,
    q: str | None = Query(default=None, max_length=60),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(models.CatalogItem).where(models.CatalogItem.active.is_(True))
    if store_type:
        stmt = stmt.join(models.StoreType).where(models.StoreType.code == store_type)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(models.CatalogItem.name.ilike(like) | models.CatalogItem.name_hi.ilike(like))
    return db.scalars(stmt.order_by(models.CatalogItem.id).limit(limit).offset(offset)).all()


@router.get("/stores", response_model=list[schemas.StoreOut])
def list_stores(village_id: int | None = None, store_type: str | None = None, db: Session = Depends(get_db)):
    stmt = select(models.Store).where(models.Store.deleted_at.is_(None))
    if village_id:
        stmt = stmt.where(models.Store.village_id == village_id)
    if store_type:
        stmt = stmt.join(models.StoreType).where(models.StoreType.code == store_type)
    return db.scalars(stmt.order_by(models.Store.name)).all()


@router.get("/stores/{store_id}", response_model=schemas.StoreOut)
def get_store(store_id: int, db: Session = Depends(get_db)):
    store = db.get(models.Store, store_id)
    if not store or store.deleted_at is not None:
        raise HTTPException(404, "Store not found")
    return store


@router.get("/stores/{store_id}/items", response_model=list[schemas.StoreItemOut])
def list_store_items(store_id: int, db: Session = Depends(get_db)):
    store = db.get(models.Store, store_id)
    if not store or store.deleted_at is not None:
        raise HTTPException(404, "Store not found")
    rows = db.scalars(
        select(models.StoreItem).options(joinedload(models.StoreItem.catalog_item)).where(models.StoreItem.store_id == store_id)
    ).all()
    out = []
    for r in rows:
        ci = r.catalog_item
        out.append(schemas.StoreItemOut(
            id=r.id, store_id=r.store_id, catalog_item_id=r.catalog_item_id,
            name=r.custom_name or (ci.name if ci else "Item"),
            name_hi=ci.name_hi if ci else None,
            price_paise=r.price_paise, available=r.available,
            requires_prescription=bool(ci and ci.requires_prescription),
            image_path=ci.image_path if ci else None,
        ))
    return out


@router.get("/search/items", response_model=list[schemas.SearchHit])
def search_items(
    q: str = Query(min_length=2, max_length=60),
    village_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Find an item in any open shop (cheapest first), for when the chosen shop does not have it."""
    like = f"%{q}%"
    stmt = (
        select(models.StoreItem, models.Store, models.CatalogItem)
        .join(models.Store, models.Store.id == models.StoreItem.store_id)
        .outerjoin(models.CatalogItem, models.CatalogItem.id == models.StoreItem.catalog_item_id)
        .where(
            models.StoreItem.available.is_(True), models.Store.is_open.is_(True), models.Store.deleted_at.is_(None),
            models.StoreItem.custom_name.ilike(like) | models.CatalogItem.name.ilike(like) | models.CatalogItem.name_hi.ilike(like),
        )
        .order_by(models.StoreItem.price_paise, models.Store.name)
        .limit(limit)
    )
    if village_id:
        stmt = stmt.where(models.Store.village_id == village_id)
    return [
        schemas.SearchHit(
            store_item_id=si.id, store_id=st.id, store_name=st.name, name=si.custom_name or ci.name, name_hi=ci.name_hi if ci else None,
            price_paise=si.price_paise, image_path=ci.image_path if ci else None, requires_prescription=bool(ci and ci.requires_prescription),
        )
        for si, st, ci in db.execute(stmt).all()
    ]
