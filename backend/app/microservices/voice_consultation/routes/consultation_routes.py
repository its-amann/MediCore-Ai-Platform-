"""
Unified consultation routes for voice and video consultations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database.models import User
from app.api.routes.auth import get_current_active_user
from ..models.consultation_models import (
    ConsultationRequest,
    ConsultationResponse,
    ProviderType
)
from ..services.voice_consultation_service import VoiceConsultationService
from ..services.video_consultation_service import VideoConsultationService
from ..services.ai_providers.ai_provider_service import AIProviderService
from ..services.storage.neo4j_consultation_storage import Neo4jConsultationStorage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/consultations", tags=["consultations"])

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
            _voice_service = VoiceConsultationService(neo4j_client=neo4j_driver)
            logger.info("Voice consultation service initialized with Neo4j client")
        except Exception as e:
            logger.warning(f"Failed to initialize with Neo4j, using limited mode: {e}")
            _voice_service = VoiceConsultationService()
    return _voice_service

def get_video_service() -> VideoConsultationService:
    """Get or create video consultation service"""
    global _video_service
    if _video_service is None:
        _video_service = VideoConsultationService()
    return _video_service

def get_ai_provider_service() -> AIProviderService:
    """Get or create AI provider service"""
    global _ai_provider_service
    if _ai_provider_service is None:
        _ai_provider_service = AIProviderService()
    return _ai_provider_service

def get_storage() -> Neo4jConsultationStorage:
    """Get or create Neo4j storage"""
    global _storage
    if _storage is None:
        try:
            db_manager = get_database_manager()
            neo4j_driver = db_manager.connect_sync() if db_manager else None
            if neo4j_driver:
                _storage = Neo4jConsultationStorage(neo4j_driver)
                logger.info("Neo4j consultation storage initialized")
            else:
                logger.warning("No Neo4j driver available for storage")
        except Exception as e:
            logger.warning(f"Failed to initialize storage: {e}")
    return _storage

# Initialize services
voice_service = get_voice_service()
video_service = get_video_service()
ai_provider_service = get_ai_provider_service()
storage = get_storage()


@router.post("/start", response_model=ConsultationResponse)
@limiter.limit("5/minute")
async def start_consultation(
    request: Request,
    consultation_request: ConsultationRequest,
    current_user: User = Depends(get_current_active_user)
) -> ConsultationResponse:
    """Start a new voice or video consultation"""
    
    try:
        # Validate request
        if consultation_request.consultation_type not in ["voice", "video"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid consultation type: {consultation_request.consultation_type}. Must be 'voice' or 'video'"
            )
        
        # Validate case ownership if case_id provided
        if consultation_request.case_id:
            from app.main import get_neo4j_client
            db = get_neo4j_client()
            if db:
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_id: $case_id})
                RETURN c.case_id as case_id
                """
                result = await db.run_query(query, {
                    "user_id": current_user.user_id,
                    "case_id": consultation_request.case_id
                })
                if not result:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Case not found or access denied"
                    )
            
        # Route to appropriate service
        if consultation_request.consultation_type == "voice":
            logger.info(f"Starting voice consultation for user {current_user.user_id}")
            return await voice_service.create_session(current_user.user_id, consultation_request)
        elif consultation_request.consultation_type == "video":
            logger.info(f"Starting video consultation for user {current_user.user_id}")
            return await video_service.create_session(current_user.user_id, consultation_request)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start consultation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start consultation: {str(e)}"
        )


