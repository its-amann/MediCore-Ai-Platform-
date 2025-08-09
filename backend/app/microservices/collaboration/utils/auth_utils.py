"""
Authentication utilities for the Collaboration microservice
Uses unified system's authentication configuration
"""

import os
from jose import jwt, JWTError
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from passlib.context import CryptContext

# Import settings for JWT configuration - same as unified system
from app.core.config import settings
from app.core.auth import token_validator

# JWT settings from unified configuration
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

security = HTTPBearer()


async def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT token using unified system's auth"""
    validation_result = token_validator.validate_token(
        token,
        verify_exp=True,
        allow_grace_period=False
    )
    
    if validation_result.is_valid:
        return validation_result.payload
    return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get current user from JWT token"""
    token = credentials.credentials
    
    user_info = await decode_jwt_token(token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract user information
    return {
        "user_id": user_info.get("user_id", user_info.get("sub")),
        "email": user_info.get("email"),
        "name": user_info.get("name", user_info.get("sub")),
        "role": user_info.get("role", "user")
    }


async def verify_ws_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify WebSocket authentication token"""
    user_info = await decode_jwt_token(token)
    if not user_info:
        return None
    
    return {
        "user_id": user_info.get("user_id", user_info.get("sub")),
        "email": user_info.get("email"),
        "name": user_info.get("name", user_info.get("sub")),
        "role": user_info.get("role", "user")
    }


async def create_access_token(
    user_id: str,
    email: Optional[str] = None,
    name: Optional[str] = None,
    role: str = "user",
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token using unified system's auth"""
    additional_claims = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "role": role
    }
    
    return token_validator.create_access_token(
        user_id=user_id,
        username=name,
        additional_claims=additional_claims,
        expires_delta=expires_delta
    )


# Create password context - same configuration as main app auth
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using unified system's auth"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password using unified system's auth"""
    return pwd_context.verify(plain_password, hashed_password)


def check_permissions(
    required_role: str,
    user_role: str
) -> bool:
    """Check if user has required role permissions"""
    role_hierarchy = {
        "admin": 4,
        "doctor": 3,
        "nurse": 2,
        "user": 1
    }
    
    required_level = role_hierarchy.get(required_role, 0)
    user_level = role_hierarchy.get(user_role, 0)
    
    return user_level >= required_level


class PermissionChecker:
    """Dependency for checking user permissions"""
    
    def __init__(self, required_role: str):
        self.required_role = required_role
    
    def __call__(
        self,
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        user_role = current_user.get("role", "user")
        
        if not check_permissions(self.required_role, user_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {self.required_role}"
            )
        
        return current_user


# Helper functions for room-specific permissions
async def check_room_access(
    room_id: str,
    user_id: str,
    required_role: Optional[str] = None
) -> bool:
    """Check if user has access to a specific room"""
    # This would typically check against a database
    # For now, we'll return True as a placeholder
    return True


async def is_room_host(room_id: str, user_id: str) -> bool:
    """Check if user is the host of a room"""
    # This would typically check against a database
    # For now, we'll return True as a placeholder
    return True