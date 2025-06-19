"""
MCP Server Interfaces

This module defines the core interfaces and abstract base classes
for the MCP WhatsApp-GitHub Copilot Bridge system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol
from .types import (
    Session, SessionId, UserId, SuggestionId,
    CopilotSuggestion, CopilotRequest, CopilotResponse,
    WhatsAppMessage, CommandResult, WorkspaceInfo,
    MCPRequest, MCPResponse, HealthCheck, CodeContext
)


class ICopilotService(Protocol):
    """Interface for GitHub Copilot integration."""
    
    async def get_suggestion(
        self,
        request: CopilotRequest
    ) -> CopilotResponse:
        """Get code suggestions from GitHub Copilot."""
        ...
    
    async def explain_code(
        self,
        code: str,
        language: str,
        context: Optional[CodeContext] = None
    ) -> str:
        """Get code explanation from Copilot."""
        ...
    
    async def generate_tests(
        self,
        function_code: str,
        test_framework: str = "pytest",
        language: str = "python"
    ) -> str:
        """Generate unit tests for given function."""
        ...


class IVSCodeService(Protocol):
    """Interface for VS Code integration."""
    
    async def open_file(self, file_path: str) -> Dict[str, Any]:
        """Open a file in VS Code."""
        ...
    
    async def get_workspace_context(self) -> WorkspaceInfo:
        """Get current workspace context."""
        ...
    
    async def apply_suggestion(
        self,
        suggestion_id: SuggestionId,
        suggestion: CopilotSuggestion
    ) -> bool:
        """Apply a code suggestion to the editor."""
        ...
    
    async def get_active_editor_context(self) -> Optional[CodeContext]:
        """Get context from the active editor."""
        ...


class ISessionManager(Protocol):
    """Interface for session management."""
    
    async def create_session(
        self,
        whatsapp_user: UserId,
        workspace: Optional[str] = None
    ) -> Session:
        """Create a new user session."""
        ...
    
    async def get_session(self, session_id: SessionId) -> Optional[Session]:
        """Get session by ID."""
        ...
    
    async def get_user_session(self, user_id: UserId) -> Optional[Session]:
        """Get active session for user."""
        ...
    
    async def update_session(self, session: Session) -> None:
        """Update session information."""
        ...
    
    async def end_session(self, session_id: SessionId) -> None:
        """End a user session."""
        ...
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        ...


class IWhatsAppService(Protocol):
    """Interface for WhatsApp integration."""
    
    async def send_message(
        self,
        user_id: UserId,
        message: str,
        session_id: Optional[SessionId] = None
    ) -> bool:
        """Send a message to WhatsApp user."""
        ...
    
    async def send_formatted_response(
        self,
        user_id: UserId,
        result: CommandResult,
        session_id: Optional[SessionId] = None
    ) -> bool:
        """Send formatted command result to user."""
        ...
    
    async def parse_command(self, message: WhatsAppMessage) -> Optional[Dict[str, Any]]:
        """Parse WhatsApp message for commands."""
        ...


class ICacheService(Protocol):
    """Interface for caching service."""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL."""
        ...
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        ...
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        ...
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        ...


class IHealthService(Protocol):
    """Interface for health monitoring."""
    
    async def check_health(self) -> HealthCheck:
        """Perform health check."""
        ...
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics."""
        ...
    
    async def log_metric(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Log a metric."""
        ...


class BaseService(ABC):
    """Base service class with common functionality."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the service gracefully."""
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized
    
    async def health_check(self) -> HealthCheck:
        """Perform service health check."""
        from datetime import datetime
        from .types import HealthCheck
        
        start_time = datetime.utcnow()
        status = "healthy" if self._initialized else "unhealthy"
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds() * 1000
        
        return HealthCheck(
            service=self.__class__.__name__,
            status=status,
            timestamp=end_time,
            details={"initialized": self._initialized},
            response_time_ms=response_time
        )


class IMCPFunction(Protocol):
    """Interface for MCP function implementations."""
    
    @property
    def name(self) -> str:
        """Function name."""
        ...
    
    @property
    def description(self) -> str:
        """Function description."""
        ...
    
    @property
    def parameters(self) -> Dict[str, Any]:
        """Function parameters schema."""
        ...
    
    async def execute(
        self,
        params: Dict[str, Any],
        session_id: Optional[SessionId] = None
    ) -> Dict[str, Any]:
        """Execute the function."""
        ...


class MCPFunctionRegistry:
    """Registry for MCP functions."""
    
    def __init__(self):
        self._functions: Dict[str, IMCPFunction] = {}
    
    def register(self, function: IMCPFunction) -> None:
        """Register a function."""
        self._functions[function.name] = function
    
    def get(self, name: str) -> Optional[IMCPFunction]:
        """Get function by name."""
        return self._functions.get(name)
    
    def list_functions(self) -> List[str]:
        """List all registered function names."""
        return list(self._functions.keys())
    
    def get_function_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get function information."""
        function = self._functions.get(name)
        if not function:
            return None
        
        return {
            "name": function.name,
            "description": function.description,
            "parameters": function.parameters
        }
