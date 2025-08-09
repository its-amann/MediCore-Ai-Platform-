"""
Unified Token Validation Module

Provides consistent JWT token validation for both HTTP and WebSocket connections.
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import jwt
from jose import JWTError
from app.core.config import settings
from app.core.unified_logging import get_logger

logger = get_logger(__name__)


class TokenValidationResult:
    """Token validation result container"""
    
    def __init__(
        self,
        is_valid: bool,
        payload: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        is_expired: bool = False,
        in_grace_period: bool = False,
        needs_refresh: bool = False
    ):
        self.is_valid = is_valid
        self.payload = payload or {}
        self.error = error
        self.is_expired = is_expired
        self.in_grace_period = in_grace_period
        self.needs_refresh = needs_refresh
    
    @property
    def user_id(self) -> Optional[str]:
        """Get user ID from token payload"""
        return self.payload.get("sub") or self.payload.get("user_id")
    
    @property
    def username(self) -> Optional[str]:
        """Get username from token payload"""
        return self.payload.get("username") or self.payload.get("name")
    
    @property
    def token_type(self) -> Optional[str]:
        """Get token type (access/refresh)"""
        return self.payload.get("type", "access")
    
    @property
    def expires_at(self) -> Optional[datetime]:
        """Get token expiration time"""
        exp = self.payload.get("exp")
        return datetime.fromtimestamp(exp) if exp else None
    
    @property
    def time_until_expiry(self) -> Optional[timedelta]:
        """Get time remaining until token expires"""
        if self.expires_at:
            return self.expires_at - datetime.utcnow()
        return None


class UnifiedTokenValidator:
    """Unified token validator for consistent validation across HTTP and WebSocket"""
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        grace_period_minutes: int = 5,
        leeway_seconds: int = 30
    ):
        """
        Initialize token validator
        
        Args:
            secret_key: JWT secret key (defaults to settings)
            algorithm: JWT algorithm (defaults to settings)
            access_token_expire_minutes: Access token expiry time
            refresh_token_expire_days: Refresh token expiry time
            grace_period_minutes: Grace period for expired tokens
            leeway_seconds: Clock skew tolerance
        """
        self.secret_key = secret_key or settings.secret_key
        self.algorithm = algorithm or settings.algorithm
        self.access_token_expire_minutes = access_token_expire_minutes or settings.access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.grace_period_minutes = grace_period_minutes
        self.leeway_seconds = leeway_seconds
        
        if not self.secret_key or self.secret_key == "your-secret-key-here":
            logger.error("Invalid JWT secret key configuration")
            raise ValueError("JWT secret key not properly configured")
    
    def validate_token(
        self,
        token: str,
        verify_exp: bool = True,
        allow_grace_period: bool = True,
        expected_type: Optional[str] = None
    ) -> TokenValidationResult:
        """
        Validate JWT token with consistent rules
        
        Args:
            token: JWT token to validate
            verify_exp: Whether to verify expiration
            allow_grace_period: Whether to allow grace period for expired tokens
            expected_type: Expected token type (access/refresh)
            
        Returns:
            TokenValidationResult with validation details
        """
        try:
            # First attempt: Normal validation with leeway
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": verify_exp},
                leeway=timedelta(seconds=self.leeway_seconds)
            )
            
            # Check token type if specified
            if expected_type and payload.get("type") != expected_type:
                return TokenValidationResult(
                    is_valid=False,
                    error=f"Invalid token type. Expected {expected_type}, got {payload.get('type')}"
                )
            
            # Check if token needs refresh soon (within 5 minutes of expiry)
            exp_time = payload.get("exp")
            needs_refresh = False
            if exp_time:
                time_until_expiry = datetime.fromtimestamp(exp_time) - datetime.utcnow()
                if time_until_expiry.total_seconds() < 300:  # 5 minutes
                    needs_refresh = True
            
            return TokenValidationResult(
                is_valid=True,
                payload=payload,
                needs_refresh=needs_refresh
            )
            
        except jwt.ExpiredSignatureError:
            # Token is expired, check if within grace period
            if not allow_grace_period:
                return TokenValidationResult(
                    is_valid=False,
                    error="Token has expired",
                    is_expired=True
                )
            
            try:
                # Decode without expiry verification
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.algorithm],
                    options={"verify_exp": False}
                )
                
                # Check if within grace period
                exp_timestamp = payload.get("exp")
                if exp_timestamp:
                    exp_time = datetime.fromtimestamp(exp_timestamp)
                    grace_deadline = exp_time + timedelta(minutes=self.grace_period_minutes)
                    
                    if datetime.utcnow() <= grace_deadline:
                        logger.info(f"Token for user {payload.get('sub')} is expired but within grace period")
                        return TokenValidationResult(
                            is_valid=True,
                            payload=payload,
                            is_expired=True,
                            in_grace_period=True,
                            needs_refresh=True
                        )
                
                return TokenValidationResult(
                    is_valid=False,
                    error="Token has expired and is outside grace period",
                    is_expired=True
                )
                
            except Exception as e:
                logger.error(f"Error decoding expired token: {e}")
                return TokenValidationResult(
                    is_valid=False,
                    error="Invalid token",
                    is_expired=True
                )
                
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token error: {e}")
            return TokenValidationResult(
                is_valid=False,
                error=f"Invalid token: {str(e)}"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error validating token: {e}")
            return TokenValidationResult(
                is_valid=False,
                error="Token validation failed"
            )
    
    def create_access_token(
        self,
        user_id: str,
        username: Optional[str] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create access token with consistent structure
        
        Args:
            user_id: User ID (stored as 'sub' claim)
            username: Username (optional)
            additional_claims: Additional JWT claims
            expires_delta: Custom expiration time
            
        Returns:
            JWT access token
        """
        now = datetime.utcnow()
        
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        claims = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "type": "access"
        }
        
        if username:
            claims["username"] = username
            
        if additional_claims:
            claims.update(additional_claims)
        
        return jwt.encode(claims, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(
        self,
        user_id: str,
        username: Optional[str] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create refresh token with consistent structure
        
        Args:
            user_id: User ID (stored as 'sub' claim)
            username: Username (optional)
            additional_claims: Additional JWT claims
            expires_delta: Custom expiration time
            
        Returns:
            JWT refresh token
        """
        now = datetime.utcnow()
        
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(days=self.refresh_token_expire_days)
        
        claims = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "type": "refresh"
        }
        
        if username:
            claims["username"] = username
            
        if additional_claims:
            claims.update(additional_claims)
        
        return jwt.encode(claims, self.secret_key, algorithm=self.algorithm)


# Global validator instance
token_validator = UnifiedTokenValidator()