@router.get("/session/{session_id}")
@limiter.limit("30/minute")
async def get_session_info(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get information about a consultation session"""
    
    # Check voice sessions
    voice_info = await voice_service.get_session_info(session_id)
    if voice_info:
        # Verify ownership
        if voice_info["session"]["user_id"] != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        return voice_info
        
    # Check video sessions
    video_info = await video_service.get_session_info(session_id)
    if video_info:
        # Verify ownership
        if video_info["session"]["user_id"] != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        return video_info
        
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Session not found"
    )


@router.post("/session/{session_id}/end", response_model=ConsultationResponse)
@limiter.limit("10/minute")
async def end_consultation(
    request: Request,
    session_id: str,
    current_user: User = Depends(get_current_active_user)
) -> ConsultationResponse:
    """End a consultation session"""
    
    # Try voice service first
    if session_id in voice_service.active_sessions:
        session = voice_service.active_sessions[session_id]
        if session.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        return await voice_service.end_session(session_id)
        
    # Try video service
    if session_id in video_service.active_sessions:
        session = video_service.active_sessions[session_id]
        if session.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        return await video_service.end_session(session_id)
        
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Session not found"
    )


@router.get("/providers/status")
async def get_providers_status(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get status of all AI providers"""
    
    return {
        "providers": ai_provider_service.get_provider_stats(),
        "available_providers": {
            "voice": ai_provider_service.get_available_providers(require_voice=True),
            "vision": ai_provider_service.get_available_providers(require_vision=True),
            "general": ai_provider_service.get_available_providers()
        }
    }


@router.get("/health")
async def consultation_health_check() -> Dict[str, Any]:
    """Consultation service health check"""
    try:
        # Check service status
        voice_sessions = len(voice_service.active_sessions)
        video_sessions = len(video_service.active_sessions)
        
        # Check database connectivity
        db_status = "disconnected"
        try:
            from app.main import get_neo4j_client
            db = get_neo4j_client()
            if db and db.is_connected():
                db_status = "connected"
        except:
            pass
        
        return {
            "status": "healthy",
            "service": "consultation",
            "active_sessions": {
                "voice": voice_sessions,
                "video": video_sessions,
                "total": voice_sessions + video_sessions
            },
            "database": db_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "service": "consultation",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/health/ready")
async def consultation_readiness_check() -> Dict[str, Any]:
    """Consultation service readiness check"""
    try:
        # Check all required services
        checks = {
            "voice_service": False,
            "video_service": False,
            "ai_providers": False,
            "database": False,
            "storage": False
        }
        
        # Check voice service
        try:
            checks["voice_service"] = hasattr(voice_service, 'active_sessions')
        except:
            pass
        
        # Check video service  
        try:
            checks["video_service"] = hasattr(video_service, 'active_sessions')
        except:
            pass
        
        # Check AI providers
        try:
            providers = ai_provider_service.get_available_providers()
            checks["ai_providers"] = len(providers) > 0
        except:
            pass
        
        # Check database
        try:
            from app.main import get_neo4j_client
            db = get_neo4j_client()
            checks["database"] = db is not None and db.is_connected()
        except:
            pass
        
        # Check storage service
        try:
            checks["storage"] = storage is not None
        except:
            pass
        
        # Determine overall readiness
        all_ready = all(checks.values())
        
        return {
            "ready": all_ready,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}", exc_info=True)
        return {
            "ready": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/history")
async def get_consultation_history(
    current_user: User = Depends(get_current_active_user),
    consultation_type: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get user's consultation history"""
    
    consultations = await storage.get_user_consultations(
        user_id=current_user.user_id,
        limit=limit,
        consultation_type=consultation_type
    )
    
    return consultations


@router.get("/transcript/{consultation_id}")
async def get_consultation_transcript(
    consultation_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get detailed transcript of a consultation"""
    
    # Query for transcript
    query = """
    MATCH (u:User {user_id: $user_id})-[:HAS_TRANSCRIPT]->(t:ConsultationTranscript {consultation_id: $consultation_id})
    
    // Get findings
    OPTIONAL MATCH (t)-[:CONTAINS_FINDING]->(f:Finding)
    WITH t, collect(f.text) as findings
    
    // Get related case
    OPTIONAL MATCH (t)-[:DOCUMENTS]->(c:Case)
    
    RETURN t {
        .*,
        findings: findings,
        case_title: c.title
    } as transcript
    """
    
    from app.main import get_neo4j_client
    db = get_neo4j_client()
    
    result = await db.run_query(query, {
        "user_id": current_user.user_id,
        "consultation_id": consultation_id
    })
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found"
        )
        
    return result[0]["transcript"]


@router.get("/doctor-types")
async def get_available_doctor_types() -> List[Dict[str, str]]:
    """Get available doctor types for consultations"""
    
    return [
        {"id": "general_consultant", "name": "General Consultant", "description": "Primary care and general health concerns"},
        {"id": "cardiologist", "name": "Cardiologist", "description": "Heart and cardiovascular specialist"},
        {"id": "dermatologist", "name": "Dermatologist", "description": "Skin, hair, and nail specialist"},
        {"id": "pediatrician", "name": "Pediatrician", "description": "Child and adolescent health specialist"},
        {"id": "psychiatrist", "name": "Psychiatrist", "description": "Mental health specialist"},
        {"id": "obgyn", "name": "OB/GYN", "description": "Women's health specialist"},
        {"id": "orthopedist", "name": "Orthopedist", "description": "Bone, joint, and muscle specialist"}
    ]


@router.get("/statistics")
async def get_user_consultation_statistics(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get user's consultation statistics"""
    
    query = """
    MATCH (u:User {user_id: $user_id})
    
    // Count consultations by type
    OPTIONAL MATCH (u)-[:PARTICIPATED_IN]->(vc:VoiceConsultation)
    WITH u, count(vc) as voice_count
    
    OPTIONAL MATCH (u)-[:PARTICIPATED_IN]->(vdc:VideoConsultation)
    WITH u, voice_count, count(vdc) as video_count
    
    // Get total duration
    OPTIONAL MATCH (u)-[:PARTICIPATED_IN]->(c)
    WHERE c:VoiceConsultation OR c:VideoConsultation
    WITH u, voice_count, video_count, sum(c.duration_seconds) as total_duration
    
    // Get transcripts
    OPTIONAL MATCH (u)-[:HAS_TRANSCRIPT]->(t:ConsultationTranscript)
    WITH u, voice_count, video_count, total_duration, count(t) as transcript_count
    
    // Get cases with consultations
    OPTIONAL MATCH (u)-[:OWNS]->(case:Case)<-[:RELATES_TO]-(consultation)
    WHERE consultation:VoiceConsultation OR consultation:VideoConsultation
    WITH u, voice_count, video_count, total_duration, transcript_count, 
         count(DISTINCT case) as cases_with_consultations
    
    RETURN {
        voice_consultations: voice_count,
        video_consultations: video_count,
        total_consultations: voice_count + video_count,
        total_duration_seconds: coalesce(total_duration, 0),
        total_transcripts: transcript_count,
        cases_with_consultations: cases_with_consultations,
        average_duration_minutes: CASE 
            WHEN (voice_count + video_count) > 0 
            THEN coalesce(total_duration, 0) / (voice_count + video_count) / 60.0
            ELSE 0
        END
    } as statistics
    """
    
    from app.main import get_neo4j_client
    db = get_neo4j_client()
    
    result = await db.run_query(query, {"user_id": current_user.user_id})
    
    if result and result[0]:
        return result[0]["statistics"]
        
    return {
        "voice_consultations": 0,
        "video_consultations": 0,
        "total_consultations": 0,
        "total_duration_seconds": 0,
        "total_transcripts": 0,
        "cases_with_consultations": 0,
        "average_duration_minutes": 0
    }