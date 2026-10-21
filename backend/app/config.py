import os


def database_url() -> str:
    """Render supplies postgres:// or postgresql://; SQLAlchemy with psycopg3 needs postgresql+psycopg://."""
    url = os.environ.get("DATABASE_URL", "sqlite:///./deliverygram.db")
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


ENV = os.environ.get("ENV", "development")  # "production" disables dev conveniences
# Must be set to a long random value in production (Render: generateValue).
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-change-me")
TOKEN_DAYS = int(os.environ.get("TOKEN_DAYS", "30"))

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()

OTP_TTL_MINUTES = int(os.environ.get("OTP_TTL_MINUTES", "10"))
OTP_MAX_ATTEMPTS = 5
OTP_MAX_REQUESTS_PER_WINDOW = 3  # per email per OTP_TTL_MINUTES
PIN_MAX_FAILURES = 5
PIN_LOCK_MINUTES = 15

# Email settings (BREVO_API_KEY, MAIL_FROM, SMTP_*) are read by app/mailer.py. Keep-alive settings by app/keepalive.py.

DELIVERY_FEE_PAISE = int(os.environ.get("DELIVERY_FEE_PAISE", "2000"))
MIN_ORDER_PAISE = int(os.environ.get("MIN_ORDER_PAISE", "10000"))
# UPI/prepaid orders, prescription orders and orders at or above this value need the delivery code at handover.
DELIVERY_CODE_THRESHOLD_PAISE = int(os.environ.get("DELIVERY_CODE_THRESHOLD_PAISE", "200000"))
