"""
Chat and Message Models
Data models for chat sessions and messages
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from .doctor_models import DoctorType


class ChatSessionType(str, Enum):
    """Types of chat sessions"""
    SINGLE_DOCTOR = "single_doctor"
    MULTI_DOCTOR = "multi_doctor"
    CONSULTATION = "consultation"


class MessageType(str, Enum):
    """Types of messages in chat"""
    USER_MESSAGE = "user_message"
    DOCTOR_RESPONSE = "doctor_response"
    SYSTEM_NOTIFICATION = "system_notification"
    TYPING_INDICATOR = "typing_indicator"
    ERROR_MESSAGE = "error_message"
    MEDIA_UPLOAD = "media_upload"
    DIAGNOSIS = "diagnosis"
    TREATMENT_PLAN = "treatment_plan"
    PRESCRIPTION = "prescription"
    LAB_REQUEST = "lab_request"
    DIAGNOSIS_SUMMARY = "diagnosis_summary"


class ChatMessage(BaseModel):
    """Individual chat message model"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    case_id: str
    user_id: str
    user_message: str
    doctor_type: str
    doctor_response: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MessageCreate(BaseModel):
    """Model for creating a new message"""
    session_id: str
    case_id: str
    user_id: str
    content: str
    message_type: MessageType = MessageType.USER_MESSAGE
    doctor_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatSession(BaseModel):
    """Chat session model"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    user_id: str
    session_type: ChatSessionType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: Optional[datetime] = None
    is_active: bool = True
    participating_doctors: List[str] = Field(default_factory=list)
    message_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    doctor_type: DoctorType
    session_id: Optional[str] = None
    image_data: Optional[str] = None  # Base64 encoded
    audio_data: Optional[str] = None  # Base64 encoded
    context_window: int = Field(default=10, ge=1, le=50)


class ChatResponse(BaseModel):
    """Chat response model"""
    session_id: str
    message_id: str
    doctor_response: str
    doctor_type: str
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)
    processing_time: float
    context_used: int
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HandoverRequest(BaseModel):
    """Doctor handover request model"""
    session_id: str
    from_doctor: DoctorType
    to_doctor: DoctorType
    handover_message: Optional[str] = None
    include_full_history: bool = True