"""
Health Service Implementation

This module implements comprehensive health checks and monitoring
for all system components including external dependencies.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, NamedTuple
from enum import Enum

import aiohttp
import psutil
from prometheus_client import Gauge, Counter

from .interfaces import IHealthService, ISessionManager, ICacheService
from .config import Config

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(NamedTuple):
    """Health information for a component."""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    last_check: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class SystemMetrics(NamedTuple):
    """System performance metrics."""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_percent: float
    uptime_seconds: float


# Prometheus metrics for health monitoring
COMPONENT_HEALTH = Gauge(
    'mcp_component_health_status',
    'Component health status (1=healthy, 0.5=degraded, 0=unhealthy)',
    ['component']
)

HEALTH_CHECK_DURATION = Gauge(
    'mcp_health_check_duration_seconds',
    'Health check response time',
    ['component']
)

HEALTH_CHECK_TOTAL = Counter(
    'mcp_health_checks_total',
    'Total health checks performed',
    ['component', 'status']
)


class HealthService(IHealthService):
    """Comprehensive health monitoring service."""
    
    def __init__(
        self,
        config: Config,
        session_manager: Optional[ISessionManager] = None,
        cache_service: Optional[ICacheService] = None
    ):
        """Initialize health service.
        
        Args:
            config: Application configuration
            session_manager: Optional session manager instance
            cache_service: Optional cache service instance
        """
        self.config = config
        self.session_manager = session_manager
        self.cache_service = cache_service
        
        self.start_time = time.time()
        self.component_healths: Dict[str, ComponentHealth] = {}
        self._check_interval = 30  # seconds
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Health check thresholds
        self.cpu_threshold = 80.0
        self.memory_threshold = 85.0
        self.disk_threshold = 90.0
        self.response_time_threshold = 5000.0  # 5 seconds
    
    async def start_monitoring(self) -> None:
        """Start continuous health monitoring."""
        self._monitoring_task = asyncio.create_task(self._periodic_health_checks())
        logger.info("Health monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitoring stopped")
    
    async def check_overall_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all components.
        
        Returns:
            Overall health status and component details
        """
        health_checks = await asyncio.gather(
            self._check_system_health(),
            self._check_session_manager_health(),
            self._check_cache_health(),
            self._check_external_services_health(),
            return_exceptions=True
        )
        
        components = {}
        overall_status = HealthStatus.HEALTHY
        
        for check_result in health_checks:
            if isinstance(check_result, Exception):
                logger.error(f"Health check failed: {check_result}")
                continue
            
            if isinstance(check_result, dict):
                components.update(check_result)
        
        # Determine overall status
        for component_name, component in components.items():
            if component.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                break
            elif component.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        # Update Prometheus metrics
        for component_name, component in components.items():
            status_value = self._status_to_metric_value(component.status)
            COMPONENT_HEALTH.labels(component=component_name).set(status_value)
            HEALTH_CHECK_TOTAL.labels(
                component=component_name,
                status=component.status.value
            ).inc()
            
            if component.response_time_ms:
                HEALTH_CHECK_DURATION.labels(component=component_name).set(
                    component.response_time_ms / 1000
                )
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - self.start_time,
            "components": {name: {
                "status": comp.status.value,
                "message": comp.message,
                "response_time_ms": comp.response_time_ms,
                "last_check": comp.last_check.isoformat() if comp.last_check else None,
                "metadata": comp.metadata
            } for name, comp in components.items()}
        }
    
    async def _check_system_health(self) -> Dict[str, ComponentHealth]:
        """Check system resource health."""
        start_time = time.time()
        
        try:
            metrics = self._get_system_metrics()
            
            # Determine status based on thresholds
            status = HealthStatus.HEALTHY
            messages = []
            
            if metrics.cpu_percent > self.cpu_threshold:
                status = HealthStatus.DEGRADED
                messages.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
            
            if metrics.memory_percent > self.memory_threshold:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                messages.append(f"High memory usage: {metrics.memory_percent:.1f}%")
            
            if metrics.disk_percent > self.disk_threshold:
                status = HealthStatus.UNHEALTHY
                messages.append(f"Critical disk usage: {metrics.disk_percent:.1f}%")
            
            message = "; ".join(messages) if messages else "System resources are healthy"
            response_time = (time.time() - start_time) * 1000
            
            return {
                "system": ComponentHealth(
                    name="system",
                    status=status,
                    message=message,
                    response_time_ms=response_time,
                    last_check=datetime.utcnow(),
                    metadata={
                        "cpu_percent": metrics.cpu_percent,
                        "memory_percent": metrics.memory_percent,
                        "memory_available_mb": metrics.memory_available_mb,
                        "disk_percent": metrics.disk_percent,
                        "uptime_seconds": metrics.uptime_seconds
                    }
                )
            }
            
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return {
                "system": ComponentHealth(
                    name="system",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Failed to get system metrics: {str(e)}",
                    last_check=datetime.utcnow()
                )
            }
    
    async def _check_session_manager_health(self) -> Dict[str, ComponentHealth]:
        """Check session manager health."""
        if not self.session_manager:
            return {
                "session_manager": ComponentHealth(
                    name="session_manager",
                    status=HealthStatus.UNKNOWN,
                    message="Session manager not configured",
                    last_check=datetime.utcnow()
                )
            }
        
        start_time = time.time()
        
        try:
            # Test basic session operations
            test_session = await self.session_manager.create_session("health_check_user")
            await self.session_manager.get_session(test_session.session_id)
            await self.session_manager.end_session(test_session.session_id)
            
            response_time = (time.time() - start_time) * 1000
            
            # Get session statistics if available
            metadata = {}
            if hasattr(self.session_manager, 'get_active_session_count'):
                try:
                    active_count = await self.session_manager.get_active_session_count()
                    metadata["active_sessions"] = active_count
                except Exception:
                    pass
            
            return {
                "session_manager": ComponentHealth(
                    name="session_manager",
                    status=HealthStatus.HEALTHY,
                    message="Session manager is operational",
                    response_time_ms=response_time,
                    last_check=datetime.utcnow(),
                    metadata=metadata
                )
            }
            
        except Exception as e:
            logger.error(f"Session manager health check failed: {e}")
            return {
                "session_manager": ComponentHealth(
                    name="session_manager",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Session manager error: {str(e)}",
                    last_check=datetime.utcnow()
                )
            }
    
    async def _check_cache_health(self) -> Dict[str, ComponentHealth]:
        """Check cache service health."""
        if not self.cache_service:
            return {
                "cache": ComponentHealth(
                    name="cache",
                    status=HealthStatus.UNKNOWN,
                    message="Cache service not configured",
                    last_check=datetime.utcnow()
                )
            }
        
        start_time = time.time()
        
        try:
            # Test basic cache operations
            test_key = "health_check_key"
            test_value = {"timestamp": datetime.utcnow().isoformat()}
            
            await self.cache_service.set(test_key, test_value, ttl=60)
            retrieved_value = await self.cache_service.get(test_key)
            await self.cache_service.delete(test_key)
            
            if retrieved_value != test_value:
                raise ValueError("Cache value mismatch")
            
            response_time = (time.time() - start_time) * 1000
            
            # Get cache statistics
            metadata = {}
            try:
                stats = await self.cache_service.get_stats()
                metadata.update(stats)
            except Exception:
                pass
            
            return {
                "cache": ComponentHealth(
                    name="cache",
                    status=HealthStatus.HEALTHY,
                    message="Cache service is operational",
                    response_time_ms=response_time,
                    last_check=datetime.utcnow(),
                    metadata=metadata
                )
            }
            
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {
                "cache": ComponentHealth(
                    name="cache",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Cache service error: {str(e)}",
                    last_check=datetime.utcnow()
                )
            }
    
    async def _check_external_services_health(self) -> Dict[str, ComponentHealth]:
        """Check external service health (GitHub Copilot, VS Code, etc.)."""
        components = {}
        
        # Check VS Code connection (if configured)
        if hasattr(self.config, 'vscode_config'):
            vscode_health = await self._check_vscode_health()
            components["vscode"] = vscode_health
        
        return components
    
    async def _check_vscode_health(self) -> ComponentHealth:
        """Check VS Code service health."""
        start_time = time.time()
        
        try:
            # Try to connect to VS Code API
            timeout = aiohttp.ClientTimeout(total=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # This is a placeholder - actual VS Code health check would depend on implementation
                async with session.get("http://localhost:3000/health") as response:
                    if response.status == 200:
                        response_time = (time.time() - start_time) * 1000
                        return ComponentHealth(
                            name="vscode",
                            status=HealthStatus.HEALTHY,
                            message="VS Code service is reachable",
                            response_time_ms=response_time,
                            last_check=datetime.utcnow()
                        )
                    else:
                        return ComponentHealth(
                            name="vscode",
                            status=HealthStatus.DEGRADED,
                            message=f"VS Code service returned status {response.status}",
                            last_check=datetime.utcnow()
                        )
                        
        except asyncio.TimeoutError:
            return ComponentHealth(
                name="vscode",
                status=HealthStatus.UNHEALTHY,
                message="VS Code service timeout",
                last_check=datetime.utcnow()
            )
        except Exception as e:
            return ComponentHealth(
                name="vscode",
                status=HealthStatus.UNHEALTHY,
                message=f"VS Code service error: {str(e)}",
                last_check=datetime.utcnow()
            )
    
    def _get_system_metrics(self) -> SystemMetrics:
        """Get current system performance metrics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        uptime = time.time() - self.start_time
        
        return SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available_mb=memory.available / (1024 * 1024),
            disk_percent=disk.percent,
            uptime_seconds=uptime
        )
    
    def _status_to_metric_value(self, status: HealthStatus) -> float:
        """Convert health status to Prometheus metric value."""
        return {
            HealthStatus.HEALTHY: 1.0,
            HealthStatus.DEGRADED: 0.5,
            HealthStatus.UNHEALTHY: 0.0,
            HealthStatus.UNKNOWN: -1.0
        }.get(status, -1.0)
    
    async def _periodic_health_checks(self) -> None:
        """Perform periodic health checks."""
        while True:
            try:
                await asyncio.sleep(self._check_interval)
                health_status = await self.check_overall_health()
                
                # Log any unhealthy components
                for component_name, component_data in health_status["components"].items():
                    if component_data["status"] in ["degraded", "unhealthy"]:
                        logger.warning(
                            f"Component {component_name} is {component_data['status']}: "
                            f"{component_data['message']}"
                        )
                
                # Store latest health status
                self.component_healths.update({
                    name: ComponentHealth(
                        name=name,
                        status=HealthStatus(data["status"]),
                        message=data["message"],
                        response_time_ms=data["response_time_ms"],
                        last_check=datetime.fromisoformat(data["last_check"]) if data["last_check"] else None,
                        metadata=data["metadata"]
                    ) for name, data in health_status["components"].items()
                })
                
            except asyncio.CancelledError:
                logger.info("Periodic health checks cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic health check: {e}")


def create_health_service(
    config: Config,
    session_manager: Optional[ISessionManager] = None,
    cache_service: Optional[ICacheService] = None
) -> HealthService:
    """Factory function to create health service.
    
    Args:
        config: Application configuration
        session_manager: Optional session manager instance
        cache_service: Optional cache service instance
        
    Returns:
        Health service instance
    """
    return HealthService(config, session_manager, cache_service)
