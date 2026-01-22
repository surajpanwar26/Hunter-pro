'''
Connection Pool and Resource Management Module
Provides connection pooling, resource cleanup, and lifecycle management.

Author: Auto-generated improvement
'''

import threading
import time
from queue import Queue, Empty, Full
from typing import Generic, TypeVar, Callable, Optional, Any, ContextManager
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
import weakref
import atexit

T = TypeVar('T')


@dataclass
class PooledResource(Generic[T]):
    """Wrapper for pooled resources with metadata."""
    resource: T
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    use_count: int = 0
    
    def touch(self) -> None:
        """Update last used time and increment use count."""
        self.last_used = datetime.now()
        self.use_count += 1
    
    def age_seconds(self) -> float:
        """Return age of resource in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
    
    def idle_seconds(self) -> float:
        """Return idle time in seconds."""
        return (datetime.now() - self.last_used).total_seconds()


class ResourcePool(Generic[T]):
    """
    Generic resource pool with connection management.
    Supports min/max pool sizes, idle timeout, and health checks.
    """
    
    def __init__(
        self,
        factory: Callable[[], T],
        destroyer: Optional[Callable[[T], None]] = None,
        validator: Optional[Callable[[T], bool]] = None,
        min_size: int = 1,
        max_size: int = 10,
        max_idle_time: float = 300.0,  # 5 minutes
        max_age: float = 3600.0,  # 1 hour
        acquire_timeout: float = 30.0
    ):
        self._factory = factory
        self._destroyer = destroyer or (lambda x: None)
        self._validator = validator or (lambda x: True)
        self._min_size = min_size
        self._max_size = max_size
        self._max_idle_time = max_idle_time
        self._max_age = max_age
        self._acquire_timeout = acquire_timeout
        
        self._pool: Queue[PooledResource[T]] = Queue(maxsize=max_size)
        self._size = 0
        self._lock = threading.Lock()
        self._shutdown = False
        
        # Initialize minimum pool size
        self._initialize_pool()
        
        # Register cleanup on exit
        atexit.register(self.shutdown)
    
    def _initialize_pool(self) -> None:
        """Initialize pool with minimum number of resources."""
        for _ in range(self._min_size):
            try:
                resource = self._create_resource()
                if resource:
                    self._pool.put_nowait(resource)
            except Exception:
                pass
    
    def _create_resource(self) -> Optional[PooledResource[T]]:
        """Create a new pooled resource."""
        with self._lock:
            if self._size >= self._max_size:
                return None
            
            try:
                raw_resource = self._factory()
                self._size += 1
                return PooledResource(resource=raw_resource)
            except Exception as e:
                raise ResourceCreationError(f"Failed to create resource: {e}") from e
    
    def _destroy_resource(self, pooled: PooledResource[T]) -> None:
        """Destroy a pooled resource."""
        with self._lock:
            self._size -= 1
        
        try:
            self._destroyer(pooled.resource)
        except Exception:
            pass
    
    def _is_resource_valid(self, pooled: PooledResource[T]) -> bool:
        """Check if resource is still valid."""
        # Check age
        if pooled.age_seconds() > self._max_age:
            return False
        
        # Check idle time
        if pooled.idle_seconds() > self._max_idle_time:
            return False
        
        # Run custom validator
        try:
            return self._validator(pooled.resource)
        except Exception:
            return False
    
    def acquire(self, timeout: Optional[float] = None) -> T:
        """
        Acquire a resource from the pool.
        
        Args:
            timeout: Maximum time to wait for resource (None uses default)
        
        Returns:
            Resource from pool
        
        Raises:
            ResourcePoolExhaustedError: If no resource available within timeout
        """
        if self._shutdown:
            raise PoolShutdownError("Resource pool is shut down")
        
        timeout = timeout if timeout is not None else self._acquire_timeout
        deadline = time.monotonic() + timeout
        
        while time.monotonic() < deadline:
            # Try to get existing resource
            try:
                pooled = self._pool.get_nowait()
                
                if self._is_resource_valid(pooled):
                    pooled.touch()
                    return pooled.resource
                else:
                    # Resource invalid, destroy and try again
                    self._destroy_resource(pooled)
                    
            except Empty:
                pass
            
            # Try to create new resource
            try:
                pooled = self._create_resource()
                if pooled:
                    pooled.touch()
                    return pooled.resource
            except ResourceCreationError:
                pass
            
            # Wait a bit before retrying
            time.sleep(0.1)
        
        raise ResourcePoolExhaustedError(
            f"Could not acquire resource within {timeout}s timeout"
        )
    
    def release(self, resource: T) -> None:
        """Release a resource back to the pool."""
        if self._shutdown:
            try:
                self._destroyer(resource)
            except Exception:
                pass
            return
        
        pooled = PooledResource(resource=resource)
        pooled.touch()
        
        try:
            self._pool.put_nowait(pooled)
        except Full:
            # Pool is full, destroy the resource
            self._destroy_resource(pooled)
    
    @contextmanager
    def connection(self) -> ContextManager[T]:
        """Context manager for acquiring and releasing resources."""
        resource = self.acquire()
        try:
            yield resource
        finally:
            self.release(resource)
    
    def shutdown(self) -> None:
        """Shutdown the pool and destroy all resources."""
        self._shutdown = True
        
        while True:
            try:
                pooled = self._pool.get_nowait()
                self._destroy_resource(pooled)
            except Empty:
                break
    
    @property
    def size(self) -> int:
        """Current number of resources in pool."""
        with self._lock:
            return self._size
    
    @property
    def available(self) -> int:
        """Number of available resources."""
        return self._pool.qsize()


class ResourceCreationError(Exception):
    """Raised when resource creation fails."""
    pass


class ResourcePoolExhaustedError(Exception):
    """Raised when pool is exhausted."""
    pass


class PoolShutdownError(Exception):
    """Raised when operating on shut down pool."""
    pass


class ResourceManager:
    """
    Central resource manager for tracking and cleaning up resources.
    Uses weak references to allow garbage collection while tracking.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance
    
    def _init(self) -> None:
        """Initialize the resource manager."""
        self._resources: dict[str, weakref.ref] = {}
        self._cleanups: dict[str, Callable[[], None]] = {}
        self._resource_lock = threading.Lock()
        atexit.register(self.cleanup_all)
    
    def register(
        self,
        name: str,
        resource: Any,
        cleanup: Optional[Callable[[], None]] = None
    ) -> None:
        """
        Register a resource for tracking.
        
        Args:
            name: Unique name for the resource
            resource: The resource object
            cleanup: Optional cleanup function
        """
        with self._resource_lock:
            self._resources[name] = weakref.ref(resource)
            if cleanup:
                self._cleanups[name] = cleanup
    
    def unregister(self, name: str) -> None:
        """Unregister a resource."""
        with self._resource_lock:
            self._resources.pop(name, None)
            self._cleanups.pop(name, None)
    
    def get(self, name: str) -> Optional[Any]:
        """Get a registered resource by name."""
        with self._resource_lock:
            ref = self._resources.get(name)
            if ref:
                return ref()
            return None
    
    def cleanup(self, name: str) -> None:
        """Clean up a specific resource."""
        with self._resource_lock:
            cleanup_func = self._cleanups.pop(name, None)
            self._resources.pop(name, None)
        
        if cleanup_func:
            try:
                cleanup_func()
            except Exception:
                pass
    
    def cleanup_all(self) -> None:
        """Clean up all registered resources."""
        with self._resource_lock:
            names = list(self._cleanups.keys())
        
        for name in names:
            self.cleanup(name)
    
    def list_resources(self) -> list[str]:
        """List all registered resource names."""
        with self._resource_lock:
            return list(self._resources.keys())


