"""
Dependency injection system for Cases Chat microservice
"""
from functools import lru_cache
from typing import AsyncGenerator, Dict, Type, Any, Optional, TypeVar, Generic
from neo4j import GraphDatabase
import logging
import concurrent.futures
from .config import settings
from .exceptions import ConfigurationError

# Check if async Neo4j is available (Neo4j 5.x)
try:
    from neo4j import AsyncGraphDatabase, AsyncDriver
    ASYNC_NEO4J_AVAILABLE = True
    DriverType = AsyncDriver
except ImportError:
    AsyncGraphDatabase = None
    AsyncDriver = None
    ASYNC_NEO4J_AVAILABLE = False
    from neo4j import Driver
    DriverType = Driver

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceContainer:
    """Service container for dependency injection"""
    
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Any] = {}
    
    def register_singleton(self, service_type: Type[T], instance: T) -> None:
        """Register a singleton service instance"""
        self._singletons[service_type] = instance
        logger.info(f"Registered singleton: {service_type.__name__}")
    
    def register_factory(self, service_type: Type[T], factory: Any) -> None:
        """Register a service factory"""
        self._factories[service_type] = factory
        logger.info(f"Registered factory for: {service_type.__name__}")
    
    def get_service(self, service_type: Type[T]) -> Optional[T]:
        """Get service instance"""
        # Check singletons first
        if service_type in self._singletons:
            return self._singletons[service_type]
        
        # Check if we have a factory
        if service_type in self._factories:
            instance = self._factories[service_type]()
            # Cache the instance as singleton
            self._singletons[service_type] = instance
            return instance
        
        # Check regular services
        return self._services.get(service_type)
    
    def register_service(self, service_type: Type[T], instance: T) -> None:
        """Register a service instance (non-singleton)"""
        self._services[service_type] = instance
        logger.info(f"Registered service: {service_type.__name__}")
    
    def clear(self) -> None:
        """Clear all registered services"""
        self._services.clear()
        self._singletons.clear()
        self._factories.clear()
        logger.info("Cleared all registered services")
    
    def has_service(self, service_type: Type) -> bool:
        """Check if a service is registered"""
        return (
            service_type in self._singletons or 
            service_type in self._factories or 
            service_type in self._services
        )


# Global container instance
container = ServiceContainer()


@lru_cache()
def get_neo4j_driver() -> DriverType:
    """Get Neo4j database driver (cached) - async or sync based on availability"""
    try:
        if ASYNC_NEO4J_AVAILABLE:
            driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password),
                max_connection_pool_size=settings.neo4j_max_connection_pool_size,
                connection_timeout=settings.neo4j_connection_timeout
            )
            logger.info(f"Created async Neo4j driver for: {settings.neo4j_uri}")
        else:
            driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password),
                max_connection_pool_size=settings.neo4j_max_connection_pool_size,
                connection_timeout=settings.neo4j_connection_timeout
            )
            logger.info(f"Created sync Neo4j driver for: {settings.neo4j_uri}")
        return driver
    except Exception as e:
        logger.error(f"Failed to create Neo4j driver: {e}")
        raise ConfigurationError(f"Failed to connect to Neo4j: {str(e)}")


async def get_storage_service():
    """Get unified storage service"""
    from ..services.storage.neo4j_storage import UnifiedNeo4jStorage
    
    storage = container.get_service(UnifiedNeo4jStorage)
    if not storage:
        driver = get_neo4j_driver()
        storage = UnifiedNeo4jStorage(driver)
        container.register_singleton(UnifiedNeo4jStorage, storage)
    
    return storage


async def get_doctor_coordinator():
    """Get doctor service coordinator"""
    from ..services.doctors.doctor_coordinator import DoctorCoordinator
    
    coordinator = container.get_service(DoctorCoordinator)
    if not coordinator:
        # Create new coordinator - it will be registered during app startup
        raise RuntimeError("DoctorCoordinator not initialized. Please ensure app startup completed.")
    
    return coordinator


async def get_websocket_manager():
    """Get WebSocket manager"""
    from .websocket_manager import websocket_manager
    return websocket_manager


async def get_case_service():
    """Get case management service"""
    from ..services.case_management.case_service import CaseService
    
    service = container.get_service(CaseService)
    if not service:
        storage = await get_storage_service()
        service = CaseService(storage)
        container.register_singleton(CaseService, service)
    
    return service


