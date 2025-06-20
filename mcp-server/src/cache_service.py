"""
Cache Service Implementation

This module implements caching functionality for improved performance
using Redis as the backend cache store.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from hashlib import sha256

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Redis not available, using in-memory cache")

from .interfaces import ICacheService
from .config import RedisConfig

logger = logging.getLogger(__name__)


class RedisCacheService(ICacheService):
    """Redis-based cache service implementation."""
    
    def __init__(self, redis_config: RedisConfig):
        """Initialize Redis cache service.
        
        Args:
            redis_config: Redis connection configuration
        """
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis not available for caching")
            
        self.redis_config = redis_config
        self.redis_client: Optional[Redis] = None
        self.default_ttl = 3600  # 1 hour default TTL
        self.key_prefix = "mcp_cache:"
        
    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_config.host,
                port=self.redis_config.port,
                password=self.redis_config.password,
                db=self.redis_config.db,
                ssl=self.redis_config.ssl,
                decode_responses=True,
                socket_keepalive=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Connected to Redis cache successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis cache: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis cache")
    
    def _make_key(self, key: str, namespace: str = "default") -> str:
        """Create a cache key with prefix and namespace.
        
        Args:
            key: Base cache key
            namespace: Optional namespace for grouping
            
        Returns:
            Formatted cache key
        """
        return f"{self.key_prefix}{namespace}:{key}"
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for cache storage.
        
        Args:
            value: Value to serialize
            
        Returns:
            Serialized string
        """
        if isinstance(value, (str, int, float, bool)):
            return json.dumps({"type": "simple", "value": value})
        else:
            return json.dumps({"type": "complex", "value": value}, default=str)
    
    def _deserialize_value(self, serialized: str) -> Any:
        """Deserialize value from cache.
        
        Args:
            serialized: Serialized string
            
        Returns:
            Deserialized value
        """
        try:
            data = json.loads(serialized)
            return data.get("value")
        except (json.JSONDecodeError, KeyError):
            return serialized
    
    async def get(self, key: str, namespace: str = "default") -> Any:
        """Get value from cache.
        
        Args:
            key: Cache key
            namespace: Optional namespace
            
        Returns:
            Cached value or None if not found
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        cache_key = self._make_key(key, namespace)
        
        try:
            value = await self.redis_client.get(cache_key)
            if value is None:
                return None
            
            return self._deserialize_value(value)
        except Exception as e:
            logger.error(f"Error getting cache value for {cache_key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "default"
    ) -> bool:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            namespace: Optional namespace
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        cache_key = self._make_key(key, namespace)
        ttl = ttl or self.default_ttl
        
        try:
            serialized_value = self._serialize_value(value)
            await self.redis_client.setex(cache_key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Error setting cache value for {cache_key}: {e}")
            return False
    
    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete value from cache.
        
        Args:
            key: Cache key
            namespace: Optional namespace
            
        Returns:
            True if deleted, False if not found
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        cache_key = self._make_key(key, namespace)
        
        try:
            result = await self.redis_client.delete(cache_key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting cache value for {cache_key}: {e}")
            return False
    
    async def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists in cache.
        
        Args:
            key: Cache key
            namespace: Optional namespace
            
        Returns:
            True if exists, False otherwise
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        cache_key = self._make_key(key, namespace)
        
        try:
            result = await self.redis_client.exists(cache_key)
            return result > 0
        except Exception as e:
            logger.error(f"Error checking cache existence for {cache_key}: {e}")
            return False
    
    async def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace.
        
        Args:
            namespace: Namespace to clear
            
        Returns:
            Number of keys deleted
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        pattern = f"{self.key_prefix}{namespace}:*"
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing namespace {namespace}: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Cache statistics dictionary
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        try:
            info = await self.redis_client.info("memory")
            keyspace = await self.redis_client.info("keyspace")
            
            stats = {
                "memory_used": info.get("used_memory_human", "N/A"),
                "memory_peak": info.get("used_memory_peak_human", "N/A"),
                "connected_clients": await self.redis_client.client_list(),
                "total_keys": 0,
                "mcp_keys": 0,
                "uptime": info.get("uptime_in_seconds", 0)
            }
            
            # Count total keys and MCP keys
            all_keys = await self.redis_client.keys("*")
            stats["total_keys"] = len(all_keys)
            
            mcp_keys = await self.redis_client.keys(f"{self.key_prefix}*")
            stats["mcp_keys"] = len(mcp_keys)
            
            return stats
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}


class InMemoryCacheService(ICacheService):
    """In-memory cache service for testing and fallback."""
    
    def __init__(self):
        """Initialize in-memory cache service."""
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = 3600  # 1 hour
        self._lock = asyncio.Lock()
    
    def _make_key(self, key: str, namespace: str = "default") -> str:
        """Create a cache key with namespace."""
        return f"{namespace}:{key}"
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        if "expires_at" not in cache_entry:
            return False
        return datetime.utcnow() > cache_entry["expires_at"]
    
    async def get(self, key: str, namespace: str = "default") -> Any:
        """Get value from cache."""
        cache_key = self._make_key(key, namespace)
        
        async with self._lock:
            if cache_key not in self.cache:
                return None
            
            entry = self.cache[cache_key]
            if self._is_expired(entry):
                del self.cache[cache_key]
                return None
            
            return entry["value"]
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: str = "default"
    ) -> bool:
        """Set value in cache."""
        cache_key = self._make_key(key, namespace)
        ttl = ttl or self.default_ttl
        
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        async with self._lock:
            self.cache[cache_key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": datetime.utcnow()
            }
        
        return True
    
    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete value from cache."""
        cache_key = self._make_key(key, namespace)
        
        async with self._lock:
            if cache_key in self.cache:
                del self.cache[cache_key]
                return True
            return False
    
    async def exists(self, key: str, namespace: str = "default") -> bool:
        """Check if key exists in cache."""
        cache_key = self._make_key(key, namespace)
        
        async with self._lock:
            if cache_key not in self.cache:
                return False
            
            entry = self.cache[cache_key]
            if self._is_expired(entry):
                del self.cache[cache_key]
                return False
            
            return True
    
    async def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace."""
        async with self._lock:
            keys_to_delete = [
                key for key in self.cache.keys()
                if key.startswith(f"{namespace}:")
            ]
            
            for key in keys_to_delete:
                del self.cache[key]
            
            return len(keys_to_delete)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            total_keys = len(self.cache)
            expired_keys = sum(
                1 for entry in self.cache.values()
                if self._is_expired(entry)
            )
            
            return {
                "total_keys": total_keys,
                "expired_keys": expired_keys,
                "active_keys": total_keys - expired_keys,
                "memory_usage": "N/A (in-memory)",
                "cache_type": "in_memory"
            }


class CacheManager:
    """High-level cache manager with advanced features."""
    
    def __init__(self, cache_service: ICacheService):
        """Initialize cache manager.
        
        Args:
            cache_service: Underlying cache service implementation
        """
        self.cache_service = cache_service
        self.hit_count = 0
        self.miss_count = 0
        self._stats_lock = asyncio.Lock()
    
    async def get_or_set(
        self,
        key: str,
        value_func: callable,
        ttl: Optional[int] = None,
        namespace: str = "default"
    ) -> Any:
        """Get value from cache or set it using the provided function.
        
        Args:
            key: Cache key
            value_func: Function to generate value if not cached
            ttl: Time to live in seconds
            namespace: Optional namespace
            
        Returns:
            Cached or generated value
        """
        # Try to get from cache first
        cached_value = await self.cache_service.get(key, namespace)
        if cached_value is not None:
            async with self._stats_lock:
                self.hit_count += 1
            return cached_value
        
        # Generate new value
        async with self._stats_lock:
            self.miss_count += 1
        
        if asyncio.iscoroutinefunction(value_func):
            new_value = await value_func()
        else:
            new_value = value_func()
        
        # Cache the new value
        await self.cache_service.set(key, new_value, ttl, namespace)
        return new_value
    
    async def mget(
        self,
        keys: List[str],
        namespace: str = "default"
    ) -> Dict[str, Any]:
        """Get multiple values from cache.
        
        Args:
            keys: List of cache keys
            namespace: Optional namespace
            
        Returns:
            Dictionary of key-value pairs
        """
        results = {}
        for key in keys:
            value = await self.cache_service.get(key, namespace)
            if value is not None:
                results[key] = value
        
        return results
    
    async def mset(
        self,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
        namespace: str = "default"
    ) -> int:
        """Set multiple values in cache.
        
        Args:
            data: Dictionary of key-value pairs
            ttl: Time to live in seconds
            namespace: Optional namespace
            
        Returns:
            Number of successfully set values
        """
        success_count = 0
        for key, value in data.items():
            if await self.cache_service.set(key, value, ttl, namespace):
                success_count += 1
        
        return success_count
    
    def cache_key_for_suggestion(
        self,
        code: str,
        language: str,
        context: Optional[str] = None
    ) -> str:
        """Generate cache key for Copilot suggestions.
        
        Args:
            code: Code snippet
            language: Programming language
            context: Optional context
            
        Returns:
            Cache key hash
        """
        content = f"{code}|{language}|{context or ''}"
        return sha256(content.encode()).hexdigest()
    
    def cache_key_for_explanation(
        self,
        code: str,
        language: str
    ) -> str:
        """Generate cache key for code explanations.
        
        Args:
            code: Code snippet
            language: Programming language
            
        Returns:
            Cache key hash
        """
        content = f"explain|{code}|{language}"
        return sha256(content.encode()).hexdigest()
    
    def cache_key_for_tests(
        self,
        function_code: str,
        test_framework: str,
        language: str
    ) -> str:
        """Generate cache key for test generation.
        
        Args:
            function_code: Function code
            test_framework: Test framework name
            language: Programming language
            
        Returns:
            Cache key hash
        """
        content = f"tests|{function_code}|{test_framework}|{language}"
        return sha256(content.encode()).hexdigest()
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics.
        
        Returns:
            Cache statistics including hit/miss ratios
        """
        service_stats = await self.cache_service.get_stats()
        
        async with self._stats_lock:
            total_requests = self.hit_count + self.miss_count
            hit_ratio = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
            
            return {
                **service_stats,
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "total_requests": total_requests,
                "hit_ratio_percent": round(hit_ratio, 2)
            }
