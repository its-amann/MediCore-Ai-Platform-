"""
Unified Database Manager for sharing connections across microservices
Manages a single connection pool for all services to reduce total connections
"""
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from neo4j import GraphDatabase, Driver
from neo4j.exceptions import Neo4jError
import asyncio
from datetime import datetime
import concurrent.futures
from functools import wraps

# Check if async Neo4j is available (Neo4j 5.x)
try:
    from neo4j import AsyncGraphDatabase, AsyncDriver
    ASYNC_NEO4J_AVAILABLE = True
except ImportError:
    AsyncGraphDatabase = None
    AsyncDriver = None
    ASYNC_NEO4J_AVAILABLE = False

from app.core.config import settings
from app.core.unified_logging import get_logger
from .suppress_neo4j_warnings import configure_neo4j_logging

logger = get_logger(__name__)

# Configure Neo4j logging to suppress index warnings
configure_neo4j_logging()


class UnifiedDatabaseManager:
    """
    Centralized database manager that maintains single connection pools
    for both sync and async Neo4j drivers, shared across all microservices.
    """
    
    def __init__(self):
        """Initialize the unified database manager"""
        self.uri = settings.neo4j_uri
        self.user = settings.neo4j_user
        self.password = settings.neo4j_password
        
        # Single sync driver for all sync operations
        self._sync_driver: Optional[Driver] = None
        
        # Single async driver for all async operations (if available)
        self._async_driver: Optional[AsyncDriver] = None if ASYNC_NEO4J_AVAILABLE else None
        
        # Thread pool for async emulation when AsyncGraphDatabase is not available
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=10) if not ASYNC_NEO4J_AVAILABLE else None
        
        # Track which services are using the drivers
        self._service_registry: Dict[str, Dict[str, Any]] = {}
        
        # Migration tracking
        self._migrations_completed = False
        self._migration_lock = asyncio.Lock()
        
        logger.info("UnifiedDatabaseManager initialized")
    
    def connect_sync(self) -> Driver:
        """
        Get or create the sync driver connection.
        This returns the same driver instance for all callers.
        """
        if not self._sync_driver:
            try:
                # Create sync driver with optimized pool settings
                self._sync_driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    max_connection_pool_size=50,  # Reduced from default
                    connection_timeout=30,
                    keep_alive=True
                )
                
                # Test the connection
                with self._sync_driver.session() as session:
                    session.run("RETURN 1")
                
                logger.info("Sync Neo4j driver created and connected")
                
            except Exception as e:
                logger.error(f"Failed to create sync Neo4j driver: {str(e)}")
                raise
        
        return self._sync_driver
    
    def get_sync_driver(self) -> Optional[Driver]:
        """
        Get the sync driver if it's connected.
        Returns None if not connected.
        """
        if self._sync_driver and self.is_connected_sync():
            return self._sync_driver
        return None
    
    def get_async_driver(self) -> Optional[AsyncDriver]:
        """
        Get the async driver if it's connected.
        Returns None if not connected or if async Neo4j is not available.
        """
        if not ASYNC_NEO4J_AVAILABLE:
            return None
        if self._async_driver:
            return self._async_driver
        return None
    
    async def connect_async(self) -> Optional[AsyncDriver]:
        """
        Get or create the async driver connection.
        This returns the same driver instance for all callers.
        If AsyncGraphDatabase is not available, returns None.
        """
        if not ASYNC_NEO4J_AVAILABLE:
            logger.warning("AsyncGraphDatabase not available in Neo4j 4.x. Use sync driver with executor for async operations.")
            return None
            
        if not self._async_driver:
            try:
                # Create async driver with optimized pool settings
                self._async_driver = AsyncGraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    max_connection_pool_size=50,  # Reduced from default
                    connection_timeout=30,
                    keep_alive=True
                )
                
                # Test the connection
                async with self._async_driver.session() as session:
                    await session.run("RETURN 1")
                
                logger.info("Async Neo4j driver created and connected")
                
            except Exception as e:
                logger.error(f"Failed to create async Neo4j driver: {str(e)}")
                raise
        
        return self._async_driver
    
    def register_service(self, service_name: str, service_info: Dict[str, Any] = None):
        """
        Register a service that's using the database manager.
        This helps track which services are active.
        """
        self._service_registry[service_name] = {
            "registered_at": datetime.utcnow().isoformat(),
            "info": service_info or {},
            "active": True
        }
        logger.info(f"Service '{service_name}' registered with database manager")
    
    def unregister_service(self, service_name: str):
        """Unregister a service"""
        if service_name in self._service_registry:
            self._service_registry[service_name]["active"] = False
            logger.info(f"Service '{service_name}' unregistered from database manager")
    
    async def initialize_constraints(self):
        """
        Initialize database constraints and indexes.
        This is run once for the entire application.
        """
        async with self._migration_lock:
            if self._migrations_completed:
                logger.info("Database constraints already initialized")
                return
            
            try:
                # Core user and authentication constraints
                constraints = [
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.username IS UNIQUE",
                    
                    # Medical case constraints
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Case) REQUIRE c.case_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (s:ChatSession) REQUIRE s.session_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (m:ChatMessage) REQUIRE m.message_id IS UNIQUE",
                    
                    # Medical imaging constraints
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Report) REQUIRE r.report_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (w:Workflow) REQUIRE w.workflow_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Image) REQUIRE i.image_id IS UNIQUE",
                    
                    # Collaboration constraints
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (room:CollaborationRoom) REQUIRE room.room_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (msg:CollaborationMessage) REQUIRE msg.message_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (jr:JoinRequest) REQUIRE jr.request_id IS UNIQUE",
                    
                    # Voice consultation constraints
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (vc:VoiceConsultation) REQUIRE vc.consultation_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (vs:VoiceSession) REQUIRE vs.session_id IS UNIQUE",
                    
                    # Notification constraints
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Notification) REQUIRE n.notification_id IS UNIQUE"
                ]
                
                # Create indexes for performance
                indexes = [
                    # User indexes
                    "CREATE INDEX IF NOT EXISTS FOR (u:User) ON (u.created_at)",
                    "CREATE INDEX IF NOT EXISTS FOR (u:User) ON (u.role)",
                    
                    # Case indexes
                    "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.user_id)",
                    "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.status)",
                    "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.created_at)",
                    
                    # Message indexes
                    "CREATE INDEX IF NOT EXISTS FOR (m:ChatMessage) ON (m.session_id)",
                    "CREATE INDEX IF NOT EXISTS FOR (m:ChatMessage) ON (m.created_at)",
                    "CREATE INDEX IF NOT EXISTS FOR (m:CollaborationMessage) ON (m.room_id)",
                    "CREATE INDEX IF NOT EXISTS FOR (m:CollaborationMessage) ON (m.created_at)",
                    
                    # Medical imaging indexes
                    "CREATE INDEX IF NOT EXISTS FOR (r:Report) ON (r.case_id)",
                    "CREATE INDEX IF NOT EXISTS FOR (r:Report) ON (r.created_at)",
                    "CREATE INDEX IF NOT EXISTS FOR (w:Workflow) ON (w.status)",
                    
                    # Collaboration indexes
                    "CREATE INDEX IF NOT EXISTS FOR (room:CollaborationRoom) ON (room.created_at)",
                    "CREATE INDEX IF NOT EXISTS FOR (room:CollaborationRoom) ON (room.status)",
                    
                    # Notification indexes
                    "CREATE INDEX IF NOT EXISTS FOR (n:Notification) ON (n.user_id)",
                    "CREATE INDEX IF NOT EXISTS FOR (n:Notification) ON (n.read)",
                    "CREATE INDEX IF NOT EXISTS FOR (n:Notification) ON (n.created_at)"
                ]
                
                if ASYNC_NEO4J_AVAILABLE:
                    driver = await self.connect_async()
                    async with driver.session() as session:
                        for constraint in constraints:
                            try:
                                await session.run(constraint)
                                logger.debug(f"Constraint created: {constraint}")
                            except Neo4jError as e:
                                if "already exists" not in str(e):
                                    logger.error(f"Error creating constraint: {str(e)}")
                        
                        for index in indexes:
                            try:
                                await session.run(index)
                                logger.debug(f"Index created: {index}")
                            except Neo4jError as e:
                                if "already exists" not in str(e):
                                    logger.error(f"Error creating index: {str(e)}")
                else:
                    # Use sync driver with executor
                    driver = self.connect_sync()
                    
                    def run_constraints_and_indexes():
                        with driver.session() as session:
                            for constraint in constraints:
                                try:
                                    session.run(constraint)
                                    logger.debug(f"Constraint created: {constraint}")
                                except Neo4jError as e:
                                    if "already exists" not in str(e):
                                        logger.error(f"Error creating constraint: {str(e)}")
                            
                            for index in indexes:
                                try:
                                    session.run(index)
                                    logger.debug(f"Index created: {index}")
                                except Neo4jError as e:
                                    if "already exists" not in str(e):
                                        logger.error(f"Error creating index: {str(e)}")
                    
                    await self._run_sync_in_executor(run_constraints_and_indexes)
                
                self._migrations_completed = True
                logger.info("Database constraints and indexes initialized successfully")
                    
            except Exception as e:
                logger.error(f"Failed to initialize database: {str(e)}")
                raise
    
    async def run_migrations(self, migration_modules: List[Any] = None):
        """
        Run database migrations from all microservices.
        Each service can provide its migration module.
        """
        async with self._migration_lock:
            logger.info("Starting unified database migrations")
            
            if migration_modules:
                for module in migration_modules:
                    try:
                        logger.info(f"Running migrations from {module.__name__}")
                        # Assuming each module has a run_migrations function
                        if hasattr(module, 'run_migrations'):
                            if ASYNC_NEO4J_AVAILABLE:
                                driver = await self.connect_async()
                                await module.run_migrations(driver)
                            else:
                                # Use sync driver for migrations
                                driver = self.connect_sync()
                                await self._run_sync_in_executor(module.run_migrations, driver)
                    except Exception as e:
                        logger.error(f"Migration failed for {module.__name__}: {str(e)}")
                        # Continue with other migrations
            
            logger.info("Unified database migrations completed")
    
    def get_sync_session(self):
        """Get a sync session from the shared driver"""
        driver = self.connect_sync()
        return driver.session()
    
    async def _run_sync_in_executor(self, func, *args, **kwargs):
        """Run a sync function in the executor for async contexts"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func, *args, **kwargs)
    
    @asynccontextmanager
    async def get_async_session(self):
        """Get an async session from the shared driver or sync fallback"""
        if ASYNC_NEO4J_AVAILABLE:
            driver = await self.connect_async()
            async with driver.session() as session:
                yield session
        else:
            # Fallback to sync driver with executor
            driver = self.connect_sync()
            session = driver.session()
            try:
                yield session
            finally:
                session.close()
    
    def is_connected_sync(self) -> bool:
        """Check if sync driver is connected"""
        try:
            if not self._sync_driver:
                return False
            with self._sync_driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False
    
    async def is_connected_async(self) -> bool:
        """Check if async driver is connected"""
        try:
            if not self._async_driver:
                return False
            async with self._async_driver.session() as session:
                await session.run("RETURN 1")
            return True
        except Exception:
            return False
    
    async def verify_connectivity(self) -> Dict[str, Any]:
        """Verify both sync and async connectivity"""
        sync_connected = self.is_connected_sync()
        async_connected = await self.is_connected_async()
        
        return {
            "sync_driver": {
                "connected": sync_connected,
                "pool_size": 50 if sync_connected else 0
            },
            "async_driver": {
                "connected": async_connected,
                "pool_size": 50 if async_connected else 0
            },
            "total_connections": 100 if (sync_connected and async_connected) else 50 if (sync_connected or async_connected) else 0,
            "registered_services": len([s for s in self._service_registry.values() if s["active"]]),
            "services": list(self._service_registry.keys())
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        connectivity = await self.verify_connectivity()
        
        return {
            "status": "healthy" if (connectivity["sync_driver"]["connected"] or connectivity["async_driver"]["connected"]) else "unhealthy",
            "connectivity": connectivity,
            "migrations_completed": self._migrations_completed,
            "uri": self.uri
        }
    
    def disconnect_sync(self):
        """Disconnect sync driver"""
        if self._sync_driver:
            try:
                self._sync_driver.close()
                logger.info("Sync Neo4j driver disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting sync driver: {str(e)}")
            finally:
                self._sync_driver = None
    
    async def disconnect_async(self):
        """Disconnect async driver"""
        if self._async_driver:
            try:
                await self._async_driver.close()
                logger.info("Async Neo4j driver disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting async driver: {str(e)}")
            finally:
                self._async_driver = None
    
    async def shutdown(self):
        """Shutdown all connections"""
        logger.info("Shutting down UnifiedDatabaseManager")
        
        # Disconnect both drivers
        self.disconnect_sync()
        await self.disconnect_async()
        
        # Shutdown executor if using sync fallback
        if self._executor:
            self._executor.shutdown(wait=True)
        
        # Clear service registry
        self._service_registry.clear()
        self._migrations_completed = False
        
        logger.info("UnifiedDatabaseManager shutdown complete")


# Create global instance
unified_db_manager = UnifiedDatabaseManager()

# Helper function for backward compatibility
def get_database_manager() -> UnifiedDatabaseManager:
    """Get the global database manager instance"""
    return unified_db_manager