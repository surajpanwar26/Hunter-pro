import queue
from typing import Callable, Optional

# Thread-safe queue for log messages
_log_queue: "queue.Queue[str]" = queue.Queue()
_subscribers: list[Callable[[str], None]] = []


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


def subscribe(cb: Callable[[str], None]) -> None:
    """Subscribe a callback(msg) to receive all new messages."""
    if cb not in _subscribers:
        _subscribers.append(cb)


def unsubscribe(cb: Callable[[str], None]) -> None:
    if cb in _subscribers:
        _subscribers.remove(cb)


def get_queue() -> "queue.Queue[str]":
    return _log_queue
