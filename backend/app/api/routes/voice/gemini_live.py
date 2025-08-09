"""
API routes for Gemini Live voice consultation
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
import json
import asyncio
from datetime import datetime
import base64

from app.api.routes.auth import get_current_user, get_current_active_user
from app.core.database.models import User
from app.microservices.voice_consultation.models.consultation_models import (
    ConsultationRequest,
    ConsultationResponse,
    ConsultationStatus
)
from app.microservices.voice_consultation.services.ai_providers.gemini.agents import (
    create_medical_agent,
    create_voice_consultation_graph
)
from app.microservices.voice_consultation.services.ai_providers.gemini.websocket_handler import (
    GeminiLiveStreamManager,
    GeminiLiveWebSocketHandler
)
from app.microservices.voice_consultation.services.ai_providers.gemini.config import (
    ConsultationMode,
    GeminiLiveConfig
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice-gemini-live"])

# Global stream manager
stream_manager = GeminiLiveStreamManager(
    config=GeminiLiveConfig(api_key=settings.gemini_api_key)
)


@router.post("/session", response_model=Dict[str, Any])
async def create_gemini_live_session(
    request: ConsultationRequest,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Create a new Gemini Live consultation session"""
    try:
        # Generate session ID
        session_id = f"gemini_live_{current_user.user_id}_{datetime.utcnow().timestamp()}"
        
        # Determine consultation mode
        mode = ConsultationMode.VOICE_AND_VIDEO if request.consultation_type == "video" else ConsultationMode.VOICE_ONLY
        
        # Create callbacks for WebSocket events
        callbacks = {
            "on_transcription": lambda data: logger.info(f"Transcription: {data}"),
            "on_response": lambda data: logger.info(f"Response: {data['type']}"),
            "on_error": lambda error: logger.error(f"Gemini Live error: {error}")
        }
        
        # Create session through stream manager
        handler = await stream_manager.create_session(
            session_id=session_id,
            user_id=str(current_user.user_id),
            mode=mode,
            callbacks=callbacks
        )
        
        if not handler:
            raise HTTPException(status_code=500, detail="Failed to create Gemini Live session")
        
        return {
            "session_id": session_id,
            "status": "created",
            "mode": mode.value,
            "specialization": request.doctor_type,
            "websocket_url": f"/ws/voice/gemini-live/{session_id}"
        }
        
    except Exception as e:
        logger.error(f"Error creating Gemini Live session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/{session_id}")
async def gemini_live_websocket(
    websocket: WebSocket,
    session_id: str
):
    """WebSocket endpoint for Gemini Live streaming"""
    await websocket.accept()
    
    try:
        # Get session handler
        handler = await stream_manager.get_session(session_id)
        if not handler:
            await websocket.send_json({
                "type": "error",
                "message": "Session not found"
            })
            await websocket.close()
            return
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Update callbacks to send data through WebSocket
        async def on_transcription(data):
            await websocket.send_json({
                "type": "transcription",
                "data": data
            })
        
        async def on_response(data):
            await websocket.send_json({
                "type": "response",
                "data": data
            })
        
        async def on_error(error):
            await websocket.send_json({
                "type": "error",
                "message": error
            })
        
        # Update handler callbacks
        handler.on_transcription = on_transcription
        handler.on_response = on_response
        handler.on_error = on_error
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                
                if data["type"] == "audio_chunk":
                    # Decode audio data
                    audio_data = base64.b64decode(data["data"])
                    await handler.send_audio_chunk(audio_data)
                
                elif data["type"] == "video_frame":
                    # Decode video frame
                    frame_data = base64.b64decode(data["data"])
                    await handler.send_video_frame(frame_data)
                
                elif data["type"] == "text_message":
                    # Send text message
                    await handler.send_text_message(data["text"])
                
                elif data["type"] == "enable_video":
                    # Update consultation mode
                    if handler.agent:
                        handler.agent.state.consultation_mode = ConsultationMode.VOICE_AND_VIDEO
                    await websocket.send_json({
                        "type": "video_enabled",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif data["type"] == "disable_video":
                    # Update consultation mode
                    if handler.agent:
                        handler.agent.state.consultation_mode = ConsultationMode.VOICE_ONLY
                    await websocket.send_json({
                        "type": "video_disabled",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif data["type"] == "end_session":
                    break
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
                break
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                await on_error(str(e))
        
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        # Clean up session
        await stream_manager.end_session(session_id)
        await websocket.close()


@router.get("/session/{session_id}/status")
async def get_session_status(
    session_id: str,
    current_user=Depends(get_current_user)
) -> Dict[str, Any]:
    """Get status of a Gemini Live session"""
    try:
        handler = await stream_manager.get_session(session_id)
        
        if not handler:
            return {
                "session_id": session_id,
                "status": "not_found",
                "active": False
            }
        
        return {
            "session_id": session_id,
            "status": "active" if handler.is_connected else "disconnected",
            "active": handler.is_connected,
            "mode": handler.agent.state.consultation_mode.value if handler.agent else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting session status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/end")
async def end_gemini_live_session(
    session_id: str,
    current_user=Depends(get_current_user)
) -> Dict[str, Any]:
    """End a Gemini Live consultation session"""
    try:
        handler = await stream_manager.get_session(session_id)
        
        if not handler:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate consultation report
        if handler.agent:
            report = await handler.agent.end_consultation(
                session_id=session_id,
                state=handler.agent.state
            )
        else:
            report = None
        
        # End session
        await stream_manager.end_session(session_id)
        
        return {
            "session_id": session_id,
            "status": "ended",
            "report": report,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error ending session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/interrupt")
async def interrupt_response(
    session_id: str,
    current_user=Depends(get_current_user)
) -> Dict[str, Any]:
    """Interrupt current Gemini Live response"""
    try:
        handler = await stream_manager.get_session(session_id)
        
        if not handler:
            raise HTTPException(status_code=404, detail="Session not found")
        
        await handler.interrupt_response()
        
        return {
            "session_id": session_id,
            "status": "interrupted",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error interrupting response: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Cleanup on shutdown
@router.on_event("shutdown")
async def shutdown_event():
    """Clean up all active sessions on shutdown"""
    await stream_manager.cleanup()