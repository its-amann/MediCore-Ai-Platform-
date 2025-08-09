"""
Database models for the application
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, validator, root_validator, model_validator
from enum import Enum


# User Models
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None


class User(UserBase):
    user_id: str
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    role: str = "patient"
    preferences: Dict[str, Any] = {}
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password_hash: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


# Authentication Models
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 3600


class TokenData(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None


# Doctor and Consultation Models
class DoctorSpecialty(str, Enum):
    CARDIOLOGIST = "cardiologist"
    BP_SPECIALIST = "bp_specialist"  
    GENERAL_CONSULTANT = "general_consultant"


class Doctor(BaseModel):
    doctor_id: str
    name: str
    specialty: DoctorSpecialty
    description: Optional[str] = None
    availability: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None


class DoctorConsultationRequest(BaseModel):
    message: str = Field(..., description="User's message or symptoms")
    case_id: str = Field(..., description="Case ID for the consultation")
    image_data: Optional[str] = Field(None, description="Base64 encoded image data")
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio data")
    specialty: Optional[str] = Field(None, description="Doctor specialty to consult")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    additional_context: Optional[str] = Field(None, description="Additional medical context")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @model_validator(mode='before')
    @classmethod
    def validate_and_transform_message(cls, values):
        """Transform various message field names to 'message'"""
        if not isinstance(values, dict):
            return values
            
        # Get message from various possible field names
        message = values.get('message')
        user_message = values.get('user_message')
        symptoms = values.get('symptoms')
        
        # Determine the actual message content
        final_message = message or user_message or symptoms or ""
        
        # Set the message field
        values['message'] = final_message
        
        # Remove alternative field names to avoid confusion
        values.pop('user_message', None)
        values.pop('symptoms', None)
            
        return values
    
    def get_message(self) -> str:
        """Get the message content"""
        return self.message or ""


class DoctorConsultationResponse(BaseModel):
    consultation_id: str
    doctor_specialty: DoctorSpecialty
    response: str  # Changed from doctor_response to response
    analysis: Optional['Analysis'] = None  # Added analysis field
    recommendations: Optional[List[str]] = None
    follow_up_questions: Optional[List[str]] = None  # Added follow_up_questions
    confidence_score: float = 0.8  # Added confidence_score
    processing_time: float = 0.0  # Added processing_time
    session_id: Optional[str] = None  # Added session_id


# Analysis Models
class AnalysisType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    MULTIMODAL = "multimodal"


class Analysis(BaseModel):
    analysis_id: str
    case_id: str
    user_id: str
    analysis_type: AnalysisType
    content: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class AnalysisCreate(BaseModel):
    case_id: str
    analysis_type: AnalysisType
    content: Dict[str, Any]


# Chat History Models
class ChatType(str, Enum):
    DOCTOR_CONSULTATION = "doctor_consultation"
    GENERAL_CHAT = "general_chat"
    CASE_DISCUSSION = "case_discussion"


class ChatHistory(BaseModel):
    chat_id: str
    user_id: str
    case_id: Optional[str] = None
    chat_type: ChatType
    messages: List[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime] = None


# Room Models
class RoomType(str, Enum):
    CASE_DISCUSSION = "case_discussion"
    TEACHING = "teaching"
    EDUCATION = "education"
    RESEARCH = "research"


class Room(BaseModel):
    room_id: str
    name: str
    room_type: RoomType
    owner_id: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    participants: List[str] = []


class RoomCreate(BaseModel):
    name: str
    room_type: RoomType
    description: Optional[str] = None


# Invitation Models
class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class Invitation(BaseModel):
    invitation_id: str
    room_id: str
    inviter_id: str
    invitee_email: str
    status: InvitationStatus = InvitationStatus.PENDING
    created_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime] = None


class InvitationCreate(BaseModel):
    room_id: str
    invitee_email: EmailStr


# Error Response Model
class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Media Models
class Media(BaseModel):
    media_id: str
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    file_hash: str
    user_id: str
    case_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class MediaCreate(BaseModel):
    filename: str
    file_size: int
    mime_type: str
    case_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None