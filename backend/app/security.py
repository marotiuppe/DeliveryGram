import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import config, models
from app.db import get_db

_bearer = HTTPBearer(auto_error=False)


def hash_pin(pin: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(pin.encode(), salt=salt, n=2**14, r=8, p=1)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_pin(pin: str, stored: str) -> bool:
    try:
        salt_b64, digest_b64 = stored.split("$")
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(digest_b64)
    except ValueError:
        return False
    actual = hashlib.scrypt(pin.encode(), salt=salt, n=2**14, r=8, p=1)
    return hmac.compare_digest(actual, expected)


def hash_otp(email: str, code: str) -> str:
    return hmac.new(config.SECRET_KEY.encode(), f"{email}:{code}".encode(), hashlib.sha256).hexdigest()


def new_otp() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def new_delivery_code() -> str:
    return f"{secrets.randbelow(10**4):04d}"


def create_token(user: models.User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=config.TOKEN_DAYS)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, config.SECRET_KEY, algorithm="HS256")


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)
) -> models.User:
    if not creds:
        raise HTTPException(401, "Login required")
    try:
        claims = jwt.decode(creds.credentials, config.SECRET_KEY, algorithms=["HS256"])
        user = db.get(models.User, int(claims["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired token")
    if not user or not user.active:
        raise HTTPException(401, "Account disabled")
    return user


def require_roles(*roles: str):
    def dep(user: models.User = Depends(current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(403, "Not allowed for your role")
        return user
    return dep
