"""
Input Validation Utilities
Provides validation functions for request data
"""
import re
from typing import Dict, Any, Optional
from uuid import UUID

from ..models import (
    CaseCreate, CaseStatus, CasePriority, 
    ChatRequest, DoctorType
)


def validate_case_data(case_data: CaseCreate) -> Dict[str, Any]:
    """
    Validate and normalize case creation data
    
    Args:
        case_data: Case creation data
        
    Returns:
        Validated and normalized case data
        
    Raises:
        ValueError: If validation fails
    """
    data = case_data.dict()
    
    # Generate title if not provided
    if not data.get("title"):
        # Create title from chief complaint
        chief_complaint = data.get("chief_complaint", "")
        data["title"] = chief_complaint[:50] + "..." if len(chief_complaint) > 50 else chief_complaint
    
    # Generate description if not provided
    if not data.get("description"):
        symptoms_text = ", ".join(data.get("symptoms", []))
        data["description"] = f"Chief complaint: {data.get('chief_complaint')}. Symptoms: {symptoms_text or 'Not specified'}"
    
    # Validate and set priority
    if data.get("priority"):
        try:
            data["priority"] = CasePriority(data["priority"])
        except ValueError:
            raise ValueError(f"Invalid priority: {data['priority']}. Must be one of: {', '.join([p.value for p in CasePriority])}")
    else:
        data["priority"] = CasePriority.MEDIUM
    
    # Validate patient age
    if data.get("patient_age") is not None:
        if not 0 <= data["patient_age"] <= 150:
            raise ValueError("Patient age must be between 0 and 150")
    
    # Validate patient gender
    if data.get("patient_gender"):
        valid_genders = ["male", "female", "other", "prefer_not_to_say"]
        if data["patient_gender"].lower() not in valid_genders:
            raise ValueError(f"Invalid gender. Must be one of: {', '.join(valid_genders)}")
        data["patient_gender"] = data["patient_gender"].lower()
    
    # Validate symptoms list
    if data.get("symptoms"):
        # Remove empty strings and duplicates
        data["symptoms"] = list(set(s.strip() for s in data["symptoms"] if s.strip()))
    
    # Set default status
    data["status"] = CaseStatus.ACTIVE
    
    return data


def validate_chat_request(request: ChatRequest) -> ChatRequest:
    """
    Validate chat request data
    
    Args:
        request: Chat request
        
    Returns:
        Validated chat request
        
    Raises:
        ValueError: If validation fails
    """
    # Validate message
    if not request.message or not request.message.strip():
        raise ValueError("Message cannot be empty")
    
    # Validate message length
    if len(request.message) > 5000:
        raise ValueError("Message cannot exceed 5000 characters")
    
    # Validate doctor type
    if not validate_doctor_type(request.doctor_type):
        raise ValueError(f"Invalid doctor type: {request.doctor_type}")
    
    # Validate session ID if provided
    if request.session_id:
        if not validate_session_id(request.session_id):
            raise ValueError("Invalid session ID format")
    
    # Validate image data if provided
    if request.image_data:
        if not _validate_base64(request.image_data):
            raise ValueError("Invalid image data format")
        
        # Check image size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(request.image_data) > max_size:
            raise ValueError("Image data exceeds maximum size of 10MB")
    
    # Validate audio data if provided
    if request.audio_data:
        if not _validate_base64(request.audio_data):
            raise ValueError("Invalid audio data format")
        
        # Check audio size (max 20MB)
        max_size = 20 * 1024 * 1024  # 20MB
        if len(request.audio_data) > max_size:
            raise ValueError("Audio data exceeds maximum size of 20MB")
    
    # Validate context window
    if request.context_window < 1 or request.context_window > 50:
        raise ValueError("Context window must be between 1 and 50")
    
    return request


def validate_doctor_type(doctor_type: Any) -> bool:
    """
    Validate doctor type
    
    Args:
        doctor_type: Doctor type to validate
        
    Returns:
        True if valid, False otherwise
    """
    if isinstance(doctor_type, str):
        try:
            DoctorType(doctor_type)
            return True
        except ValueError:
            return False
    elif isinstance(doctor_type, DoctorType):
        return True
    return False


def validate_session_id(session_id: str) -> bool:
    """
    Validate session ID format (UUID)
    
    Args:
        session_id: Session ID to validate
        
    Returns:
        True if valid UUID, False otherwise
    """
    try:
        UUID(session_id)
        return True
    except ValueError:
        return False


