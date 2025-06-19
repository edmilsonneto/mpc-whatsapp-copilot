"""
Unit tests for MCP Server core functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from src.types import (
    Session, CopilotSuggestion, LanguageType, SessionStatus,
    CodeContext, generate_id, create_session, create_suggestion
)
from src.config import Config, get_config, validate_config
from src.functions import (
    GetCopilotSuggestionFunction,
    ExplainCodeFunction,
    GenerateTestsFunction,
    OpenFileFunction,
    GetWorkspaceContextFunction,
    ApplySuggestionFunction,
    GetActiveSessionFunction
)


class TestTypes:
    """Test core types and data structures."""
    
    def test_generate_id(self):
        """Test ID generation."""
        id1 = generate_id()
        id2 = generate_id()
        
        assert isinstance(id1, str)
        assert isinstance(id2, str)
        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0
    
    def test_create_session(self):
        """Test session creation."""
        user = "test_user"
        workspace = "/test/workspace"
        
        session = create_session(user, workspace)
        
        assert isinstance(session, Session)
        assert session.whatsapp_user == user
        assert session.vscode_workspace == workspace
        assert session.status == SessionStatus.ACTIVE
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_activity, datetime)
        assert session.active_suggestions == []
        assert session.metadata == {}
    
    def test_create_suggestion(self):
        """Test suggestion creation."""
        content = "def test_function():\n    pass"
        language = LanguageType.PYTHON
        context = CodeContext(file_path="test.py", language=language)
        
        suggestion = create_suggestion(content, language, context)
        
        assert isinstance(suggestion, CopilotSuggestion)
        assert suggestion.content == content
        assert suggestion.language == language
        assert suggestion.context == context
        assert 0 <= suggestion.confidence <= 1
        assert isinstance(suggestion.created_at, datetime)


class TestConfig:
    """Test configuration management."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = Config()
        
        assert config.server.host == "localhost"
        assert config.server.port == 8000
        assert config.server.debug is False
        assert config.redis.host == "localhost"
        assert config.redis.port == 6379
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = Config()
        
        # Valid config should have no errors
        errors = validate_config(config)
        assert len(errors) == 0
        
        # Invalid port should cause error
        config.server.port = 0
        errors = validate_config(config)
        assert len(errors) > 0
        assert any("port must be between" in error for error in errors)
    
    @patch.dict('os.environ', {'MCP_PORT': '9000', 'MCP_DEBUG': 'true'})
    def test_env_override(self):
        """Test environment variable override."""
        from src.config import load_config_from_env
        
        config = load_config_from_env()
        
        assert config.server.port == 9000
        assert config.server.debug is True


