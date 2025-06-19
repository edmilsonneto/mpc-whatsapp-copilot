"""
MCP WhatsApp-GitHub Copilot Bridge Server

This package implements a Model Context Protocol (MCP) server that bridges
WhatsApp messaging with GitHub Copilot functionality in VS Code.
"""

__version__ = "0.1.0"
__author__ = "MCP WhatsApp Copilot Team"
__description__ = "MCP Server for WhatsApp-GitHub Copilot Bridge"

from .server import MCPServer, create_server, main
from .config import Config, get_config
from .types import (
    Session, CopilotSuggestion, WhatsAppMessage, CommandResult,
    SessionStatus, CommandType, SuggestionStatus, LanguageType
)

__all__ = [
    "MCPServer",
    "create_server", 
    "main",
    "Config",
    "get_config",
    "Session",
    "CopilotSuggestion",
    "WhatsAppMessage", 
    "CommandResult",
    "SessionStatus",
    "CommandType",
    "SuggestionStatus",
    "LanguageType"
]
