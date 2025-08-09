"""
Neo4j Connection Pool Manager - Centralized database connection management
"""

import logging
from typing import Optional, Dict, Any
from neo4j import GraphDatabase, Driver
import asyncio
from threading import Lock
from contextlib import contextmanager, asynccontextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jConnectionPool:
    """
    Singleton connection pool manager for Neo4j database.
    Provides both sync and async drivers with proper lifecycle management.
    """
    
    _instance: Optional['Neo4jConnectionPool'] = None
    _lock = Lock()
    
    def __new__(cls) -> 'Neo4jConnectionPool':
        """Thread-safe singleton implementation"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the connection pool"""
        if not hasattr(self, '_initialized'):
            self._sync_driver: Optional[Driver] = None
            self._async_driver: Optional[Driver] = None
            self._config = self._get_connection_config()
            self._initialized = True
            logger.info("Neo4j Connection Pool initialized")
    
    def _get_connection_config(self) -> Dict[str, Any]:
        """Get Neo4j connection configuration"""
        return {
            'uri': settings.neo4j_uri,
            'auth': (settings.neo4j_user, settings.neo4j_password),
            'max_connection_lifetime': 3600,  # 1 hour
            'max_connection_pool_size': 100,
            'connection_acquisition_timeout': 60,
            'connection_timeout': 30,
            'keep_alive': True,
            'encrypted': False,  # Set to True in production with SSL
            'trust': 'TRUST_ALL_CERTIFICATES'  # Change in production
        }
    
    @property
    def sync_driver(self) -> Driver:
        """Get or create sync driver with lazy initialization"""
        if self._sync_driver is None:
            self._sync_driver = GraphDatabase.driver(**self._config)
            logger.info("Created new sync Neo4j driver")
        return self._sync_driver
    
    @property
    async def async_driver(self) -> Driver:
        """Get or create async driver with lazy initialization"""
        if self._async_driver is None:
            self._async_driver = GraphDatabase.driver(**self._config)
            logger.info("Created new async Neo4j driver")
        return self._async_driver
    
    @contextmanager
    def get_sync_session(self, database: str = "neo4j"):
        """Get a sync session from the pool"""
        session = None
        try:
            session = self.sync_driver.session(database=database)
            yield session
        finally:
            if session:
                session.close()
    
    @asynccontextmanager
    async def get_async_session(self, database: str = "neo4j"):
        """Get an async session from the pool"""
        session = None
        try:
            driver = await self.async_driver
            session = driver.session(database=database)
            yield session
        finally:
            if session:
                await session.close()
    
    def verify_connectivity(self) -> bool:
        """Verify database connectivity synchronously"""
        try:
            self.sync_driver.verify_connectivity()
            logger.info("Neo4j sync connectivity verified")
            return True
        except Exception as e:
            logger.error(f"Neo4j sync connectivity check failed: {e}")
            return False
    
    async def verify_connectivity_async(self) -> bool:
        """Verify database connectivity asynchronously"""
        try:
            driver = await self.async_driver
            await driver.verify_connectivity()
            logger.info("Neo4j async connectivity verified")
            return True
        except Exception as e:
            logger.error(f"Neo4j async connectivity check failed: {e}")
            return False
    
    def close(self):
        """Close all connections and cleanup resources"""
        if self._sync_driver:
            self._sync_driver.close()
            self._sync_driver = None
            logger.info("Closed sync Neo4j driver")
        
        if self._async_driver:
            # Async driver close needs to be handled in async context
            logger.warning("Async driver close should be called from async context")
    
    async def close_async(self):
        """Close all connections asynchronously"""
        if self._async_driver:
            await self._async_driver.close()
            self._async_driver = None
            logger.info("Closed async Neo4j driver")
        
        if self._sync_driver:
            self._sync_driver.close()
            self._sync_driver = None
            logger.info("Closed sync Neo4j driver")
    
    def get_pool_metrics(self) -> Dict[str, Any]:
        """Get connection pool metrics"""
        metrics = {
            'sync_driver_active': self._sync_driver is not None,
            'async_driver_active': self._async_driver is not None,
        }
        
        # Add detailed metrics if drivers are active
        if self._sync_driver:
            try:
                # Note: Neo4j Python driver doesn't expose detailed pool metrics
                # This is a placeholder for future enhancement
                metrics['sync_pool_status'] = 'active'
            except Exception as e:
                logger.error(f"Failed to get sync pool metrics: {e}")
        
        if self._async_driver:
            try:
                metrics['async_pool_status'] = 'active'
            except Exception as e:
                logger.error(f"Failed to get async pool metrics: {e}")
        
        return metrics
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (useful for testing)"""
        with cls._lock:
            if cls._instance:
                cls._instance.close()
            cls._instance = None


# Global instance getter
def get_neo4j_pool() -> Neo4jConnectionPool:
    """Get the global Neo4j connection pool instance"""
    return Neo4jConnectionPool()


# Convenience functions for direct driver access
def get_sync_driver() -> Driver:
    """Get the sync Neo4j driver from the global pool"""
    return get_neo4j_pool().sync_driver


async def get_async_driver() -> Driver:
    """Get the async Neo4j driver from the global pool"""
    return await get_neo4j_pool().async_driver