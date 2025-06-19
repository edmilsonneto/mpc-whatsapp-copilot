"""
MCP Server Core Types and Interfaces

This module defines the core types, interfaces, and data structures
used throughout the MCP WhatsApp-GitHub Copilot Bridge system.
"""

from typing import Any, Dict, List, Optional, Union, Literal
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import uuid


class SessionStatus(str, Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    BLOCKED = "blocked"


class CommandType(str, Enum):
    """WhatsApp command types."""
    COMPLETE = "completa"
    EXPLAIN = "explica"
    TEST = "testa" 
    OPEN = "abre"
    CONTEXT = "contexto"
    APPLY = "aplica"
    STATUS = "status"


class SuggestionStatus(str, Enum):
    """Status of code suggestions."""
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"
    EXPIRED = "expired"


class LanguageType(str, Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"
    GO = "go"
    RUST = "rust"
    PHP = "php"
    RUBY = "ruby"
    HTML = "html"
    CSS = "css"
    SQL = "sql"
    BASH = "bash"
    YAML = "yaml"
    JSON = "json"
    MARKDOWN = "markdown"
    OTHER = "other"


@dataclass
class WhatsAppMessage:
    """WhatsApp message data structure."""
    id: str
    from_user: str
    body: str
    timestamp: datetime
    command_type: Optional[CommandType] = None
    parsed_content: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class CodeContext:
    """Code context information."""
    file_path: Optional[str] = None
    language: Optional[LanguageType] = None
    cursor_position: Optional[int] = None
    selected_text: Optional[str] = None
    surrounding_code: Optional[str] = None
    project_context: Optional[Dict[str, Any]] = None


@dataclass
class CopilotSuggestion:
    """GitHub Copilot suggestion data."""
    id: str
    content: str
    language: LanguageType
    start_position: int
    end_position: int
    confidence: float
    context: CodeContext
    metadata: Dict[str, Any]
    created_at: datetime
    status: SuggestionStatus = SuggestionStatus.PENDING


@dataclass
class Session:
    """User session information."""
    id: str
    whatsapp_user: str
    vscode_workspace: Optional[str]
    status: SessionStatus
    created_at: datetime
    last_activity: datetime
    context: Optional[CodeContext]
    active_suggestions: List[CopilotSuggestion]
    metadata: Dict[str, Any]


@dataclass
class WorkspaceInfo:
    """VS Code workspace information."""
    path: str
    name: str
    language: Optional[LanguageType]
    active_file: Optional[str]
    open_files: List[str]
    project_type: Optional[str]
    git_info: Optional[Dict[str, str]]


@dataclass
class HealthCheck:
    """System health check data."""
    service: str
    status: Literal["healthy", "unhealthy", "degraded"]
    timestamp: datetime
    details: Dict[str, Any]
    response_time_ms: float


@dataclass
class MCPRequest:
    """MCP request structure."""
    id: str
    method: str
    params: Dict[str, Any]
    session_id: Optional[str]
    timestamp: datetime


@dataclass
class MCPResponse:
    """MCP response structure."""
    id: str
    result: Optional[Dict[str, Any]]
    error: Optional[Dict[str, Any]]
    timestamp: datetime


@dataclass
class CopilotRequest:
    """Request to GitHub Copilot."""
    code_snippet: str
    language: LanguageType
    context: Optional[CodeContext] = None
    max_suggestions: int = 3
    temperature: float = 0.7


@dataclass
class CopilotResponse:
    """Response from GitHub Copilot."""
    suggestions: List[CopilotSuggestion]
    metadata: Dict[str, Any]
    request_id: str
    processing_time_ms: float


@dataclass
class CommandResult:
    """Result of a WhatsApp command execution."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[CopilotSuggestion]] = None
    error_code: Optional[str] = None


# Type aliases for better readability
SessionId = str
UserId = str
SuggestionId = str
WorkspacePath = str
FilePath = str

# Configuration types
ServerConfig = Dict[str, Any]
WhatsAppConfig = Dict[str, Any]
VSCodeConfig = Dict[str, Any]


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


def create_session(whatsapp_user: str, workspace: Optional[str] = None) -> Session:
    """Create a new session."""
    now = datetime.utcnow()
    return Session(
        id=generate_id(),
        whatsapp_user=whatsapp_user,
        vscode_workspace=workspace,
        status=SessionStatus.ACTIVE,
        created_at=now,
        last_activity=now,
        context=None,
        active_suggestions=[],
        metadata={}
    )


def create_suggestion(
    content: str,
    language: LanguageType,
    context: CodeContext,
    confidence: float = 0.8
) -> CopilotSuggestion:
    """Create a new Copilot suggestion."""
    return CopilotSuggestion(
        id=generate_id(),
        content=content,
        language=language,
        start_position=0,
        end_position=len(content),
        confidence=confidence,
        context=context,
        metadata={},
        created_at=datetime.utcnow(),
        status=SuggestionStatus.PENDING
    )
