"""
Case-related Models
Data models for medical case management
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CaseStatus(str, Enum):
    """Case status enumeration"""
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"
    PENDING = "pending"


class CasePriority(str, Enum):
    """Case priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseBase(BaseModel):
    """Base case model with common fields"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    chief_complaint: str = Field(..., min_length=1, max_length=500)
    symptoms: List[str] = Field(default_factory=list)
    priority: CasePriority = CasePriority.MEDIUM
    patient_age: Optional[int] = Field(None, ge=0, le=150)
    patient_gender: Optional[str] = None
    past_medical_history: Optional[str] = None
    current_medications: Optional[str] = None
    allergies: Optional[str] = None
    medical_category: Optional[str] = None


class CaseCreate(BaseModel):
    """Model for creating a new case"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    chief_complaint: str = Field(..., min_length=1, max_length=500)
    symptoms: List[str] = Field(default_factory=list)
    priority: Optional[str] = None
    past_medical_history: Optional[str] = None
    current_medications: Optional[str] = None
    allergies: Optional[str] = None
    medical_category: Optional[str] = None
    patient_age: Optional[int] = Field(None, ge=0, le=150)
    patient_gender: Optional[str] = None


class CaseUpdate(BaseModel):
    """Model for updating a case"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CaseStatus] = None
    priority: Optional[CasePriority] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    outcome: Optional[str] = None


class CaseResponse(BaseModel):
    """Case response model with all fields"""
    case_id: str
    case_number: Optional[str] = None
    user_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    chief_complaint: str
    symptoms: List[str]
    status: CaseStatus
    priority: CasePriority
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    past_medical_history: Optional[str] = None
    current_medications: Optional[str] = None
    allergies: Optional[str] = None
    medical_category: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    outcome: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    chat_sessions: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CaseData(BaseModel):
    """Case data model for internal use"""
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    chief_complaint: str
    symptoms: List[str] = Field(default_factory=list)
    status: CaseStatus = CaseStatus.ACTIVE
    priority: CasePriority = CasePriority.MEDIUM
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    past_medical_history: Optional[str] = None
    current_medications: Optional[str] = None
    allergies: Optional[str] = None
    medical_category: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    outcome: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    user_id: Optional[str] = None
    case_number: Optional[str] = None
    chat_sessions: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CaseReportRequest(BaseModel):
    """Case report generation request"""
    case_id: str
    session_id: str
    include_sections: List[str] = Field(
        default_factory=lambda: [
            "chief_complaint",
            "symptoms_analysis",
            "conversation_summary",
            "diagnosis_discussion",
            "treatment_recommendations",
            "follow_up_plan"
        ]
    )
    format: str = "markdown"  # markdown, pdf, html


# Alias for backward compatibility
class Case(CaseData):
    """Alias for backward compatibility"""
    pass