'''
Fault Tolerance Module
Provides retry mechanisms, circuit breakers, and graceful degradation utilities.

Author: Auto-generated improvement
'''

import functools
import time
import threading
from typing import Callable, TypeVar, Optional
from enum import Enum
from datetime import datetime

T = TypeVar('T')


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.
    Prevents cascading failures by stopping calls to failing services.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        self._lock = threading.Lock()
    
    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self._last_failure_time:
                    elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                    if elapsed >= self.recovery_timeout:
                        self._state = CircuitState.HALF_OPEN
                        self._half_open_calls = 0
            return self._state
    
    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0
    
    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
    
    def can_execute(self) -> bool:
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
        return False
    
    def reset(self) -> None:
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._last_failure_time = None


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        config: RetryConfig instance with retry parameters
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback called on each retry with (exception, attempt_number)
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import random
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_retries:
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        delay = delay * (0.5 + random.random())
                    
                    if on_retry:
                        on_retry(e, attempt + 1)
                    
                    time.sleep(delay)
            
            raise last_exception  # Should never reach here
        
        return wrapper
    return decorator


def with_circuit_breaker(circuit_breaker: CircuitBreaker, fallback: Optional[Callable[..., T]] = None):
    """
    Decorator to wrap function calls with circuit breaker protection.
    
    Args:
        circuit_breaker: CircuitBreaker instance
        fallback: Optional fallback function to call when circuit is open
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if not circuit_breaker.can_execute():
                if fallback:
                    return fallback(*args, **kwargs)
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is open for {func.__name__}"
                )
            
            try:
                result = func(*args, **kwargs)
                circuit_breaker.record_success()
                return result
            except Exception:
                circuit_breaker.record_failure()
                raise
        
        return wrapper
    return decorator


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and no fallback is provided."""
    pass


def safe_execute(
    func: Callable[..., T],
    *args,
    default: T = None,
    log_error: bool = True,
    error_callback: Optional[Callable[[Exception], None]] = None,
    **kwargs
) -> T:
    """
    Safely execute a function, returning default value on error.
    
    Args:
        func: Function to execute
        *args: Positional arguments to pass to func
        default: Default value to return on error
        log_error: Whether to log the error
        error_callback: Optional callback on error
        **kwargs: Keyword arguments to pass to func
    
    Returns:
        Result of func or default value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            try:
                from modules.helpers import print_lg
                print_lg(f"Safe execute caught error in {func.__name__}: {e}")
            except ImportError:
                print(f"Safe execute caught error in {func.__name__}: {e}")
        
        if error_callback:
            try:
                error_callback(e)
            except Exception:
                pass
        
        return default


class RateLimiter:
    """
    Token bucket rate limiter for controlling request rates.
    """
    
    def __init__(self, rate: float, burst: int = 1):
        """
        Args:
            rate: Tokens per second
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = burst
        self._tokens = float(burst)
        self._last_update = time.monotonic()
        self._lock = threading.Lock()
    
    def acquire(self, tokens: int = 1, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            blocking: Whether to block until tokens are available
            timeout: Maximum time to wait (None for infinite)
        
        Returns:
            True if tokens were acquired, False otherwise
        """
        start_time = time.monotonic()
        
        while True:
            with self._lock:
                now = time.monotonic()
                # Refill tokens based on time passed
                elapsed = now - self._last_update
                self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
                self._last_update = now
                
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
            
            if not blocking:
                return False
            
            if timeout is not None:
                elapsed = time.monotonic() - start_time
                if elapsed >= timeout:
                    return False
            
            # Wait a bit before trying again
            time.sleep(0.01)


class HealthChecker:
    """
    Health checker for monitoring system components.
    """
    
    def __init__(self):
        self._checks: dict[str, Callable[[], bool]] = {}
        self._status: dict[str, bool] = {}
        self._last_check: dict[str, datetime] = {}
        self._lock = threading.Lock()
    
    def register(self, name: str, check_func: Callable[[], bool]) -> None:
        """Register a health check function."""
        with self._lock:
            self._checks[name] = check_func
    
    def check(self, name: str) -> bool:
        """Run a specific health check."""
        with self._lock:
            if name not in self._checks:
                return False
            
            try:
                result = self._checks[name]()
                self._status[name] = result
                self._last_check[name] = datetime.now()
                return result
            except Exception:
                self._status[name] = False
                self._last_check[name] = datetime.now()
                return False
    
    def check_all(self) -> dict[str, bool]:
        """Run all health checks."""
        results = {}
        for name in list(self._checks.keys()):
            results[name] = self.check(name)
        return results
    
    def is_healthy(self) -> bool:
        """Check if all components are healthy."""
        return all(self.check_all().values())
    
    def get_status(self) -> dict[str, dict]:
        """Get detailed status of all components."""
        with self._lock:
            return {
                name: {
                    "healthy": self._status.get(name, False),
                    "last_check": self._last_check.get(name)
                }
                for name in self._checks
            }


# Global instances for common use
_ai_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
_selenium_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
_api_rate_limiter = RateLimiter(rate=1.0, burst=5)  # 1 request per second, burst of 5
_health_checker = HealthChecker()


def get_ai_circuit_breaker() -> CircuitBreaker:
    return _ai_circuit_breaker


def get_selenium_circuit_breaker() -> CircuitBreaker:
    return _selenium_circuit_breaker


def get_api_rate_limiter() -> RateLimiter:
    return _api_rate_limiter


def get_health_checker() -> HealthChecker:
    return _health_checker
