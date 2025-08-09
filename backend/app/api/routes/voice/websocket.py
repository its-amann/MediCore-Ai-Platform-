"""
WebSocket routes for voice consultation with VAD integration
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from typing import Dict, Any, Optional
import logging
import json
import asyncio
from datetime import datetime
import base64

from app.api.routes.auth import get_current_user, get_current_active_user, verify_websocket_token
from app.core.database.models import User
from app.microservices.voice_consultation.services.voice_consultation_service import voice_consultation_service
from app.microservices.voice_consultation.models.consultation_models import (
    ConsultationRequest,
    ConsultationResponse,
    ConsultationStatus,
    MessageType,
    ProviderType
)
from app.microservices.voice_consultation.websocket.voice_websocket_adapter import (
    voice_consultation_websocket,
    VoiceConsultationMessageType
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice-websocket"])


@router.websocket("/ws/{session_id}")
async def voice_consultation_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = None
):
    """WebSocket endpoint for real-time voice consultation with VAD"""
    
    # For development/testing, allow auth bypass
    import os
    auth_required = os.getenv('WS_AUTH_REQUIRED', 'true').lower() == 'true'
    
    # Verify token if auth is required
    current_user = None
    if auth_required and token:
        try:
            current_user = await verify_websocket_token(token)
            if not current_user:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    elif auth_required:
        # Auth required but no token provided
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    await websocket.accept()
    
    # Generate connection ID
    connection_id = f"voice_ws_{session_id}_{datetime.utcnow().timestamp()}"
    
    try:
        # Get session status or create a new one if it doesn't exist
        session_status = await voice_consultation_service.get_session_status(session_id)
        if not session_status:
            # Create a new session automatically for development
            logger.info(f"Creating new session for WebSocket connection: {session_id}")
            from app.microservices.voice_consultation.models.consultation_models import ConsultationRequest
            
            consultation_request = ConsultationRequest(
                consultation_type="voice",
                doctor_type="general",
                language="en",
                symptoms=[],
                duration_minutes=30
            )
            
            # Create session
            user_id = current_user.user_id if current_user else "anonymous"
            session_response = await voice_consultation_service.create_session(
                request=consultation_request,
                user_id=user_id,
                session_id=session_id  # Use the provided session_id
            )
            
            if not session_response:
                await websocket.send_json({
                    "type": "error",
                    "message": "Failed to create session",
                    "session_id": session_id
                })
                await websocket.close()
                return
                
            session_status = await voice_consultation_service.get_session_status(session_id)
            
            # Create WebSocket session in the adapter
            user_id = current_user.user_id if current_user else "anonymous"
            ws_session_id = await voice_consultation_websocket.create_voice_session(
                user_id=user_id,
                consultation_session_id=session_id,
                case_id=None,
                doctor_type="general",
                ai_provider=None,
                language="en"
            )
        else:
            # Get existing WebSocket session ID
            ws_session_id = voice_consultation_websocket.get_ws_session_id_by_consultation(session_id)
            if not ws_session_id:
                # Create WebSocket session if it doesn't exist
                user_id = current_user.user_id if current_user else session_status.get("user_id", "anonymous")
                ws_session_id = await voice_consultation_websocket.create_voice_session(
                    user_id=user_id,
                    consultation_session_id=session_id,
                    case_id=session_status.get("case_id"),
                    doctor_type=session_status.get("doctor_type", "general"),
                    ai_provider=None,
                    language=session_status.get("language", "en")
                )
        
        # Connect user to WebSocket session
        user_id = current_user.user_id if current_user else session_status.get("user_id", "anonymous")
        
        # Debug logging
        logger.info(f"About to connect user {user_id} with ws_session_id: {ws_session_id}")
        
        connected = await voice_consultation_websocket.connect_user_to_session(
            user_id=user_id,
            ws_session_id=ws_session_id,
            connection_id=connection_id
        )
        
        if not connected:
            await websocket.send_json({
                "type": "error",
                "message": "Failed to connect to session"
            })
            await websocket.close()
            return
        
        # Send connection success
        await websocket.send_json({
            "type": "connection_established",
            "session_id": session_id,
            "status": session_status,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Handle incoming messages
        while True:
            try:
                # Receive message (can be JSON or bytes)
                message = await websocket.receive()
                
                if "text" in message:
                    # JSON message
                    data = json.loads(message["text"])
                    await handle_json_message(websocket, session_id, data)
                    
                elif "bytes" in message:
                    # Binary audio data
                    await handle_audio_data(websocket, session_id, message["bytes"])
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # Disconnect user from session
        if current_user:
            await voice_consultation_websocket.disconnect_user_from_session(
                user_id=current_user.user_id,
                connection_id=connection_id
            )
        # Note: Don't end the consultation session here - user might reconnect


async def handle_json_message(websocket: WebSocket, session_id: str, data: Dict[str, Any]):
    """Handle JSON messages from WebSocket"""
    
    message_type = data.get("type")
    
    if message_type == "audio_chunk":
        # Audio data sent as base64 in JSON
        audio_base64 = data.get("data")
        if audio_base64:
            audio_bytes = base64.b64decode(audio_base64)
            await handle_audio_data(websocket, session_id, audio_bytes, data)
            
    elif message_type == "video_frame":
        # Video frame for Gemini Live analysis
        frame_base64 = data.get("data")
        if frame_base64:
            result = await voice_consultation_service.process_video_frame(
                session_id=session_id,
                frame_data=frame_base64
            )
            if result:
                await websocket.send_json({
                    "type": "visual_analysis",
                    "data": result,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    elif message_type == "screen_frame":
        # Screen share frame for medical data analysis
        frame_base64 = data.get("data")
        dimensions = data.get("dimensions", {"width": 1920, "height": 1080})
        if frame_base64:
            result = await voice_consultation_service.process_screen_frame(
                session_id=session_id,
                frame_data=frame_base64,
                dimensions=dimensions
            )
            if result:
                await websocket.send_json({
                    "type": "screen_analysis",
                    "data": result,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    elif message_type == "force_finalize":
        # Force finalize current speech segment
        audio_data = await voice_consultation_service.force_finalize_speech(session_id)
        if audio_data:
            await websocket.send_json({
                "type": "speech_finalized",
                "timestamp": datetime.utcnow().isoformat()
            })
            
    elif message_type == "end_session":
        # End the consultation
        result = await voice_consultation_service.end_consultation(session_id)
        await websocket.send_json({
            "type": "session_ended",
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        await websocket.close()
        
    elif message_type == "ping":
        # Heartbeat
        await websocket.send_json({
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    else:
        logger.warning(f"Unknown message type: {message_type}")


async def handle_audio_data(
    websocket: WebSocket, 
    session_id: str, 
    audio_bytes: bytes,
    metadata: Dict[str, Any] = None
):
    """Handle binary audio data with VAD processing"""
    
    try:
        # Extract format and sample rate from metadata if provided
        format = "pcm16"
        sample_rate = 16000
        
        if metadata:
            format = metadata.get("format", "pcm16")
            sample_rate = metadata.get("sample_rate", 16000)
        
        # Process audio chunk through VAD
        vad_status = await voice_consultation_service.process_audio_chunk(
            session_id=session_id,
            audio_data=audio_bytes,
            format=format,
            sample_rate=sample_rate
        )
        
        # Send VAD status update - check WebSocket state first
        if vad_status:
            try:
                await websocket.send_json({
                    "type": "vad_status",
                    "data": vad_status,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as send_error:
                logger.debug(f"Could not send VAD status - connection may be closed: {send_error}")
            
    except Exception as e:
        logger.error(f"Error processing audio data: {e}")
        # Only try to send error if WebSocket is still open
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Audio processing error: {str(e)}"
            })
        except Exception as send_error:
            logger.debug(f"Could not send error message - connection closed: {send_error}")


@router.post("/consultation/start", response_model=ConsultationResponse)
async def start_voice_consultation(
    request: ConsultationRequest,
    current_user: User = Depends(get_current_active_user)
) -> ConsultationResponse:
    """Start a new voice consultation session"""
    
    try:
        # Create consultation session
        response = await voice_consultation_service.create_consultation(
            request=request,
            user_id=str(current_user.user_id)
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error creating consultation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/consultation/{session_id}/status")
async def get_consultation_status(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get current status of a voice consultation"""
    
    try:
        status = await voice_consultation_service.get_session_status(session_id)
        if not status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting consultation status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/consultation/{session_id}/end")
async def end_voice_consultation(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """End a voice consultation session"""
    
    try:
        result = await voice_consultation_service.end_consultation(session_id)
        return result
        
    except Exception as e:
        logger.error(f"Error ending consultation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )