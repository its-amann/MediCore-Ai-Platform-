"""
Response Formatting Utilities
Provides formatting functions for API responses
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json


def format_case_response(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format case data for API response
    
    Args:
        case_data: Raw case data from storage
        
    Returns:
        Formatted case response
    """
    # Ensure required fields
    formatted = {
        "case_id": case_data.get("case_id", ""),
        "case_number": case_data.get("case_number"),
        "user_id": case_data.get("user_id", ""),
        "title": case_data.get("title"),
        "description": case_data.get("description"),
        "chief_complaint": case_data.get("chief_complaint", ""),
        "symptoms": case_data.get("symptoms", []),
        "status": case_data.get("status", "active"),
        "priority": case_data.get("priority", "medium"),
        "patient_age": case_data.get("patient_age"),
        "patient_gender": case_data.get("patient_gender"),
        "past_medical_history": case_data.get("past_medical_history"),
        "current_medications": case_data.get("current_medications"),
        "allergies": case_data.get("allergies"),
        "medical_category": case_data.get("medical_category"),
        "diagnosis": case_data.get("diagnosis"),
        "treatment_plan": case_data.get("treatment_plan"),
        "outcome": case_data.get("outcome"),
        "created_at": format_timestamp(case_data.get("created_at")),
        "updated_at": format_timestamp(case_data.get("updated_at")),
        "closed_at": format_timestamp(case_data.get("closed_at")),
        "chat_sessions": case_data.get("chat_sessions", [])
    }
    
    # Remove None values for cleaner response
    return {k: v for k, v in formatted.items() if v is not None}


def format_chat_message(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format chat message for API response
    
    Args:
        message_data: Raw message data
        
    Returns:
        Formatted message
    """
    formatted = {
        "message_id": message_data.get("message_id"),
        "session_id": message_data.get("session_id"),
        "case_id": message_data.get("case_id"),
        "user_id": message_data.get("user_id"),
        "user_message": message_data.get("user_message", ""),
        "doctor_type": message_data.get("doctor_type", ""),
        "doctor_response": message_data.get("doctor_response", ""),
        "created_at": format_timestamp(message_data.get("created_at")),
        "metadata": message_data.get("metadata", {})
    }
    
    return formatted


def format_error_response(
    error_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 500
) -> Dict[str, Any]:
    """
    Format error response in consistent structure
    
    Args:
        error_type: Type of error (e.g., "validation_error", "storage_error")
        message: Error message
        details: Additional error details
        status_code: HTTP status code
        
    Returns:
        Formatted error response
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


def format_timestamp(timestamp: Any) -> Optional[str]:
    """
    Format timestamp to ISO format string
    
    Args:
        timestamp: Timestamp to format (datetime, string, or None)
        
    Returns:
        ISO format timestamp string or None
    """
    if timestamp is None:
        return None
    
    if isinstance(timestamp, str):
        # Already a string, ensure it's in ISO format
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.isoformat()
        except:
            return timestamp
    
    if isinstance(timestamp, datetime):
        return timestamp.isoformat()
    
    # Try to convert other types
    try:
        return datetime(timestamp).isoformat()
    except:
        return str(timestamp)


def format_doctor_response(
    response_data: Dict[str, Any],
    session_id: str,
    message_id: str,
    doctor_type: str,
    processing_time: float
) -> Dict[str, Any]:
    """
    Format doctor response for API
    
    Args:
        response_data: Raw response from doctor service
        session_id: Chat session ID
        message_id: Message ID
        doctor_type: Type of doctor
        processing_time: Time taken to process
        
    Returns:
        Formatted response
    """
    return {
        "session_id": session_id,
        "message_id": message_id,
        "doctor_response": response_data.get("response", ""),
        "doctor_type": doctor_type,
        "confidence_score": response_data.get("confidence_score", 0.8),
        "processing_time": round(processing_time, 3),
        "context_used": response_data.get("context_used", 0),
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": response_data.get("metadata", {})
    }


def format_case_list_response(
    cases: List[Dict[str, Any]],
    total_count: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Format case list response with pagination
    
    Args:
        cases: List of cases
        total_count: Total number of cases (for pagination)
        limit: Page size
        offset: Page offset
        
    Returns:
        Formatted response with cases and pagination info
    """
    formatted_cases = [format_case_response(case) for case in cases]
    
    response = {
        "cases": formatted_cases,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "count": len(formatted_cases)
        }
    }
    
    if total_count is not None:
        response["pagination"]["total"] = total_count
        response["pagination"]["has_more"] = (offset + len(formatted_cases)) < total_count
    
    return response


def format_websocket_message(
    message_type: str,
    data: Dict[str, Any],
    connection_id: Optional[str] = None
) -> str:
    """
    Format message for WebSocket transmission
    
    Args:
        message_type: Type of WebSocket message
        data: Message data
        connection_id: Optional connection ID
        
    Returns:
        JSON string for WebSocket
    """
    message = {
        "type": message_type,
        "timestamp": datetime.utcnow().isoformat(),
        **data
    }
    
    if connection_id:
        message["connection_id"] = connection_id
    
    return json.dumps(message, default=str)


def format_health_check_response(
    service_name: str,
    status: str,
    components: Dict[str, Dict[str, Any]],
    version: str
) -> Dict[str, Any]:
    """
    Format health check response
    
    Args:
        service_name: Name of the service
        status: Overall status
        components: Component health statuses
        version: Service version
        
    Returns:
        Formatted health check response
    """
    return {
        "service": service_name,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": version,
        "components": components,
        "healthy": status in ["healthy", "degraded"]
    }