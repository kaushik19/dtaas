"""
Caching utilities for DTaaS
Provides in-memory caching for frequently accessed data
"""
from functools import lru_cache, wraps
from typing import Any, Callable, Optional
import logging
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


class TTLCache:
    """
    Time-To-Live cache implementation
    Thread-safe cache with automatic expiration
    """
    
    def __init__(self, default_ttl_seconds: int = 300):
        """
        Args:
            default_ttl_seconds: Default time-to-live in seconds (5 minutes default)
        """
        self._cache = {}
        self._timestamps = {}
        self._ttl = default_ttl_seconds
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        with self._lock:
            if key not in self._cache:
                return None
            
            # Check if expired
            if datetime.now() - self._timestamps[key] > timedelta(seconds=self._ttl):
                logger.debug(f"Cache expired for key: {key}")
                del self._cache[key]
                del self._timestamps[key]
                return None
            
            logger.debug(f"Cache hit for key: {key}")
            return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with TTL"""
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = datetime.now()
            logger.debug(f"Cache set for key: {key} (TTL: {ttl or self._ttl}s)")
    
    def delete(self, key: str):
        """Delete specific key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
                logger.debug(f"Cache cleared for key: {key}")
    
    def clear(self):
        """Clear all cache"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            logger.info("Cache cleared completely")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        with self._lock:
            return {
                "size": len(self._cache),
                "ttl_seconds": self._ttl,
                "keys": list(self._cache.keys())
            }


# Global caches
connector_cache = TTLCache(default_ttl_seconds=600)  # 10 minutes
variable_cache = TTLCache(default_ttl_seconds=300)  # 5 minutes
schema_cache = TTLCache(default_ttl_seconds=1800)   # 30 minutes


def cached(cache: TTLCache, key_prefix: str = "", ttl: Optional[int] = None):
    """
    Decorator for caching function results
    
    Usage:
        @cached(connector_cache, key_prefix="conn")
        def get_connector(conn_id):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(cache: TTLCache, pattern: Optional[str] = None):
    """
    Invalidate cache entries matching pattern
    
    Args:
        cache: TTLCache instance
        pattern: Optional pattern to match keys (if None, clears all)
    """
    if pattern is None:
        cache.clear()
    else:
        # Get matching keys
        stats = cache.get_stats()
        matching_keys = [k for k in stats['keys'] if pattern in k]
        
        # Delete matching keys
        for key in matching_keys:
            cache.delete(key)
        
        logger.info(f"Invalidated {len(matching_keys)} cache entries matching '{pattern}'")

