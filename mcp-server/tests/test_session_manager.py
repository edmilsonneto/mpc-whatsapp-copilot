"""
Tests for Session Manager Implementation
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.session_manager import InMemorySessionManager, RedisSessionManager
from src.types import SessionStatus, SessionId, UserId
from src.config import RedisConfig


class TestInMemorySessionManager:
    """Test cases for InMemorySessionManager."""
    
    @pytest.fixture
    def session_manager(self):
        """Create session manager instance."""
        return InMemorySessionManager()
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_manager):
        """Test session creation."""
        user_id = UserId("test_user")
        
        session = await session_manager.create_session(user_id, workspace="/test/workspace")
        
        assert session.whatsapp_user == user_id
        assert session.workspace == "/test/workspace"
        assert session.status == SessionStatus.ACTIVE
        assert session.suggestions_count == 0
        assert len(session.commands_executed) == 0
    
    @pytest.mark.asyncio
    async def test_get_session(self, session_manager):
        """Test getting session by ID."""
        user_id = UserId("test_user")
        
        # Create session
        created_session = await session_manager.create_session(user_id)
        
        # Get session
        retrieved_session = await session_manager.get_session(created_session.session_id)
        
        assert retrieved_session is not None
        assert retrieved_session.session_id == created_session.session_id
        assert retrieved_session.whatsapp_user == user_id
    
    @pytest.mark.asyncio
    async def test_get_user_session(self, session_manager):
        """Test getting session by user ID."""
        user_id = UserId("test_user")
        
        # Create session
        created_session = await session_manager.create_session(user_id)
        
        # Get session by user
        retrieved_session = await session_manager.get_user_session(user_id)
        
        assert retrieved_session is not None
        assert retrieved_session.session_id == created_session.session_id
    
    @pytest.mark.asyncio
    async def test_update_session(self, session_manager):
        """Test updating session."""
        user_id = UserId("test_user")
        
        # Create session
        session = await session_manager.create_session(user_id)
        original_last_activity = session.last_activity
        
        # Wait a bit and update
        await asyncio.sleep(0.01)
        session.suggestions_count = 5
        await session_manager.update_session(session)
        
        # Verify update
        updated_session = await session_manager.get_session(session.session_id)
        assert updated_session.suggestions_count == 5
        assert updated_session.last_activity > original_last_activity
    
    @pytest.mark.asyncio
    async def test_end_session(self, session_manager):
        """Test ending session."""
        user_id = UserId("test_user")
        
        # Create session
        session = await session_manager.create_session(user_id)
        
        # End session
        await session_manager.end_session(session.session_id)
        
        # Verify session ended
        ended_session = await session_manager.get_session(session.session_id)
        assert ended_session.status == SessionStatus.ENDED
        
        # Verify user session mapping removed
        user_session = await session_manager.get_user_session(user_id)
        assert user_session is None
    
    @pytest.mark.asyncio
    async def test_duplicate_session_creation(self, session_manager):
        """Test that creating session for same user returns existing active session."""
        user_id = UserId("test_user")
        
        # Create first session
        session1 = await session_manager.create_session(user_id)
        
        # Try to create second session for same user
        session2 = await session_manager.create_session(user_id)
        
        # Should return the same session
        assert session1.session_id == session2.session_id
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, session_manager):
        """Test cleanup of expired sessions."""
        # Override TTL for testing
        session_manager.session_ttl = 1  # 1 second
        
        user_id = UserId("test_user")
        
        # Create session
        session = await session_manager.create_session(user_id)
        
        # Manually set last activity to past
        session.last_activity = datetime.utcnow() - timedelta(seconds=2)
        session_manager.sessions[session.session_id] = session
        
        # Run cleanup
        cleaned_count = await session_manager.cleanup_expired_sessions()
        
        assert cleaned_count == 1
        
        # Verify session was ended
        ended_session = await session_manager.get_session(session.session_id)
        assert ended_session.status == SessionStatus.ENDED


class TestRedisSessionManager:
    """Test cases for RedisSessionManager."""
    
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
        mock.hset = AsyncMock()
        mock.hgetall = AsyncMock()
        mock.set = AsyncMock()
        mock.get = AsyncMock()
        mock.delete = AsyncMock()
        mock.expire = AsyncMock()
        mock.sadd = AsyncMock()
        mock.srem = AsyncMock()
        mock.smembers = AsyncMock()
        mock.scard = AsyncMock()
        mock.pipeline = MagicMock()
        mock.close = AsyncMock()
        return mock
    
    @pytest.fixture
    def session_manager(self, redis_config, mock_redis, monkeypatch):
        """Create Redis session manager with mocked Redis."""
        manager = RedisSessionManager(redis_config)
        manager.redis_client = mock_redis
        return manager
    
    @pytest.mark.asyncio
    async def test_create_session_redis(self, session_manager, mock_redis):
        """Test session creation with Redis."""
        user_id = UserId("test_user")
        
        # Mock Redis responses
        mock_redis.get.return_value = None  # No existing session
        mock_pipeline = AsyncMock()
        mock_redis.pipeline.return_value.__aenter__.return_value = mock_pipeline
        mock_pipeline.execute = AsyncMock()
        
        session = await session_manager.create_session(user_id, workspace="/test")
        
        assert session.whatsapp_user == user_id
        assert session.workspace == "/test"
        assert session.status == SessionStatus.ACTIVE
        
        # Verify Redis calls
        mock_pipeline.hset.assert_called()
        mock_pipeline.expire.assert_called()
        mock_pipeline.set.assert_called()
        mock_pipeline.sadd.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_session_redis(self, session_manager, mock_redis):
        """Test getting session from Redis."""
        session_id = SessionId("test_session")
        
        # Mock Redis response
        mock_redis.hgetall.return_value = {
            "session_id": "test_session",
            "whatsapp_user": "test_user",
            "workspace": "/test",
            "status": "active",
            "created_at": "2024-01-01T00:00:00",
            "last_activity": "2024-01-01T00:00:00",
            "suggestions_count": "5",
            "commands_executed": "[]"
        }
        
        session = await session_manager.get_session(session_id)
        
        assert session is not None
        assert session.session_id == session_id
        assert session.whatsapp_user == "test_user"
        assert session.suggestions_count == 5
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, redis_config):
        """Test handling of Redis connection errors."""
        manager = RedisSessionManager(redis_config)
        
        # Test operations without connection
        with pytest.raises(RuntimeError, match="Redis client not connected"):
            await manager.create_session(UserId("test"))
        
        with pytest.raises(RuntimeError, match="Redis client not connected"):
            await manager.get_session(SessionId("test"))


if __name__ == "__main__":
    pytest.main([__file__])
