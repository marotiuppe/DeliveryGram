from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import database_url

_url = database_url()
if _url.startswith("sqlite"):
    engine = create_engine(_url, connect_args={"check_same_thread": False}, pool_pre_ping=True)
else:
    # Hosted Postgres (Neon etc.) closes idle connections and may be asleep: test a connection before use and recycle often.
    engine = create_engine(_url, pool_pre_ping=True, pool_recycle=240, pool_size=5, max_overflow=5, connect_args={"connect_timeout": 15})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_ready(eng=None) -> None:
    """Fail fast with a clear message instead of a 500 on the first login when migrations have not been run."""
    from sqlalchemy import inspect

    tables = set(inspect(eng or engine).get_table_names())
    missing = {"users", "stores", "orders", "alembic_version"} - tables
    if missing:
        raise RuntimeError(
            f"The database ({_url.split('@')[-1]}) is not set up (missing tables: {', '.join(sorted(missing))}). "
            "Run:  python -m alembic upgrade head   and then (development only)  python -m scripts.demo_data"
        )
