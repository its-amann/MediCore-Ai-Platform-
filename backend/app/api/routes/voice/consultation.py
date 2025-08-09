"""
Unified consultation routes for voice and video consultations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database.models import User
from app.api.routes.auth import get_current_active_user, get_current_user
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import uuid
from app.microservices.voice_consultation.models.consultation_models import (
    ConsultationRequest,
    ConsultationResponse,
    ProviderType
)
from app.microservices.voice_consultation.services.voice_consultation_service import VoiceConsultationService
# Comment out non-existent imports for now
# from app.microservices.voice_consultation.services.video_consultation_service import VideoConsultationService
# from app.microservices.voice_consultation.services.ai_providers.ai_provider_service import AIProviderService
# from app.microservices.voice_consultation.services.storage.neo4j_consultation_storage import Neo4jConsultationStorage

logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice-consultations"])

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Import database manager
from app.core.services.database_manager import get_database_manager

# Service instances
_voice_service = None
_video_service = None
_ai_provider_service = None
_storage = None

def get_voice_service() -> VoiceConsultationService:
    """Get or create voice consultation service with Neo4j client"""
    global _voice_service
    if _voice_service is None:
        try:
            db_manager = get_database_manager()
            neo4j_driver = db_manager.connect_sync() if db_manager else None
            if neo4j_driver:
                # Create a Neo4jClient wrapper
                from app.core.database.neo4j_client import Neo4jClient
                neo4j_client = Neo4jClient()
                neo4j_client.driver = neo4j_driver
                _voice_service = VoiceConsultationService(neo4j_client=neo4j_client)
                logger.info("Voice consultation service initialized with Neo4j client")
            else:
                _voice_service = VoiceConsultationService()
                logger.warning("No Neo4j driver available, using limited mode")
        except Exception as e:
            logger.warning(f"Failed to initialize with Neo4j, using limited mode: {e}")
            _voice_service = VoiceConsultationService()
    return _voice_service

def get_video_service():
    """Get or create video consultation service - stub for now"""
    global _video_service
    if _video_service is None:
        # Return a stub object for now
        class VideoStub:
            active_sessions = {}
            async def create_session(self, user_id, request):
                from app.microservices.voice_consultation.models.consultation_models import ConsultationResponse
                return ConsultationResponse(
                    session_id="video-stub",
                    status="error",
                    message="Video consultation not yet implemented"
                )
            async def end_session(self, session_id):
                from app.microservices.voice_consultation.models.consultation_models import ConsultationResponse
                return ConsultationResponse(
                    session_id=session_id,
                    status="ended",
                    message="Session ended"
                )
        _video_service = VideoStub()
    return _video_service

def get_ai_provider_service():
    """Get or create AI provider service - stub for now"""
    global _ai_provider_service
    if _ai_provider_service is None:
        # Return a stub object for now
        class AIProviderStub:
            async def get_providers_status(self):
                return {
                    "providers": {
                        "gemini": {"status": "available", "models": ["gemini-pro"]},
                        "groq": {"status": "available", "models": ["llama3-8b-8192"]}
                    },
                    "default": "gemini"
                }
        _ai_provider_service = AIProviderStub()
    return _ai_provider_service

def get_storage():
    """Get storage service if available - stub for now"""
    global _storage
    if _storage is None:
        # Return a stub object for now
        class StorageStub:
            async def get_user_sessions(self, user_id, consultation_type=None, status=None, limit=50):
                return []
            async def get_session(self, session_id):
                return None
            async def get_consultation_transcript(self, session_id):
                return None
        _storage = StorageStub()
        logger.warning("Using stub storage service")
    return _storage


async def get_current_user_optional() -> User:
    """Get current user or create anonymous user for development"""
    # Check if authentication is disabled
    auth_required = os.getenv('WS_AUTH_REQUIRED', 'true').lower() == 'true'
    
    if not auth_required:
        # Create anonymous user for development
        # Use a consistent anonymous ID for the session
        anonymous_id = str(uuid.uuid4())
        from datetime import datetime
        return User(
            user_id=f"anonymous_{anonymous_id}",
            username="anonymous",
            email=f"anonymous_{anonymous_id}@test.com",
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            role="patient",
            preferences={}
        )
    
    # If auth is required, try to get the current user
    try:
        # This will raise an exception if no valid token
        from app.core.database.neo4j_client import get_database
        db = await get_database()
        # Try to get user from Bearer token
        credentials = HTTPBearer()
        # This is a simplified approach - in production you'd properly handle auth
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )


@router.post("/create", response_model=ConsultationResponse)
@limiter.limit("100/minute")  # Increased from 10 to 100 for testing
async def create_consultation(
    request: Request,
    consultation_request: ConsultationRequest,
    current_user: User = Depends(get_current_active_user),  # Use proper authentication
    voice_service: VoiceConsultationService = Depends(get_voice_service),
    video_service = Depends(get_video_service)
):
    """Create a new consultation session (voice or video)"""
    try:
        if consultation_request.consultation_type == "voice":
            # Always use the authenticated user's ID
            user_id = current_user.user_id
            return await voice_service.create_session(
                consultation_request,
                user_id
            )
        elif consultation_request.consultation_type == "video":
            # Always use the authenticated user's ID
            user_id = current_user.user_id
            return await video_service.create_session(
                user_id,
                consultation_request
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid consultation type: {consultation_request.consultation_type}"
            )
            
    except Exception as e:
        logger.error(f"Error creating consultation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create consultation: {str(e)}"
        )


@router.get("/sessions", response_model=List[Dict[str, Any]])
async def get_user_sessions(
    consultation_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    storage = Depends(get_storage)
):
    """Get user's consultation sessions"""
    try:
        if not storage:
            return []
            
        sessions = await storage.get_user_sessions(
            user_id=current_user.user_id,
            consultation_type=consultation_type,
            status=status,
            limit=limit
        )
        
        return sessions
        
    except Exception as e:
        logger.error(f"Error getting sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sessions: {str(e)}"
        )


