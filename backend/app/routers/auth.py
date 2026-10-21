import hmac
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config, models, notify, security
from app.db import get_db

router = APIRouter(tags=["auth"])

PHONE = r"^[6-9]\d{9}$"
PIN = r"^\d{4,6}$"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)  # SQLite returns naive datetimes


class OtpRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=120)


class OtpVerify(OtpRequest):
    code: str = Field(pattern=r"^\d{6}$")


class PinLogin(BaseModel):
    phone: str = Field(pattern=PHONE)
    pin: str = Field(pattern=PIN)


class PinChange(BaseModel):
    old_pin: str | None = Field(default=None, pattern=PIN)
    new_pin: str = Field(pattern=PIN)


class TokenOut(BaseModel):
    access_token: str
    role: str
    pin_must_change: bool = False


class MeOut(BaseModel):
    id: int
    role: str
    name: str | None
    phone: str | None
    email: str | None
    pin_must_change: bool


@router.post("/auth/otp/request")
def request_otp(body: OtpRequest, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    window = _now() - timedelta(minutes=config.OTP_TTL_MINUTES)
    recent = db.scalar(select(func.count()).select_from(models.OtpCode).where(models.OtpCode.email == email, models.OtpCode.created_at > window))
    if recent >= config.OTP_MAX_REQUESTS_PER_WINDOW:
        raise HTTPException(429, "Too many requests. Try again later.")
    code = security.new_otp()
    db.add(models.OtpCode(email=email, code_hash=security.hash_otp(email, code), expires_at=_now() + timedelta(minutes=config.OTP_TTL_MINUTES)))
    db.commit()
    tasks.add_task(notify.send_otp_email, email, code)
    return {"sent": True}  # same answer whether or not the account exists


@router.post("/auth/otp/verify", response_model=TokenOut)
def verify_otp(body: OtpVerify, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    otp = db.scalar(
        select(models.OtpCode).where(models.OtpCode.email == email, models.OtpCode.used.is_(False)).order_by(models.OtpCode.id.desc())
    )
    if not otp or _aware(otp.expires_at) < _now() or otp.attempts >= config.OTP_MAX_ATTEMPTS:
        raise HTTPException(400, "Code expired or invalid. Request a new one.")
    otp.attempts += 1
    if not hmac.compare_digest(otp.code_hash, security.hash_otp(email, body.code)):
        db.commit()
        raise HTTPException(400, "Wrong code")
    otp.used = True
    user = db.scalar(select(models.User).where(models.User.email == email))
    if not user:  # self-registration is always a customer; staff roles are granted by an admin
        user = models.User(email=email, role="customer", active=True)
        db.add(user)
    if not user.active:
        db.commit()
        raise HTTPException(403, "Account disabled")
    db.commit()
    return TokenOut(access_token=security.create_token(user), role=user.role, pin_must_change=user.pin_must_change)


@router.post("/auth/pin/login", response_model=TokenOut)
def pin_login(body: PinLogin, db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.phone == body.phone))
    bad = HTTPException(401, "Wrong phone or PIN")
    if not user or not user.pin_hash or not user.active:
        raise bad
    if user.locked_until and _aware(user.locked_until) > _now():
        raise HTTPException(429, "Too many wrong attempts. Try again in a few minutes.")
    if not security.verify_pin(body.pin, user.pin_hash):
        user.failed_pin_attempts += 1
        if user.failed_pin_attempts >= config.PIN_MAX_FAILURES:
            user.locked_until = _now() + timedelta(minutes=config.PIN_LOCK_MINUTES)
            user.failed_pin_attempts = 0
        db.commit()
        raise bad
    user.failed_pin_attempts, user.locked_until = 0, None
    db.commit()
    return TokenOut(access_token=security.create_token(user), role=user.role, pin_must_change=user.pin_must_change)


@router.post("/auth/pin/change")
def change_pin(body: PinChange, user: models.User = Depends(security.current_user), db: Session = Depends(get_db)):
    if user.pin_hash and not (body.old_pin and security.verify_pin(body.old_pin, user.pin_hash)):
        raise HTTPException(403, "Current PIN is wrong")
    user.pin_hash, user.pin_must_change = security.hash_pin(body.new_pin), False
    db.commit()
    return {"ok": True}


@router.get("/me", response_model=MeOut)
def me(user: models.User = Depends(security.current_user)):
    return user
