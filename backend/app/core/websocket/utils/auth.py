"""
WebSocket Authentication Utilities

Provides authentication and authorization functionality for WebSocket connections.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging
import jwt
from datetime import datetime, timedelta
from app.core.auth import token_validator, TokenValidationResult

logger = logging.getLogger(__name__)


class AuthResult:
    """Authentication result container"""
    
    def __init__(self, is_valid: bool, user_info: Optional[Dict[str, Any]] = None, error_message: Optional[str] = None):
        self.is_valid = is_valid
        self.user_info = user_info or {}
        self.error_message = error_message
    
    @property
    def user_id(self) -> Optional[str]:
        """Get user ID from auth result"""
        return self.user_info.get("user_id") or self.user_info.get("sub")
    
    @property
    def username(self) -> Optional[str]:
        """Get username from auth result"""
        return self.user_info.get("username") or self.user_info.get("name")
    
    @property
    def roles(self) -> List[str]:
        """Get user roles from auth result"""
        return self.user_info.get("roles", [])
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role"""
        return role in self.roles


@dataclass
class TokenConfig:
    """JWT token configuration"""
    secret_key: str
    algorithm: str = "HS256"
    verify_exp: bool = True
    verify_signature: bool = True
    leeway: int = 30  # 30 seconds grace period


