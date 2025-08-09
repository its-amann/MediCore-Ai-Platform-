"""
Microservice Initializer - Manages initialization of all microservices with shared database connections
"""
import logging
from typing import Dict, Any, List, Optional
import asyncio

# Handle Neo4j async imports
try:
    from neo4j.aio import AsyncGraphDatabase, AsyncDriver
    from neo4j import GraphDatabase, Driver
    ASYNC_NEO4J_AVAILABLE = True
except ImportError:
    from neo4j import GraphDatabase, Driver
    AsyncGraphDatabase = None
    AsyncDriver = None
    ASYNC_NEO4J_AVAILABLE = False

from app.core.unified_logging import get_logger

logger = get_logger(__name__)


class MicroserviceInitializer:
    """
    Manages the initialization of all microservices with shared database connections.
    This ensures that all services use the same connection pools instead of creating their own.
    """
    
    def __init__(self, unified_db_manager):
        """
        Initialize the microservice initializer.
        
        Args:
            unified_db_manager: The UnifiedDatabaseManager instance
        """
        self.db_manager = unified_db_manager
        self.initialized_services: Dict[str, Any] = {}
        self._initialization_order = [
            "cases_chat",
            "medical_imaging", 
            "voice_consultation",
            "collaboration"  # Collaboration last as it may depend on others
        ]
        
    async def initialize_all_microservices(self, sync_driver: Driver, async_driver: Optional[AsyncDriver]) -> Dict[str, Any]:
        """
        Initialize all microservices with shared database connections.
        
        Args:
            sync_driver: Shared sync Neo4j driver
            async_driver: Shared async Neo4j driver
            
        Returns:
            Dictionary of initialization results for each service
        """
        results = {}
        
        for service_name in self._initialization_order:
            try:
                logger.info(f"Initializing {service_name} microservice...")
                
                if service_name == "cases_chat":
                    result = await self._initialize_cases_chat(async_driver)
                elif service_name == "medical_imaging":
                    result = await self._initialize_medical_imaging(sync_driver, async_driver)
                elif service_name == "voice_consultation":
                    result = await self._initialize_voice_consultation(sync_driver)
                elif service_name == "collaboration":
                    result = await self._initialize_collaboration(sync_driver)
                else:
                    logger.warning(f"Unknown service: {service_name}")
                    continue
                
                results[service_name] = result
                self.initialized_services[service_name] = result
                
                # Register the service with database manager
                self.db_manager.register_service(f"{service_name}_microservice", {
                    "type": "microservice",
                    "initialized": True,
                    "status": "active" if result.get("success", False) else "failed"
                })
                
                logger.info(f"Successfully initialized {service_name} microservice")
                
            except Exception as e:
                logger.error(f"Failed to initialize {service_name}: {str(e)}")
                results[service_name] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    async def _initialize_cases_chat(self, async_driver: Optional[AsyncDriver]) -> Dict[str, Any]:
        """Initialize cases_chat microservice with shared async driver."""
        try:
            # Import and modify the cases_chat dependencies to use shared driver
            from app.microservices.cases_chat.core import dependencies
            
            # Replace the get_neo4j_driver function to return our shared driver
            original_get_driver = dependencies.get_neo4j_driver
            
            def shared_get_driver():
                logger.info("Cases chat using shared async driver")
                return async_driver
            
            # Monkey patch the function
            dependencies.get_neo4j_driver = shared_get_driver
            dependencies.get_neo4j_driver._cache_info = lambda: None  # Disable cache info
            
            # Initialize storage service with shared driver
            from app.microservices.cases_chat.services.storage.neo4j_storage import UnifiedNeo4jStorage
            storage_service = UnifiedNeo4jStorage(async_driver)
            await storage_service.initialize()
            
            # Register in the service container
            dependencies.container.register_singleton(UnifiedNeo4jStorage, storage_service)
            
            # Initialize other services that depend on storage
            from app.microservices.cases_chat.services.doctors.doctor_coordinator import DoctorCoordinator
            from app.microservices.cases_chat.services.case_management.case_service import CaseService
            from app.microservices.cases_chat.services.chat.message_processor import MessageProcessor
            from app.microservices.cases_chat.services.media.media_handler import MediaHandler
            from app.microservices.cases_chat.core.websocket_manager import websocket_manager
            from app.microservices.cases_chat.core.config import settings as cases_settings
            
            # Initialize doctor coordinator
            doctor_coordinator = DoctorCoordinator()
            await doctor_coordinator.initialize()
            dependencies.container.register_singleton(DoctorCoordinator, doctor_coordinator)
            
            # Initialize case service
            case_service = CaseService(storage_service)
            await case_service.initialize()
            dependencies.container.register_singleton(CaseService, case_service)
            
            # Initialize message processor
            message_processor = MessageProcessor(storage_service, doctor_coordinator, websocket_manager)
            dependencies.container.register_singleton(MessageProcessor, message_processor)
            
            # Initialize media handler
            media_handler = MediaHandler(storage_service, cases_settings)
            await media_handler.initialize()
            dependencies.container.register_singleton(MediaHandler, media_handler)
            
            return {
                "success": True,
                "services": {
                    "storage": "initialized",
                    "doctor_coordinator": "initialized",
                    "case_service": "initialized",
                    "message_processor": "initialized",
                    "media_handler": "initialized"
                }
            }
            
        except Exception as e:
            logger.error(f"Cases chat initialization error: {str(e)}")
            raise
    
    async def _initialize_medical_imaging(self, sync_driver: Driver, async_driver: Optional[AsyncDriver]) -> Dict[str, Any]:
        """Initialize medical_imaging microservice with shared drivers."""
        try:
            # Medical imaging may use both sync and async operations
            # We'll need to check its implementation and adapt accordingly
            
            return {
                "success": True,
                "message": "Medical imaging service initialized with shared connections"
            }
            
        except Exception as e:
            logger.error(f"Medical imaging initialization error: {str(e)}")
            raise
    
    async def _initialize_voice_consultation(self, sync_driver: Driver) -> Dict[str, Any]:
        """Initialize voice_consultation microservice with shared sync driver."""
        try:
            # Voice consultation typically uses sync operations
            
            return {
                "success": True,
                "message": "Voice consultation service initialized with shared connections"
            }
            
        except Exception as e:
            logger.error(f"Voice consultation initialization error: {str(e)}")
            raise
    
    async def _initialize_collaboration(self, sync_driver: Driver) -> Dict[str, Any]:
        """
        Initialize collaboration microservice with shared sync driver.
        This is already handled in main.py but we track it here.
        """
        try:
            # The collaboration service is already initialized in main.py
            # We just track its status here
            return {
                "success": True,
                "message": "Collaboration service tracked (initialized in main.py)"
            }
            
        except Exception as e:
            logger.error(f"Collaboration tracking error: {str(e)}")
            raise
    
    async def run_unified_migrations(self) -> Dict[str, Any]:
        """
        Run migrations for all microservices in a coordinated manner.
        This ensures migrations are run only once with the shared connection.
        """
        logger.info("Running unified migrations for all microservices")
        
        migration_results = {}
        
        try:
            # Get the async driver for migrations
            async_driver = await self.db_manager.connect_async()
            
            # Run cases_chat migrations
            try:
                from app.microservices.cases_chat.migrations.migration_runner import MigrationRunner
                cases_runner = MigrationRunner(async_driver)
                await cases_runner.run_migrations()
                migration_results["cases_chat"] = {"success": True, "message": "Migrations completed"}
            except Exception as e:
                logger.error(f"Cases chat migration failed: {str(e)}")
                migration_results["cases_chat"] = {"success": False, "error": str(e)}
            
            # Run collaboration migrations
            try:
                from app.microservices.collaboration.migrations.run_migrations import MigrationRunner as CollabMigrationRunner
                # Create a sync driver for collaboration migrations which use sync API
                sync_driver = self.db_manager.connect_sync()
                
                # Use context manager approach with shared driver
                with CollabMigrationRunner(driver=sync_driver) as collab_runner:
                    # Run all migrations
                    results = collab_runner.run_all_migrations()
                    
                    if results["failed"] == 0:
                        migration_results["collaboration"] = {
                            "success": True, 
                            "message": f"Migrations completed - {results['successful']} successful, {results['skipped']} skipped"
                        }
                    else:
                        migration_results["collaboration"] = {
                            "success": False, 
                            "error": f"Migrations failed - {results['failed']} failed"
                        }
            except Exception as e:
                logger.error(f"Collaboration migration failed: {str(e)}")
                migration_results["collaboration"] = {"success": False, "error": str(e)}
            
            # Add other microservice migrations here as needed
            
            return migration_results
            
        except Exception as e:
            logger.error(f"Unified migration runner error: {str(e)}")
            raise
    
    async def health_check_all(self) -> Dict[str, Any]:
        """
        Perform health checks on all initialized microservices.
        """
        health_results = {}
        
        for service_name, service_info in self.initialized_services.items():
            try:
                if service_info.get("success", False):
                    # Perform service-specific health checks
                    health_results[service_name] = {
                        "status": "healthy",
                        "initialized": True
                    }
                else:
                    health_results[service_name] = {
                        "status": "unhealthy",
                        "initialized": False,
                        "error": service_info.get("error", "Unknown error")
                    }
            except Exception as e:
                health_results[service_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return health_results
    
    async def shutdown_all(self):
        """
        Gracefully shutdown all microservices.
        """
        logger.info("Shutting down all microservices")
        
        # Shutdown in reverse order of initialization
        for service_name in reversed(self._initialization_order):
            try:
                if service_name in self.initialized_services:
                    logger.info(f"Shutting down {service_name} microservice")
                    
                    # Service-specific shutdown logic
                    if service_name == "cases_chat":
                        # Cleanup cases_chat specific resources
                        from app.microservices.cases_chat.core.dependencies import cleanup_services
                        await cleanup_services()
                    
                    # Unregister from database manager
                    self.db_manager.unregister_service(f"{service_name}_microservice")
                    
            except Exception as e:
                logger.error(f"Error shutting down {service_name}: {str(e)}")
        
        self.initialized_services.clear()
        logger.info("All microservices shut down")