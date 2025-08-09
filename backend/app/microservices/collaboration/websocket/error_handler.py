"""
Error Handling and Recovery System for Collaboration WebSocket

This module provides centralized error handling, retry logic, and 
recovery mechanisms for WebSocket operations.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Callable, TypeVar, Union
from datetime import datetime, timedelta
from enum import Enum
import functools

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorType(Enum):
    """WebSocket error types"""
    CONNECTION_ERROR = "connection_error"
    AUTHENTICATION_ERROR = "authentication_error"
    MESSAGE_PARSE_ERROR = "message_parse_error"
    HANDLER_ERROR = "handler_error"
    BROADCAST_ERROR = "broadcast_error"
    ROOM_ACCESS_ERROR = "room_access_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    INTERNAL_ERROR = "internal_error"


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"          # Log and continue
    MEDIUM = "medium"    # Notify user and continue
    HIGH = "high"        # Retry with backoff
    CRITICAL = "critical" # Disconnect and cleanup


class WebSocketError(Exception):
    """Base WebSocket error class"""
    
    def __init__(
        self,
        error_type: ErrorType,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None
    ):
        self.error_type = error_type
        self.message = message
        self.severity = severity
        self.details = details or {}
        self.retry_after = retry_after
        self.timestamp = datetime.utcnow()
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for client response"""
        return {
            "error": True,
            "error_type": self.error_type.value,
            "message": self.message,
            "severity": self.severity.value,
            "details": self.details,
            "retry_after": self.retry_after,
            "timestamp": self.timestamp.isoformat()
        }


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class ErrorHandler:
    """Centralized error handler for WebSocket operations"""
    
    def __init__(self):
        self._error_count: Dict[str, int] = {}
        self._error_history: Dict[str, List[WebSocketError]] = {}
        self._retry_configs: Dict[ErrorType, RetryConfig] = {
            ErrorType.CONNECTION_ERROR: RetryConfig(max_attempts=5, initial_delay=2.0),
            ErrorType.BROADCAST_ERROR: RetryConfig(max_attempts=3, initial_delay=0.5),
            ErrorType.HANDLER_ERROR: RetryConfig(max_attempts=2, initial_delay=1.0),
            ErrorType.RATE_LIMIT_ERROR: RetryConfig(max_attempts=1, initial_delay=5.0)
        }
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def get_retry_config(self, error_type: ErrorType) -> RetryConfig:
        """Get retry configuration for error type"""
        return self._retry_configs.get(error_type, RetryConfig(max_attempts=1))
    
    def record_error(self, user_id: str, error: WebSocketError):
        """Record an error for tracking"""
        if user_id not in self._error_history:
            self._error_history[user_id] = []
        
        self._error_history[user_id].append(error)
        
        # Keep only recent errors (last hour)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self._error_history[user_id] = [
            e for e in self._error_history[user_id] 
            if e.timestamp > cutoff
        ]
        
        # Update error count
        self._error_count[user_id] = len(self._error_history[user_id])
    
    def get_user_error_rate(self, user_id: str, window_minutes: int = 5) -> float:
        """Get error rate for a user in the specified time window"""
        if user_id not in self._error_history:
            return 0.0
        
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent_errors = [
            e for e in self._error_history[user_id]
            if e.timestamp > cutoff
        ]
        
        return len(recent_errors) / window_minutes
    
    def should_disconnect_user(self, user_id: str) -> bool:
        """Check if user should be disconnected due to excessive errors"""
        error_rate = self.get_user_error_rate(user_id, window_minutes=5)
        
        # Disconnect if more than 10 errors per minute average
        return error_rate > 2.0
    
    def get_circuit_breaker(self, key: str) -> 'CircuitBreaker':
        """Get or create a circuit breaker for a key"""
        if key not in self._circuit_breakers:
            self._circuit_breakers[key] = CircuitBreaker(key)
        return self._circuit_breakers[key]
    
    async def handle_error(
        self,
        error: Union[Exception, WebSocketError],
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle an error and return appropriate response"""
        if isinstance(error, WebSocketError):
            ws_error = error
        else:
            # Convert to WebSocketError
            ws_error = WebSocketError(
                ErrorType.INTERNAL_ERROR,
                str(error),
                ErrorSeverity.HIGH,
                details={"original_error": type(error).__name__}
            )
        
        # Log the error
        log_level = {
            ErrorSeverity.LOW: logging.DEBUG,
            ErrorSeverity.MEDIUM: logging.INFO,
            ErrorSeverity.HIGH: logging.WARNING,
            ErrorSeverity.CRITICAL: logging.ERROR
        }.get(ws_error.severity, logging.ERROR)
        
        logger.log(
            log_level,
            f"WebSocket error for user {user_id}: {ws_error.error_type.value} - {ws_error.message}",
            extra={"error_details": ws_error.details, "context": context}
        )
        
        # Record error if user_id provided
        if user_id:
            self.record_error(user_id, ws_error)
        
        # Return error response
        return ws_error.to_dict()


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascading failures"""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._failure_count = 0
        self._last_failure_time = None
        self._state = "closed"  # closed, open, half-open
    
    @property
    def state(self) -> str:
        """Get current circuit breaker state"""
        if self._state == "open":
            if self._last_failure_time:
                time_since_failure = (datetime.utcnow() - self._last_failure_time).total_seconds()
                if time_since_failure >= self.recovery_timeout:
                    self._state = "half-open"
        return self._state
    
    def call_succeeded(self):
        """Record successful call"""
        self._failure_count = 0
        self._state = "closed"
    
    def call_failed(self):
        """Record failed call"""
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()
        
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning(f"Circuit breaker {self.name} opened after {self._failure_count} failures")
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Call function with circuit breaker protection"""
        if self.state == "open":
            raise WebSocketError(
                ErrorType.INTERNAL_ERROR,
                f"Circuit breaker {self.name} is open",
                ErrorSeverity.HIGH,
                details={"retry_after": int(self.recovery_timeout)}
            )
        
        try:
            result = await func(*args, **kwargs)
            self.call_succeeded()
            return result
        except self.expected_exception as e:
            self.call_failed()
            raise


def with_retry(
    retry_config: Optional[RetryConfig] = None,
    error_handler: Optional[ErrorHandler] = None
):
    """Decorator for adding retry logic to async functions"""
    if retry_config is None:
        retry_config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(retry_config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == retry_config.max_attempts - 1:
                        # Last attempt failed
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        retry_config.initial_delay * (retry_config.exponential_base ** attempt),
                        retry_config.max_delay
                    )
                    
                    # Add jitter if enabled
                    if retry_config.jitter:
                        import random
                        delay *= (0.5 + random.random())
                    
                    logger.debug(
                        f"Retry {attempt + 1}/{retry_config.max_attempts} "
                        f"for {func.__name__} after {delay:.1f}s delay"
                    )
                    
                    await asyncio.sleep(delay)
            
            # All retries failed
            if error_handler and last_exception:
                await error_handler.handle_error(last_exception)
            
            raise last_exception
        
        return wrapper
    return decorator


def with_circuit_breaker(circuit_breaker: CircuitBreaker):
    """Decorator for adding circuit breaker protection to async functions"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await circuit_breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


# Global error handler instance
error_handler = ErrorHandler()