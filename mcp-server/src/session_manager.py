"""
Session Management Implementation

This module implements session management with Redis for persistence
and automatic cleanup of expired sessions.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from uuid import uuid4

import redis.asyncio as redis
from redis.asyncio import Redis

from .interfaces import ISessionManager
from .types import Session, SessionId, UserId, SessionStatus
from .config import RedisConfig

logger = logging.getLogger(__name__)


class RedisSessionManager(ISessionManager):
    """Redis-based session manager implementation."""
    
    def __init__(self, redis_config: RedisConfig):
        """Initialize Redis session manager.
        
        Args:
            redis_config: Redis connection configuration
        """
        self.redis_config = redis_config
        self.redis_client: Optional[Redis] = None
        self.session_ttl = 24 * 60 * 60  # 24 hours in seconds
        self.cleanup_interval = 60 * 60  # 1 hour cleanup interval
        self._cleanup_task: Optional[asyncio.Task] = None
        
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
            logger.info("Connected to Redis successfully")
            
            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
    
    async def create_session(
        self,
        whatsapp_user: UserId,
        workspace: Optional[str] = None
    ) -> Session:
        """Create a new user session.
        
        Args:
            whatsapp_user: WhatsApp user ID
            workspace: Optional workspace path
            
        Returns:
            Created session object
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        # Check if user already has an active session
        existing_session = await self.get_user_session(whatsapp_user)
        if existing_session and existing_session.status == SessionStatus.ACTIVE:
            logger.info(f"User {whatsapp_user} already has active session: {existing_session.session_id}")
            return existing_session
        
        # Create new session
        session = Session(
            session_id=SessionId(str(uuid4())),
            whatsapp_user=whatsapp_user,
            workspace=workspace,
            status=SessionStatus.ACTIVE,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            suggestions_count=0,
            commands_executed=[]
        )
        
        # Store in Redis
        session_key = f"session:{session.session_id}"
        user_session_key = f"user_session:{whatsapp_user}"
        
        session_data = {
            "session_id": session.session_id,
            "whatsapp_user": session.whatsapp_user,
            "workspace": session.workspace or "",
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "suggestions_count": session.suggestions_count,
            "commands_executed": json.dumps(session.commands_executed)
        }
        
        async with self.redis_client.pipeline() as pipe:
            # Store session data
            pipe.hset(session_key, mapping=session_data)
            pipe.expire(session_key, self.session_ttl)
            
            # Map user to session
            pipe.set(user_session_key, session.session_id, ex=self.session_ttl)
            
            # Add to active sessions set
            pipe.sadd("active_sessions", session.session_id)
            
            await pipe.execute()
        
        logger.info(f"Created new session {session.session_id} for user {whatsapp_user}")
        return session
    
    async def get_session(self, session_id: SessionId) -> Optional[Session]:
        """Get session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session object if found, None otherwise
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        session_key = f"session:{session_id}"
        session_data = await self.redis_client.hgetall(session_key)
        
        if not session_data:
            return None
        
        try:
            return Session(
                session_id=SessionId(session_data["session_id"]),
                whatsapp_user=UserId(session_data["whatsapp_user"]),
                workspace=session_data["workspace"] or None,
                status=SessionStatus(session_data["status"]),
                created_at=datetime.fromisoformat(session_data["created_at"]),
                last_activity=datetime.fromisoformat(session_data["last_activity"]),
                suggestions_count=int(session_data["suggestions_count"]),
                commands_executed=json.loads(session_data["commands_executed"])
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing session data for {session_id}: {e}")
            return None
    
    async def get_user_session(self, user_id: UserId) -> Optional[Session]:
        """Get active session for user.
        
        Args:
            user_id: WhatsApp user ID
            
        Returns:
            Active session if found, None otherwise
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        user_session_key = f"user_session:{user_id}"
        session_id = await self.redis_client.get(user_session_key)
        
        if not session_id:
            return None
        
        return await self.get_session(SessionId(session_id))
    
    async def update_session(self, session: Session) -> None:
        """Update session information.
        
        Args:
            session: Session object to update
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        session_key = f"session:{session.session_id}"
        
        # Update last activity
        session.last_activity = datetime.utcnow()
        
        session_data = {
            "status": session.status.value,
            "last_activity": session.last_activity.isoformat(),
            "suggestions_count": session.suggestions_count,
            "commands_executed": json.dumps(session.commands_executed),
            "workspace": session.workspace or ""
        }
        
        await self.redis_client.hset(session_key, mapping=session_data)
        await self.redis_client.expire(session_key, self.session_ttl)
        
        logger.debug(f"Updated session {session.session_id}")
    
    async def end_session(self, session_id: SessionId) -> None:
        """End a user session.
        
        Args:
            session_id: Session identifier to end
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for ending")
            return
        
        session.status = SessionStatus.ENDED
        session.last_activity = datetime.utcnow()
        
        session_key = f"session:{session_id}"
        user_session_key = f"user_session:{session.whatsapp_user}"
        
        async with self.redis_client.pipeline() as pipe:
            # Update session status
            pipe.hset(session_key, "status", session.status.value)
            pipe.hset(session_key, "last_activity", session.last_activity.isoformat())
            
            # Remove from active sessions
            pipe.srem("active_sessions", session_id)
            
            # Remove user session mapping
            pipe.delete(user_session_key)
            
            await pipe.execute()
        
        logger.info(f"Ended session {session_id} for user {session.whatsapp_user}")
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        cleaned_count = 0
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.session_ttl)
        
        # Get all active sessions
        active_sessions = await self.redis_client.smembers("active_sessions")
        
        for session_id in active_sessions:
            session = await self.get_session(SessionId(session_id))
            
            if not session:
                # Session data missing, remove from active set
                await self.redis_client.srem("active_sessions", session_id)
                cleaned_count += 1
                continue
            
            if session.last_activity < cutoff_time:
                # Session expired
                await self.end_session(session.session_id)
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired sessions")
        
        return cleaned_count
    
    async def get_active_session_count(self) -> int:
        """Get number of active sessions.
        
        Returns:
            Number of active sessions
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        return await self.redis_client.scard("active_sessions")
    
    async def get_all_active_sessions(self) -> List[Session]:
        """Get all active sessions.
        
        Returns:
            List of active sessions
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        active_session_ids = await self.redis_client.smembers("active_sessions")
        sessions = []
        
        for session_id in active_session_ids:
            session = await self.get_session(SessionId(session_id))
            if session:
                sessions.append(session)
        
        return sessions
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup task."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_expired_sessions()
            except asyncio.CancelledError:
                logger.info("Session cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")


