"""Sends email. Chosen by environment variables (never commit them). Pattern taken from the Program-Practice project.

1. HTTP API (works on Render's FREE plan, which blocks SMTP ports): Brevo
     BREVO_API_KEY  API key from Brevo (Settings -> SMTP & API -> API keys)
     MAIL_FROM      sender address, which must be verified in Brevo (Senders, domains & dedicated IPs)
   Brevo's free plan allows about 300 emails a day.
2. SMTP (any provider; needs a host that allows outbound SMTP, e.g. a paid Render instance or your own PC)
     SMTP_HOST / SMTP_PORT (default 465, implicit TLS) / SMTP_USER / SMTP_PASSWORD, MAIL_FROM optional (defaults to SMTP_USER)
If both are set, the HTTP API is used. Set MAIL_BACKEND=memory in tests to collect messages in `outbox`.

Environment is read on every call, so tests and the admin System page always see the current settings.
"""
import json
import logging
import os
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage
from email.utils import parseaddr

log = logging.getLogger("deliverygram.mailer")

outbox: list[dict] = []  # only used when MAIL_BACKEND=memory
last_error = ""  # why the most recent send failed ("" if it worked); shown on the admin System screen


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _memory() -> bool:
    return _env("MAIL_BACKEND") == "memory"


def _from() -> str:
    return _env("MAIL_FROM") or _env("SMTP_USER")


def _use_brevo() -> bool:
    return bool(_env("BREVO_API_KEY") and _env("MAIL_FROM"))


def _use_smtp() -> bool:
    return bool(_env("SMTP_USER") and _env("SMTP_PASSWORD"))


def configured() -> bool:
    return _memory() or _use_brevo() or _use_smtp()


def backend() -> str:
    """Short description of how mail is sent, for the admin System screen. Never includes a key or password."""
    if _memory():
        return "memory (test)"
    if _use_brevo():
        return f"Brevo HTTP API, sending as {parseaddr(_env('MAIL_FROM'))[1]}"
    if _use_smtp():
        port = int(_env("SMTP_PORT", "465"))
        note = " (these ports are blocked on Render's free plan)" if port in (25, 465, 587) else ""
        return f"SMTP {_env('SMTP_HOST', 'smtp.gmail.com')}:{port} as {_env('SMTP_USER')}{note}"
    return "not configured"


def _send_brevo(to: str, subject: str, body: str, html: str | None) -> bool:
    global last_error
    name, address = parseaddr(_env("MAIL_FROM"))
    payload = {"sender": {"email": address, **({"name": name} if name else {})}, "to": [{"email": to}], "subject": subject, "textContent": body}
    if html:
        payload["htmlContent"] = html
    req = urllib.request.Request(
        _env("BREVO_URL", "https://api.brevo.com/v3/smtp/email"), data=json.dumps(payload).encode(), method="POST",
        headers={"api-key": _env("BREVO_API_KEY"), "content-type": "application/json", "accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            ok = 200 <= r.status < 300
            last_error = "" if ok else f"Brevo answered HTTP {r.status}"
            return ok
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:300].decode("utf-8", "replace")
        last_error = f"Brevo rejected the message: HTTP {exc.code} {detail}"
        log.error("Brevo rejected %r to %s: HTTP %s %s", subject, to, exc.code, detail)
    except Exception as exc:  # network down, DNS, timeout...
        last_error = f"{type(exc).__name__}: {exc}"
        log.exception("could not send %r to %s through Brevo", subject, to)
    return False


def _send_smtp(to: str, subject: str, body: str, html: str | None) -> bool:
    global last_error
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = _from(), to, subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    host, port = _env("SMTP_HOST", "smtp.gmail.com"), int(_env("SMTP_PORT", "465"))
    try:
        ctx = ssl.create_default_context()
        if port == 465:  # implicit TLS
            conn = smtplib.SMTP_SSL(host, port, context=ctx, timeout=20)
        else:  # 587 / 2525 / ...: plain connect, then upgrade with STARTTLS before logging in
            conn = smtplib.SMTP(host, port, timeout=20)
            conn.ehlo()
            conn.starttls(context=ctx)
            conn.ehlo()
        with conn as s:
            s.login(_env("SMTP_USER"), _env("SMTP_PASSWORD"))
            s.send_message(msg)
        last_error = ""
        return True
    except Exception as exc:
        last_error = f"{type(exc).__name__}: {exc}"
        log.exception("could not send %r to %s", subject, to)
        return False


def send(to: str, subject: str, body: str, html: str | None = None) -> bool:
    """Send one message. Blocking: call it from a background task. Returns False (and records last_error) on failure."""
    global last_error
    if _memory():
        outbox.append({"to": to, "subject": subject, "body": body, "html": html})
        return True
    if not configured():
        last_error = "Email is not configured (set BREVO_API_KEY and MAIL_FROM)"
        log.warning("mail not configured; would have sent %r to %s", subject, to)
        return False
    return _send_brevo(to, subject, body, html) if _use_brevo() else _send_smtp(to, subject, body, html)
