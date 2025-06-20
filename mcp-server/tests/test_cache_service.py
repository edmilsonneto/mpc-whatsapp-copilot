"""
Tests for Cache Service Implementation
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.cache_service import InMemoryCacheService, RedisCacheService
from src.config import RedisConfig


class TestInMemoryCacheService:
    """Test cases for InMemoryCacheService."""
    
    @pytest.fixture
    def cache_service(self):
        """Create cache service instance."""
        return InMemoryCacheService(default_ttl=60, max_size=10)
    
    @pytest.mark.asyncio
    async def test_set_and_get(self, cache_service):
        """Test basic set and get operations."""
        await cache_service.connect()
        
        key = "test_key"
        value = {"data": "test_value", "number": 42}
        
        await cache_service.set(key, value)
        retrieved_value = await cache_service.get(key)
        
        assert retrieved_value == value
        
        await cache_service.disconnect()
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache_service):
        """Test getting non-existent key."""
        await cache_service.connect()
        
        result = await cache_service.get("nonexistent_key")
        assert result is None
        
        await cache_service.disconnect()
    
    @pytest.mark.asyncio
    async def test_delete(self, cache_service):
        """Test deleting keys."""
        await cache_service.connect()
        
        key = "test_key"
        value = "test_value"
        
        await cache_service.set(key, value)
        assert await cache_service.exists(key) == True
        
        deleted = await cache_service.delete(key)
        assert deleted == True
        assert await cache_service.exists(key) == False
        
        # Try deleting non-existent key
        deleted = await cache_service.delete("nonexistent")
        assert deleted == False
        
        await cache_service.disconnect()
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache_service):
        """Test TTL expiration."""
        await cache_service.connect()
        
        key = "expiring_key"
        value = "expiring_value"
        
        # Set with very short TTL
        await cache_service.set(key, value, ttl=1)
        
        # Should exist immediately
        assert await cache_service.exists(key) == True
        assert await cache_service.get(key) == value
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        assert await cache_service.get(key) is None
        assert await cache_service.exists(key) == False
        
        await cache_service.disconnect()
    
    @pytest.mark.asyncio
    async def test_cache_size_limit(self, cache_service):
        """Test cache size limit and LRU eviction."""
        await cache_service.connect()
        
        # Fill cache to capacity
        for i in range(10):
            await cache_service.set(f"key_{i}", f"value_{i}")
        
        # Add one more item to trigger eviction
        await cache_service.set("new_key", "new_value")
        
        # Check stats
        stats = await cache_service.get_stats()
        assert stats["current_size"] == 10  # Should not exceed max size
        assert stats["evictions"] >= 1
        
        await cache_service.disconnect()
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, cache_service):
        """Test clearing cache entries."""
        await cache_service.connect()
        
        # Add some entries
        await cache_service.set("key1", "value1")
        await cache_service.set("prefix_key2", "value2")
        await cache_service.set("prefix_key3", "value3")
        
        # Clear with pattern
        cleared = await cache_service.clear("prefix_*")
        assert cleared == 2
        
        # Check remaining entries
        assert await cache_service.exists("key1") == True
        assert await cache_service.exists("prefix_key2") == False
        assert await cache_service.exists("prefix_key3") == False
        
        # Clear all
        cleared_all = await cache_service.clear()
        assert cleared_all >= 1
        
        await cache_service.disconnect()
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_service):
        """Test cache statistics."""
        await cache_service.connect()
        
        # Perform some operations
        await cache_service.set("key1", "value1")
        await cache_service.get("key1")  # Hit
        await cache_service.get("nonexistent")  # Miss
        await cache_service.delete("key1")
        
        stats = await cache_service.get_stats()
        
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert stats["sets"] >= 1
        assert stats["deletes"] >= 1
        assert "hit_rate" in stats
        assert "total_requests" in stats
        
        await cache_service.disconnect()


class TestRedisCacheService:
    """Test cases for RedisCacheService."""
    
    @pytest.fixture
    def redis_config(self):
        """Create Redis config for testing."""
        return RedisConfig(
            host="localhost",
            port=6379,
            password=None,
            db=15,  # Use test database
            ssl=False
        )
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock = AsyncMock()
        mock.ping = AsyncMock()
        mock.get = AsyncMock()
        mock.set = AsyncMock()
        mock.delete = AsyncMock()
        mock.exists = AsyncMock()
        mock.scan_iter = AsyncMock()
        mock.info = AsyncMock()
        mock.close = AsyncMock()
        return mock
    
    @pytest.fixture
    def cache_service(self, redis_config, mock_redis):
        """Create Redis cache service with mocked Redis."""
        service = RedisCacheService(redis_config)
        service.redis_client = mock_redis
        return service
    
    @pytest.mark.asyncio
    async def test_redis_set_and_get(self, cache_service, mock_redis):
        """Test Redis set and get operations."""
        import pickle
        
        key = "test_key"
        value = {"data": "test_value"}
        
        # Mock Redis get to return None initially
        mock_redis.get.return_value = None
        
        # Test set
        await cache_service.set(key, value)
        mock_redis.set.assert_called()
        
        # Mock Redis get to return pickled data
        from src.cache_service import CacheEntry
        entry = CacheEntry(value, 3600)
        mock_redis.get.return_value = pickle.dumps(entry)
        
        # Test get
        retrieved_value = await cache_service.get(key)
        assert retrieved_value == value
    
    @pytest.mark.asyncio
    async def test_redis_connection_error(self, redis_config):
        """Test Redis connection error handling."""
        service = RedisCacheService(redis_config)
        
        # Test operations without connection
        with pytest.raises(RuntimeError, match="Redis client not connected"):
            await service.get("test_key")
        
        with pytest.raises(RuntimeError, match="Redis client not connected"):
            await service.set("test_key", "test_value")


if __name__ == "__main__":
    pytest.main([__file__])
