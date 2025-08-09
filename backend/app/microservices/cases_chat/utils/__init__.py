"""
Cases Chat Utilities Module
Exports utility functions for the Cases Chat microservice
"""
from .validators import (
    validate_case_data,
    validate_chat_request,
    validate_doctor_type,
    validate_session_id
)
from .formatters import (
    format_case_response,
    format_chat_message,
    format_error_response,
    format_timestamp
)
from .error_handlers import (
    handle_storage_error,
    handle_ai_service_error,
    handle_mcp_error,
    ServiceUnavailableError
)

__all__ = [
    # Validators
    "validate_case_data",
    "validate_chat_request",
    "validate_doctor_type",
    "validate_session_id",
    
    # Formatters
    "format_case_response",
    "format_chat_message",
    "format_error_response",
    "format_timestamp",
    
    # Error handlers
    "handle_storage_error",
    "handle_ai_service_error",
    "handle_mcp_error",
    "ServiceUnavailableError"
]