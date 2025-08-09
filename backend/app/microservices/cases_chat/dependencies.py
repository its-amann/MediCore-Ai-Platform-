"""
Dependency Injection Configuration
Provides dependency injection for the Cases Chat microservice
"""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header
import logging

from .config import settings
from .core import (
    get_service_container,
    get_storage_service as container_get_storage,
    get_doctor_service as container_get_doctor,
    get_case_number_generator as container_get_case_number,
    get_websocket_adapter as container_get_websocket
)
from .mcp_server.mcp_client import MCPClient
from .utils.error_handlers import ServiceUnavailableError

# Import shared authentication dependencies
from app.core.auth.shared_dependencies import (
    get_current_user_id,
    get_current_user,
    get_optional_user
)
from app.core.auth import token_validator

logger = logging.getLogger(__name__)

# MCP client instance (still managed separately as it's optional)
_mcp_client_instance: Optional[MCPClient] = None


async def verify_websocket_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Verify WebSocket authentication token using shared validator
    
    Args:
        token: JWT token
        
    Returns:
        User data if valid, None otherwise
    """
    if not token:
        logger.debug("No token provided for WebSocket authentication")
        return None
    
    try:
        # Use shared token validator
        validation_result = token_validator.validate_token(
            token,
            allow_grace_period=True
        )
        
        if not validation_result.is_valid:
            logger.warning(f"WebSocket token validation failed: {validation_result.error}")
            return None
        
        logger.debug(f"WebSocket token validated for user: {validation_result.username}")
        
        return {
            "user_id": validation_result.user_id,
            "username": validation_result.username,
            "roles": validation_result.payload.get("roles", []),
            "needs_refresh": validation_result.needs_refresh
        }
    except Exception as e:
        logger.error(f"WebSocket token validation error: {e}")
        return None


def get_storage_service():
    """
    Get storage service instance from service container
    
    Returns:
        Storage service instance
        
    Raises:
        ServiceUnavailableError: If storage is unavailable
    """
    try:
        return container_get_storage()
    except Exception as e:
        logger.error(f"Failed to get storage service: {e}")
        raise ServiceUnavailableError("Storage service is unavailable")


def get_doctor_service():
    """
    Get doctor service instance from service container
    
    Returns:
        Doctor service instance
        
    Raises:
        ServiceUnavailableError: If service is unavailable
    """
    try:
        return container_get_doctor()
    except Exception as e:
        logger.error(f"Failed to get doctor service: {e}")
        raise ServiceUnavailableError("Doctor service is unavailable")


def get_case_service():
    """
    Get case service instance from service container
    
    Returns:
        CaseService instance
        
    Raises:
        ServiceUnavailableError: If service is unavailable
    """
    try:
        container = get_service_container()
        return container.case_service
    except Exception as e:
        logger.error(f"Failed to get case service: {e}")
        raise ServiceUnavailableError("Case service is unavailable")


def get_case_number_generator():
    """
    Get case number generator instance from service container
    
    Returns:
        Case number generator instance
        
    Raises:
        ServiceUnavailableError: If service is unavailable
    """
    try:
        return container_get_case_number()
    except Exception as e:
        logger.error(f"Failed to get case number generator: {e}")
        raise ServiceUnavailableError("Case number generator is unavailable")


def get_websocket_adapter():
    """
    Get WebSocket adapter instance from service container
    
    Returns:
        WebSocket adapter instance
        
    Raises:
        ServiceUnavailableError: If adapter is unavailable
    """
    try:
        return container_get_websocket()
    except Exception as e:
        logger.error(f"Failed to get WebSocket adapter: {e}")
        raise ServiceUnavailableError("WebSocket adapter is unavailable")


def get_mcp_client() -> Optional[MCPClient]:
    """
    Get MCP client instance (singleton)
    
    Returns:
        MCP client instance or None if not initialized
    """
    global _mcp_client_instance
    
    if _mcp_client_instance is None and settings.MCP_ENABLED:
        try:
            _mcp_client_instance = MCPClient(
                host=settings.MCP_HOST,
                port=settings.MCP_PORT
            )
            logger.info(f"MCP client initialized at {settings.MCP_HOST}:{settings.MCP_PORT}")
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
    
    return _mcp_client_instance


async def optional_user_id(
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
) -> Optional[str]:
    """
    Get user ID from authentication or header (for testing)
    
    Args:
        user_id: User ID from header (testing)
        current_user: Authenticated user
        
    Returns:
        User ID or None
    """
    if current_user:
        return current_user["user_id"]
    return user_id


# Export all dependencies
__all__ = [
    "get_current_user_id",
    "get_current_user",
    "get_optional_user",
    "verify_websocket_token",
    "get_storage_service",
    "get_doctor_service",
    "get_case_service",
    "get_case_number_generator",
    "get_websocket_adapter",
    "get_mcp_client",
    "optional_user_id"
]