class TestMCPFunctions:
    """Test MCP function implementations."""
    
    @pytest.mark.asyncio
    async def test_get_copilot_suggestion_function(self):
        """Test GetCopilotSuggestionFunction."""
        function = GetCopilotSuggestionFunction()
        
        assert function.name == "get_copilot_suggestion"
        assert "code_snippet" in function.parameters["properties"]
        assert "language" in function.parameters["properties"]
        
        params = {
            "code_snippet": "def hello():",
            "language": "python"
        }
        
        result = await function.execute(params)
        
        assert result["success"] is True
        assert "suggestion" in result
        assert "content" in result["suggestion"]
    
    @pytest.mark.asyncio
    async def test_explain_code_function(self):
        """Test ExplainCodeFunction."""
        function = ExplainCodeFunction()
        
        assert function.name == "explain_code"
        assert "code_block" in function.parameters["properties"]
        
        params = {
            "code_block": "def add(a, b):\n    return a + b",
            "language": "python"
        }
        
        result = await function.execute(params)
        
        assert result["success"] is True
        assert "explanation" in result
        assert isinstance(result["explanation"], str)
    
    @pytest.mark.asyncio
    async def test_generate_tests_function(self):
        """Test GenerateTestsFunction."""
        function = GenerateTestsFunction()
        
        assert function.name == "generate_tests"
        assert "function_code" in function.parameters["properties"]
        
        params = {
            "function_code": "def add(a, b):\n    return a + b",
            "test_framework": "pytest",
            "language": "python"
        }
        
        result = await function.execute(params)
        
        assert result["success"] is True
        assert "test_code" in result
        assert "pytest" in result["test_code"]
    
    @pytest.mark.asyncio
    async def test_open_file_function(self):
        """Test OpenFileFunction."""
        function = OpenFileFunction()
        
        assert function.name == "open_file"
        assert "file_path" in function.parameters["properties"]
        
        params = {
            "file_path": "/test/file.py",
            "line": 10,
            "column": 5
        }
        
        result = await function.execute(params)
        
        assert result["success"] is True
        assert result["file_path"] == "/test/file.py"
        assert result["line"] == 10
        assert result["column"] == 5
    
    @pytest.mark.asyncio
    async def test_get_workspace_context_function(self):
        """Test GetWorkspaceContextFunction."""
        function = GetWorkspaceContextFunction()
        
        assert function.name == "get_workspace_context"
        
        params = {}
        result = await function.execute(params)
        
        assert result["success"] is True
        assert "workspace" in result
        assert "path" in result["workspace"]
        assert "name" in result["workspace"]
    
    @pytest.mark.asyncio
    async def test_apply_suggestion_function(self):
        """Test ApplySuggestionFunction."""
        function = ApplySuggestionFunction()
        
        assert function.name == "apply_suggestion"
        assert "suggestion_id" in function.parameters["properties"]
        
        params = {
            "suggestion_id": "test-suggestion-id"
        }
        
        result = await function.execute(params)
        
        assert result["success"] is True
        assert result["suggestion_id"] == "test-suggestion-id"
    
    @pytest.mark.asyncio
    async def test_get_active_session_function(self):
        """Test GetActiveSessionFunction."""
        function = GetActiveSessionFunction()
        
        assert function.name == "get_active_session"
        
        params = {"user_id": "test-user"}
        result = await function.execute(params, session_id="test-session")
        
        assert result["success"] is True
        assert "session" in result
        assert result["session"]["id"] == "test-session"


class TestErrorHandling:
    """Test error handling in MCP functions."""
    
    @pytest.mark.asyncio
    async def test_missing_required_params(self):
        """Test handling of missing required parameters."""
        function = GetCopilotSuggestionFunction()
        
        # Missing required parameter should raise an error
        with pytest.raises(KeyError):
            await function.execute({})
    
    @pytest.mark.asyncio
    async def test_invalid_language(self):
        """Test handling of invalid language parameter."""
        function = GetCopilotSuggestionFunction()
        
        params = {
            "code_snippet": "def hello():",
            "language": "invalid-language"
        }
        
        # Should handle invalid enum gracefully
        with pytest.raises(ValueError):
            await function.execute(params)


@pytest.fixture
def sample_session():
    """Fixture providing a sample session."""
    return create_session("test_user", "/test/workspace")


@pytest.fixture
def sample_suggestion():
    """Fixture providing a sample suggestion."""
    context = CodeContext(
        file_path="test.py",
        language=LanguageType.PYTHON
    )
    return create_suggestion(
        "def test():\n    pass",
        LanguageType.PYTHON,
        context
    )


class TestIntegration:
    """Integration tests for MCP Server components."""
    
    def test_session_suggestion_integration(self, sample_session, sample_suggestion):
        """Test session and suggestion integration."""
        # Add suggestion to session
        sample_session.active_suggestions.append(sample_suggestion)
        
        assert len(sample_session.active_suggestions) == 1
        assert sample_session.active_suggestions[0].id == sample_suggestion.id
    
    def test_language_type_enum(self):
        """Test LanguageType enum functionality."""
        # Test enum values
        assert LanguageType.PYTHON.value == "python"
        assert LanguageType.JAVASCRIPT.value == "javascript"
        
        # Test enum creation from string
        lang = LanguageType("python")
        assert lang == LanguageType.PYTHON
        
        # Test invalid language
        with pytest.raises(ValueError):
            LanguageType("invalid")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
