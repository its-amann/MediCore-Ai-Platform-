"""
Collaboration API Endpoints
Handles real-time multi-doctor collaboration via WebSocket and REST APIs
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import json
import logging
import asyncio
from datetime import datetime

from app.core.collaboration.chat_system import (
    CollaborationManager,
    ParticipantRole,
    MessageType
)
from app.core.database.neo4j_client import Neo4jClient
from app.core.mcp.history_server import MedicalHistoryServer
from app.api.routes.auth import get_current_user, get_database as get_db_client
from app.core.database.models import User, DoctorSpecialty

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collaboration", tags=["collaboration"])

# Global collaboration manager instance
collaboration_manager = CollaborationManager()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, room_id: str, user_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            if room_id not in self.active_connections:
                self.active_connections[room_id] = {}
            self.active_connections[room_id][user_id] = websocket
            logger.info(f"User {user_id} connected to room {room_id}")
    
    async def disconnect(self, room_id: str, user_id: str):
        async with self._lock:
            if room_id in self.active_connections:
                if user_id in self.active_connections[room_id]:
                    del self.active_connections[room_id][user_id]
                    logger.info(f"User {user_id} disconnected from room {room_id}")
                
                if not self.active_connections[room_id]:
                    del self.active_connections[room_id]
    
    async def broadcast_to_room(self, room_id: str, message: Dict[str, Any], exclude_user: Optional[str] = None):
        if room_id in self.active_connections:
            disconnected_users = []
            
            for user_id, websocket in self.active_connections[room_id].items():
                if user_id != exclude_user:
                    try:
                        await websocket.send_json(message)
                    except Exception as e:
                        logger.error(f"Failed to send message to {user_id}: {e}")
                        disconnected_users.append(user_id)
            
            # Clean up disconnected users
            for user_id in disconnected_users:
                await self.disconnect(room_id, user_id)
    
    async def send_to_user(self, room_id: str, user_id: str, message: Dict[str, Any]):
        if room_id in self.active_connections and user_id in self.active_connections[room_id]:
            try:
                await self.active_connections[room_id][user_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")
                await self.disconnect(room_id, user_id)

# Global connection manager
connection_manager = ConnectionManager()

# REST API Endpoints

@router.post("/rooms")
async def create_collaboration_room(
    case_id: str,
    case_description: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new collaboration room for a medical case"""
    
    try:
        room = await collaboration_manager.create_room(
            case_id=case_id,
            creator_id=current_user.user_id,
            creator_name=current_user.name,
            case_description=case_description,
            creator_role=ParticipantRole.HUMAN_DOCTOR
        )
        
        return {
            "success": True,
            "room": room.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to create collaboration room: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create collaboration room"
        )

@router.get("/rooms")
async def get_user_rooms(
    active_only: bool = True,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all collaboration rooms for the current user"""
    
    try:
        rooms = await collaboration_manager.get_user_rooms(
            user_id=current_user.user_id,
            active_only=active_only
        )
        
        return {
            "success": True,
            "rooms": rooms
        }
        
    except Exception as e:
        logger.error(f"Failed to get user rooms: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get collaboration rooms"
        )

@router.get("/rooms/{room_id}")
async def get_room_details(
    room_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get details of a specific collaboration room"""
    
    room = await collaboration_manager.get_room(room_id)
    
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # Check if user is a participant
    if current_user.user_id not in room.participants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this room"
        )
    
    return {
        "success": True,
        "room": room.to_dict(),
        "messages": room.get_messages(limit=50)
    }

