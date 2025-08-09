"""
Shared authentication dependencies for all microservices

This module provides unified authentication dependencies that can be used
across all microservices to ensure consistent authentication handling.
"""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.auth import token_validator
from app.core.unified_logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.
    
    This is the main authentication dependency that should be used
    across all microservices for consistent authentication.
    
    Returns:
        Dict containing user information:
        - user_id: User ID
        - username: Username
        - email: User email (if available)
        - role: User role (if available)
        - token_type: Type of token (access/refresh)
        
    Raises:
        HTTPException: 401 if authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate token using unified validator
    validation_result = token_validator.validate_token(
        credentials.credentials,
        allow_grace_period=True
    )
    
    if not validation_result.is_valid:
        logger.warning(f"Authentication failed: {validation_result.error}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=validation_result.error or "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Log if token needs refresh
    if validation_result.needs_refresh:
        logger.info(f"Token for user {validation_result.username} needs refresh")
    
    # Return user information
    return {
        "user_id": validation_result.user_id,
        "username": validation_result.username,
        "email": validation_result.payload.get("email"),
        "role": validation_result.payload.get("role", "user"),
        "token_type": validation_result.token_type,
        "needs_refresh": validation_result.needs_refresh,
        "payload": validation_result.payload
    }


async def get_current_user_id(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> str:
    """
    Get current user ID.
    
    Simple dependency that returns just the user ID.
    """
    return current_user["user_id"]


async def get_current_username(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> str:
    """
    Get current username.
    
    Simple dependency that returns just the username.
    """
    return current_user["username"]


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Get current user if authenticated, otherwise return None.
    
    Use this for endpoints that support both authenticated and
    anonymous access.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_role(required_role: str):
    """
    Dependency factory to require a specific role.
    
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            current_user: Dict = Depends(require_role("admin"))
        ):
            ...
    """
    async def role_checker(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        user_role = current_user.get("role", "user")
        
        # Check if user has required role
        if user_role != required_role and user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        
        return current_user
    
    return role_checker


# Convenience dependencies for specific roles
get_admin_user = require_role("admin")
get_doctor_user = require_role("doctor")
get_patient_user = require_role("patient")


# Export all dependencies
__all__ = [
    "get_current_user",
    "get_current_user_id", 
    "get_current_username",
    "get_optional_user",
    "require_role",
    "get_admin_user",
    "get_doctor_user",
    "get_patient_user",
    "security"
]