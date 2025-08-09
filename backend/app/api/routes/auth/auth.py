"""
Authentication routes for the Unified Medical AI Platform
Clean implementation with working JSON body login
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.api.dependencies.auth import get_auth_credentials
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid
import os
import json
import logging
from app.core.auth import token_validator, TokenValidationResult

from app.core.database.neo4j_client import Neo4jClient
from app.core.database.models import User, UserCreate, UserResponse, Token

# Get unified logger
try:
    from app.core.unified_logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Import settings for JWT configuration
from app.core.config import settings

# JWT settings from unified configuration
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
TOKEN_EXPIRY_GRACE_PERIOD_MINUTES = 5  # 5-minute grace period for ongoing operations

# Request models
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: str = "patient"

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token with issued at timestamp"""
    # Extract user info from data
    user_id = data.get("sub") or data.get("user_id")
    username = data.get("username") or data.get("name")
    
    # Remove standard claims from additional data
    additional_claims = {k: v for k, v in data.items() if k not in ["sub", "user_id", "username", "name"]}
    
    # Use unified token validator to create token
    return token_validator.create_access_token(
        user_id=user_id,
        username=username,
        additional_claims=additional_claims,
        expires_delta=expires_delta
    )

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT refresh token with issued at timestamp"""
    # Extract user info from data
    user_id = data.get("sub") or data.get("user_id")
    username = data.get("username") or data.get("name")
    
    # Remove standard claims from additional data
    additional_claims = {k: v for k, v in data.items() if k not in ["sub", "user_id", "username", "name"]}
    
    # Use unified token validator to create token
    return token_validator.create_refresh_token(
        user_id=user_id,
        username=username,
        additional_claims=additional_claims,
        expires_delta=expires_delta if expires_delta else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )

def verify_token_with_grace_period(token: str, grace_period: bool = False) -> dict:
    """Verify JWT token with optional grace period for expired tokens"""
    # Use unified token validator
    validation_result = token_validator.validate_token(
        token,
        verify_exp=True,
        allow_grace_period=grace_period,
        expected_type="access"
    )
    
    # Convert to legacy format for compatibility
    return {
        "valid": validation_result.is_valid,
        "payload": validation_result.payload if validation_result.is_valid else None,
        "expired": validation_result.is_expired,
        "in_grace_period": validation_result.in_grace_period
    }

# Database dependency
async def get_database():
    """Get database client"""
    from app.main import get_neo4j_client
    return get_neo4j_client()

# Auth dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(get_auth_credentials),
    db: Neo4jClient = Depends(get_database)
) -> User:
    """Get current authenticated user with grace period support"""
    
    # Try normal token verification first
    token_result = verify_token_with_grace_period(credentials.credentials, grace_period=False)
    
    if not token_result["valid"]:
        # If expired, try with grace period
        if token_result["expired"]:
            grace_result = verify_token_with_grace_period(credentials.credentials, grace_period=True)
            if grace_result["valid"] and grace_result.get("in_grace_period"):
                # Token is in grace period, allow but add warning header
                payload = grace_result["payload"]
                logger.warning(f"Token in grace period for user: {payload.get('sub')}")
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={
                        "WWW-Authenticate": "Bearer",
                        "X-Token-Status": "expired",
                        "X-Refresh-Required": "true"
                    },
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        payload = token_result["payload"]
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token structure",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_data = await db.get_user_by_username(username=username)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Convert preferences from JSON string to dict if needed
    if isinstance(user_data.get('preferences'), str):
        try:
            user_data['preferences'] = json.loads(user_data['preferences'])
        except:
            user_data['preferences'] = {}
    elif user_data.get('preferences') is None:
        user_data['preferences'] = {}
    
    # Ensure role field exists
    if 'role' not in user_data:
        user_data['role'] = 'patient'
    
    # Convert datetime strings to datetime objects
    if isinstance(user_data.get('created_at'), str):
        user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
    if isinstance(user_data.get('updated_at'), str):
        user_data['updated_at'] = datetime.fromisoformat(user_data['updated_at'])
    if isinstance(user_data.get('last_login'), str):
        user_data['last_login'] = datetime.fromisoformat(user_data['last_login'])
    
    return User(**user_data)

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_user_ws(token: str, db: Neo4jClient = Depends(get_database)) -> dict:
    """Get current user for WebSocket authentication with enhanced error info"""
    
    # Try normal token verification first
    token_result = verify_token_with_grace_period(token, grace_period=False)
    
    if not token_result["valid"]:
        # If expired, try with grace period
        if token_result["expired"]:
            grace_result = verify_token_with_grace_period(token, grace_period=True)
            if grace_result["valid"] and grace_result.get("in_grace_period"):
                # Token is in grace period, allow but flag for refresh
                payload = grace_result["payload"]
                logger.warning(f"WebSocket token in grace period for user: {payload.get('sub')}")
                result = {"user": None, "payload": payload, "needs_refresh": True, "in_grace_period": True}
            else:
                return {"user": None, "error": "token_expired", "needs_refresh": True}
        else:
            return {"user": None, "error": "invalid_token", "needs_refresh": False}
    else:
        payload = token_result["payload"]
        result = {"user": None, "payload": payload, "needs_refresh": False, "in_grace_period": False}
    
    username: str = payload.get("sub")
    if username is None:
        return {"user": None, "error": "invalid_token_structure", "needs_refresh": False}
    
    try:
        user_data = await db.get_user_by_username(username=username)
        if user_data is None:
            return {"user": None, "error": "user_not_found", "needs_refresh": False}
        
        # Convert preferences from JSON string to dict if needed
        if isinstance(user_data.get('preferences'), str):
            try:
                user_data['preferences'] = json.loads(user_data['preferences'])
            except:
                user_data['preferences'] = {}
        elif user_data.get('preferences') is None:
            user_data['preferences'] = {}
        
        # Ensure role field exists
        if 'role' not in user_data:
            user_data['role'] = 'patient'
        
        # Convert datetime strings to datetime objects
        if isinstance(user_data.get('created_at'), str):
            user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
        if isinstance(user_data.get('updated_at'), str):
            user_data['updated_at'] = datetime.fromisoformat(user_data['updated_at'])
        if isinstance(user_data.get('last_login'), str):
            user_data['last_login'] = datetime.fromisoformat(user_data['last_login'])
        
        user = User(**user_data)
        result["user"] = user
        return result
        
    except Exception as e:
        logger.error(f"Database error during WebSocket auth: {e}")
        return {"user": None, "error": "database_error", "needs_refresh": False}

async def verify_websocket_token(token: str) -> Optional[User]:
    """Verify WebSocket token and return user if valid"""
    from app.core.database.neo4j_client import get_database
    
    try:
        db = await get_database()
        result = await get_current_user_ws(token, db)
        
        if result.get("user"):
            return result["user"]
        else:
            return None
    except Exception as e:
        logger.error(f"Error verifying WebSocket token: {e}")
        return None

# Routes
@router.post("/register", response_model=UserResponse)
async def register(
    register_data: RegisterRequest,
    db: Neo4jClient = Depends(get_database)
):
    """Register a new user"""
    try:
        logger.info(f"Registering new user: {register_data.username}")
        
        # Check if user exists
        existing_user = await db.get_user_by_username(register_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Create user
        user_data = {
            "user_id": str(uuid.uuid4()),
            "username": register_data.username,
            "email": register_data.email,
            "first_name": register_data.first_name,
            "last_name": register_data.last_name,
            "role": register_data.role,
            "password_hash": get_password_hash(register_data.password),
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
            "last_login": None,
            "preferences": "{}"  # Store as JSON string for Neo4j
        }
        
        created_user = await db.create_user(user_data)
        logger.info(f"User created successfully: {register_data.username}")
        
        # Return response
        return UserResponse(
            user_id=created_user["user_id"],
            username=created_user["username"],
            email=created_user["email"],
            first_name=created_user["first_name"],  # Database uses snake_case
            last_name=created_user["last_name"],    # Database uses snake_case
            role=created_user["role"],
            is_active=created_user["is_active"],
            created_at=created_user["created_at"],
            last_login=created_user.get("last_login")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "User registration failed",
            extra={
                "operation": "user_registration",
                "username": register_data.username,
                "email": register_data.email,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: Neo4jClient = Depends(get_database)
):
    """Login user - accepts JSON body"""
    try:
        logger.info(f"Login attempt for user: {login_data.username}")
        
        # Get user
        user_data = await db.get_user_by_username(login_data.username)
        if not user_data:
            logger.warning(f"User not found: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        # Verify password
        if not verify_password(login_data.password, user_data["password_hash"]):
            logger.warning(f"Invalid password for user: {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
        
        # Check if active
        if not user_data.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive"
            )
        
        # Create tokens
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        token_data = {"sub": user_data["username"], "user_id": user_data["user_id"]}
        access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
        refresh_token = create_refresh_token(data=token_data, expires_delta=refresh_token_expires)
        
        # Update last login
        await db.run_write_query(
            "MATCH (u:User {username: $username}) SET u.last_login = $last_login",
            {"username": login_data.username, "last_login": datetime.utcnow().isoformat()}
        )
        
        logger.info(
            "User login successful",
            extra={
                "username": login_data.username,
                "user_id": user_data["user_id"],
                "operation": "login",
                "status": "success",
                "security_event": "user_login_success"
            }
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "User login failed",
            extra={
                "operation": "user_login",
                "username": login_data.username,
                "error": str(e),
                "security_event": "user_login_failure"
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current user profile"""
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@router.post("/test-token")
async def create_test_token():
    """Create a test JWT token for WebSocket testing"""
    # Create test user data
    test_user = {
        "sub": "test_user",
        "user_id": "test_user_id",
        "username": "test_user",
        "email": "test@example.com",
        "roles": ["user"],
        "is_active": True
    }
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data=test_user, expires_delta=access_token_expires)
    
    logger.info(
        "Test token created",
        extra={
            "username": "test_user",
            "user_id": "test_user_id",
            "operation": "create_test_token"
        }
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "test_websocket_url": "ws://localhost:8080/api/v1/ws/",
        "usage_note": "Pass token via Sec-WebSocket-Protocol header as ['bearer', token] for security"
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Neo4jClient = Depends(get_database)
):
    """Refresh access token using refresh token"""
    try:
        # Decode refresh token
        payload = jwt.decode(refresh_data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        
        if not username or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Verify user still exists and is active
        user_data = await db.get_user_by_username(username)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user_data.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive"
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {"sub": username, "user_id": user_id}
        new_access_token = create_access_token(data=token_data, expires_delta=access_token_expires)
        
        logger.info(
            "Token refreshed successfully",
            extra={
                "username": username,
                "user_id": user_id,
                "operation": "token_refresh",
                "status": "success"
            }
        )
        
        return Token(
            access_token=new_access_token,
            refresh_token=refresh_data.refresh_token,  # Return same refresh token
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Token refresh failed",
            extra={
                "operation": "token_refresh",
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """Logout user"""
    # In a real app, you might want to blacklist the token
    return {"message": "Successfully logged out"}

@router.get("/verify")
async def verify_token(current_user: User = Depends(get_current_active_user)):
    """Verify if token is valid"""
    return {
        "valid": True,
        "user_id": current_user.user_id,
        "username": current_user.username
    }

@router.get("/token/status")
async def check_token_status(
    credentials: HTTPAuthorizationCredentials = Depends(get_auth_credentials)
):
    """Check token expiration status without requiring valid token"""
    token_result = verify_token_with_grace_period(credentials.credentials, grace_period=True)
    
    if token_result["valid"]:
        payload = token_result["payload"]
        exp_timestamp = payload.get("exp")
        current_time = datetime.utcnow().timestamp()
        
        time_until_expiry = exp_timestamp - current_time if exp_timestamp else 0
        
        return {
            "valid": True,
            "expired": token_result.get("expired", False),
            "in_grace_period": token_result.get("in_grace_period", False),
            "expires_in_seconds": max(0, int(time_until_expiry)),
            "should_refresh": time_until_expiry < 300,  # Suggest refresh if less than 5 minutes
            "username": payload.get("sub"),
            "user_id": payload.get("user_id")
        }
    else:
        return {
            "valid": False,
            "expired": token_result.get("expired", False),
            "in_grace_period": False,
            "expires_in_seconds": 0,
            "should_refresh": True,
            "error": "invalid_token"
        }

# Test endpoint - UPDATED
@router.get("/test")
async def test_auth():
    """Test if auth module is loaded"""
    return {"status": "Auth module is working - UPDATED", "time": datetime.utcnow().isoformat()}

@router.get("/test-model-schema")
async def test_model_schema():
    """Show the actual RegisterRequest model schema"""
    return {
        "model_fields": list(RegisterRequest.__fields__.keys()) if hasattr(RegisterRequest, '__fields__') else "No __fields__",
        "model_annotations": RegisterRequest.__annotations__ if hasattr(RegisterRequest, '__annotations__') else "No annotations",
        "model_dict": str(RegisterRequest.model_json_schema()) if hasattr(RegisterRequest, 'model_json_schema') else "No schema method"
    }