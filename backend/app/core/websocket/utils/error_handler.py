"""
WebSocket Error Handler

Centralized error handling and logging for WebSocket connections.
"""

import traceback
from typing import Optional, Dict, Any, Union
from enum import IntEnum
from datetime import datetime
from app.core.unified_logging import get_logger

logger = get_logger(__name__)


class WebSocketErrorCode(IntEnum):
    """WebSocket close codes as per RFC 6455"""
    # Standard codes
    NORMAL_CLOSURE = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED_DATA = 1003
    NO_STATUS_RCVD = 1005
    ABNORMAL_CLOSURE = 1006
    INVALID_FRAME_PAYLOAD_DATA = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    MANDATORY_EXT = 1010
    INTERNAL_ERROR = 1011
    SERVICE_RESTART = 1012
    TRY_AGAIN_LATER = 1013
    BAD_GATEWAY = 1014
    TLS_HANDSHAKE = 1015
    
    # Application-specific codes (4000-4999)
    AUTH_REQUIRED = 4001
    AUTH_FAILED = 4003
    TOKEN_EXPIRED = 4004
    INVALID_REQUEST = 4005
    RATE_LIMIT_EXCEEDED = 4008
    PERMISSION_DENIED = 4009
    SESSION_EXPIRED = 4010
    SERVICE_UNAVAILABLE = 4011
    INVALID_MESSAGE_FORMAT = 4012
    RESOURCE_NOT_FOUND = 4013


class WebSocketError(Exception):
    """Base WebSocket error class"""
    def __init__(
        self,
        message: str,
        code: WebSocketErrorCode = WebSocketErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class AuthenticationError(WebSocketError):
    """Authentication-related errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, WebSocketErrorCode.AUTH_FAILED, details)


class RateLimitError(WebSocketError):
    """Rate limit exceeded errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, WebSocketErrorCode.RATE_LIMIT_EXCEEDED, details)


class ValidationError(WebSocketError):
    """Message validation errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, WebSocketErrorCode.INVALID_MESSAGE_FORMAT, details)


class WebSocketErrorHandler:
    """Centralized error handler for WebSocket connections"""
    
    def __init__(self):
        """Initialize error handler"""
        self.error_counts: Dict[str, int] = {}
        self.error_history: list = []
        self.max_history = 1000
    
    async def handle_error(
        self,
        error: Exception,
        connection_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle and log WebSocket errors
        
        Args:
            error: The exception that occurred
            connection_id: WebSocket connection ID
            user_id: User ID if available
            context: Additional context information
            
        Returns:
            Error response dict
        """
        # Build error context
        error_context = {
            "connection_id": connection_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            **(context or {})
        }
        
        # Determine error code and message
        if isinstance(error, WebSocketError):
            code = error.code
            message = error.message
            details = error.details
        elif isinstance(error, ValueError) and "authentication" in str(error).lower():
            code = WebSocketErrorCode.AUTH_FAILED
            message = str(error)
            details = {}
        elif isinstance(error, ValueError) and "rate limit" in str(error).lower():
            code = WebSocketErrorCode.RATE_LIMIT_EXCEEDED
            message = str(error)
            details = {}
        elif isinstance(error, (ValueError, TypeError)):
            code = WebSocketErrorCode.INVALID_REQUEST
            message = f"Invalid request: {error}"
            details = {}
        else:
            code = WebSocketErrorCode.INTERNAL_ERROR
            message = "Internal server error"
            details = {"original_error": str(error)}
        
        # Log the error
        self._log_error(error, error_context, code)
        
        # Track error statistics
        self._track_error(error_type=type(error).__name__, connection_id=connection_id)
        
        # Build error response
        error_response = {
            "type": "error",
            "code": int(code),
            "message": message,
            "timestamp": error_context["timestamp"]
        }
        
        # Add details in development mode
        if logger.isEnabledFor(10):  # DEBUG level
            error_response["details"] = details
            error_response["traceback"] = traceback.format_exc()
        
        return error_response
    
    def _log_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        code: WebSocketErrorCode
    ):
        """Log error with appropriate level"""
        # Determine log level based on error code
        if code in [
            WebSocketErrorCode.AUTH_FAILED,
            WebSocketErrorCode.RATE_LIMIT_EXCEEDED,
            WebSocketErrorCode.INVALID_REQUEST,
            WebSocketErrorCode.PERMISSION_DENIED
        ]:
            # Client errors - log as warning
            logger.warning(
                f"WebSocket client error: {error}",
                extra=context,
                exc_info=False
            )
        elif code == WebSocketErrorCode.INTERNAL_ERROR:
            # Server errors - log as error with full traceback
            logger.error(
                f"WebSocket server error: {error}",
                extra=context,
                exc_info=True
            )
        else:
            # Other errors - log as info
            logger.info(
                f"WebSocket error: {error}",
                extra=context,
                exc_info=False
            )
    
    def _track_error(self, error_type: str, connection_id: Optional[str]):
        """Track error statistics"""
        # Count errors by type
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Add to history
        self.error_history.append({
            "timestamp": datetime.utcnow(),
            "error_type": error_type,
            "connection_id": connection_id
        })
        
        # Trim history if too large
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        # Calculate error rate over last minute
        now = datetime.utcnow()
        recent_errors = [
            err for err in self.error_history
            if (now - err["timestamp"]).total_seconds() < 60
        ]
        
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts_by_type": self.error_counts.copy(),
            "errors_last_minute": len(recent_errors),
            "error_rate": len(recent_errors) / 60.0,  # errors per second
            "most_common_error": max(self.error_counts.items(), key=lambda x: x[1])[0] if self.error_counts else None
        }
    
    def should_close_connection(self, error: Exception) -> bool:
        """Determine if connection should be closed after error"""
        # Always close on authentication errors
        if isinstance(error, (AuthenticationError, WebSocketError)):
            return error.code in [
                WebSocketErrorCode.AUTH_FAILED,
                WebSocketErrorCode.TOKEN_EXPIRED,
                WebSocketErrorCode.PERMISSION_DENIED,
                WebSocketErrorCode.RATE_LIMIT_EXCEEDED,
                WebSocketErrorCode.INTERNAL_ERROR
            ]
        
        # Close on specific error types
        return isinstance(error, (
            ConnectionError,
            TimeoutError,
            MemoryError
        ))
    
    def get_close_code(self, error: Exception) -> int:
        """Get appropriate WebSocket close code for error"""
        if isinstance(error, WebSocketError):
            return int(error.code)
        elif isinstance(error, ValueError) and "authentication" in str(error).lower():
            return int(WebSocketErrorCode.AUTH_FAILED)
        elif isinstance(error, ValueError) and "rate limit" in str(error).lower():
            return int(WebSocketErrorCode.RATE_LIMIT_EXCEEDED)
        elif isinstance(error, (ValueError, TypeError)):
            return int(WebSocketErrorCode.INVALID_REQUEST)
        else:
            return int(WebSocketErrorCode.INTERNAL_ERROR)


# Global error handler instance
websocket_error_handler = WebSocketErrorHandler()