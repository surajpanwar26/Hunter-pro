'''
Performance Optimization Utilities
Provides caching, memoization, lazy loading, and performance monitoring.

Author: Auto-generated improvement
'''

import functools
import time
import threading
import hashlib
from typing import TypeVar, Callable, Any, Optional, Dict
from collections import OrderedDict
from dataclasses import dataclass

T = TypeVar('T')


class LRUCache:
    """
    Thread-safe Least Recently Used (LRU) cache implementation.
    """
    
    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = value
            else:
                if len(self._cache) >= self.maxsize:
                    # Remove oldest item
                    self._cache.popitem(last=False)
                self._cache[key] = value
    
    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate
            }


class TTLCache:
    """
    Thread-safe Time-To-Live cache implementation.
    """
    
    def __init__(self, maxsize: int = 128, ttl_seconds: float = 300.0):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    return value
                else:
                    # Expired, remove it
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl if ttl is not None else self.ttl_seconds
        expiry = time.time() + ttl
        
        with self._lock:
            if len(self._cache) >= self.maxsize:
                # Remove expired entries first
                self._cleanup()
                
                # If still full, remove oldest
                if len(self._cache) >= self.maxsize:
                    oldest_key = min(self._cache.keys(), 
                                    key=lambda k: self._cache[k][1])
                    del self._cache[oldest_key]
            
            self._cache[key] = (value, expiry)
    
    def _cleanup(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired = [k for k, (_, exp) in self._cache.items() if exp <= now]
        for k in expired:
            del self._cache[k]
    
    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._cache.clear()


def memoize(maxsize: int = 128, ttl: Optional[float] = None):
    """
    Decorator to memoize function results.
    
    Args:
        maxsize: Maximum cache size
        ttl: Time-to-live in seconds (None for no expiry)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if ttl is not None:
            cache = TTLCache(maxsize=maxsize, ttl_seconds=ttl)
        else:
            cache = LRUCache(maxsize=maxsize)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Create cache key from arguments
            key_parts = [str(arg) for arg in args]
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key = hashlib.md5(str(key_parts).encode()).hexdigest()
            
            result = cache.get(key)
            if result is not None:
                return result
            
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        
        wrapper.cache = cache
        wrapper.cache_clear = cache.clear
        
        return wrapper
    return decorator


@dataclass
class TimingStats:
    """Statistics for timing measurements."""
    count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    
    @property
    def avg_time(self) -> float:
        return self.total_time / self.count if self.count > 0 else 0.0


class PerformanceMonitor:
    """
    Monitor and record performance metrics for functions.
    """
    
    def __init__(self):
        self._timings: Dict[str, TimingStats] = {}
        self._lock = threading.Lock()
    
    def record(self, name: str, duration: float) -> None:
        """Record a timing measurement."""
        with self._lock:
            if name not in self._timings:
                self._timings[name] = TimingStats()
            
            stats = self._timings[name]
            stats.count += 1
            stats.total_time += duration
            stats.min_time = min(stats.min_time, duration)
            stats.max_time = max(stats.max_time, duration)
    
    def get_stats(self, name: str) -> Optional[TimingStats]:
        """Get stats for a specific function."""
        with self._lock:
            return self._timings.get(name)
    
    def get_all_stats(self) -> Dict[str, TimingStats]:
        """Get all timing stats."""
        with self._lock:
            return dict(self._timings)
    
    def clear(self) -> None:
        """Clear all stats."""
        with self._lock:
            self._timings.clear()


# Global performance monitor
_perf_monitor = PerformanceMonitor()


def timed(name: Optional[str] = None, log: bool = False):
    """
    Decorator to time function execution.
    
    Args:
        name: Optional name for the timing (defaults to function name)
        log: Whether to log timing information
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        timing_name = name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                _perf_monitor.record(timing_name, duration)
                
                if log:
                    try:
                        from modules.helpers import print_lg
                        print_lg(f"[TIMING] {timing_name}: {duration:.4f}s")
                    except ImportError:
                        print(f"[TIMING] {timing_name}: {duration:.4f}s")
        
        return wrapper
    return decorator


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor."""
    return _perf_monitor


class LazyLoader:
    """
    Lazy loading wrapper for expensive objects.
    """
    
    def __init__(self, factory: Callable[[], T]):
        self._factory = factory
        self._value: Optional[T] = None
        self._loaded = False
        self._lock = threading.Lock()
    
    def get(self) -> T:
        """Get the lazily loaded value."""
        if not self._loaded:
            with self._lock:
                if not self._loaded:
                    self._value = self._factory()
                    self._loaded = True
        return self._value
    
    def reset(self) -> None:
        """Reset the lazy loader."""
        with self._lock:
            self._value = None
            self._loaded = False
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded


class BatchProcessor:
    """
    Process items in batches for better performance.
    """
    
    def __init__(
        self,
        processor: Callable[[list], list],
        batch_size: int = 10,
        flush_interval: float = 5.0
    ):
        self._processor = processor
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._buffer: list = []
        self._results: list = []
        self._lock = threading.Lock()
        self._last_flush = time.time()
    
    def add(self, item: Any) -> None:
        """Add item to batch buffer."""
        with self._lock:
            self._buffer.append(item)
            
            if len(self._buffer) >= self._batch_size:
                self._flush_locked()
            elif time.time() - self._last_flush >= self._flush_interval:
                self._flush_locked()
    
    def _flush_locked(self) -> None:
        """Flush buffer while holding lock."""
        if self._buffer:
            batch_results = self._processor(self._buffer)
            self._results.extend(batch_results)
            self._buffer = []
            self._last_flush = time.time()
    
    def flush(self) -> list:
        """Flush remaining items and return all results."""
        with self._lock:
            self._flush_locked()
            results = self._results
            self._results = []
            return results


def debounce(wait: float):
    """
    Decorator to debounce function calls.
    Only the last call within the wait period will be executed.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        timer = None
        lock = threading.Lock()
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> None:
            nonlocal timer
            
            with lock:
                if timer is not None:
                    timer.cancel()
                
                timer = threading.Timer(wait, func, args, kwargs)
                timer.start()
        
        return wrapper
    return decorator


def throttle(rate: float):
    """
    Decorator to throttle function calls.
    Limits calls to at most once per rate seconds.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        last_call = 0
        lock = threading.Lock()
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            nonlocal last_call
            
            with lock:
                now = time.time()
                if now - last_call >= rate:
                    last_call = now
                    return func(*args, **kwargs)
                return None
        
        return wrapper
    return decorator
