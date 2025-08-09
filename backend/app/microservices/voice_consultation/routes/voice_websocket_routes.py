"""
Voice Consultation WebSocket Routes
WebSocket endpoints for real-time voice consultation updates
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from typing import Dict, Any, Optional
import json

from app.core.database.models import User
from app.api.routes.auth import get_current_active_user
from app.core.websocket.manager import websocket_manager
from ..websocket import voice_consultation_websocket

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice/ws", tags=["voice-websocket"])


@router.websocket("/consultation/{consultation_session_id}")
async def voice_consultation_websocket_endpoint(
    websocket: WebSocket,
    consultation_session_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for voice consultation real-time updates
    
    Args:
        websocket: WebSocket connection
        consultation_session_id: Voice consultation session ID
        token: Optional JWT token for authentication
    """
    connection_id = None
    
    try:
        # Accept the WebSocket connection
        await websocket.accept()
        
        # Check if authentication is required from environment
        import os
        auth_required = os.getenv('WS_AUTH_REQUIRED', 'true').lower() == 'true'
        
        # Authenticate the connection using JWT validation
        user_data = None
        if token and auth_required:
            try:
                # Import JWT validation functions
                from app.api.routes.auth import verify_token_with_grace_period, get_database
                from jose import jwt
                
                # Verify the token
                token_result = verify_token_with_grace_period(token, grace_period=True)
                
                if not token_result["valid"]:
                    logger.error(f"Invalid token for voice consultation WebSocket")
                    await websocket.close(code=4003, reason="Authentication failed")
                    return
                
                # Extract user info from token payload
                payload = token_result["payload"]
                username = payload.get("sub")
                
                # Get user from database
                db = await get_database()
                if db:
                    query = """
                    MATCH (u:User {username: $username})
                    RETURN u.user_id as user_id, u.username as username
                    """
                    result = await db.run_query(query, {"username": username})
                    if result:
                        user_data = {
                            "user_id": result[0]["user_id"],
                            "username": result[0]["username"]
                        }
                    else:
                        logger.error(f"User not found in database: {username}")
                        await websocket.close(code=4003, reason="User not found")
                        return
                else:
                    # Fallback if database is not available
                    user_data = {
                        "user_id": username,
                        "username": username
                    }
                    
            except Exception as e:
                logger.error(f"Authentication failed: {e}")
                await websocket.close(code=4003, reason="Authentication failed")
                return
        elif auth_required:
            # Require authentication for voice consultations when auth is enabled
            logger.error("No token provided for voice consultation WebSocket")
            await websocket.close(code=4001, reason="Authentication required")
            return
        else:
            # When auth is disabled, create a default user
            # Extract the actual user_id from the WebSocket session if available
            ws_session_id = voice_consultation_websocket.get_ws_session_id_by_consultation(consultation_session_id)
            if ws_session_id:
                # Get the session to find the original user_id
                ws_sessions = voice_consultation_websocket._voice_ws_sessions
                if ws_session_id in ws_sessions:
                    original_user_id = ws_sessions[ws_session_id].user_id
                    logger.info(f"Authentication disabled - using original user_id {original_user_id} from WebSocket session")
                    user_data = {
                        "user_id": original_user_id,
                        "username": "anonymous"
                    }
                else:
                    # Fallback to anonymous pattern
                    logger.info("Authentication disabled - using anonymous user for WebSocket")
                    user_data = {
                        "user_id": f"anonymous_{consultation_session_id}",
                        "username": "anonymous"
                    }
            else:
                # Fallback to anonymous pattern
                logger.info("Authentication disabled - using anonymous user for WebSocket")
                user_data = {
                    "user_id": f"anonymous_{consultation_session_id}",
                    "username": "anonymous"
                }
        
        # Connect to the unified WebSocket manager
        connection_id = await websocket_manager.connect(
            websocket,
            user_data["user_id"],
            user_data["username"]
        )
        
        # Find the WebSocket session ID for this consultation
        ws_session_id = voice_consultation_websocket.get_ws_session_id_by_consultation(consultation_session_id)
        
        if not ws_session_id:
            logger.error(f"No WebSocket session found for consultation {consultation_session_id}")
            await websocket.close(code=1003, reason="Consultation session not found")
            return
        
        # Connect to the voice consultation session
        success = await voice_consultation_websocket.connect_user_to_session(
            user_data["user_id"],
            ws_session_id,
            connection_id
        )
        
        if not success:
            await websocket.close(code=1003, reason="Failed to join consultation session")
            return
        
        logger.info(f"User {user_data['user_id']} connected to voice consultation {consultation_session_id}")
        
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_confirmed",
            "consultation_session_id": consultation_session_id,
            "connection_id": connection_id,
            "message": "Connected to voice consultation session"
        }))
        
        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle the message through the unified WebSocket manager
                await websocket_manager.handle_message(connection_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for consultation {consultation_session_id}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": "Invalid JSON format"
                }))
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": str(e)
                }))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected during setup for consultation {consultation_session_id}")
    except Exception as e:
        logger.error(f"Error in voice consultation WebSocket: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    finally:
        # Clean up connection
        if connection_id:
            try:
                await voice_consultation_websocket.disconnect_user_from_session(
                    user_data["user_id"] if user_data else "unknown",
                    connection_id
                )
                await websocket_manager.disconnect(connection_id)
            except Exception as e:
                logger.error(f"Error during WebSocket cleanup: {e}")


@router.get("/consultation/{consultation_session_id}/stats")
async def get_voice_consultation_websocket_stats(
    consultation_session_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get WebSocket statistics for a voice consultation session
    
    Args:
        consultation_session_id: Voice consultation session ID
        current_user: Current authenticated user
        
    Returns:
        WebSocket session statistics
    """
    try:
        # Get general WebSocket stats
        ws_stats = voice_consultation_websocket.get_session_stats()
        
        # Filter for the specific consultation session
        session_info = None
        for session_detail in ws_stats.get("session_details", []):
            if session_detail.get("consultation_session_id") == consultation_session_id:
                # Verify user has access to this session
                if session_detail.get("user_id") == current_user.user_id:
                    session_info = session_detail
                    break
        
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Voice consultation session not found or access denied"
            )
        
        return {
            "consultation_session_id": consultation_session_id,
            "session_info": session_info,
            "connection_count": session_info.get("connection_count", 0),
            "last_activity": session_info.get("last_activity"),
            "created_at": session_info.get("created_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting voice consultation WebSocket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get WebSocket statistics"
        )


@router.get("/stats")
async def get_all_voice_websocket_stats(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get overall voice consultation WebSocket statistics
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Overall WebSocket statistics
    """
    try:
        # Get voice consultation WebSocket stats
        voice_stats = voice_consultation_websocket.get_session_stats()
        
        # Get unified WebSocket manager stats
        manager_stats = websocket_manager.get_connection_stats()
        
        return {
            "voice_consultation": voice_stats,
            "unified_manager": manager_stats,
            "timestamp": logger.info("Voice consultation WebSocket stats requested")
        }
        
    except Exception as e:
        logger.error(f"Error getting voice WebSocket stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get WebSocket statistics"
        )