@router.post("/rooms/{room_id}/join")
async def join_room(
    room_id: str,
    specialty: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Join a collaboration room"""
    
    success = await collaboration_manager.join_room(
        room_id=room_id,
        participant_id=current_user.user_id,
        participant_name=current_user.name,
        participant_role=ParticipantRole.HUMAN_DOCTOR,
        participant_specialty=specialty
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to join room"
        )
    
    # Notify other participants
    await connection_manager.broadcast_to_room(
        room_id,
        {
            "type": "user_joined",
            "user": {
                "id": current_user.user_id,
                "name": current_user.name,
                "specialty": specialty
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    return {"success": True, "message": "Successfully joined the room"}

@router.post("/rooms/{room_id}/leave")
async def leave_room(
    room_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Leave a collaboration room"""
    
    success = await collaboration_manager.leave_room(
        room_id=room_id,
        participant_id=current_user.user_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to leave room"
        )
    
    # Notify other participants
    await connection_manager.broadcast_to_room(
        room_id,
        {
            "type": "user_left",
            "user": {
                "id": current_user.user_id,
                "name": current_user.name
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    return {"success": True, "message": "Successfully left the room"}

@router.get("/rooms/{room_id}/messages")
async def get_room_messages(
    room_id: str,
    limit: Optional[int] = 50,
    since_timestamp: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get messages from a collaboration room"""
    
    # Verify user is participant
    room = await collaboration_manager.get_room(room_id)
    if not room or current_user.user_id not in room.participants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    messages = await collaboration_manager.get_room_messages(
        room_id=room_id,
        limit=limit,
        since_timestamp=since_timestamp
    )
    
    return {
        "success": True,
        "messages": messages
    }

@router.post("/rooms/{room_id}/consensus")
async def set_consensus(
    room_id: str,
    recommendations: List[str],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Set consensus recommendations for a room"""
    
    success = await collaboration_manager.set_consensus(
        room_id=room_id,
        recommendations=recommendations
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to set consensus"
        )
    
    # Notify all participants
    await connection_manager.broadcast_to_room(
        room_id,
        {
            "type": "consensus_reached",
            "recommendations": recommendations,
            "set_by": current_user.name,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    return {"success": True, "message": "Consensus set successfully"}

# WebSocket Endpoint

@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    token: str,
    neo4j_client: Neo4jClient = Depends(get_db_client)
):
    """WebSocket endpoint for real-time collaboration"""
    
    # Authenticate user from token
    try:
        # In production, properly decode and validate the token
        # For now, we'll use a simple validation
        user_data = await validate_websocket_token(token, neo4j_client)
        if not user_data:
            await websocket.close(code=4001, reason="Authentication failed")
            return
        
        user_id = user_data["user_id"]
        
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    # Connect to room
    await connection_manager.connect(room_id, user_id, websocket)
    
    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "room_id": room_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Handle different message types
            message_type = data.get("type", "text")
            
            if message_type == "message":
                # Send regular message
                content = data.get("content", "")
                msg_type = MessageType(data.get("message_type", "text"))
                metadata = data.get("metadata", {})
                
                # Store message
                message = await collaboration_manager.send_message(
                    room_id=room_id,
                    sender_id=user_id,
                    content=content,
                    message_type=msg_type,
                    metadata=metadata
                )
                
                if message:
                    # Broadcast to all participants
                    await connection_manager.broadcast_to_room(
                        room_id,
                        {
                            "type": "new_message",
                            "message": message
                        }
                    )
            
            elif message_type == "typing":
                # Broadcast typing indicator
                await connection_manager.broadcast_to_room(
                    room_id,
                    {
                        "type": "typing",
                        "user_id": user_id,
                        "is_typing": data.get("is_typing", False)
                    },
                    exclude_user=user_id
                )
            
            elif message_type == "request_ai_opinion":
                # Request AI doctor opinion
                specialty = data.get("specialty")
                await handle_ai_opinion_request(room_id, user_id, specialty)
            
            elif message_type == "ping":
                # Respond to ping
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        await connection_manager.disconnect(room_id, user_id)
        await collaboration_manager.leave_room(room_id, user_id)
        
        # Notify others
        await connection_manager.broadcast_to_room(
            room_id,
            {
                "type": "user_disconnected",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id} in room {room_id}: {e}")
        await connection_manager.disconnect(room_id, user_id)

async def validate_websocket_token(token: str, neo4j_client: Neo4jClient) -> Optional[Dict[str, Any]]:
    """Validate WebSocket authentication token"""
    
    # In production, implement proper JWT validation
    # For now, return mock user data
    
    # This should validate the token and return user data
    # Example implementation would decode JWT and verify against database
    
    return {
        "user_id": "user_" + token[:8],  # Mock user ID from token
        "name": "Dr. WebSocket User"
    }

async def handle_ai_opinion_request(room_id: str, requester_id: str, specialty: Optional[str] = None):
    """Handle request for AI doctor opinion"""
    
    try:
        # Get room and case context
        room = await collaboration_manager.get_room(room_id)
        if not room:
            return
        
        # Simulate AI doctor joining
        ai_doctor_id = f"ai_doctor_{specialty or 'general'}"
        ai_doctor_name = f"Dr. AI ({specialty or 'General'})"
        
        # Add AI doctor as participant
        await collaboration_manager.join_room(
            room_id=room_id,
            participant_id=ai_doctor_id,
            participant_name=ai_doctor_name,
            participant_role=ParticipantRole.AI_DOCTOR,
            participant_specialty=specialty
        )
        
        # Generate AI opinion based on case context
        # In production, this would use the actual AI doctor services
        opinion = await generate_ai_opinion(room.case_data, specialty)
        
        # Send AI opinion
        message = await collaboration_manager.send_message(
            room_id=room_id,
            sender_id=ai_doctor_id,
            content=opinion,
            message_type=MessageType.MEDICAL_OPINION,
            metadata={
                "confidence": 0.85,
                "based_on": "case_analysis"
            }
        )
        
        if message:
            # Broadcast to all participants
            await connection_manager.broadcast_to_room(
                room_id,
                {
                    "type": "new_message",
                    "message": message
                }
            )
            
    except Exception as e:
        logger.error(f"Failed to handle AI opinion request: {e}")

async def generate_ai_opinion(case_data: Dict[str, Any], specialty: Optional[str] = None) -> str:
    """Generate AI doctor opinion based on case data"""
    
    # In production, this would use actual AI services
    # For now, return template response
    
    base_opinion = "Based on the case presentation and available data, "
    
    if specialty == "cardiology":
        return base_opinion + "from a cardiology perspective, I recommend monitoring cardiac biomarkers and considering an ECG to rule out any cardiac involvement. The symptoms could indicate cardiovascular stress."
    elif specialty == "radiology":
        return base_opinion + "the imaging findings suggest we should consider additional views or advanced imaging modalities for better characterization of the abnormalities."
    else:
        return base_opinion + "I recommend a comprehensive evaluation including laboratory tests and imaging studies to establish a definitive diagnosis. Close monitoring is advised."