"""Email (Brevo HTTP API / SMTP / memory), the Render keep-alive, and the admin System screen. No real network calls."""
import asyncio
import io
import json
import urllib.error

import pytest

from app import keepalive, mailer, notify


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in ("BREVO_API_KEY", "MAIL_FROM", "MAIL_BACKEND", "SMTP_USER", "SMTP_PASSWORD", "SMTP_HOST", "SMTP_PORT", "KEEPALIVE_URL", "RENDER_EXTERNAL_URL", "KEEPALIVE_SECONDS"):
        monkeypatch.delenv(k, raising=False)
    mailer.outbox.clear()
    mailer.last_error = ""
    keepalive.status.update(enabled=False, url="", last_at=None, last_ok=None, last_error="")


class FakeResponse:
    def __init__(self, status=201):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# ---------- mailer ----------

def test_memory_backend_collects_messages(monkeypatch):
    monkeypatch.setenv("MAIL_BACKEND", "memory")
    assert mailer.configured() and mailer.send("a@b.co", "Hi", "Body") is True
    assert mailer.outbox == [{"to": "a@b.co", "subject": "Hi", "body": "Body", "html": None}]


def test_unconfigured_mail_fails_softly_and_says_why():
    assert mailer.configured() is False and mailer.backend() == "not configured"
    assert mailer.send("a@b.co", "Hi", "Body") is False
    assert "not configured" in mailer.last_error


def test_brevo_request_shape(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "key-123")
    monkeypatch.setenv("MAIL_FROM", "DeliveryGram <no-reply@example.com>")
    seen = {}

    def fake_urlopen(req, timeout=0):
        seen.update(url=req.full_url, headers={k.lower(): v for k, v in req.header_items()}, body=json.loads(req.data), timeout=timeout)
        return FakeResponse(201)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert mailer.send("villager@example.com", "Code", "123456", html="<b>123456</b>") is True
    assert seen["url"] == "https://api.brevo.com/v3/smtp/email" and seen["headers"]["api-key"] == "key-123"
    assert seen["body"]["sender"] == {"email": "no-reply@example.com", "name": "DeliveryGram"}
    assert seen["body"]["to"] == [{"email": "villager@example.com"}] and seen["body"]["textContent"] == "123456" and seen["body"]["htmlContent"] == "<b>123456</b>"
    assert seen["timeout"] == 20 and mailer.last_error == ""


def test_brevo_rejection_is_recorded_not_raised(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "key-123")
    monkeypatch.setenv("MAIL_FROM", "no-reply@example.com")

    def reject(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b'{"message":"Key not found"}'))

    monkeypatch.setattr("urllib.request.urlopen", reject)
    assert mailer.send("a@b.co", "Hi", "Body") is False
    assert "HTTP 401" in mailer.last_error and "Key not found" in mailer.last_error


def test_network_failure_is_recorded(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "key-123")
    monkeypatch.setenv("MAIL_FROM", "no-reply@example.com")
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("network down")))
    assert mailer.send("a@b.co", "Hi", "Body") is False and "network down" in mailer.last_error


def test_brevo_wins_over_smtp_and_secrets_never_appear_in_backend_text(monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "super-secret-key")
    monkeypatch.setenv("MAIL_FROM", "no-reply@example.com")
    monkeypatch.setenv("SMTP_USER", "me@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "super-secret-password")
    monkeypatch.setattr("smtplib.SMTP_SSL", lambda *a, **k: (_ for _ in ()).throw(AssertionError("SMTP must not be used when Brevo is configured")))
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: FakeResponse(201))
    assert mailer.send("a@b.co", "Hi", "Body") is True
    text = mailer.backend()
    assert "Brevo" in text and "super-secret" not in text


def test_smtp_path_and_free_plan_warning(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "me@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "pw")
    assert "blocked on Render" in mailer.backend()
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, context=None, timeout=0):
            sent["host"], sent["port"] = host, port

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, user, pw):
            sent["login"] = (user, pw)

        def send_message(self, msg):
            sent["to"], sent["subject"] = msg["To"], msg["Subject"]

    monkeypatch.setattr("smtplib.SMTP_SSL", FakeSMTP)
    assert mailer.send("a@b.co", "Hi", "Body") is True
    assert sent == {"host": "smtp.gmail.com", "port": 465, "login": ("me@gmail.com", "pw"), "to": "a@b.co", "subject": "Hi"}


