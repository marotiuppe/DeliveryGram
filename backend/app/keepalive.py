"""Stops Render's free plan from spinning the API down after 15 idle minutes (pattern from the Program-Practice project).

The service calls its OWN PUBLIC url (RENDER_EXTERNAL_URL, which Render sets automatically) every KEEPALIVE_SECONDS, so the
request enters through Render's edge and counts as inbound traffic; calling localhost would not help. /health does not touch the
database on purpose, so a scale-to-zero database such as Neon can still sleep.

Limits: it only works while the service is already awake (a redeploy or restart still cold-starts it, about a minute), and one
always-awake free service uses about 720-744 of the workspace's 750 free instance hours per month, so a SECOND always-awake free
service in the same workspace would get both suspended. Set KEEPALIVE_SECONDS=0 to turn it off.
"""
import asyncio
import logging
import os
import time
import urllib.request

log = logging.getLogger("deliverygram.keepalive")

status: dict = {"enabled": False, "url": "", "last_at": None, "last_ok": None, "last_error": ""}


def interval_seconds() -> int:
    try:
        return int(os.environ.get("KEEPALIVE_SECONDS", "300"))
    except ValueError:
        return 300


def target_url() -> str:
    base = os.environ.get("KEEPALIVE_URL") or os.environ.get("RENDER_EXTERNAL_URL") or ""
    return base.rstrip("/") + "/health" if base else ""


def ping(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            ok = 200 <= r.status < 300
            status.update(last_at=time.time(), last_ok=ok, last_error="" if ok else f"HTTP {r.status}")
            return ok
    except Exception as exc:  # never let a failed ping crash the loop
        status.update(last_at=time.time(), last_ok=False, last_error=f"{type(exc).__name__}: {exc}")
        log.warning("keep-alive failed: %s", exc)
        return False


async def run(url: str, seconds: int) -> None:
    while True:
        await asyncio.sleep(seconds)
        await asyncio.to_thread(ping, url)


def start() -> asyncio.Task | None:
    """Start the loop if this is a Render-style deployment (or KEEPALIVE_URL is set) and it has not been disabled."""
    url, seconds = target_url(), interval_seconds()
    status.update(enabled=bool(url) and seconds > 0, url=url)
    if not status["enabled"]:
        return None
    log.info("keep-alive: calling %s every %s s", url, seconds)
    return asyncio.create_task(run(url, seconds))
