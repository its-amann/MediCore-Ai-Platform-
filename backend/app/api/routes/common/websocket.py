"""
Unified WebSocket router for all microservices
Consolidates all WebSocket endpoints into a single, well-organized router
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Optional, Dict, Any
import json
import logging
from datetime import datetime

from app.core.websocket import websocket_manager, MessageType
from app.core.websocket.utils.error_handler import WebSocketError, WebSocketErrorCode
from app.core.unified_logging import get_logger
from app.api.dependencies.websocket_auth import get_websocket_user, check_token_expiry_soon
from app.microservices.cases_chat.websocket_adapter import get_cases_chat_ws_adapter
from app.microservices.medical_imaging.workflows.websocket_adapter import medical_imaging_websocket
from app.microservices.voice_consultation.websocket import voice_consultation_websocket as get_voice_ws_adapter
from app.microservices.collaboration.integration import collaboration_integration

logger = get_logger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_info: Optional[Dict[str, Any]] = Depends(get_websocket_user),
    token: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    username: Optional[str] = Query(None)
):
    """
    Main WebSocket endpoint with proper authentication
    """
    if not user_info:
        # Authentication failed, connection already closed by dependency
        return
    
    # Log authentication success
    logger.info(f"WebSocket authenticated connection - user: {user_info.get('username')} ({user_info.get('user_id')})")
    
    # Forward to unified endpoint with authenticated user info
    return await unified_websocket_endpoint(
        websocket, 
        token, 
        user_info.get('user_id'), 
        user_info.get('username'), 
        service=None,
        user_info=user_info
    )


@router.websocket("/ws/unified")
async def unified_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    user_info: Optional[Dict[str, Any]] = None
):
    """
    Unified WebSocket endpoint for all microservices
    
    Query parameters:
    - token: Authentication token (required for production)
    - user_id: User ID (fallback for testing)
    - username: Username (fallback for testing)
    - service: Optional service hint (cases, medical_imaging, voice, collaboration)
    """
    connection_id = None
    
    try:
        logger.info(f"WebSocket unified endpoint - handling connection")
        # Accept the WebSocket connection
        await websocket.accept()
        
        # If user_info is provided (from authenticated endpoint), use it
        if user_info:
            user_id = user_info.get('user_id')
            username = user_info.get('username')
            logger.info(f"Using pre-authenticated user info: {username} ({user_id})")
        # Otherwise validate authentication
        elif not token and not (user_id and username):
            logger.warning("WebSocket connection rejected - no authentication provided")
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        # Connect to WebSocket manager
        connection_kwargs = {}
        if token:
            connection_kwargs["token"] = token
            logger.info(f"WebSocket connection with token authentication")
        else:
            # Testing mode
            connection_kwargs["testing_mode"] = True
            logger.info(f"WebSocket testing mode for user {username}")
        
        try:
            connection_id = await websocket_manager.connect(
                websocket, 
                user_id or "pending_auth", 
                username or "pending_auth", 
                **connection_kwargs
            )
        except (ValueError, WebSocketError) as e:
            # Handle WebSocketError specifically
            if isinstance(e, WebSocketError):
                await websocket.close(code=int(e.code), reason=e.message)
                logger.warning(f"WebSocket error (code {e.code}): {e.message}")
            else:
                # Legacy ValueError handling
                error_message = str(e)
                if "rate limit" in error_message.lower():
                    # Rate limit exceeded - use 4008 code
                    await websocket.close(code=4008, reason=error_message)
                    logger.warning(f"WebSocket rate limit exceeded: {error_message}")
                else:
                    # Authentication failed - use 4003 code
                    await websocket.close(code=4003, reason=error_message)
                    logger.warning(f"WebSocket authentication failed: {error_message}")
            return
        
        # Get authenticated user info
        connection_info = websocket_manager._connections.get(connection_id)
        if connection_info:
            user_id = connection_info.user_id
            username = connection_info.username
        
        logger.info(f"Unified WebSocket connected: {connection_id} for user {username} (service: {service})")
        
        # Check if token is expiring soon
        if user_info and check_token_expiry_soon(user_info, threshold_seconds=300):
            logger.warning(f"Token expiring soon for user {username}")
            # Notify client to refresh token
            await websocket_manager._send_message(connection_id, {
                "type": "token_refresh_required",
                "message": "Your authentication token will expire soon. Please refresh it.",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Send connection established message
        await websocket_manager._send_message(connection_id, {
            "type": "connection_established",
            "connection_id": connection_id,
            "user_id": user_id,
            "username": username,
            "service": service,
            "timestamp": datetime.utcnow().isoformat(),
            "features": {
                "cases_chat": True,
                "medical_imaging": True,
                "voice_consultation": True,
                "collaboration": True
            }
        })
        
        # Initialize service-specific adapters if service hint provided
        if service:
            await _initialize_service_adapter(service, connection_id, user_id, username)
        
        # Handle messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Route message based on type or service
                await _route_message(connection_id, message, user_id, username)
                
            except json.JSONDecodeError:
                await websocket_manager._send_error(connection_id, "Invalid JSON format")
            except WebSocketDisconnect:
                break
            except WebSocketError as e:
                # WebSocket error from manager - connection should be closed
                logger.error(f"WebSocket error in message handling: {e.message}")
                await websocket.close(code=int(e.code), reason=e.message)
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                await websocket_manager._send_error(connection_id, f"Error: {str(e)}")
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}", exc_info=True)
    
    finally:
        if connection_id:
            try:
                await websocket_manager.disconnect(connection_id)
                logger.info(f"WebSocket disconnected: {connection_id}")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")


async def _initialize_service_adapter(service: str, connection_id: str, user_id: str, username: str):
    """Initialize service-specific adapters based on service hint"""
    try:
        if service == "cases":
            # Initialize cases chat adapter
            adapter = get_cases_chat_ws_adapter()
            logger.info(f"Initialized cases chat adapter for {username}")
            
        elif service == "medical_imaging":
            # Initialize medical imaging session
            session_id = await medical_imaging_websocket.create_medical_session(
                user_id=user_id,
                case_id="default-case"
            )
            await websocket_manager._send_message(connection_id, {
                "type": "medical_imaging_initialized",
                "session_id": session_id
            })
            logger.info(f"Initialized medical imaging session for {username}")
            
        elif service == "voice":
            # Initialize voice adapter
            adapter = get_voice_ws_adapter()
            logger.info(f"Initialized voice consultation adapter for {username}")
            
        elif service == "collaboration":
            # Collaboration uses the unified WebSocket manager directly
            logger.info(f"Collaboration service ready for {username}")
            
    except Exception as e:
        logger.error(f"Error initializing {service} adapter: {e}")


async def _route_message(connection_id: str, message: Dict[str, Any], user_id: str, username: str):
    """Route messages to appropriate handlers based on message type or content"""
    msg_type = message.get("type", "")
    
    # Cases Chat messages
    if msg_type in ["chat_message", "load_chat_history", "create_chat_session", 
                    "join_case_room", "leave_case_room", "get_available_cases"]:
        await _handle_cases_message(connection_id, message, user_id)
    
    # Medical Imaging messages
    elif msg_type in ["start_analysis", "get_workflow_status", "cancel_workflow",
                      "get_analysis_history", "medical_imaging_request", "register_medical_imaging"]:
        await _handle_medical_imaging_message(connection_id, message, user_id)
    
    # Voice Consultation messages
    elif msg_type in ["start_voice_session", "end_voice_session", "voice_data",
                      "transcription_request", "voice_command"]:
        await _handle_voice_message(connection_id, message, user_id)
    
    # Collaboration messages
    elif msg_type in ["join_room", "leave_room", "collaboration_message",
                      "screen_share", "video_call"]:
        await _handle_collaboration_message(connection_id, message, user_id)
    
    # Common messages
    elif msg_type in ["ping", "pong", "status_update", "typing", "stopped_typing"]:
        await websocket_manager.handle_message(connection_id, message)
    
    # Unknown message type - try to infer from content
    else:
        await _infer_and_route_message(connection_id, message, user_id)


async def _handle_cases_message(connection_id: str, message: Dict[str, Any], user_id: str):
    """Handle cases chat specific messages"""
    try:
        adapter = get_cases_chat_ws_adapter()
        msg_type = message.get("type")
        
        if msg_type == "join_case_room":
            case_id = message.get("case_id")
            if case_id:
                await adapter.join_case_room(user_id, case_id)
                await websocket_manager.join_room(connection_id, f"case_{case_id}")
                
        elif msg_type == "leave_case_room":
            case_id = message.get("case_id")
            if case_id:
                await adapter.leave_case_room(user_id, case_id)
                await websocket_manager.leave_room(connection_id, f"case_{case_id}")
                
        else:
            # Use WebSocket manager's built-in message handling
            await websocket_manager.handle_message(connection_id, message)
            
    except Exception as e:
        logger.error(f"Error handling cases message: {e}")
        await websocket_manager._send_error(connection_id, f"Cases error: {str(e)}")


async def _handle_medical_imaging_message(connection_id: str, message: Dict[str, Any], user_id: str):
    """Handle medical imaging specific messages"""
    try:
        msg_type = message.get("type")
        data = message.get("data", {})
        
        if msg_type == "register_medical_imaging":
            # Handle registration for medical imaging updates
            case_id = message.get("case_id")
            if case_id:
                # Simply acknowledge the registration - no room concept for medical imaging
                await websocket_manager._send_message(connection_id, {
                    "type": "registration_confirmed",
                    "service": "medical_imaging",
                    "case_id": case_id,
                    "message": f"Registered for medical imaging updates for case: {case_id}"
                })
                logger.info(f"User {user_id} registered for medical imaging updates on case {case_id}")
            
        elif msg_type == "start_analysis":
            case_id = data.get("case_id")
            image_ids = data.get("image_ids", [])
            if case_id and image_ids:
                result = await medical_imaging_websocket.start_image_analysis(
                    case_id=case_id,
                    image_ids=image_ids,
                    user_id=user_id,
                    options=data.get("options", {})
                )
                await websocket_manager._send_message(connection_id, {
                    "type": "analysis_started",
                    "data": result
                })
                
        elif msg_type == "get_workflow_status":
            workflow_id = data.get("workflow_id")
            if workflow_id:
                status = await medical_imaging_websocket.get_workflow_status(workflow_id)
                await websocket_manager._send_message(connection_id, {
                    "type": "workflow_status",
                    "data": status
                })
                
        else:
            # Forward to medical imaging adapter
            await medical_imaging_websocket.handle_message(user_id, message)
            
    except Exception as e:
        logger.error(f"Error handling medical imaging message: {e}")
        await websocket_manager._send_error(connection_id, f"Medical imaging error: {str(e)}")


async def _handle_voice_message(connection_id: str, message: Dict[str, Any], user_id: str):
    """Handle voice consultation specific messages"""
    try:
        adapter = get_voice_ws_adapter()
        msg_type = message.get("type")
        
        if msg_type == "start_voice_session":
            case_id = message.get("case_id")
            if case_id:
                session = await adapter.start_voice_session(user_id, case_id)
                await websocket_manager._send_message(connection_id, {
                    "type": "voice_session_started",
                    "session": session
                })
                
        elif msg_type == "voice_data":
            # Handle voice data streaming
            await adapter.handle_voice_data(user_id, message.get("data"))
            
        else:
            # Forward to voice adapter
            await adapter.handle_message(user_id, message)
            
    except Exception as e:
        logger.error(f"Error handling voice message: {e}")
        await websocket_manager._send_error(connection_id, f"Voice error: {str(e)}")


async def _handle_collaboration_message(connection_id: str, message: Dict[str, Any], user_id: str):
    """Handle collaboration specific messages"""
    try:
        msg_type = message.get("type")
        
        if msg_type == "join_room":
            room_id = message.get("room_id")
            if room_id:
                await websocket_manager.join_room(connection_id, room_id)
                # Notify collaboration service
                if hasattr(collaboration_integration, 'websocket_manager'):
                    await collaboration_integration.websocket_manager.handle_message(user_id, message)
                    
        elif msg_type == "leave_room":
            room_id = message.get("room_id")
            if room_id:
                await websocket_manager.leave_room(connection_id, room_id)
                # Notify collaboration service
                if hasattr(collaboration_integration, 'websocket_manager'):
                    await collaboration_integration.websocket_manager.handle_message(user_id, message)
                    
        else:
            # Forward to collaboration integration
            if hasattr(collaboration_integration, 'websocket_manager'):
                await collaboration_integration.websocket_manager.handle_message(user_id, message)
            else:
                await websocket_manager.handle_message(connection_id, message)
                
    except Exception as e:
        logger.error(f"Error handling collaboration message: {e}")
        await websocket_manager._send_error(connection_id, f"Collaboration error: {str(e)}")


async def _infer_and_route_message(connection_id: str, message: Dict[str, Any], user_id: str):
    """Infer message type from content and route appropriately"""
    try:
        # Check for case_id - likely cases chat
        if "case_id" in message and ("content" in message or "user_message" in message):
            message["type"] = "chat_message"
            await _handle_cases_message(connection_id, message, user_id)
            
        # Check for image_ids - likely medical imaging
        elif "image_ids" in message or "workflow_id" in message:
            await _handle_medical_imaging_message(connection_id, message, user_id)
            
        # Check for audio/voice data
        elif "audio_data" in message or "voice_data" in message:
            await _handle_voice_message(connection_id, message, user_id)
            
        # Check for room_id - likely collaboration
        elif "room_id" in message:
            await _handle_collaboration_message(connection_id, message, user_id)
            
        # Default to generic message handling
        else:
            await websocket_manager.handle_message(connection_id, message)
            
    except Exception as e:
        logger.error(f"Error inferring message type: {e}")
        await websocket_manager._send_error(connection_id, "Unable to process message")


# Test endpoint to verify routes are loaded
@router.get("/test")
async def test_websocket_route():
    """Test endpoint to verify WebSocket routes are loaded"""
    return {"message": "WebSocket routes are loaded", "routes": ["/ws", "/ws/unified"]}

# Additional HTTP endpoints for WebSocket management

@router.get("/status")
async def get_websocket_status():
    """Get overall WebSocket connection status"""
    try:
        return {
            "status": "healthy",
            "connections": websocket_manager.get_connection_stats(),
            "online_users": len(websocket_manager.get_online_users()),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/connections")
async def get_active_connections():
    """Get list of active WebSocket connections"""
    try:
        connections = []
        for conn_id, conn in websocket_manager._connections.items():
            connections.append({
                "connection_id": conn_id,
                "user_id": conn.user_id,
                "username": conn.username,
                "connected_at": conn.connected_at.isoformat() if hasattr(conn, 'connected_at') else None,
                "rooms": list(conn.rooms) if hasattr(conn, 'rooms') else []
            })
        
        return {
            "connections": connections,
            "total": len(connections),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting connections: {e}")
        return {
            "error": str(e),
            "connections": [],
            "total": 0
        }