def test_otp_email_contains_the_code_and_dev_mode_logs_it(monkeypatch, caplog):
    monkeypatch.setenv("MAIL_BACKEND", "memory")
    notify.send_otp_email("a@b.co", "482913")
    assert "482913" in mailer.outbox[0]["body"] and "10 minutes" in mailer.outbox[0]["body"]
    monkeypatch.delenv("MAIL_BACKEND")
    with caplog.at_level("WARNING"):
        notify.send_otp_email("a@b.co", "111222")
    assert "111222" in caplog.text  # development without email configured: the code is shown in the log


def test_production_never_logs_the_code(monkeypatch, caplog):
    from app import config
    monkeypatch.setattr(config, "ENV", "production")
    with caplog.at_level("DEBUG"):
        notify.send_otp_email("a@b.co", "999888")
    assert "999888" not in caplog.text and "was not sent" in caplog.text


# ---------- keep-alive ----------

def test_keepalive_targets_the_public_url_only(monkeypatch):
    assert keepalive.target_url() == ""
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://dg-api.onrender.com/")
    assert keepalive.target_url() == "https://dg-api.onrender.com/health"
    monkeypatch.setenv("KEEPALIVE_URL", "https://custom.example.com")
    assert keepalive.target_url() == "https://custom.example.com/health"


def test_keepalive_is_off_locally_and_can_be_disabled(monkeypatch):
    async def go():
        assert keepalive.start() is None  # no RENDER_EXTERNAL_URL: nothing to call
        monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://dg-api.onrender.com")
        monkeypatch.setenv("KEEPALIVE_SECONDS", "0")
        assert keepalive.start() is None and keepalive.status["enabled"] is False  # saves free instance hours when set to 0
        monkeypatch.setenv("KEEPALIVE_SECONDS", "junk")
        assert keepalive.interval_seconds() == 300

    asyncio.run(go())


def test_ping_records_success_and_failure(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: FakeResponse(200))
    assert keepalive.ping("https://x/health") is True and keepalive.status["last_ok"] is True
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("boom")))
    assert keepalive.ping("https://x/health") is False
    assert keepalive.status["last_ok"] is False and "boom" in keepalive.status["last_error"]


def test_keepalive_loop_keeps_pinging_even_when_every_ping_fails(monkeypatch):
    calls = []
    monkeypatch.setattr(keepalive, "ping", lambda url: calls.append(url) or False)  # ping() reports failure by returning False

    async def go():
        task = asyncio.create_task(keepalive.run("https://x/health", 0.01))
        await asyncio.sleep(0.15)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(go())
    assert len(calls) >= 3 and set(calls) == {"https://x/health"}


def test_app_starts_the_keepalive_when_deployed_on_render(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    started = []
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://dg-api.onrender.com")
    monkeypatch.setattr(keepalive, "run", lambda url, seconds: started.append((url, seconds)) or asyncio.sleep(3600))
    monkeypatch.setattr("app.main.check_database_ready", lambda: None)
    with TestClient(app):
        pass  # entering the client runs the lifespan startup
    assert started == [("https://dg-api.onrender.com/health", 300)]


# ---------- admin System screen ----------

def test_system_endpoint_is_admin_only_and_never_leaks_secrets(client, world, monkeypatch):
    monkeypatch.setenv("BREVO_API_KEY", "super-secret-key")
    monkeypatch.setenv("MAIL_FROM", "DeliveryGram <no-reply@example.com>")
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
    mailer.send("a@b.co", "Hi", "Body")
    for who in ("customer", "merchant", "rider", "agent"):
        assert client.get("/api/admin/system", headers=world["auth"][who]).status_code == 403
    r = client.get("/api/admin/system", headers=world["auth"]["admin"])
    assert r.status_code == 200
    body = r.json()
    assert body["database"] in ("sqlite", "postgresql") and body["email_configured"] is True
    assert "Brevo" in body["email_backend"] and "offline" in body["last_email_error"]
    assert "super-secret-key" not in r.text and "postgres" not in body["keepalive_url"]
