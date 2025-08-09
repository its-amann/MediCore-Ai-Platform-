"""
Voice Consultation WebSocket Module

This module provides WebSocket functionality for voice consultations using the unified WebSocket manager.
It includes real-time updates for transcription, AI responses, audio processing, and session management.
"""

from .voice_websocket_adapter import (
    VoiceConsultationWebSocketAdapter,
    VoiceConsultationMessageType,
    VoiceWebSocketSession,
    voice_consultation_websocket,
    
    # Convenience functions
    create_voice_session,
    send_transcription_update,
    send_ai_response_update,
    send_audio_processing_update,
    send_error_notification,
    end_voice_session,
    cleanup_voice_websocket
)

__all__ = [
    'VoiceConsultationWebSocketAdapter',
    'VoiceConsultationMessageType', 
    'VoiceWebSocketSession',
    'voice_consultation_websocket',
    'create_voice_session',
    'send_transcription_update',
    'send_ai_response_update',
    'send_audio_processing_update',
    'send_error_notification',
    'end_voice_session',
    'cleanup_voice_websocket'
]