class WebSocketAuth:
    """
    WebSocket Authentication Manager
    
    Handles authentication and authorization for WebSocket connections
    using various authentication methods.
    """
    
    def __init__(self, config):
        """
        Initialize the authentication manager
        
        Args:
            config: WebSocket configuration
        """
        self.config = config
        self.token_config: Optional[TokenConfig] = None
        self.auth_cache: Dict[str, AuthResult] = {}
        self.cache_timeout = 300  # 5 minutes
        
        # Set up token configuration if available
        self._setup_token_config()
    
    def _setup_token_config(self):
        """Set up JWT token configuration"""
        # Import settings to get the JWT configuration
        from app.core.config import settings
        
        logger.info(f"Setting up JWT config - secret_key exists: {bool(settings.secret_key)}, algorithm: {settings.algorithm}")
        
        if settings.secret_key and settings.secret_key != "your-secret-key-here":
            self.token_config = TokenConfig(
                secret_key=settings.secret_key,
                algorithm=settings.algorithm,
                verify_exp=True,
                verify_signature=True,
                leeway=30  # 30 seconds grace period for clock skew and token refresh
            )
            logger.info(f"JWT token configuration loaded from settings - Algorithm: {settings.algorithm}, Secret Key Length: {len(settings.secret_key)}")
        else:
            logger.warning("No valid JWT secret key found in settings, token authentication disabled")
    
    async def authenticate_connection(self, websocket, **kwargs) -> AuthResult:
        """
        Authenticate a WebSocket connection
        
        Args:
            websocket: WebSocket connection
            **kwargs: Connection parameters including auth tokens
            
        Returns:
            AuthResult: Authentication result
        """
        # Check for bypass mode (DEVELOPMENT ONLY)
        from ..test_bypass import BypassAuth
        if BypassAuth.should_bypass(self.config):
            test_result = BypassAuth.get_test_auth_result()
            return AuthResult(
                is_valid=test_result["is_valid"],
                user_info=test_result["user_info"]
            )
        
        auth_mode = self.config.auth_mode
        logger.info(f"WebSocket authentication attempt - mode: {auth_mode}, kwargs: {list(kwargs.keys())}")
        
        try:
            if auth_mode.value == "token":
                return await self._authenticate_with_token(**kwargs)
            elif auth_mode.value == "session":
                return await self._authenticate_with_session(**kwargs)
            elif auth_mode.value == "none":
                return self._create_anonymous_auth()
            else:
                return AuthResult(False, error_message=f"Unknown auth mode: {auth_mode}")
        
        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            return AuthResult(False, error_message="Authentication failed")
    
    async def _authenticate_with_token(self, **kwargs) -> AuthResult:
        """Authenticate using JWT token"""
        token = kwargs.get("token") or kwargs.get("auth_token")
        
        logger.info(f"Token authentication - token present: {bool(token)}, token length: {len(token) if token else 0}")
        
        if not token:
            logger.warning("No authentication token provided for WebSocket connection")
            return AuthResult(False, error_message="No authentication token provided")
        
        # Check cache first
        cache_key = f"token:{token[:16]}..."  # Use first 16 chars as cache key
        if cache_key in self.auth_cache:
            cached_result = self.auth_cache[cache_key]
            if self._is_cache_valid(cached_result):
                logger.debug("Using cached authentication result")
                return cached_result
        
        # Validate token
        result = await self._validate_jwt_token(token)
        
        # Cache result if valid
        if result.is_valid:
            self.auth_cache[cache_key] = result
        
        return result
    
    async def _authenticate_with_session(self, **kwargs) -> AuthResult:
        """Authenticate using session"""
        session_id = kwargs.get("session_id")
        
        if not session_id:
            return AuthResult(False, error_message="No session ID provided")
        
        # Check cache first
        cache_key = f"session:{session_id}"
        if cache_key in self.auth_cache:
            cached_result = self.auth_cache[cache_key]
            if self._is_cache_valid(cached_result):
                logger.debug("Using cached session authentication")
                return cached_result
        
        # Validate session (implement session validation logic here)
        result = await self._validate_session(session_id)
        
        # Cache result if valid
        if result.is_valid:
            self.auth_cache[cache_key] = result
        
        return result
    
    def _create_anonymous_auth(self) -> AuthResult:
        """Create anonymous authentication result"""
        return AuthResult(
            is_valid=True,
            user_info={
                "user_id": "anonymous",
                "username": "Anonymous",
                "roles": ["anonymous"]
            }
        )
    
    async def _validate_jwt_token(self, token: str) -> AuthResult:
        """Validate JWT token using unified validator"""
        if not self.token_config:
            logger.error("JWT token configuration not available")
            return AuthResult(False, error_message="Token authentication not configured")
        
        try:
            # Use unified token validator for consistent validation
            validation_result = token_validator.validate_token(
                token,
                verify_exp=self.token_config.verify_exp,
                allow_grace_period=True,  # Allow grace period for WebSocket connections
                expected_type="access"
            )
            
            if not validation_result.is_valid:
                logger.warning(f"Token validation failed: {validation_result.error}")
                return AuthResult(False, error_message=validation_result.error)
            
            # Log if token is in grace period or needs refresh
            if validation_result.in_grace_period:
                logger.info(f"WebSocket token for user {validation_result.user_id} is in grace period")
            if validation_result.needs_refresh:
                logger.info(f"WebSocket token for user {validation_result.user_id} needs refresh soon")
            
            # Extract user information
            user_info = {
                "user_id": validation_result.user_id,
                "username": validation_result.username,
                "email": validation_result.payload.get("email"),
                "roles": validation_result.payload.get("roles", []),
                "exp": validation_result.payload.get("exp"),
                "iat": validation_result.payload.get("iat"),
                "token_data": validation_result.payload,
                "needs_refresh": validation_result.needs_refresh,
                "in_grace_period": validation_result.in_grace_period
            }
            
            # Validate required fields
            if not user_info["user_id"]:
                return AuthResult(False, error_message="Token missing user ID")
            
            logger.info(f"Token validated successfully for user: {user_info['username']} (ID: {user_info['user_id']})")
            return AuthResult(True, user_info=user_info)
        
        except Exception as e:
            logger.error(f"JWT validation error for WebSocket: {e}", exc_info=True)
            return AuthResult(False, error_message=f"Token validation failed: {str(e)}")
    
    async def _validate_session(self, session_id: str) -> AuthResult:
        """Validate session ID"""
        # Placeholder for session validation logic
        # In a real implementation, this would check with a session store
        
        logger.warning("Session authentication not implemented")
        return AuthResult(False, error_message="Session authentication not implemented")
    
    def _is_cache_valid(self, auth_result: AuthResult) -> bool:
        """Check if cached authentication result is still valid"""
        if not auth_result.is_valid:
            return False
        
        # Check token expiration if available
        exp = auth_result.user_info.get("exp")
        if exp:
            try:
                exp_time = datetime.fromtimestamp(exp)
                if datetime.utcnow() >= exp_time:
                    logger.debug("Cached token expired")
                    return False
            except (TypeError, ValueError):
                logger.warning("Invalid token expiration time")
                return False
        
        return True
    
    def authorize_action(self, auth_result: AuthResult, action: str, resource: Optional[str] = None) -> bool:
        """
        Authorize an action for an authenticated user
        
        Args:
            auth_result: Authentication result
            action: Action to authorize
            resource: Optional resource identifier
            
        Returns:
            bool: True if authorized
        """
        if not auth_result.is_valid:
            return False
        
        # Basic role-based authorization
        user_roles = auth_result.roles
        
        # Define action-role mappings
        action_roles = {
            "connect": ["user", "admin", "anonymous"],
            "send_message": ["user", "admin"],
            "join_room": ["user", "admin"],
            "create_room": ["user", "admin"],
            "delete_room": ["admin"],
            "admin_action": ["admin"]
        }
        
        required_roles = action_roles.get(action, ["admin"])
        
        # Check if user has any required role
        has_permission = any(role in user_roles for role in required_roles)
        
        if not has_permission:
            logger.warning(f"User {auth_result.username} denied action {action}")
        
        return has_permission
    
    def clear_cache(self):
        """Clear authentication cache"""
        self.auth_cache.clear()
        logger.info("Authentication cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get authentication cache statistics"""
        return {
            "cache_size": len(self.auth_cache),
            "cache_timeout": self.cache_timeout
        }