class InMemorySessionManager(ISessionManager):
    """In-memory session manager for testing and development."""
    
    def __init__(self):
        """Initialize in-memory session manager."""
        self.sessions: Dict[SessionId, Session] = {}
        self.user_sessions: Dict[UserId, SessionId] = {}
        self.session_ttl = 24 * 60 * 60  # 24 hours
    
    async def create_session(
        self,
        whatsapp_user: UserId,
        workspace: Optional[str] = None
    ) -> Session:
        """Create a new user session."""
        # Check if user already has an active session
        if whatsapp_user in self.user_sessions:
            existing_session_id = self.user_sessions[whatsapp_user]
            existing_session = self.sessions.get(existing_session_id)
            if existing_session and existing_session.status == SessionStatus.ACTIVE:
                return existing_session
        
        # Create new session
        session = Session(
            session_id=SessionId(str(uuid4())),
            whatsapp_user=whatsapp_user,
            workspace=workspace,
            status=SessionStatus.ACTIVE,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            suggestions_count=0,
            commands_executed=[]
        )
        
        self.sessions[session.session_id] = session
        self.user_sessions[whatsapp_user] = session.session_id
        
        logger.info(f"Created new in-memory session {session.session_id} for user {whatsapp_user}")
        return session
    
    async def get_session(self, session_id: SessionId) -> Optional[Session]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    async def get_user_session(self, user_id: UserId) -> Optional[Session]:
        """Get active session for user."""
        session_id = self.user_sessions.get(user_id)
        if session_id:
            return self.sessions.get(session_id)
        return None
    
    async def update_session(self, session: Session) -> None:
        """Update session information."""
        session.last_activity = datetime.utcnow()
        self.sessions[session.session_id] = session
    
    async def end_session(self, session_id: SessionId) -> None:
        """End a user session."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.status = SessionStatus.ENDED
            session.last_activity = datetime.utcnow()
            
            # Remove from user sessions mapping
            if session.whatsapp_user in self.user_sessions:
                del self.user_sessions[session.whatsapp_user]
            
            logger.info(f"Ended in-memory session {session_id}")
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.session_ttl)
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.last_activity < cutoff_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.end_session(session_id)
        
        return len(expired_sessions)
