"""
Voice consultation routes using Gemini Live API
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Dict, Any
from datetime import datetime
import uuid

from app.core.database.neo4j_client import Neo4jClient
from app.core.database.models import User
from app.api.routes.auth import get_current_active_user
# from app.core.ai.gemini_voice_service import VoiceSessionManager  # TODO: Module doesn't exist yet
from pydantic import BaseModel

router = APIRouter(prefix="/voice", tags=["voice"])

# Initialize voice session manager
# voice_manager = VoiceSessionManager()  # TODO: Uncomment when module is available
voice_manager = None  # Temporary placeholder

# Request/Response models
class VoiceSessionRequest(BaseModel):
    case_id: str
    doctor_type: str = "general_consultant"

class VoiceProcessRequest(BaseModel):
    session_id: str
    audio_data: str  # Base64 encoded audio

class VoiceSessionResponse(BaseModel):
    session_id: str
    status: str
    doctor_type: str
    created_at: str

class VoiceProcessResponse(BaseModel):
    success: bool
    transcription: str
    response_text: str
    response_audio: str = None
    session_id: str
    timestamp: str

# Dependency to get database client
async def get_database():
    """Get database client dependency"""
    from app.main import get_neo4j_client
    return get_neo4j_client()

@router.post("/session", response_model=VoiceSessionResponse)
async def create_voice_session(
    request: VoiceSessionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Neo4jClient = Depends(get_database)
):
    """Create a new voice consultation session"""
    
    # Verify case ownership
    case_query = """
    MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_id: $case_id})
    RETURN c.case_id as case_id
    """
    
    result = await db.run_query(case_query, {
        "user_id": current_user.user_id,
        "case_id": request.case_id
    })
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or access denied"
        )
    
    # Create voice session
    session = await voice_manager.create_session(
        user_id=current_user.user_id,
        case_id=request.case_id,
        doctor_type=request.doctor_type
    )
    
    return VoiceSessionResponse(**session)

@router.post("/process", response_model=VoiceProcessResponse)
async def process_voice_message(
    request: VoiceProcessRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Process voice message in a session"""
    
    # Get session
    session = voice_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice session not found"
        )
    
    # Process audio
    result = await voice_manager.process_audio(
        session_id=request.session_id,
        audio_data=request.audio_data
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to process voice message")
        )
    
    return VoiceProcessResponse(**result)

@router.post("/session/{session_id}/end")
async def end_voice_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """End a voice session"""
    
    session = voice_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice session not found"
        )
    
    voice_manager.end_session(session_id)
    
    return {
        "message": "Voice session ended successfully",
        "session_id": session_id
    }

@router.post("/sessions")
async def create_voice_session(
    current_user: User = Depends(get_current_active_user),
    db: Neo4jClient = Depends(get_database),
    case_id: str = None
):
    """Create a new voice consultation session"""
    try:
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": current_user.user_id,
            "case_id": case_id,
            "started_at": datetime.utcnow().isoformat(),
            "status": "active",
            "transcript": []
        }
        
        # Store session in database
        query = """
        CREATE (s:VoiceSession $session_data)
        RETURN s
        """
        await db.run_write_query(query, {"session_data": session_data})
        
        return {
            "session_id": session_id,
            "case_id": case_id,
            "started_at": session_data["started_at"],
            "status": "active"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create voice session: {str(e)}"
        )

@router.post("/transcribe")
async def transcribe_audio(
    current_user: User = Depends(get_current_active_user),
    db: Neo4jClient = Depends(get_database),
    audio: UploadFile = File(...),
    session_id: str = Form(None)
):
    """Transcribe audio and get AI response"""
    try:
        # Read audio data
        audio_data = await audio.read()
        
        # TODO: Integrate with actual speech-to-text service
        # For now, return mock data
        transcript_text = "This is a simulated transcript of the user's voice input."
        ai_response = "This is a simulated AI response. In a real implementation, this would be generated based on the user's input and medical context."
        
        # Update session if provided
        if session_id:
            update_query = """
            MATCH (s:VoiceSession {session_id: $session_id})
            SET s.last_activity = $timestamp,
                s.transcript = s.transcript + [{
                    timestamp: $timestamp,
                    user_text: $user_text,
                    ai_response: $ai_response
                }]
            RETURN s
            """
            await db.run_write_query(update_query, {
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "user_text": transcript_text,
                "ai_response": ai_response
            })
        
        return {
            "transcript": transcript_text,
            "ai_response": ai_response,
            "confidence": 0.95,
            "session_id": session_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process audio: {str(e)}"
        )

@router.get("/session/{session_id}")
async def get_session_info(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get voice session information"""
    
    session = voice_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voice session not found"
        )
    
    return session