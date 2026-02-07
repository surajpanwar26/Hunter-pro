import threading
from collections import defaultdict, deque
from typing import Dict, List

_lock = threading.Lock()
_metrics: Dict[str, float] = defaultdict(float)
_counters: Dict[str, int] = defaultdict(int)
_time_series: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))  # keep last 200 samples


def inc(name: str, n: int = 1) -> None:
    with _lock:
        _counters[name] += n


def set_metric(name: str, value: float) -> None:
    with _lock:
        _metrics[name] = value


def get_metric(name: str, default: float = 0.0) -> float:
    """Get a single metric or counter value by name."""
    with _lock:
        if name in _metrics:
            return _metrics[name]
        if name in _counters:
            return float(_counters[name])
        return default


def append_sample(name: str, value: float) -> None:
    """Append a float sample to a named time series."""
    with _lock:
        _time_series[name].append(float(value))


def get_time_series(name: str) -> List[float]:
    with _lock:
        return list(_time_series.get(name, []))


def get_average(name: str) -> float:
    """Average of time series samples or metric if present."""
    with _lock:
        series = _time_series.get(name)
        if series and len(series) > 0:
            return sum(series) / len(series)
        return _metrics.get(name, 0.0)


def estimate_eta(avg_seconds_per_item: float, remaining_items: int) -> float:
    """Estimate ETA in seconds given avg seconds per item and remaining count."""
    try:
        return float(avg_seconds_per_item) * float(remaining_items)
    except Exception:
        return float('inf')


def get_metrics() -> dict:
    with _lock:
        # include basic metrics, counters, and last/avg samples
        out = {**_metrics, **{k: v for k, v in _counters.items()}}
        for name, series in _time_series.items():
            if series:
                out[f"{name}_avg"] = sum(series) / len(series)
                out[f"{name}_last"] = series[-1]
                out[f"{name}_count"] = len(series)
        return out


def get_sample_stats(name: str) -> dict:
    """Return basic sample stats for a time series."""
    with _lock:
        series = _time_series.get(name, None)
        if not series or len(series) == 0:
            return {"count": 0, "avg": 0.0, "min": 0.0, "max": 0.0, "last": 0.0}
        arr = list(series)
        return {"count": len(arr), "avg": sum(arr) / len(arr), "min": min(arr), "max": max(arr), "last": arr[-1]}


def get_eta(jobs_processed: int, max_jobs: int) -> float | None:
    """Estimate ETA in seconds given jobs processed and max jobs to process. Returns None if not estimable."""
    if max_jobs <= 0 or jobs_processed >= max_jobs:
        return None
    stats = get_sample_stats('job_time')
    if stats['count'] == 0:
        return None
    avg = stats['avg']
    remaining = max_jobs - jobs_processed
    try:
        return avg * remaining
    except Exception:
        return None


def reset_all() -> None:
    with _lock:
        _metrics.clear()
        _counters.clear()
        _time_series.clear()
