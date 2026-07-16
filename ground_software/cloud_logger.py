"""
Fire-and-forget cloud logger for SilverSat ground station.

Enqueues log events and delivers them asynchronously to the SilverSat
log-ingest Cloud Function endpoint.  The serial reader threads call
post_event() and return immediately; a single daemon thread drains
the queue.  If the endpoint is unreachable or not configured, events
are dropped with a warning — the ground station continues normally.

Configuration (environment variables):
  SILVERSAT_INGEST_URL      Full URL of the log-ingest Cloud Function
  SILVERSAT_INGEST_API_KEY  API key sent in the X-API-Key header
  SILVERSAT_SESSION_ID      Pass / session label (default: "unset")
  SILVERSAT_MODE            "live" or "test"      (default: "live")
"""

import json
import logging
import os
import queue
import threading
import uuid
from datetime import datetime, timezone
from urllib import request as _urlrequest
from urllib.error import HTTPError, URLError

_INGEST_URL = os.environ.get("SILVERSAT_INGEST_URL", "")
_API_KEY = os.environ.get("SILVERSAT_INGEST_API_KEY", "")
_DEFAULT_SESSION_ID = os.environ.get("SILVERSAT_SESSION_ID", "unset")
_DEFAULT_MODE = os.environ.get("SILVERSAT_MODE", "live")

_QUEUE_MAXSIZE = 500
_POST_TIMEOUT = 10  # seconds

_event_queue: queue.Queue = queue.Queue(maxsize=_QUEUE_MAXSIZE)
_worker_started = False
_worker_lock = threading.Lock()

log = logging.getLogger(__name__)


def _worker() -> None:
    """Background daemon thread: drain the queue and POST each event."""
    while True:
        event = _event_queue.get()
        try:
            if not (_INGEST_URL and _API_KEY):
                continue  # not configured; discard silently
            body = json.dumps(event).encode()
            req = _urlrequest.Request(
                _INGEST_URL,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": _API_KEY,
                },
                method="POST",
            )
            with _urlrequest.urlopen(req, timeout=_POST_TIMEOUT) as resp:
                if resp.status not in (200, 201):
                    log.warning(
                        "cloud_logger: unexpected HTTP %s for log_id=%s",
                        resp.status,
                        event.get("log_id"),
                    )
        except HTTPError as exc:
            log.warning(
                "cloud_logger: HTTP %s for log_id=%s", exc.code, event.get("log_id")
            )
        except URLError as exc:
            log.warning(
                "cloud_logger: network error for log_id=%s: %s",
                event.get("log_id"),
                exc.reason,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "cloud_logger: unexpected error for log_id=%s: %s",
                event.get("log_id"),
                exc,
            )
        finally:
            _event_queue.task_done()


def _ensure_worker() -> None:
    global _worker_started
    with _worker_lock:
        if not _worker_started:
            t = threading.Thread(target=_worker, name="cloud-logger", daemon=True)
            t.start()
            _worker_started = True


def post_event(
    source: str,
    details: dict,
    *,
    session_id: str | None = None,
    mode: str | None = None,
    device_timestamp: str | None = None,
) -> None:
    """Enqueue a log event for async delivery to the cloud ingest endpoint.

    Returns immediately and never raises.  Safe to call from any thread.

    Args:
        source:           Subsystem label, e.g. "ground_station" or "ground_radio".
        details:          Dict of subsystem-specific fields stored in the JSON
                          details column.
        session_id:       Override the default session ID for this event.
        mode:             Override the default mode ("live" / "test") for this event.
        device_timestamp: ISO 8601 UTC string; current time used when omitted.
    """
    if not _INGEST_URL:
        return  # cloud logging not configured — skip silently

    _ensure_worker()

    ts = device_timestamp or (
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    )
    event = {
        "log_id": str(uuid.uuid4()),
        "device_timestamp": ts,
        "source": source,
        "mode": mode or _DEFAULT_MODE,
        "session_id": session_id or _DEFAULT_SESSION_ID,
        "details": details,
    }

    try:
        _event_queue.put_nowait(event)
    except queue.Full:
        log.warning(
            "cloud_logger: queue full, dropping event source=%s", source
        )
