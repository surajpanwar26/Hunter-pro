import threading
from collections import defaultdict, deque
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

_lock = threading.RLock()  # Use RLock to allow nested locking
_metrics: Dict[str, float] = defaultdict(float)
_counters: Dict[str, int] = defaultdict(int)
_time_series: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))  # keep last 200 samples
_timestamps: Dict[str, datetime] = {}  # Track when metrics were last updated


@dataclass
class MetricSnapshot:
    """Snapshot of a metric at a point in time."""
    name: str
    value: float
    timestamp: datetime
    metric_type: str  # 'counter', 'gauge', 'sample'


def inc(name: str, n: int = 1) -> None:
    """Increment a counter metric."""
    with _lock:
        _counters[name] += n
        _timestamps[name] = datetime.now()


def dec(name: str, n: int = 1) -> None:
    """Decrement a counter metric."""
    with _lock:
        _counters[name] = max(0, _counters[name] - n)
        _timestamps[name] = datetime.now()


def set_metric(name: str, value: float) -> None:
    """Set a gauge metric to a specific value."""
    with _lock:
        _metrics[name] = value
        _timestamps[name] = datetime.now()


def get_metric(name: str, default: float = 0.0) -> float:
    """Get the current value of a metric."""
    with _lock:
        if name in _counters:
            return float(_counters[name])
        return _metrics.get(name, default)


def append_sample(name: str, value: float) -> None:
    """Append a float sample to a named time series."""
    with _lock:
        _time_series[name].append(float(value))
        _timestamps[name] = datetime.now()


def get_time_series(name: str) -> List[float]:
    """Get all samples from a time series."""
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
        if remaining_items <= 0:
            return 0.0
        return float(avg_seconds_per_item) * float(remaining_items)
    except (TypeError, ValueError):
        return float('inf')


def get_metrics() -> dict:
    """Get all metrics as a dictionary."""
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
            return {"count": 0, "avg": 0.0, "min": 0.0, "max": 0.0, "last": 0.0, "sum": 0.0}
        arr = list(series)
        return {
            "count": len(arr), 
            "avg": sum(arr) / len(arr), 
            "min": min(arr), 
            "max": max(arr), 
            "last": arr[-1],
            "sum": sum(arr)
        }


def get_eta(jobs_processed: int, max_jobs: int) -> Optional[float]:
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
    except (TypeError, ValueError):
        return None


def get_percentile(name: str, percentile: float) -> float:
    """Get a percentile value from a time series."""
    with _lock:
        series = _time_series.get(name)
        if not series or len(series) == 0:
            return 0.0
        sorted_data = sorted(series)
        index = int(percentile / 100 * (len(sorted_data) - 1))
        return sorted_data[min(index, len(sorted_data) - 1)]


def reset_metric(name: str) -> None:
    """Reset a specific metric."""
    with _lock:
        _metrics.pop(name, None)
        _counters.pop(name, None)
        _time_series.pop(name, None)
        _timestamps.pop(name, None)


def reset_all() -> None:
    """Reset all metrics."""
    with _lock:
        _metrics.clear()
        _counters.clear()
        _time_series.clear()
        _timestamps.clear()


def export_metrics() -> dict:
    """Export all metrics with metadata for persistence."""
    with _lock:
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": dict(_metrics),
            "counters": dict(_counters),
            "time_series": {k: list(v) for k, v in _time_series.items()},
            "last_updated": {k: v.isoformat() for k, v in _timestamps.items()}
        }
