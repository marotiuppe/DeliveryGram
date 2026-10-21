import os
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import config, keepalive
from app.db import check_database_ready
from app.routers import admin, auth, catalog, checkout, deliveries, khata, merchant, orders, staff

if config.ENV == "production" and config.SECRET_KEY == "dev-only-secret-change-me":
    raise RuntimeError("SECRET_KEY must be set in production")

@asynccontextmanager
async def lifespan(_: FastAPI):
    check_database_ready()  # stop at startup with instructions, not with a 500 on the first request
    task = keepalive.start()  # Render free plan: call our own public /health so the service does not sleep
    yield
    if task:
        task.cancel()


app = FastAPI(title="DeliveryGram API", version="0.4.0", lifespan=lifespan)

origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

for r in (catalog.router, auth.router, checkout.router, orders.router, deliveries.router, khata.router, merchant.router, staff.router, admin.router):
    app.include_router(r, prefix="/api")

_images = Path(os.environ.get("IMAGES_DIR", Path(__file__).resolve().parents[2] / "assets" / "catalog-images"))
if _images.is_dir():
    app.mount("/images", StaticFiles(directory=_images), name="images")


@app.get("/health")
def health():
    return {"status": "ok"}
