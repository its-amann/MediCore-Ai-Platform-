"""
WebSocket routes for real-time communication
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
import logging
import json

from ...core.websocket_manager import websocket_manager, MessageType
from ...core.dependencies import get_storage_service, get_chat_service
from ...models.chat_models import MessageCreate, MessageType as ChatMessageType
from ...services.chat.message_processor import MessageProcessor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/connect/{case_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    case_id: str,
    user_id: str = Query(..., description="User ID"),
    chat_service: MessageProcessor = Depends(get_chat_service)
):
    """
    WebSocket endpoint for real-time chat
    
    Args:
        websocket: WebSocket connection
        case_id: Case ID to connect to
        user_id: User ID
    """
    connection = None
    
    try:
        # Connect to WebSocket manager
        connection = await websocket_manager.connect(websocket, case_id, user_id)
        logger.info(f"WebSocket connected: user={user_id}, case={case_id}")
        
        # Main message loop
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Handle the message
            message_data = await websocket_manager.handle_incoming_message(
                connection.id, 
                data
            )
            
            if message_data:
                # Process different message types
                message_type = message_data.get("type", MessageType.USER_MESSAGE.value)
                
                if message_type == MessageType.USER_MESSAGE.value:
                    # Create message object
                    message = MessageCreate(
                        case_id=case_id,
                        content=message_data.get("content", ""),
                        message_type=ChatMessageType.USER_MESSAGE,
                        sender_id=user_id,
                        sender_type="user",
                        metadata=message_data.get("metadata", {})
                    )
                    
                    # Send to all connections in the case
                    await websocket_manager.broadcast_to_case(case_id, {
                        "type": MessageType.USER_MESSAGE.value,
                        "message": message.dict(),
                        "sender_id": user_id,
                        "timestamp": message.timestamp.isoformat()
                    })
                    
                    # Process with AI and get response
                    try:
                        # Send typing indicator
                        await websocket_manager.broadcast_to_case(case_id, {
                            "type": MessageType.TYPING_INDICATOR.value,
                            "user_id": "ai_doctor",
                            "is_typing": True,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                        # Process message
                        response = await chat_service.process_message(message)
                        
                        # Stop typing indicator
                        await websocket_manager.broadcast_to_case(case_id, {
                            "type": MessageType.TYPING_INDICATOR.value,
                            "user_id": "ai_doctor",
                            "is_typing": False,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                        # Send AI response to all connections
                        await websocket_manager.broadcast_to_case(case_id, {
                            "type": MessageType.DOCTOR_RESPONSE.value,
                            "message": response.dict(),
                            "sender_id": response.sender_id,
                            "timestamp": response.timestamp.isoformat()
                        })
                        
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        await websocket_manager.send_personal_message(connection, {
                            "type": MessageType.ERROR_MESSAGE.value,
                            "error": "Failed to process message",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                
                elif message_type == MessageType.MEDIA_UPLOAD.value:
                    # Handle media upload notification
                    await websocket_manager.broadcast_to_case(case_id, {
                        "type": MessageType.MEDIA_UPLOAD.value,
                        "attachment_id": message_data.get("attachment_id"),
                        "filename": message_data.get("filename"),
                        "sender_id": user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }, exclude_connection=connection)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: user={user_id}, case={case_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Disconnect from manager
        if connection:
            await websocket_manager.disconnect(connection.id)


@router.websocket("/stream/{case_id}")
async def websocket_stream_endpoint(
    websocket: WebSocket,
    case_id: str,
    user_id: str = Query(..., description="User ID"),
    chat_service: MessageProcessor = Depends(get_chat_service)
):
    """
    WebSocket endpoint for streaming AI responses
    
    Args:
        websocket: WebSocket connection
        case_id: Case ID to connect to
        user_id: User ID
    """
    connection = None
    
    try:
        # Connect to WebSocket manager
        connection = await websocket_manager.connect(websocket, case_id, user_id)
        logger.info(f"WebSocket stream connected: user={user_id}, case={case_id}")
        
        # Main message loop
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "user_message":
                # Create message object
                message = MessageCreate(
                    case_id=case_id,
                    content=message_data.get("content", ""),
                    message_type=ChatMessageType.USER_MESSAGE,
                    sender_id=user_id,
                    sender_type="user",
                    metadata=message_data.get("metadata", {})
                )
                
                # Send user message to all
                await websocket_manager.broadcast_to_case(case_id, {
                    "type": "user_message",
                    "message": message.dict(),
                    "sender_id": user_id,
                    "timestamp": message.timestamp.isoformat()
                })
                
                # Stream AI response
                try:
                    # Send typing indicator
                    await websocket_manager.broadcast_to_case(case_id, {
                        "type": "typing_indicator",
                        "user_id": "ai_doctor",
                        "is_typing": True,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    # Stream response
                    full_response = ""
                    async for chunk in chat_service.stream_response(message):
                        full_response += chunk["content"]
                        
                        # Send chunk to all connections
                        await websocket_manager.broadcast_to_case(case_id, {
                            "type": "stream_chunk",
                            "chunk": chunk["content"],
                            "sender_id": "ai_doctor",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    
                    # Send completion signal
                    await websocket_manager.broadcast_to_case(case_id, {
                        "type": "stream_complete",
                        "full_response": full_response,
                        "sender_id": "ai_doctor",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    # Stop typing indicator
                    await websocket_manager.broadcast_to_case(case_id, {
                        "type": "typing_indicator",
                        "user_id": "ai_doctor",
                        "is_typing": False,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"Error streaming response: {e}")
                    await websocket_manager.send_personal_message(connection, {
                        "type": "error",
                        "error": "Failed to stream response",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket stream disconnected: user={user_id}, case={case_id}")
    except Exception as e:
        logger.error(f"WebSocket stream error: {e}")
    finally:
        # Disconnect from manager
        if connection:
            await websocket_manager.disconnect(connection.id)


@router.get("/active-connections")
async def get_active_connections():
    """
    Get information about active WebSocket connections
    
    Returns:
        Dictionary with connection statistics
    """
    return {
        "total_connections": websocket_manager.get_connection_count(),
        "active_cases": websocket_manager.get_active_cases(),
        "cases": {
            case_id: websocket_manager.get_connection_count(case_id)
            for case_id in websocket_manager.get_active_cases()
        }
    }


# Import datetime for timestamps
from datetime import datetime