"""
Voice Consultation API Routes
REST endpoints and WebSocket integration
Uses shared database manager for Neo4j connections
"""

from fastapi import APIRouter, WebSocket, HTTPException, UploadFile, File, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uuid
import base64
import logging
from datetime import datetime

from ..websocket.voice_websocket_handler import voice_websocket_handler
from ..services.voice_consultation_service import VoiceConsultationService
from ..services.audio_processing import AudioProcessor
from ..agents.voice_agent import get_voice_agent
from app.core.services.database_manager import get_database_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice-consultation"])

# Service instances
voice_service = VoiceConsultationService()
audio_processor = AudioProcessor()

# Request models
class ProcessTextRequest(BaseModel):
    session_id: str
    text: str

class EndSessionRequest(BaseModel):
    session_id: str

# Get shared database manager
def get_db():
    """Get shared database connection"""
    db_manager = get_database_manager()
    driver = db_manager.connect_sync()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )
    return driver


@router.websocket("/ws/{session_id}")
async def websocket_voice_endpoint(websocket: WebSocket, session_id: str, user_id: Optional[str] = None):
    """WebSocket endpoint for real-time voice/video consultation"""
    # Route to the centralized WebSocket handler
    await voice_websocket_handler.handle_websocket(websocket, session_id)


@router.post("/sessions/create", response_model=Dict[str, Any])
async def create_session(
    consultation_type: str = "audio",  # audio, video, screen_share
    user_id: Optional[str] = None
):
    """Create a new voice consultation session"""
    try:
        session_id = f"voice_{uuid.uuid4()}"
        
        # Create user if not provided
        if not user_id:
            user_id = f"user_{uuid.uuid4()}"
        
        # Get shared database connection
        driver = get_db()
        
        # Initialize session in database
        with driver.session() as db_session:
            # First ensure user exists
            db_session.run("""
                MERGE (u:User {user_id: $user_id})
                ON CREATE SET 
                    u.username = $username,
                    u.created_at = datetime(),
                    u.updated_at = datetime(),
                    u.role = 'patient'
                ON MATCH SET
                    u.updated_at = datetime()
            """, user_id=user_id, username=f"user_{user_id[-8:]}")
            
            # Create voice consultation
            result = db_session.run("""
                CREATE (vc:VoiceConsultation {
                    consultation_id: $session_id,
                    user_id: $user_id,
                    type: $consultation_type,
                    status: 'active',
                    mode: $consultation_type,
                    created_at: datetime(),
                    updated_at: datetime(),
                    chat_count: 0,
                    provider: 'groq',
                    model: 'llama-3.3-70b-versatile'
                })
                
                WITH vc
                MATCH (u:User {user_id: $user_id})
                CREATE (u)-[r:HAS_VOICE_CONSULTATION {created_at: datetime()}]->(vc)
                
                RETURN vc.consultation_id as session_id, 
                       vc.status as status,
                       vc.created_at as created_at
            """, session_id=session_id, user_id=user_id, consultation_type=consultation_type)
            
            # Check if session was created
            record = result.single()
            if not record:
                raise Exception("Failed to create session in database")
        
        # Initialize session in voice service
        await voice_service.start_consultation(session_id, {"user_id": user_id})
        
        return {
            "session_id": session_id,
            "status": "created",
            "mode": consultation_type,
            "user_id": user_id,
            "websocket_url": f"/api/v1/voice/consultation/ws/{session_id}"
        }
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.post("/process-audio")
async def process_audio(
    session_id: str,
    audio_file: UploadFile = File(...),
    format: str = "webm"
):
    """Process audio input and return transcription + response"""
    try:
        # Read audio file
        audio_data = await audio_file.read()
        
        # Convert to base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Process with voice service
        result = await voice_service.process_audio(
            session_id=session_id,
            audio_base64=audio_base64,
            format=format
        )
        
        # Store conversation in database
        driver = get_db()
        with driver.session() as db_session:
            # Store user message (transcription)
            if result.get('transcription'):
                db_session.run("""
                    MATCH (vc:VoiceConsultation {consultation_id: $session_id})
                    CREATE (ce:ConversationEntry {
                        entry_id: $entry_id,
                        type: 'user',
                        text: $text,
                        timestamp: datetime(),
                        sequence: vc.chat_count
                    })
                    CREATE (vc)-[:HAS_CONVERSATION {sequence: vc.chat_count}]->(ce)
                    SET vc.chat_count = vc.chat_count + 1,
                        vc.updated_at = datetime()
                """, session_id=session_id, 
                     entry_id=str(uuid.uuid4()),
                     text=result['transcription'])
            
            # Store AI response
            if result.get('response_text'):
                db_session.run("""
                    MATCH (vc:VoiceConsultation {consultation_id: $session_id})
                    CREATE (ce:ConversationEntry {
                        entry_id: $entry_id,
                        type: 'assistant',
                        text: $text,
                        timestamp: datetime(),
                        sequence: vc.chat_count
                    })
                    CREATE (vc)-[:HAS_CONVERSATION {sequence: vc.chat_count}]->(ce)
                    SET vc.chat_count = vc.chat_count + 1,
                        vc.updated_at = datetime()
                """, session_id=session_id,
                     entry_id=str(uuid.uuid4()),
                     text=result['response_text'])
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process audio: {str(e)}"
        )


