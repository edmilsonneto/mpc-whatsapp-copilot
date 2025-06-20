"""
MCP Server Implementation

This module implements the core MCP (Model Context Protocol) server
that bridges WhatsApp and GitHub Copilot integration.
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from .config import get_config, validate_config, Config
from .types import (
    MCPRequest, MCPResponse, HealthCheck, SessionStatus,
    generate_id, Session, CommandResult
)
from .interfaces import (
    ISessionManager, ICopilotService, IVSCodeService,
    IWhatsAppService, ICacheService, IHealthService,
    MCPFunctionRegistry
)
from .session_manager import RedisSessionManager, InMemorySessionManager
from .cache_service import RedisCacheService, InMemoryCacheService
from .health_service import HealthService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('mcp_requests_total', 'Total MCP requests', ['method', 'status'])
REQUEST_DURATION = Histogram('mcp_request_duration_seconds', 'Request duration')
ACTIVE_SESSIONS = Counter('mcp_active_sessions_total', 'Total active sessions')


class MCPServer:
    """Main MCP Server class."""
    
    def __init__(self, config: Config):
        self.config = config
        self.app: Optional[FastAPI] = None
        self.function_registry = MCPFunctionRegistry()
        
        # Service dependencies (to be injected)
        self.session_manager: Optional[ISessionManager] = None
        self.copilot_service: Optional[ICopilotService] = None
        self.vscode_service: Optional[IVSCodeService] = None
        self.whatsapp_service: Optional[IWhatsAppService] = None
        self.cache_service: Optional[ICacheService] = None
        self.health_service: Optional[IHealthService] = None
        
        self._shutdown_event = asyncio.Event()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the MCP server and all services."""
        logger.info("Initializing MCP Server...")
        
        # Validate configuration
        config_errors = validate_config(self.config)
        if config_errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(config_errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Initialize FastAPI app
        self.app = self._create_app()
        
        # Initialize services (would be dependency injected in real implementation)
        await self._initialize_services()
        
        # Register MCP functions
        self._register_mcp_functions()
        
        self._initialized = True
        logger.info("MCP Server initialized successfully")
    
    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application."""
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info("Starting MCP Server...")
            yield
            # Shutdown
            logger.info("Shutting down MCP Server...")
            await self.shutdown()
        
        app = FastAPI(
            title="MCP WhatsApp-Copilot Bridge",
            description="Model Context Protocol server for WhatsApp-GitHub Copilot integration",
            version="0.1.0",
            lifespan=lifespan
        )
        
        # Add middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.server.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # Add routes
        self._add_routes(app)
        
        return app
    
    def _add_routes(self, app: FastAPI) -> None:
        """Add routes to FastAPI app."""
        
        @app.get("/health")
        async def health_check():
            """Health check endpoint."""
            try:
                health = await self.get_health_status()
                status_code = 200 if health.status == "healthy" else 503
                return JSONResponse(
                    content=health.__dict__,
                    status_code=status_code
                )
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return JSONResponse(
                    content={"status": "unhealthy", "error": str(e)},
                    status_code=503
                )
        
        @app.get("/metrics")
        async def metrics():
            """Prometheus metrics endpoint."""
            if not self.config.monitoring.enable_metrics:
                raise HTTPException(status_code=404, detail="Metrics disabled")
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
        
        @app.post("/mcp/call")
        async def mcp_call(request: Dict[str, Any]):
            """Main MCP function call endpoint."""
            start_time = datetime.utcnow()
            
            try:
                # Parse request
                mcp_request = MCPRequest(
                    id=request.get("id", generate_id()),
                    method=request["method"],
                    params=request.get("params", {}),
                    session_id=request.get("session_id"),
                    timestamp=start_time
                )
                
                # Execute function
                result = await self._execute_mcp_function(mcp_request)
                
                # Create response
                response = MCPResponse(
                    id=mcp_request.id,
                    result=result,
                    error=None,
                    timestamp=datetime.utcnow()
                )
                
                REQUEST_COUNT.labels(method=mcp_request.method, status="success").inc()
                return response.__dict__
                
            except Exception as e:
                logger.error(f"MCP call failed: {e}")
                error_response = MCPResponse(
                    id=request.get("id", generate_id()),
                    result=None,
                    error={"code": -32603, "message": str(e)},
                    timestamp=datetime.utcnow()
                )
                REQUEST_COUNT.labels(method=request.get("method", "unknown"), status="error").inc()
                return JSONResponse(
                    content=error_response.__dict__,
                    status_code=500
                )
            finally:
                duration = (datetime.utcnow() - start_time).total_seconds()
                REQUEST_DURATION.observe(duration)
        
        @app.get("/sessions")
        async def list_sessions():
            """List active sessions."""
            if not self.session_manager:
                raise HTTPException(status_code=503, detail="Session manager not available")
            
            # This would need to be implemented in the session manager
            return {"sessions": []}
          @app.get("/functions")
        async def list_functions():
            """List available MCP functions."""
            return {
                "functions": [
                    self.function_registry.get_function_info(name)
                    for name in self.function_registry.list_functions()
                ]
            }
    
    async def _initialize_services(self) -> None:
        """Initialize all services."""
        logger.info("Initializing services...")
        
        # Initialize Session Manager
        if self.config.redis:
            logger.info("Initializing Redis session manager")
            self.session_manager = RedisSessionManager(self.config.redis)
            await self.session_manager.connect()
        else:
            logger.info("Initializing in-memory session manager")
            self.session_manager = InMemorySessionManager()
        
        # Initialize Cache Service
        if self.config.redis:
            logger.info("Initializing Redis cache service")
            self.cache_service = RedisCacheService(self.config.redis)
            await self.cache_service.connect()
        else:
            logger.info("Initializing in-memory cache service")
            self.cache_service = InMemoryCacheService()
            await self.cache_service.connect()
        
        # Initialize Health Service
        self.health_service = HealthService(
            self.config,
            self.session_manager,
            self.cache_service
        )
        await self.health_service.start_monitoring()
        
        # TODO: Initialize other services when implemented
        # self.copilot_service = CopilotService(self.config)
        # self.vscode_service = VSCodeService(self.config)
        # self.whatsapp_service = WhatsAppService(self.config)
        
        logger.info("Services initialized successfully")
    
    def _register_mcp_functions(self) -> None:
        """Register MCP functions."""
        logger.info("Registering MCP functions...")
        
        from .functions import (
            GetCopilotSuggestionFunction,
            ExplainCodeFunction,
            GenerateTestsFunction,
            OpenFileFunction,
            GetWorkspaceContextFunction,
            ApplySuggestionFunction,
            GetActiveSessionFunction
        )
        
        # Register all MCP function implementations
        self.function_registry.register(GetCopilotSuggestionFunction())
        self.function_registry.register(ExplainCodeFunction())
        self.function_registry.register(GenerateTestsFunction())
        self.function_registry.register(OpenFileFunction())
        self.function_registry.register(GetWorkspaceContextFunction())
        self.function_registry.register(ApplySuggestionFunction())
        self.function_registry.register(GetActiveSessionFunction())
        
        logger.info(f"Registered {len(self.function_registry.list_functions())} MCP functions")
    
    async def _execute_mcp_function(self, request: MCPRequest) -> Dict[str, Any]:
        """Execute an MCP function."""
        function = self.function_registry.get(request.method)
        if not function:
            raise ValueError(f"Unknown MCP function: {request.method}")
        
        return await function.execute(request.params, request.session_id)
    
    async def get_health_status(self) -> HealthCheck:
        """Get overall health status."""
        start_time = datetime.utcnow()
        
        # Check if server is initialized
        if not self._initialized:
            return HealthCheck(
                service="mcp-server",
                status="unhealthy",
                timestamp=datetime.utcnow(),
                details={"error": "Server not initialized"},
                response_time_ms=0
            )
        
        # TODO: Check health of all services
        status = "healthy"
        details = {
            "initialized": self._initialized,
            "functions_registered": len(self.function_registry.list_functions())
        }
        
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds() * 1000
        
        return HealthCheck(
            service="mcp-server",
            status=status,
            timestamp=end_time,
            details=details,
            response_time_ms=response_time
        )
    
    async def start(self) -> None:
        """Start the MCP server."""
        if not self._initialized:
            await self.initialize()
        
        if not self.app:
            raise RuntimeError("Server not initialized")
        
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for signame in ('SIGINT', 'SIGTERM'):
            if hasattr(signal, signame):
                loop.add_signal_handler(
                    getattr(signal, signame),
                    lambda: asyncio.create_task(self._signal_handler())
                )
        
        # Start server
        config = uvicorn.Config(
            self.app,
            host=self.config.server.host,
            port=self.config.server.port,
            log_level=self.config.server.log_level.lower(),
            workers=1,  # Single worker for now
            access_log=self.config.monitoring.log_requests
        )
        
        server = uvicorn.Server(config)
        logger.info(f"Starting MCP Server on {self.config.server.host}:{self.config.server.port}")
        
        try:
            await server.serve()
        except Exception as e:
            logger.error(f"Server failed to start: {e}")
            raise
    
    async def _signal_handler(self) -> None:
        """Handle shutdown signals."""
        logger.info("Received shutdown signal")
        self._shutdown_event.set()
    
    async def shutdown(self) -> None:
        """Shutdown the server gracefully."""
        logger.info("Shutting down MCP Server...")
        
        # TODO: Shutdown all services
        # if self.session_manager:
        #     await self.session_manager.shutdown()
        # if self.copilot_service:
        #     await self.copilot_service.shutdown()
        # etc...
        
        self._initialized = False
        logger.info("MCP Server shutdown complete")


async def create_server() -> MCPServer:
    """Create and initialize MCP server."""
    config = get_config()
    server = MCPServer(config)
    await server.initialize()
    return server


async def main() -> None:
    """Main entry point."""
    try:
        server = await create_server()
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
