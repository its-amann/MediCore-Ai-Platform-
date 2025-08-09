"""
Error Handling Utilities
Provides error handling and exception management
"""
from fastapi import HTTPException, status
from typing import Any, Optional, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ServiceUnavailableError(Exception):
    """Custom exception for service unavailability"""
    def __init__(self, service_name: str, message: str = ""):
        self.service_name = service_name
        self.message = message or f"{service_name} service is unavailable"
        super().__init__(self.message)


def handle_storage_error(error: Exception) -> HTTPException:
    """
    Handle storage-related errors
    
    Args:
        error: The exception that occurred
        
    Returns:
        HTTPException with appropriate status code and message
    """
    error_str = str(error).lower()
    
    # Neo4j connection errors
    if "connection" in error_str or "connect" in error_str:
        logger.error(f"Storage connection error: {error}")
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed. Please try again later."
        )
    
    # Not found errors
    if "not found" in error_str or "does not exist" in error_str:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested resource was not found"
        )
    
    # Constraint violations
    if "constraint" in error_str or "duplicate" in error_str:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A resource with the same identifier already exists"
        )
    
    # Permission errors
    if "permission" in error_str or "unauthorized" in error_str:
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
    
    # Default error
    logger.error(f"Unhandled storage error: {error}")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An error occurred while accessing the database"
    )


def handle_ai_service_error(error: Exception) -> HTTPException:
    """
    Handle AI service-related errors (Groq, Gemini, etc.)
    
    Args:
        error: The exception that occurred
        
    Returns:
        HTTPException with appropriate status code and message
    """
    error_str = str(error).lower()
    
    # API key errors
    if "api key" in error_str or "authentication" in error_str:
        logger.error(f"AI service authentication error: {error}")
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service authentication failed. Please contact support."
        )
    
    # Rate limiting
    if "rate limit" in error_str or "quota" in error_str:
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI service rate limit exceeded. Please try again later."
        )
    
    # Model errors
    if "model" in error_str or "not available" in error_str:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The requested AI model is not available"
        )
    
    # Content filtering
    if "content" in error_str or "safety" in error_str or "blocked" in error_str:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The content was blocked by safety filters. Please modify your request."
        )
    
    # Timeout errors
    if "timeout" in error_str or "timed out" in error_str:
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI service request timed out. Please try again."
        )
    
    # Default error
    logger.error(f"Unhandled AI service error: {error}")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An error occurred while processing your request with the AI service"
    )


def handle_mcp_error(error: Exception) -> HTTPException:
    """
    Handle MCP server-related errors
    
    Args:
        error: The exception that occurred
        
    Returns:
        HTTPException with appropriate status code and message
    """
    error_str = str(error).lower()
    
    # MCP server unavailable
    if isinstance(error, ServiceUnavailableError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{error.service_name} is currently unavailable"
        )
    
    # Connection errors
    if "connection" in error_str or "connect" in error_str:
        logger.error(f"MCP connection error: {error}")
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Medical history service is unavailable. Core features are still accessible."
        )
    
    # Timeout
    if "timeout" in error_str:
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Medical history service request timed out"
        )
    
    # Default error
    logger.error(f"Unhandled MCP error: {error}")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An error occurred while accessing medical history service"
    )


def handle_validation_error(field: str, message: str) -> HTTPException:
    """
    Handle validation errors with consistent formatting
    
    Args:
        field: Field that failed validation
        message: Validation error message
        
    Returns:
        HTTPException with validation details
    """
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "type": "validation_error",
            "errors": [{
                "field": field,
                "message": message
            }]
        }
    )


def log_error_with_context(
    error: Exception,
    context: Dict[str, Any],
    severity: str = "error"
) -> None:
    """
    Log error with additional context information
    
    Args:
        error: The exception
        context: Additional context (user_id, case_id, etc.)
        severity: Log level (error, warning, critical)
    """
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "error_type": type(error).__name__,
        "error_message": str(error),
        **context
    }
    
    log_message = f"Error occurred: {log_data}"
    
    if severity == "critical":
        logger.critical(log_message, exc_info=True)
    elif severity == "warning":
        logger.warning(log_message)
    else:
        logger.error(log_message, exc_info=True)


def create_error_response(
    error_type: str,
    message: str,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response
    
    Args:
        error_type: Type of error
        message: Error message
        status_code: HTTP status code
        details: Additional error details
        
    Returns:
        Error response dictionary
    """
    response = {
        "error": {
            "type": error_type,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "status_code": status_code
        }
    }
    
    if details:
        response["error"]["details"] = details
    
    return response


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable
    
    Args:
        error: The exception
        
    Returns:
        True if the error is retryable, False otherwise
    """
    error_str = str(error).lower()
    
    retryable_patterns = [
        "timeout",
        "connection",
        "temporarily unavailable",
        "rate limit",
        "quota",
        "503",
        "504"
    ]
    
    return any(pattern in error_str for pattern in retryable_patterns)