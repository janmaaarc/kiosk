"""Optional RFID reader background service.

Runs in a dedicated thread that polls an MFRC522 reader on a Raspberry Pi
and POSTs every scanned UID to the running Flask app's ``/check_rfid``.

Import guards ensure the kiosk still starts on laptops or any environment
without the Pi-specific libraries installed. To actually use it on the Pi,
install the optional extras and call ``start_rfid_watcher()`` on boot::

    sudo pip install mfrc522 RPi.GPIO spidev
    python -m kiosk_app.rfid_runner           # or import and call start_rfid_watcher

The watcher never crashes the kiosk: hardware errors are logged and retried.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional
from urllib import request as urlrequest
from urllib.parse import urlencode

log = logging.getLogger("kiosk.rfid")

try:  # Pi-only deps — absence is not an error
    from mfrc522 import SimpleMFRC522  # type: ignore[import-not-found]
    import RPi.GPIO as GPIO  # type: ignore[import-not-found]
    _HARDWARE_AVAILABLE = True
except Exception:  # noqa: BLE001
    SimpleMFRC522 = None  # type: ignore[assignment]
    GPIO = None  # type: ignore[assignment]
    _HARDWARE_AVAILABLE = False


def hardware_available() -> bool:
    """True when running on a Pi with the required libraries installed."""
    return _HARDWARE_AVAILABLE


def _default_handler(uid: str, server_url: str) -> None:
    """Fire-and-forget: open ``/rfid?uid=<uid>`` so the kiosk navigates."""
    url = f"{server_url.rstrip('/')}/rfid?{urlencode({'uid': uid})}"
    req = urlrequest.Request(url, method="GET")
    try:
        with urlrequest.urlopen(req, timeout=3) as resp:
            log.info("rfid uid=%s server_status=%s", uid, resp.status)
    except Exception as exc:  # noqa: BLE001
        log.warning("rfid request failed uid=%s: %s", uid, exc)


def _watcher(handler: Callable[[str], None], poll_interval: float) -> None:
    reader = SimpleMFRC522()  # type: ignore[call-arg]
    log.info("RFID watcher started")
    try:
        while True:
            try:
                uid, _text = reader.read()  # blocking call
                if uid:
                    handler(str(uid))
            except Exception as exc:  # noqa: BLE001
                log.exception("RFID read error: %s", exc)
                time.sleep(poll_interval)
    finally:
        if GPIO is not None:
            GPIO.cleanup()
        log.info("RFID watcher stopped")


def start_rfid_watcher(
    server_url: str = "http://127.0.0.1:8000",
    handler: Optional[Callable[[str], None]] = None,
    poll_interval: float = 0.5,
) -> Optional[threading.Thread]:
    """Start a background thread that reads RFID scans.

    Returns ``None`` when hardware is unavailable (e.g. on a laptop); the
    caller should treat that as a soft failure and continue starting the
    app normally.
    """
    if not _HARDWARE_AVAILABLE:
        log.info("RFID hardware not detected — watcher not started")
        return None

    active_handler = handler or (lambda uid: _default_handler(uid, server_url))
    thread = threading.Thread(
        target=_watcher,
        args=(active_handler, poll_interval),
        daemon=True,
        name="rfid-watcher",
    )
    thread.start()
    return thread
