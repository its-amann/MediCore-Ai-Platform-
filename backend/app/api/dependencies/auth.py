"""
Authentication dependencies for the Unified Medical AI Platform
Properly implemented to avoid FastAPI parameter injection issues
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

# Create the HTTPBearer instance that will handle authentication
# We use auto_error=True to let FastAPI handle missing credentials automatically
http_bearer = HTTPBearer()

def get_auth_credentials(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer)
) -> HTTPAuthorizationCredentials:
    """
    Get authentication credentials from the request.
    This is a dependency function that wraps HTTPBearer to avoid
    the 'request' parameter issue in FastAPI's OpenAPI generation.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return credentials