@router.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session_details(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    storage = Depends(get_storage)
):
    """Get detailed information about a specific session"""
    try:
        if not storage:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service unavailable"
            )
            
        session = await storage.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
            
        # Verify user owns this session
        if session.get("user_id") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
            
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session: {str(e)}"
        )


@router.post("/sessions/{session_id}/end", response_model=ConsultationResponse)
async def end_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    voice_service: VoiceConsultationService = Depends(get_voice_service),
    video_service = Depends(get_video_service),
    storage = Depends(get_storage)
):
    """End a consultation session"""
    try:
        # Get session to determine type
        if storage:
            session = await storage.get_session(session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
                
            # Verify user owns this session
            if session.get("user_id") != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
                
            # End session based on type
            if session.get("consultation_type") == "voice":
                return await voice_service.end_session(session_id)
            else:
                return await video_service.end_session(session_id)
        else:
            # Try both services if storage unavailable
            if session_id in voice_service.active_sessions:
                return await voice_service.end_session(session_id)
            elif session_id in video_service.active_sessions:
                return await video_service.end_session(session_id)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {str(e)}"
        )


@router.get("/providers", response_model=Dict[str, Any])
async def get_available_providers(
    current_user: User = Depends(get_current_active_user),
    ai_provider_service = Depends(get_ai_provider_service)
):
    """Get available AI providers and their status"""
    try:
        status = await ai_provider_service.get_providers_status()
        return status
        
    except Exception as e:
        logger.error(f"Error getting providers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get providers: {str(e)}"
        )


@router.get("/transcripts/{session_id}", response_model=Dict[str, Any])
async def get_session_transcript(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    storage = Depends(get_storage)
):
    """Get transcript for a completed session"""
    try:
        if not storage:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service unavailable"
            )
            
        # Get session first to verify ownership
        session = await storage.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
            
        # Verify user owns this session
        if session.get("user_id") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
            
        # Get transcript
        transcript = await storage.get_consultation_transcript(session_id)
        
        if not transcript:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript not found"
            )
            
        return transcript
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transcript: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve transcript: {str(e)}"
        )