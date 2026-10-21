from sqlalchemy import func, select

from app import models
from app.seed import DEFAULT_XLSX, import_catalog


def test_import_catalog_is_idempotent(db):
    n = import_catalog(db, DEFAULT_XLSX)
    assert n == 251
    import_catalog(db, DEFAULT_XLSX)
    assert db.scalar(select(func.count()).select_from(models.CatalogItem)) == 251
    assert db.scalar(select(func.count()).select_from(models.StoreType)) == 8
    rx = db.scalar(select(func.count()).select_from(models.CatalogItem).where(models.CatalogItem.requires_prescription.is_(True)))
    assert rx >= 7  # at least the prescription medicines


def test_startup_check_explains_an_unmigrated_database():
    import pytest
    from sqlalchemy import create_engine

    from app.db import Base, check_database_ready

    empty = create_engine("sqlite://")
    with pytest.raises(RuntimeError, match="alembic upgrade head"):
        check_database_ready(empty)
    full = create_engine("sqlite://")
    Base.metadata.create_all(full)
    from sqlalchemy import text
    with full.begin() as c:
        c.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
    check_database_ready(full)  # all required tables present: no error
