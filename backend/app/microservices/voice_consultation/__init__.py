"""
Voice Consultation Microservice
Modern voice and video consultation system with multi-provider AI support
"""

# Only import what actually exists
from .services.voice_consultation_service import VoiceConsultationService

__all__ = [
    'VoiceConsultationService'
]