def _validate_base64(data: str) -> bool:
    """
    Validate base64 encoded data
    
    Args:
        data: Base64 string to validate
        
    Returns:
        True if valid base64, False otherwise
    """
    # Basic base64 validation
    base64_pattern = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
    
    # Remove data URL prefix if present
    if data.startswith('data:'):
        parts = data.split(',', 1)
        if len(parts) == 2:
            data = parts[1]
    
    # Check if it matches base64 pattern
    return bool(base64_pattern.match(data)) and len(data) % 4 == 0


def validate_case_id(case_id: str) -> bool:
    """
    Validate case ID format
    
    Args:
        case_id: Case ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Case IDs should be valid UUIDs or custom format
    if not case_id:
        return False
    
    # Try UUID validation first
    try:
        UUID(case_id)
        return True
    except ValueError:
        # Check custom format (e.g., CASE-YYYYMMDD-XXXX)
        pattern = re.compile(r'^CASE-\d{8}-\d{4}$')
        return bool(pattern.match(case_id))


def validate_priority(priority: str) -> Optional[CasePriority]:
    """
    Validate and convert priority string to enum
    
    Args:
        priority: Priority string
        
    Returns:
        CasePriority enum or None if invalid
    """
    try:
        return CasePriority(priority.lower())
    except (ValueError, AttributeError):
        return None


def validate_status(status: str) -> Optional[CaseStatus]:
    """
    Validate and convert status string to enum
    
    Args:
        status: Status string
        
    Returns:
        CaseStatus enum or None if invalid
    """
    try:
        return CaseStatus(status.lower())
    except (ValueError, AttributeError):
        return None


def normalize_case_data_for_storage(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize case data for storage layer
    
    Args:
        case_data: Case data dictionary
        
    Returns:
        Normalized case data
    """
    # Normalize enums to lowercase strings for Neo4j storage
    if isinstance(case_data.get("status"), (str, CaseStatus)):
        if isinstance(case_data["status"], CaseStatus):
            case_data["status"] = case_data["status"].value
        else:
            case_data["status"] = case_data["status"].lower()
    
    if isinstance(case_data.get("priority"), (str, CasePriority)):
        if isinstance(case_data["priority"], CasePriority):
            case_data["priority"] = case_data["priority"].value
        else:
            case_data["priority"] = case_data["priority"].lower()
    
    # Ensure lists for array fields
    if "symptoms" in case_data and not isinstance(case_data["symptoms"], list):
        case_data["symptoms"] = [case_data["symptoms"]] if case_data["symptoms"] else []
    
    # Add timestamps if missing
    from datetime import datetime
    if "created_at" not in case_data:
        case_data["created_at"] = datetime.utcnow().isoformat()
    if "updated_at" not in case_data:
        case_data["updated_at"] = case_data["created_at"]
    
    return case_data


def normalize_message_data_for_storage(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize message data for storage layer
    
    Args:
        message_data: Message data dictionary
        
    Returns:
        Normalized message data
    """
    # Ensure required fields
    required_fields = ["content", "role"]
    for field in required_fields:
        if field not in message_data:
            raise ValueError(f"Missing required field: {field}")
    
    # Add message ID if missing
    import uuid
    if "message_id" not in message_data:
        message_data["message_id"] = str(uuid.uuid4())
    
    # Add timestamp if missing
    from datetime import datetime
    if "created_at" not in message_data:
        message_data["created_at"] = datetime.utcnow().isoformat()
    
    # Normalize role to lowercase
    if "role" in message_data:
        message_data["role"] = message_data["role"].lower()
    
    return message_data


def validate_case_response(case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and transform case data from database for API response
    
    Args:
        case: Case data from database
        
    Returns:
        Validated case data for API response
    """
    # Convert priority string to enum if needed
    if case.get("priority"):
        priority_str = case["priority"].lower() if isinstance(case["priority"], str) else case["priority"]
        if priority_str in ["low", "medium", "high", "critical"]:
            case["priority"] = CasePriority(priority_str)
        else:
            case["priority"] = CasePriority.MEDIUM
    
    # Convert status string to enum if needed
    if case.get("status"):
        status_str = case["status"].lower() if isinstance(case["status"], str) else case["status"]
        if status_str in ["active", "closed", "archived", "pending"]:
            case["status"] = CaseStatus(status_str)
        else:
            case["status"] = CaseStatus.ACTIVE
    
    return case