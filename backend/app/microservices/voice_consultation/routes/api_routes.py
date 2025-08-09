"""
API Routes for Voice Consultation Service
REST endpoints and WebSocket routes
"""

from fastapi import APIRouter, WebSocket, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import uuid
from ..websocket.voice_websocket_handler import voice_websocket_handler
from ..services.voice_consultation_service import voice_consultation_service
from ..services.audio_processing import audio_processor
from ..agents.voice_agent import get_voice_agent
import base64
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice-consultation", tags=["voice-consultation"])


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time voice consultation"""
    await voice_websocket_handler.handle_websocket(websocket, session_id)


@router.post("/start-session")
async def start_session(user_info: Optional[Dict[str, Any]] = None):
    """Start a new voice consultation session"""
    try:
        session_id = str(uuid.uuid4())
        result = await voice_consultation_service.start_consultation(session_id, user_info)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-audio/{session_id}")
async def process_audio(session_id: str, audio_file: UploadFile = File(...)):
    """Process audio file and get response"""
    try:
        # Read audio file
        audio_data = await audio_file.read()
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Get file format from content type or filename
        format = "wav"
        if audio_file.content_type:
            format = audio_file.content_type.split('/')[-1]
        elif audio_file.filename:
            format = audio_file.filename.split('.')[-1]
        
        # Process audio
        result = await voice_consultation_service.process_audio(
            session_id, audio_base64, format
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-text/{session_id}")
async def process_text(session_id: str, request: Dict[str, str]):
    """Process text input and get response"""
    try:
        text = request.get("text")
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        result = await voice_consultation_service.process_text(session_id, text)
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/set-mode/{session_id}")
async def set_mode(session_id: str, request: Dict[str, str]):
    """Set consultation mode (voice, video, screen_share)"""
    try:
        mode = request.get("mode")
        if not mode:
            raise HTTPException(status_code=400, detail="Mode is required")
        
        result = await voice_consultation_service.set_mode(session_id, mode)
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error setting mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session-info/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a session"""
    try:
        result = await voice_consultation_service.get_session_info(session_id)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/end-session/{session_id}")
async def end_session(session_id: str):
    """End a consultation session"""
    try:
        result = await voice_consultation_service.end_consultation(session_id)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active-sessions")
async def get_active_sessions():
    """Get list of active sessions"""
    try:
        sessions = await voice_consultation_service.get_active_sessions()
        return JSONResponse(content={"sessions": sessions})
    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch-provider")
async def switch_provider(request: Dict[str, Any]):
    """Switch AI provider"""
    try:
        provider = request.get("provider")
        model_id = request.get("model_id")
        
        if not provider:
            raise HTTPException(status_code=400, detail="Provider is required")
        
        result = await voice_consultation_service.switch_provider(provider, model_id)
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Error switching provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-info")
async def get_agent_info():
    """Get current agent configuration"""
    try:
        agent = get_voice_agent()
        info = agent.get_agent_info()
        return JSONResponse(content=info)
    except Exception as e:
        logger.error(f"Error getting agent info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        agent = get_voice_agent()
        agent_info = agent.get_agent_info()
        return JSONResponse(content={
            "status": "healthy",
            "agent_status": agent_info.get("status"),
            "provider": agent_info.get("provider")
        })
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )