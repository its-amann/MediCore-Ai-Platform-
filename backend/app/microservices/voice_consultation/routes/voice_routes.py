"""
Voice-specific consultation routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from typing import Dict, Any, Optional
from datetime import datetime
import base64
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database.models import User
from app.api.routes.auth import get_current_active_user
from ..models.consultation_models import ConsultationResponse
from ..services.voice_consultation_service import VoiceConsultationService
from app.core.services.database_manager import get_database_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice-consultation"])

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Service instance
_voice_service = None

def get_voice_service() -> VoiceConsultationService:
    """Get or create voice consultation service with Neo4j client"""
    global _voice_service
    if _voice_service is None:
        try:
            db_manager = get_database_manager()
            neo4j_driver = db_manager.connect_sync() if db_manager else None
            _voice_service = VoiceConsultationService(neo4j_client=neo4j_driver)
            logger.info("Voice consultation service initialized with Neo4j client")
        except Exception as e:
            logger.warning(f"Failed to initialize with Neo4j, using limited mode: {e}")
            _voice_service = VoiceConsultationService()
    return _voice_service

# For backward compatibility
voice_service = get_voice_service()


@router.post("/session/{session_id}/audio", response_model=ConsultationResponse)
@limiter.limit("30/minute")
async def process_voice_audio(
    request: Request,
    session_id: str,
    audio: UploadFile = File(...),
    format: str = Form("webm"),
    current_user: User = Depends(get_current_active_user)
) -> ConsultationResponse:
    """Process audio input in a voice session"""
    
    try:
        # Validate audio file
        if not audio.content_type or not audio.content_type.startswith(('audio/', 'video/')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid audio file type"
            )
        
        # Verify session ownership
        if session_id not in voice_service.active_sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
            
        session = voice_service.active_sessions[session_id]
        if session.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
            
        # Read audio data
        audio_data = await audio.read()
        
        # Validate audio size (10MB limit)
        if len(audio_data) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Audio file too large. Maximum size is 10MB"
            )
        
        logger.info(f"Processing audio for session {session_id}, size: {len(audio_data)} bytes")
        
        # Process audio
        return await voice_service.process_audio(session_id, audio_data, format)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process audio: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process audio: {str(e)}"
        )


@router.post("/session/{session_id}/audio-base64", response_model=ConsultationResponse)
@limiter.limit("30/minute")
async def process_voice_audio_base64(
    request: Request,
    session_id: str,
    audio_data: str = Form(...),
    format: str = Form("webm"),
    current_user: User = Depends(get_current_active_user)
) -> ConsultationResponse:
    """Process base64-encoded audio input"""
    
    # Verify session ownership
    if session_id not in voice_service.active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
        
    session = voice_service.active_sessions[session_id]
    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
        
    # Decode base64 audio
    try:
        audio_bytes = base64.b64decode(audio_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 audio data: {str(e)}"
        )
        
    # Process audio
    return await voice_service.process_audio(session_id, audio_bytes, format)


@router.post("/session/{session_id}/text", response_model=ConsultationResponse)
@limiter.limit("60/minute")
async def process_text_input(
    request: Request,
    session_id: str,
    text: str = Form(...),
    current_user: User = Depends(get_current_active_user)
) -> ConsultationResponse:
    """Process text input in a voice session"""
    
    # Verify session ownership
    if session_id not in voice_service.active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
        
    session = voice_service.active_sessions[session_id]
    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
        
    # Process text
    return await voice_service.process_text(session_id, text)


@router.get("/session/{session_id}/transcript")
async def get_session_transcript(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get current transcript of a voice session"""
    
    # Verify session ownership
    if session_id not in voice_service.active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
        
    session = voice_service.active_sessions[session_id]
    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
        
    # Return transcript
    return {
        "session_id": session_id,
        "transcript": [entry.dict() for entry in session.transcript],
        "duration_seconds": session.duration_seconds,
        "status": session.status.value
    }


@router.post("/session/{session_id}/pause")
async def pause_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """Pause a voice session"""
    
    # Verify session ownership
    if session_id not in voice_service.active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
        
    session = voice_service.active_sessions[session_id]
    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
        
    # Update status
    from ..models.consultation_models import ConsultationStatus
    session.status = ConsultationStatus.PAUSED
    
    return {
        "message": "Session paused",
        "session_id": session_id,
        "status": session.status.value
    }


@router.post("/session/{session_id}/resume")
async def resume_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """Resume a paused voice session"""
    
    # Verify session ownership
    if session_id not in voice_service.active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
        
    session = voice_service.active_sessions[session_id]
    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
        
    # Update status
    from ..models.consultation_models import ConsultationStatus
    if session.status == ConsultationStatus.PAUSED:
        session.status = ConsultationStatus.ACTIVE
        
    return {
        "message": "Session resumed",
        "session_id": session_id,
        "status": session.status.value
    }


@router.get("/health")
async def voice_health_check() -> Dict[str, Any]:
    """Voice consultation service health check"""
    try:
        # Check service status
        active_sessions = len(voice_service.active_sessions)
        
        # Check AI provider status
        from ..services.ai_providers.ai_provider_service import AIProviderService
        ai_service = AIProviderService()
        provider_status = ai_service.get_provider_stats()
        
        return {
            "status": "healthy",
            "service": "voice-consultation",
            "active_sessions": active_sessions,
            "providers": {
                "available": len([p for p in provider_status if p["enabled"]]),
                "total": len(provider_status)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "service": "voice-consultation",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/health/detailed")
async def voice_detailed_health_check(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Detailed voice consultation service health check"""
    try:
        # Check service components
        from ..services.ai_providers.ai_provider_service import AIProviderService
        from ..services.audio.whisper.audio_processing_service import AudioProcessingService
        from ..services.monitoring.rate_limiter_service import RateLimiterService
        
        ai_service = AIProviderService()
        audio_service = AudioProcessingService()
        rate_limiter = RateLimiterService()
        
        # Get detailed stats
        active_sessions = voice_service.active_sessions
        session_stats = {
            "total": len(active_sessions),
            "by_status": {},
            "by_provider": {}
        }
        
        for session_id, session in active_sessions.items():
            # Count by status
            status = session.status.value
            session_stats["by_status"][status] = session_stats["by_status"].get(status, 0) + 1
            
            # Count by provider
            provider = session.ai_provider.value
            session_stats["by_provider"][provider] = session_stats["by_provider"].get(provider, 0) + 1
        
        return {
            "status": "healthy",
            "service": "voice-consultation",
            "components": {
                "voice_service": "healthy",
                "ai_providers": ai_service.get_provider_stats(),
                "audio_processing": {
                    "status": "healthy",
                    "supported_formats": audio_service.supported_formats
                },
                "rate_limiter": {
                    "status": "healthy",
                    "current_usage": rate_limiter.get_usage_stats()
                }
            },
            "sessions": session_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )