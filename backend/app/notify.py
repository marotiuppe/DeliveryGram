"""OTP delivery. Email for now (see app/mailer.py). Other channels (WhatsApp, SMS, voice) plug in by adding a function here;
see docs/OTP_AND_IDENTITY_RESEARCH.md."""
import logging

from app import config, mailer

log = logging.getLogger("deliverygram.notify")


def send_otp_email(to: str, code: str) -> None:
    subject = "Your DeliveryGram login code"
    body = f"Your DeliveryGram login code is {code}. It expires in {config.OTP_TTL_MINUTES} minutes. Do not share it."
    if mailer.send(to, subject, body):
        return
    if config.ENV == "production":
        log.error("OTP email to %s was not sent (%s)", to, mailer.last_error)  # the code is never logged in production
    elif not mailer.configured():
        log.warning("DEV MODE (email not configured): OTP for %s is %s", to, code)
