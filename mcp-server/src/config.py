"""
Configuration management for MCP Server.

This module handles configuration loading from environment variables,
config files, and provides default values.
"""

import os
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """MCP Server configuration."""
    host: str = "localhost"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: list = field(default_factory=lambda: ["*"])
    max_workers: int = 4
    timeout: int = 30


@dataclass 
class RedisConfig:
    """Redis configuration."""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    ssl: bool = False
    connection_pool_size: int = 10


@dataclass
class VSCodeConfig:
    """VS Code integration configuration."""
    executable_path: Optional[str] = None
    workspace_path: Optional[str] = None
    extension_id: str = "mcp-whatsapp-copilot-extension"
    timeout: int = 10
    port: int = 8001


@dataclass
class WhatsAppConfig:
    """WhatsApp integration configuration."""
    webhook_url: str = "http://localhost:3000/webhook"
    session_timeout: int = 3600  # 1 hour
    max_message_length: int = 4000
    rate_limit_per_minute: int = 20
    allowed_users: list = field(default_factory=list)


@dataclass
class CopilotConfig:
    """GitHub Copilot configuration."""
    api_key: Optional[str] = None
    model: str = "copilot-codex"
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout: int = 15


@dataclass
class SecurityConfig:
    """Security configuration."""
    secret_key: str = "your-secret-key-change-this"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600
    encryption_key: Optional[str] = None
    allowed_origins: list = field(default_factory=lambda: ["*"])


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration."""
    enable_metrics: bool = True
    metrics_port: int = 8002
    prometheus_endpoint: str = "/metrics"
    health_check_interval: int = 30
    log_requests: bool = True


@dataclass
class Config:
    """Main configuration class."""
    server: ServerConfig = field(default_factory=ServerConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    vscode: VSCodeConfig = field(default_factory=VSCodeConfig)
    whatsapp: WhatsAppConfig = field(default_factory=WhatsAppConfig)
    copilot: CopilotConfig = field(default_factory=CopilotConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)


def load_config_from_env() -> Config:
    """Load configuration from environment variables."""
    config = Config()
    
    # Server config
    config.server.host = os.getenv("MCP_HOST", config.server.host)
    config.server.port = int(os.getenv("MCP_PORT", config.server.port))
    config.server.debug = os.getenv("MCP_DEBUG", "false").lower() == "true"
    config.server.log_level = os.getenv("MCP_LOG_LEVEL", config.server.log_level)
    config.server.max_workers = int(os.getenv("MCP_MAX_WORKERS", config.server.max_workers))
    config.server.timeout = int(os.getenv("MCP_TIMEOUT", config.server.timeout))
    
    # Redis config
    config.redis.host = os.getenv("REDIS_HOST", config.redis.host)
    config.redis.port = int(os.getenv("REDIS_PORT", config.redis.port))
    config.redis.password = os.getenv("REDIS_PASSWORD")
    config.redis.db = int(os.getenv("REDIS_DB", config.redis.db))
    config.redis.ssl = os.getenv("REDIS_SSL", "false").lower() == "true"
    
    # VS Code config
    config.vscode.executable_path = os.getenv("VSCODE_PATH")
    config.vscode.workspace_path = os.getenv("VSCODE_WORKSPACE")
    config.vscode.timeout = int(os.getenv("VSCODE_TIMEOUT", config.vscode.timeout))
    config.vscode.port = int(os.getenv("VSCODE_PORT", config.vscode.port))
    
    # WhatsApp config
    config.whatsapp.webhook_url = os.getenv("WHATSAPP_WEBHOOK_URL", config.whatsapp.webhook_url)
    config.whatsapp.session_timeout = int(os.getenv("WHATSAPP_SESSION_TIMEOUT", config.whatsapp.session_timeout))
    config.whatsapp.rate_limit_per_minute = int(os.getenv("WHATSAPP_RATE_LIMIT", config.whatsapp.rate_limit_per_minute))
    
    # Parse allowed users
    allowed_users_str = os.getenv("WHATSAPP_ALLOWED_USERS", "")
    if allowed_users_str:
        config.whatsapp.allowed_users = [user.strip() for user in allowed_users_str.split(",")]
    
    # Copilot config
    config.copilot.api_key = os.getenv("COPILOT_API_KEY")
    config.copilot.model = os.getenv("COPILOT_MODEL", config.copilot.model)
    config.copilot.max_tokens = int(os.getenv("COPILOT_MAX_TOKENS", config.copilot.max_tokens))
    config.copilot.temperature = float(os.getenv("COPILOT_TEMPERATURE", config.copilot.temperature))
    config.copilot.timeout = int(os.getenv("COPILOT_TIMEOUT", config.copilot.timeout))
    
    # Security config
    config.security.secret_key = os.getenv("SECRET_KEY", config.security.secret_key)
    config.security.jwt_algorithm = os.getenv("JWT_ALGORITHM", config.security.jwt_algorithm)
    config.security.jwt_expiration = int(os.getenv("JWT_EXPIRATION", config.security.jwt_expiration))
    config.security.encryption_key = os.getenv("ENCRYPTION_KEY")
    
    # Monitoring config
    config.monitoring.enable_metrics = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    config.monitoring.metrics_port = int(os.getenv("METRICS_PORT", config.monitoring.metrics_port))
    config.monitoring.health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", config.monitoring.health_check_interval))
    config.monitoring.log_requests = os.getenv("LOG_REQUESTS", "true").lower() == "true"
    
    return config


def load_config_from_file(file_path: str) -> Optional[Config]:
    """Load configuration from JSON file."""
    try:
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"Config file not found: {file_path}")
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = Config()
        
        # Update config from file data
        if "server" in data:
            for key, value in data["server"].items():
                if hasattr(config.server, key):
                    setattr(config.server, key, value)
        
        if "redis" in data:
            for key, value in data["redis"].items():
                if hasattr(config.redis, key):
                    setattr(config.redis, key, value)
        
        if "vscode" in data:
            for key, value in data["vscode"].items():
                if hasattr(config.vscode, key):
                    setattr(config.vscode, key, value)
        
        if "whatsapp" in data:
            for key, value in data["whatsapp"].items():
                if hasattr(config.whatsapp, key):
                    setattr(config.whatsapp, key, value)
        
        if "copilot" in data:
            for key, value in data["copilot"].items():
                if hasattr(config.copilot, key):
                    setattr(config.copilot, key, value)
        
        if "security" in data:
            for key, value in data["security"].items():
                if hasattr(config.security, key):
                    setattr(config.security, key, value)
        
        if "monitoring" in data:
            for key, value in data["monitoring"].items():
                if hasattr(config.monitoring, key):
                    setattr(config.monitoring, key, value)
        
        return config
        
    except Exception as e:
        logger.error(f"Error loading config from file {file_path}: {e}")
        return None


def get_config() -> Config:
    """Get configuration with precedence: env vars > config file > defaults."""
    # Start with defaults
    config = Config()
    
    # Try to load from config file
    config_file = os.getenv("MCP_CONFIG_FILE", "config.json")
    file_config = load_config_from_file(config_file)
    if file_config:
        config = file_config
    
    # Override with environment variables
    env_config = load_config_from_env()
    
    # Merge configs (env takes precedence)
    for section_name in ["server", "redis", "vscode", "whatsapp", "copilot", "security", "monitoring"]:
        section = getattr(config, section_name)
        env_section = getattr(env_config, section_name)
        
        for field_name in section.__dataclass_fields__:
            env_value = getattr(env_section, field_name)
            default_value = getattr(Config(), section_name).__dict__.get(field_name)
            
            # Only override if env value is different from default
            if env_value != default_value:
                setattr(section, field_name, env_value)
    
    return config


def validate_config(config: Config) -> list[str]:
    """Validate configuration and return list of errors."""
    errors = []
    
    # Validate server config
    if config.server.port < 1 or config.server.port > 65535:
        errors.append("Server port must be between 1 and 65535")
    
    if config.server.max_workers < 1:
        errors.append("Max workers must be at least 1")
    
    # Validate Redis config
    if config.redis.port < 1 or config.redis.port > 65535:
        errors.append("Redis port must be between 1 and 65535")
    
    # Validate VS Code config
    if config.vscode.port < 1 or config.vscode.port > 65535:
        errors.append("VS Code port must be between 1 and 65535")
    
    # Validate Copilot config
    if config.copilot.temperature < 0 or config.copilot.temperature > 2:
        errors.append("Copilot temperature must be between 0 and 2")
    
    if config.copilot.max_tokens < 1:
        errors.append("Copilot max tokens must be at least 1")
    
    # Validate security config
    if len(config.security.secret_key) < 16:
        errors.append("Secret key must be at least 16 characters long")
    
    # Validate monitoring config
    if config.monitoring.metrics_port < 1 or config.monitoring.metrics_port > 65535:
        errors.append("Metrics port must be between 1 and 65535")
    
    if config.monitoring.health_check_interval < 1:
        errors.append("Health check interval must be at least 1 second")
    
    return errors