@router.post("/process-text")
async def process_text(request: ProcessTextRequest):
    """Process text input and return response"""
    try:
        # Process with voice service
        result = await voice_service.process_text(
            session_id=request.session_id,
            text=request.text
        )
        
        # Store conversation in database
        driver = get_db()
        with driver.session() as db_session:
            # Store user message
            db_session.run("""
                MATCH (vc:VoiceConsultation {consultation_id: $session_id})
                CREATE (ce:ConversationEntry {
                    entry_id: $entry_id,
                    type: 'user',
                    text: $text,
                    timestamp: datetime(),
                    sequence: vc.chat_count
                })
                CREATE (vc)-[:HAS_CONVERSATION {sequence: vc.chat_count}]->(ce)
                SET vc.chat_count = vc.chat_count + 1,
                    vc.updated_at = datetime()
            """, session_id=request.session_id,
                 entry_id=str(uuid.uuid4()),
                 text=request.text)
            
            # Store AI response
            if result.get('response_text'):
                db_session.run("""
                    MATCH (vc:VoiceConsultation {consultation_id: $session_id})
                    CREATE (ce:ConversationEntry {
                        entry_id: $entry_id,
                        type: 'assistant',
                        text: $text,
                        timestamp: datetime(),
                        sequence: vc.chat_count
                    })
                    CREATE (vc)-[:HAS_CONVERSATION {sequence: vc.chat_count}]->(ce)
                    SET vc.chat_count = vc.chat_count + 1,
                        vc.updated_at = datetime()
                """, session_id=request.session_id,
                     entry_id=str(uuid.uuid4()),
                     text=result['response_text'])
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process text: {str(e)}"
        )


@router.post("/set-mode")
async def set_mode(
    session_id: str,
    mode: str  # voice, video, screen_share
):
    """Change consultation mode"""
    try:
        result = await voice_service.set_mode(session_id, mode)
        
        # Update in database
        driver = get_db()
        with driver.session() as db_session:
            db_session.run("""
                MATCH (vc:VoiceConsultation {consultation_id: $session_id})
                SET vc.mode = $mode,
                    vc.updated_at = datetime()
            """, session_id=session_id, mode=mode)
        
        return result
        
    except Exception as e:
        logger.error(f"Error setting mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set mode: {str(e)}"
        )


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get session information including conversation history"""
    try:
        driver = get_db()
        with driver.session() as db_session:
            # Get session info
            result = db_session.run("""
                MATCH (vc:VoiceConsultation {consultation_id: $session_id})
                OPTIONAL MATCH (vc)-[:HAS_CONVERSATION]->(ce:ConversationEntry)
                WITH vc, ce
                ORDER BY ce.sequence
                RETURN vc.consultation_id as session_id,
                       vc.status as status,
                       vc.mode as mode,
                       vc.created_at as created_at,
                       vc.chat_count as chat_count,
                       collect({
                           type: ce.type,
                           text: ce.text,
                           timestamp: ce.timestamp,
                           sequence: ce.sequence
                       }) as conversation_history
            """, session_id=session_id)
            
            record = result.single()
            if not record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            
            return {
                "session_id": record["session_id"],
                "status": record["status"],
                "mode": record["mode"],
                "created_at": record["created_at"],
                "chat_count": record["chat_count"],
                "conversation_history": [
                    entry for entry in record["conversation_history"] 
                    if entry["type"] is not None
                ]
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session info: {str(e)}"
        )


@router.post("/end")
async def end_session(request: EndSessionRequest):
    """End a consultation session"""
    try:
        # End in voice service
        result = await voice_service.end_consultation(request.session_id)
        
        # Update in database
        driver = get_db()
        with driver.session() as db_session:
            db_session.run("""
                MATCH (vc:VoiceConsultation {consultation_id: $session_id})
                SET vc.status = 'completed',
                    vc.ended_at = datetime(),
                    vc.updated_at = datetime()
            """, session_id=request.session_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {str(e)}"
        )


@router.post("/switch-provider")
async def switch_provider(
    session_id: str,
    provider: str,
    model: Optional[str] = None
):
    """Switch AI provider for the session"""
    try:
        # Switch provider at the agent/service level (global agent in current design)
        result = await voice_service.switch_provider(provider, model)
        
        # Update in database for the specific session
        driver = get_db()
        with driver.session() as db_session:
            db_session.run("""
                MATCH (vc:VoiceConsultation {consultation_id: $session_id})
                SET vc.provider = $provider,
                    vc.model = $model,
                    vc.updated_at = datetime()
            """, session_id=session_id, provider=provider, model=model)
        
        # Attach session_id for client context
        result["session_id"] = session_id
        return result
        
    except Exception as e:
        logger.error(f"Error switching provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to switch provider: {str(e)}"
        )


@router.get("/active-sessions")
async def get_active_sessions() -> Dict[str, Any]:
    """Return list of active session IDs"""
    try:
        sessions = await voice_service.get_active_sessions()
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active sessions"
        )


@router.get("/agent-info")
async def get_agent_info():
    """Get information about the voice agent"""
    try:
        agent = get_voice_agent()
        return {
            "provider": agent.provider,
            "model_id": agent.model_id,
            "tools": [tool.name for tool in agent.tools],
            "status": "ready"
        }
    except Exception as e:
        logger.error(f"Error getting agent info: {e}")
        return {
            "provider": None,
            "model_id": None,
            "tools": [],
            "status": f"error: {str(e)}"
        }