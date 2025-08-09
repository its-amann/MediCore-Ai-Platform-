"""
Doctor and Media Models
Data models for AI doctors and media handling
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class DoctorType(str, Enum):
    """Available AI doctor types"""
    GENERAL = "general_consultant"
    CARDIOLOGIST = "cardiologist"
    BP_SPECIALIST = "bp_specialist"


class DoctorProfile(BaseModel):
    """Doctor profile configuration"""
    doctor_type: DoctorType
    name: str
    specialty: str
    description: str
    personality_traits: List[str]
    expertise_areas: List[str]
    response_style: str = "professional"
    model_name: str
    temperature: float = 0.3
    max_tokens: int = 500


class MediaData(BaseModel):
    """Media data model for images and audio"""
    media_type: str  # "image" or "audio"
    mime_type: str
    size: int
    data: Optional[str] = None  # Base64 encoded
    url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)