"""
Custom exceptions for the collaboration microservice
"""

from typing import Optional, Any


class BaseCollaborationError(Exception):
    """Base exception class for collaboration microservice"""
    
    def __init__(self, message: str, status_code: int = 500, details: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class NotFoundError(BaseCollaborationError):
    """Raised when a requested resource is not found"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, status_code=404, details=details)


class ValidationError(BaseCollaborationError):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, status_code=400, details=details)


class UnauthorizedError(BaseCollaborationError):
    """Raised when user is not authorized to perform an action"""
    
    def __init__(self, message: str = "Unauthorized", details: Optional[Any] = None):
        super().__init__(message, status_code=401, details=details)


class ConflictError(BaseCollaborationError):
    """Raised when there's a conflict with existing data"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, status_code=409, details=details)


class DatabaseError(BaseCollaborationError):
    """Raised when a database operation fails"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message, status_code=500, details=details)


class ServiceUnavailableError(BaseCollaborationError):
    """Raised when a required service is unavailable"""
    
    def __init__(self, message: str = "Service temporarily unavailable", details: Optional[Any] = None):
        super().__init__(message, status_code=503, details=details)


class PermissionError(BaseCollaborationError):
    """Raised when user doesn't have permission to perform an action"""
    
    def __init__(self, message: str = "Permission denied", details: Optional[Any] = None):
        super().__init__(message, status_code=403, details=details)