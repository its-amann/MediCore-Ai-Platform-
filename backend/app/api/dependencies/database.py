"""
Database dependency injection for unified database access
"""
from typing import Optional
from functools import lru_cache
from neo4j import Driver, AsyncDriver
from fastapi import HTTPException, status
import logging

from app.core.services.database_manager import unified_db_manager

logger = logging.getLogger(__name__)

@lru_cache()
def get_database_manager():
    """Get the unified database manager instance"""
    return unified_db_manager

def get_sync_driver() -> Driver:
    """Get synchronous Neo4j driver from unified database manager"""
    try:
        driver = unified_db_manager.get_sync_driver()
        if not driver:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection is not available"
            )
        return driver
    except Exception as e:
        logger.error(f"Failed to get sync driver: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is currently unavailable"
        )

async def get_async_driver() -> AsyncDriver:
    """Get asynchronous Neo4j driver from unified database manager"""
    try:
        driver = unified_db_manager.get_async_driver()
        if not driver:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection is not available"
            )
        return driver
    except Exception as e:
        logger.error(f"Failed to get async driver: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is currently unavailable"
        )

def get_db_session():
    """Get a database session for sync operations"""
    driver = get_sync_driver()
    session = driver.session()
    try:
        yield session
    finally:
        session.close()

async def get_async_db_session():
    """Get a database session for async operations"""
    driver = await get_async_driver()
    session = driver.async_session()
    try:
        yield session
    finally:
        await session.close()