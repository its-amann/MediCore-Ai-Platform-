"""
WebSocket Authentication Dependencies

Provides authentication dependencies for WebSocket endpoints that validate
authentication BEFORE the WebSocket connection is upgraded.
"""

from fastapi import WebSocket, Query, HTTPException, status
from typing import Optional, Dict, Any
import jwt
from datetime import datetime
from app.core.config import settings
from app.core.unified_logging import get_logger
from app.core.auth import token_validator

logger = get_logger(__name__)


async def get_websocket_user(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    username: Optional[str] = Query(None)
) -> Optional[Dict[str, Any]]:
    """
    Validate WebSocket authentication before accepting connection.
    This runs BEFORE the WebSocket is accepted by FastAPI.
    
    Returns user info dict or None if authentication fails.
    """
    # Check if authentication is required
    auth_required = settings.ws_auth_required
    auth_bypass = settings.ws_auth_bypass
    
    logger.info(f"WebSocket auth check - auth_required: {auth_required}, auth_bypass: {auth_bypass}")
    
    # If auth is not required or bypass is enabled, allow connection
    if not auth_required or auth_bypass:
        # Testing mode - use provided user info or defaults
        if user_id and username:
            logger.info(f"WebSocket testing mode - user: {username} ({user_id})")
            return {
                "user_id": user_id,
                "username": username,
                "testing_mode": True,
                "authenticated": True
            }
        else:
            logger.warning("WebSocket testing mode but no user info provided")
            return {
                "user_id": "anonymous",
                "username": "Anonymous",
                "testing_mode": True,
                "authenticated": False
            }
    
    # Production mode - require valid token
    if not token:
        # Check if token is passed via Sec-WebSocket-Protocol header
        # This is more secure than URL parameters as it prevents token logging
        protocols_header = websocket.headers.get("sec-websocket-protocol", "")
        bearer_token = None
        
        if protocols_header:
            # The header contains comma-separated protocols: "bearer, <token>"
            protocols = [p.strip() for p in protocols_header.split(",")]
            
            # Look for bearer protocol followed by token
            if len(protocols) >= 2 and protocols[0] == "bearer":
                bearer_token = protocols[1]
                logger.info(f"Token found in Sec-WebSocket-Protocol header (length: {len(bearer_token)})")
        
        if bearer_token:
            token = bearer_token
        else:
            logger.warning("No authentication token provided for WebSocket connection")
            await websocket.close(code=4001, reason="Authentication required")
            return None
    
    try:
        # Use unified token validator for consistent validation
        validation_result = token_validator.validate_token(
            token,
            verify_exp=True,
            allow_grace_period=True,  # Allow grace period for WebSocket
            expected_type="access"
        )
        
        if not validation_result.is_valid:
            logger.warning(f"WebSocket token validation failed: {validation_result.error}")
            if validation_result.is_expired:
                await websocket.close(code=4001, reason="Token expired")
            else:
                await websocket.close(code=4003, reason="Invalid token")
            return None
        
        # Log if token needs refresh
        if validation_result.needs_refresh:
            logger.info(f"WebSocket token for user {validation_result.user_id} needs refresh soon")
        
        # Extract user information
        user_info = {
            "user_id": validation_result.user_id,
            "username": validation_result.username,
            "email": validation_result.payload.get("email"),
            "roles": validation_result.payload.get("roles", []),
            "token_exp": validation_result.payload.get("exp"),
            "authenticated": True,
            "needs_refresh": validation_result.needs_refresh,
            "in_grace_period": validation_result.in_grace_period
        }
        
        # Validate required fields
        if not user_info["user_id"]:
            logger.error("Token missing user ID")
            await websocket.close(code=4001, reason="Invalid token")
            return None
        
        logger.info(f"WebSocket authenticated: {user_info['username']} ({user_info['user_id']})")
        return user_info
        
    except Exception as e:
        logger.error(f"WebSocket auth error: {e}", exc_info=True)
        await websocket.close(code=4003, reason="Authentication failed")
        return None


async def require_websocket_auth(
    user_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Require authenticated WebSocket connection.
    Use this as a dependency when authentication is mandatory.
    
    Raises HTTPException if not authenticated.
    """
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="WebSocket authentication required"
        )
    
    if not user_info.get("authenticated"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="WebSocket authentication failed"
        )
    
    return user_info


async def get_optional_websocket_user(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
) -> Optional[Dict[str, Any]]:
    """
    Optional WebSocket authentication.
    Returns user info if authenticated, None otherwise.
    Does not close the connection on failure.
    """
    if not token:
        return None
    
    try:
        # Use unified token validator
        validation_result = token_validator.validate_token(
            token,
            verify_exp=True,
            allow_grace_period=True,
            expected_type="access"
        )
        
        if validation_result.is_valid:
            user_info = {
                "user_id": validation_result.user_id,
                "username": validation_result.username,
                "email": validation_result.payload.get("email"),
                "roles": validation_result.payload.get("roles", []),
                "token_exp": validation_result.payload.get("exp"),
                "authenticated": True,
                "needs_refresh": validation_result.needs_refresh,
                "in_grace_period": validation_result.in_grace_period
            }
            
            if user_info["user_id"]:
                return user_info
        
    except Exception as e:
        logger.debug(f"Optional WebSocket auth failed: {e}")
    
    return None


def check_token_expiry_soon(user_info: Dict[str, Any], threshold_seconds: int = 300) -> bool:
    """
    Check if token is expiring soon (within threshold).
    
    Args:
        user_info: User info dict with token_exp field
        threshold_seconds: Seconds before expiry to consider "soon" (default 5 minutes)
        
    Returns:
        True if token expires within threshold
    """
    token_exp = user_info.get("token_exp")
    if not token_exp:
        return False
    
    try:
        exp_time = datetime.fromtimestamp(token_exp)
        now = datetime.utcnow()
        time_until_expiry = (exp_time - now).total_seconds()
        
        return time_until_expiry <= threshold_seconds
        
    except Exception as e:
        logger.error(f"Error checking token expiry: {e}")
        return False