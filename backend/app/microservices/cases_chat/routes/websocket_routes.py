"""
WebSocket Routes
Handles WebSocket connections for real-time chat features
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Optional
import logging
import json

from ..dependencies import get_websocket_adapter, verify_websocket_token
from ..models import DoctorType

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ws",
    tags=["websocket"]
)


@router.websocket("/chat/{case_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    case_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time chat in a case
    
    This endpoint handles:
    - Real-time message delivery
    - Typing indicators
    - Doctor response streaming
    - Case updates
    
    Args:
        websocket: WebSocket connection
        case_id: Case ID to join
        token: Authentication token
    """
    ws_adapter = None
    connection_id = None
    
    try:
        # Accept connection first
        await websocket.accept()
        
        # Then verify authentication
        user_data = await verify_websocket_token(token)
        if not user_data:
            logger.warning(f"WebSocket authentication failed for case {case_id}")
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        user_id = user_data["user_id"]
        username = user_data.get("username", f"User_{user_id[:8]}")
        
        logger.info(f"WebSocket connection authenticated for user {user_id} in case {case_id}")
        
        # Get WebSocket adapter
        from ..dependencies import get_websocket_adapter
        ws_adapter = get_websocket_adapter()
        
        # Register connection with the unified WebSocket manager
        connection_id = await ws_adapter.ws_manager.connect(
            websocket=websocket,
            user_id=user_id,
            username=username
        )
        
        # Join case room
        success = await ws_adapter.join_case_room(user_id, case_id)
        if not success:
            await websocket.send_json({
                "type": "error",
                "message": "Failed to join case room"
            })
            await websocket.close()
            return
        
        # Send connection success message
        await websocket.send_json({
            "type": "connection_established",
            "case_id": case_id,
            "user_id": user_id,
            "connection_id": connection_id,
            "room_members": ws_adapter.get_case_room_users(case_id)
        })
        
        # Handle incoming messages
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                message_type = message.get("type")
                
                if message_type == "ping":
                    # Respond to ping
                    await websocket.send_json({"type": "pong"})
                    
                elif message_type == "typing_start":
                    # Handle typing indicator
                    await ws_adapter.send_typing_indicator(
                        case_id=case_id,
                        user_id=user_id,
                        username=username,
                        is_typing=True
                    )
                    
                elif message_type == "typing_stop":
                    # Handle stop typing
                    await ws_adapter.send_typing_indicator(
                        case_id=case_id,
                        user_id=user_id,
                        username=username,
                        is_typing=False
                    )
                    
                elif message_type == "request_room_info":
                    # Send current room information
                    await websocket.send_json({
                        "type": "room_info",
                        "case_id": case_id,
                        "members": ws_adapter.get_case_room_users(case_id)
                    })
                    
                else:
                    # Unknown message type
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Error processing message"
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user in case {case_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=4000, reason="Internal error")
        except:
            pass
    finally:
        # Clean up
        if ws_adapter and connection_id:
            try:
                # Leave case room
                if user_id:
                    await ws_adapter.leave_case_room(user_id, case_id)
                
                # Disconnect from WebSocket manager
                await ws_adapter.ws_manager.disconnect(connection_id)
            except Exception as e:
                logger.error(f"Error during WebSocket cleanup: {e}")


@router.websocket("/stream/{session_id}")
async def websocket_stream_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for streaming doctor responses
    
    This endpoint is specifically for:
    - Streaming AI doctor responses in real-time
    - Progress updates during long operations
    - MCP analysis updates
    
    Args:
        websocket: WebSocket connection
        session_id: Chat session ID
        token: Authentication token
    """
    try:
        # Accept connection first
        await websocket.accept()
        
        # Then verify authentication
        user_data = await verify_websocket_token(token)
        if not user_data:
            logger.warning(f"WebSocket authentication failed for stream session {session_id}")
            await websocket.close(code=4001, reason="Authentication required")
            return
        
        user_id = user_data["user_id"]
        
        logger.info(f"Streaming WebSocket authenticated for session {session_id} by user {user_id}")
        
        # Send connection established
        await websocket.send_json({
            "type": "stream_ready",
            "session_id": session_id,
            "user_id": user_id
        })
        
        # Keep connection alive and handle control messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif message.get("type") == "close_stream":
                    break
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Stream WebSocket error: {e}")
                break
                
    except Exception as e:
        logger.error(f"Stream endpoint error: {e}")
        try:
            await websocket.close(code=4000, reason="Internal error")
        except:
            pass
    finally:
        logger.info(f"Streaming WebSocket disconnected for session {session_id}")


@router.get("/active-connections")
async def get_active_connections(
    ws_adapter = Depends(get_websocket_adapter)
):
    """
    Get information about active WebSocket connections
    
    Returns:
        Statistics about active connections and rooms
    """
    try:
        stats = ws_adapter.ws_manager.get_stats()
        
        # Get case-specific stats
        case_rooms = {}
        for room_id, connections in ws_adapter.ws_manager._rooms.items():
            if room_id.startswith("case_"):
                case_id = room_id.replace("case_", "")
                case_rooms[case_id] = {
                    "connection_count": len(connections),
                    "users": ws_adapter.get_case_room_users(case_id)
                }
        
        return {
            "total_connections": stats["total_connections"],
            "total_users": stats["total_users"],
            "total_rooms": stats["total_rooms"],
            "case_rooms": case_rooms,
            "health": "healthy" if stats["total_connections"] < 1000 else "high_load"
        }
        
    except Exception as e:
        logger.error(f"Error getting connection stats: {e}")
        return {
            "error": "Failed to retrieve connection statistics",
            "health": "unknown"
        }