import queue
import threading
from datetime import datetime
from typing import Callable, Optional, Any

# Thread-safe queue for log messages
_log_queue: "queue.Queue[str]" = queue.Queue()
_event_queue: "queue.Queue[dict]" = queue.Queue()
_subscribers: list[Callable[[str], None]] = []
_event_subscribers: list[Callable[[dict], None]] = []


def publish_event(event: str, data: Optional[dict] = None, source: str = "system") -> None:
    """Publish structured telemetry event for deterministic dashboard updates."""
    payload = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        "source": source,
        "data": data or {},
    }
    try:
        _event_queue.put_nowait(payload)
    except Exception:
        pass
    for sub in list(_event_subscribers):
        try:
            sub(payload)
        except Exception:
            pass


def publish(msg: str, tag: Optional[str] = None, meta: Optional[dict] = None) -> None:
    """Publish a log message to the queue and notify subscribers.

    If `tag` is provided, it prefixes the message with `[TAG] ` for easy filtering in UIs.
    """
    try:
        text = f"[{tag}] {msg}" if tag else msg
        _log_queue.put_nowait(text)
    except Exception:
        pass
    for sub in list(_subscribers):
        try:
            sub(text)
        except Exception:
            pass

    if meta and isinstance(meta, dict) and meta.get("event"):
        try:
            publish_event(
                event=str(meta.get("event")),
                data=meta.get("data") if isinstance(meta.get("data"), dict) else meta,
                source=str(meta.get("source", "log")),
            )
        except Exception:
            pass


def subscribe(cb: Callable[[str], None]) -> None:
    """Subscribe a callback(msg) to receive all new messages."""
    if cb not in _subscribers:
        _subscribers.append(cb)


def unsubscribe(cb: Callable[[str], None]) -> None:
    if cb in _subscribers:
        _subscribers.remove(cb)


def subscribe_events(cb: Callable[[dict], None]) -> None:
    if cb not in _event_subscribers:
        _event_subscribers.append(cb)


def unsubscribe_events(cb: Callable[[dict], None]) -> None:
    if cb in _event_subscribers:
        _event_subscribers.remove(cb)


def get_queue() -> "queue.Queue[str]":
    return _log_queue


def get_event_queue() -> "queue.Queue[dict]":
    return _event_queue
