"""
Core components for voice consultation microservice
"""

from .models.consultation_models import (
    VoiceSession,
    ConsultationStatus,
    TranscriptEntry,
    MessageType,
    ProviderType,
    ConsultationRequest,
    ConsultationResponse
)

from .prompts.consultation_prompts import get_doctor_prompt

__all__ = [
    "VoiceSession",
    "ConsultationStatus", 
    "TranscriptEntry",
    "MessageType",
    "ProviderType",
    "ConsultationRequest",
    "ConsultationResponse",
    "get_doctor_prompt"
]