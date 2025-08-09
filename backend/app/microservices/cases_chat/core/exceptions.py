"""
Custom exceptions for Cases Chat microservice
"""
from typing import Any, Dict, Optional


class CasesChatException(Exception):
    """Base exception for Cases Chat service"""
    
    def __init__(self, message: str, code: str = "CASES_CHAT_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details
        }


class ConfigurationError(CasesChatException):
    """Raised when there's a configuration issue"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIGURATION_ERROR", details)


class StorageError(CasesChatException):
    """Raised when there's a storage/database issue"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "STORAGE_ERROR", details)


class DoctorServiceError(CasesChatException):
    """Raised when there's an issue with doctor services"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DOCTOR_SERVICE_ERROR", details)


class WebSocketError(CasesChatException):
    """Raised when there's a WebSocket communication issue"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "WEBSOCKET_ERROR", details)


class ValidationError(CasesChatException):
    """Raised when validation fails"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)


class CaseNotFoundError(CasesChatException):
    """Raised when a case is not found"""
    
    def __init__(self, case_id: str):
        super().__init__(
            f"Case not found: {case_id}",
            "CASE_NOT_FOUND",
            {"case_id": case_id}
        )


class MessageNotFoundError(CasesChatException):
    """Raised when a message is not found"""
    
    def __init__(self, message_id: str):
        super().__init__(
            f"Message not found: {message_id}",
            "MESSAGE_NOT_FOUND",
            {"message_id": message_id}
        )


class MCPServiceError(CasesChatException):
    """Raised when there's an issue with MCP service"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "MCP_SERVICE_ERROR", details)


class MediaError(CasesChatException):
    """Raised when there's an issue with media handling"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "MEDIA_ERROR", details)


class AuthenticationError(CasesChatException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTHENTICATION_ERROR")


class AuthorizationError(CasesChatException):
    """Raised when authorization fails"""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, "AUTHORIZATION_ERROR")


class RateLimitError(CasesChatException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(message, "RATE_LIMIT_ERROR", details)