async def get_chat_service():
    """Get chat service"""
    from ..services.chat.message_processor import MessageProcessor
    
    service = container.get_service(MessageProcessor)
    if not service:
        storage = await get_storage_service()
        doctor_coordinator = await get_doctor_coordinator()
        ws_manager = await get_websocket_manager()
        
        service = MessageProcessor(storage, doctor_coordinator, ws_manager)
        container.register_singleton(MessageProcessor, service)
    
    return service


async def get_media_handler():
    """Get media handler service"""
    from ..services.media.media_handler import MediaHandler
    
    handler = container.get_service(MediaHandler)
    if not handler:
        storage = await get_storage_service()
        handler = MediaHandler(storage, settings)
        container.register_singleton(MediaHandler, handler)
    
    return handler


async def get_mcp_client():
    """Get MCP client if enabled"""
    if not settings.mcp_server_enabled:
        return None
    
    from ..services.mcp.mcp_client import MCPClient
    
    client = container.get_service(MCPClient)
    if not client:
        client = MCPClient(
            host=settings.mcp_server_host,
            port=settings.mcp_server_port,
            timeout=settings.mcp_server_timeout
        )
        container.register_singleton(MCPClient, client)
    
    return client


# Dependency injection for FastAPI routes
async def get_db_session() -> AsyncGenerator:
    """Get database session for routes"""
    driver = get_neo4j_driver()
    async with driver.session() as session:
        yield session


# Health check dependencies
async def check_database_health() -> Dict[str, Any]:
    """Check database health"""
    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run("RETURN 1 as health")
            record = await result.single()
            return {
                "status": "healthy",
                "details": {
                    "connected": True,
                    "uri": settings.neo4j_uri,
                    "database": settings.neo4j_database
                }
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "details": {
                "connected": False,
                "error": str(e)
            }
        }


async def check_ai_services_health() -> Dict[str, Any]:
    """Check AI services health"""
    services_status = {}
    
    # Check Gemini
    if settings.gemini_api_key:
        services_status["gemini"] = {
            "configured": True,
            "status": "ready"
        }
    else:
        services_status["gemini"] = {
            "configured": False,
            "status": "not_configured"
        }
    
    # Check Groq
    if settings.groq_api_key:
        services_status["groq"] = {
            "configured": True,
            "status": "ready"
        }
    else:
        services_status["groq"] = {
            "configured": False,
            "status": "not_configured"
        }
    
    # Check OpenAI
    if settings.openai_api_key:
        services_status["openai"] = {
            "configured": True,
            "status": "ready"
        }
    else:
        services_status["openai"] = {
            "configured": False,
            "status": "not_configured"
        }
    
    # Overall status
    configured_count = sum(1 for s in services_status.values() if s["configured"])
    
    return {
        "status": "healthy" if configured_count > 0 else "unhealthy",
        "configured_services": configured_count,
        "services": services_status
    }


async def check_mcp_health() -> Dict[str, Any]:
    """Check MCP server health"""
    if not settings.mcp_server_enabled:
        return {
            "status": "disabled",
            "details": {
                "enabled": False
            }
        }
    
    try:
        client = await get_mcp_client()
        if client:
            health = await client.health_check()
            return {
                "status": "healthy" if health else "unhealthy",
                "details": {
                    "enabled": True,
                    "host": settings.mcp_server_host,
                    "port": settings.mcp_server_port,
                    "connected": health
                }
            }
    except Exception as e:
        logger.error(f"MCP health check failed: {e}")
        return {
            "status": "unhealthy",
            "details": {
                "enabled": True,
                "error": str(e)
            }
        }


# Cleanup function for graceful shutdown
async def cleanup_services():
    """Clean up services during shutdown"""
    logger.info("Cleaning up services...")
    
    # Close Neo4j driver
    try:
        driver = get_neo4j_driver()
        await driver.close()
        logger.info("Closed Neo4j driver")
    except Exception as e:
        logger.error(f"Error closing Neo4j driver: {e}")
    
    # Shutdown WebSocket manager
    try:
        ws_manager = await get_websocket_manager()
        await ws_manager.shutdown()
        logger.info("Shutdown WebSocket manager")
    except Exception as e:
        logger.error(f"Error shutting down WebSocket manager: {e}")
    
    # Clear service container
    container.clear()
    logger.info("Cleared service container")
    
    logger.info("Service cleanup complete")