class SessionManager:
    """
    Manages browser sessions and handles recovery.
    """
    
    def __init__(self):
        self._sessions: dict[str, Any] = {}
        self._session_health: dict[str, bool] = {}
        self._lock = threading.Lock()
    
    def register_session(self, name: str, driver: Any) -> None:
        """Register a browser session."""
        with self._lock:
            self._sessions[name] = driver
            self._session_health[name] = True
    
    def get_session(self, name: str) -> Optional[Any]:
        """Get a registered session."""
        with self._lock:
            return self._sessions.get(name)
    
    def is_session_alive(self, name: str) -> bool:
        """Check if a session is still alive."""
        with self._lock:
            driver = self._sessions.get(name)
            if not driver:
                return False
            
            try:
                # Try to access window handles to check if session is alive
                _ = driver.window_handles
                self._session_health[name] = True
                return True
            except Exception:
                self._session_health[name] = False
                return False
    
    def close_session(self, name: str) -> None:
        """Close and remove a session."""
        with self._lock:
            driver = self._sessions.pop(name, None)
            self._session_health.pop(name, None)
        
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
    
    def close_all(self) -> None:
        """Close all sessions."""
        with self._lock:
            names = list(self._sessions.keys())
        
        for name in names:
            self.close_session(name)


# Global instances
_resource_manager = ResourceManager()
_session_manager = SessionManager()


def get_resource_manager() -> ResourceManager:
    return _resource_manager


def get_session_manager() -> SessionManager:
    return _session_manager
