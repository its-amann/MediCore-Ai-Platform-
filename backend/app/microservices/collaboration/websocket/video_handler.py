"""
WebSocket handler for video/audio functionality with teaching room support
"""

from typing import Dict, Any, Optional, Set
import logging
import asyncio
from datetime import datetime
from dataclasses import dataclass, field

from ..services.video_service import VideoService
from ..services.room_service import RoomService
from ..models import WebRTCSignal

logger = logging.getLogger(__name__)


@dataclass
class PeerConnection:
    """Represents a WebRTC peer connection"""
    user_id: str
    room_id: str
    connection_state: str = "new"  # new, connecting, connected, disconnected, failed
    video_enabled: bool = True
    audio_enabled: bool = True
    screen_sharing: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TeachingRoomInfo:
    """Teaching room specific information"""
    institution_name: str
    class_name: str
    subject: str
    teacher_id: str
    teacher_name: str
    max_participants: int = 50
    recording_enabled: bool = False
    ai_assistant_enabled: bool = True


class VideoHandler:
    """Handles WebSocket events for video/audio functionality with teaching room support"""
    
    def __init__(self):
        self.video_service = VideoService()
        self.room_service = RoomService()
        
        # Track peer connections per room
        self.peer_connections: Dict[str, Dict[str, PeerConnection]] = {}
        
        # Track teaching room info
        self.teaching_rooms: Dict[str, TeachingRoomInfo] = {}
        
        # Track active recordings
        self.active_recordings: Set[str] = set()
        
        # Track hand raises
        self.hand_raises: Dict[str, Set[str]] = {}  # room_id -> set of user_ids
        
        # Maximum participants per room
        self.MAX_PARTICIPANTS = 50
    
    async def handle_join_video(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle joining a video session"""
        try:
            room_id = data.get("room_id")
            
            if not room_id:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": "room_id is required"
                    }
                )
                return
            
            # Verify user is in room
            participant = await self.room_service.get_participant(room_id, user_id)
            if not participant or not participant.is_active:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": "Not a member of this room"
                    }
                )
                return
            
            # Join video session
            session_info = await self.video_service.join_video_session(
                room_id=room_id,
                user_id=user_id
            )
            
            # Send session info to user
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "video_session_joined",
                    "session_info": session_info
                }
            )
            
            # Notify other participants
            await connection_manager.broadcast_to_room(
                room_id,
                {
                    "type": "participant_joined_video",
                    "user_id": user_id,
                    "user_name": participant.user_name
                },
                exclude_user=user_id
            )
            
        except Exception as e:
            logger.error(f"Error handling join_video: {e}")
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "Failed to join video session"
                }
            )
    
    async def handle_leave_video(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle leaving a video session"""
        room_id = data.get("room_id")
        
        if not room_id:
            return
        
        # Leave video session
        success = await self.video_service.leave_video_session(
            room_id=room_id,
            user_id=user_id
        )
        
        if success:
            # Notify other participants
            await connection_manager.broadcast_to_room(
                room_id,
                {
                    "type": "participant_left_video",
                    "user_id": user_id
                },
                exclude_user=user_id
            )
    
    async def handle_webrtc_offer(
        self,
        room_id: str,
        user_id: str,
        offer_data: Dict[str, Any],
        connection_manager
    ):
        """Process WebRTC offers"""
        try:
            # Verify user is in room
            participant = await self.room_service.get_participant(room_id, user_id)
            if not participant or not participant.is_active:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": "Not authorized for this room"
                    }
                )
                return
            
            # Update peer connection state
            if room_id not in self.peer_connections:
                self.peer_connections[room_id] = {}
            
            self.peer_connections[room_id][user_id] = PeerConnection(
                user_id=user_id,
                room_id=room_id,
                connection_state="connecting"
            )
            
            # Broadcast offer to other participants
            await connection_manager.broadcast_to_room(
                room_id,
                {
                    "type": "webrtc_offer",
                    "from_user": user_id,
                    "offer": offer_data
                },
                exclude_user=user_id
            )
            
            logger.info(f"WebRTC offer processed from {user_id} in room {room_id}")
            
        except Exception as e:
            logger.error(f"Error handling WebRTC offer: {e}")
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "Failed to process WebRTC offer"
                }
            )
    
    async def handle_webrtc_answer(
        self,
        room_id: str,
        user_id: str,
        answer_data: Dict[str, Any],
        connection_manager
    ):
        """Process WebRTC answers"""
        try:
            # Verify user is in room
            participant = await self.room_service.get_participant(room_id, user_id)
            if not participant or not participant.is_active:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": "Not authorized for this room"
                    }
                )
                return
            
            # Update peer connection state
            if room_id in self.peer_connections and user_id in self.peer_connections[room_id]:
                self.peer_connections[room_id][user_id].connection_state = "connected"
                self.peer_connections[room_id][user_id].updated_at = datetime.utcnow()
            
            # Send answer to the target user
            target_user = answer_data.get("target_user")
            if target_user and connection_manager.is_user_online(target_user):
                await connection_manager.send_personal_message(
                    target_user,
                    {
                        "type": "webrtc_answer",
                        "from_user": user_id,
                        "answer": answer_data.get("answer")
                    }
                )
            
            logger.info(f"WebRTC answer processed from {user_id} in room {room_id}")
            
        except Exception as e:
            logger.error(f"Error handling WebRTC answer: {e}")
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "Failed to process WebRTC answer"
                }
            )
    
    async def handle_ice_candidate(
        self,
        room_id: str,
        user_id: str,
        candidate_data: Dict[str, Any],
        connection_manager
    ):
        """Handle ICE candidates for WebRTC"""
        try:
            # Verify user is in room
            participant = await self.room_service.get_participant(room_id, user_id)
            if not participant or not participant.is_active:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": "Not authorized for this room"
                    }
                )
                return
            
            # Send ICE candidate to target user
            target_user = candidate_data.get("target_user")
            if target_user and connection_manager.is_user_online(target_user):
                await connection_manager.send_personal_message(
                    target_user,
                    {
                        "type": "ice_candidate",
                        "from_user": user_id,
                        "candidate": candidate_data.get("candidate")
                    }
                )
            
            logger.debug(f"ICE candidate forwarded from {user_id} to {target_user}")
            
        except Exception as e:
            logger.error(f"Error handling ICE candidate: {e}")
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "Failed to process ICE candidate"
                }
            )
    
    async def handle_webrtc_signal(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle WebRTC signaling (offer/answer/ice candidate) - backward compatibility"""
        signal_type = data.get("signal_type")
        room_id = data.get("room_id")
        
        if not signal_type or not room_id:
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "signal_type and room_id are required"
                }
            )
            return
        
        # Route to appropriate handler based on signal type
        if signal_type == "offer":
            await self.handle_webrtc_offer(room_id, user_id, data.get("signal_data", {}), connection_manager)
        elif signal_type == "answer":
            await self.handle_webrtc_answer(room_id, user_id, data.get("signal_data", {}), connection_manager)
        elif signal_type == "ice_candidate":
            await self.handle_ice_candidate(room_id, user_id, data.get("signal_data", {}), connection_manager)
        else:
            # Legacy handling for backward compatibility
            to_user = data.get("to_user")
            signal_data = data.get("signal_data")
            
            if not to_user or not signal_data:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": "to_user and signal_data are required"
                    }
                )
                return
            
            # Create WebRTC signal
            signal = WebRTCSignal(
                type=signal_type,
                from_user=user_id,
                to_user=to_user,
                data=signal_data
            )
            
            # Store signal for retrieval
            await self.video_service.handle_webrtc_signal(signal)
            
            # Send directly to target user if online
            if connection_manager.is_user_online(to_user):
                await connection_manager.send_personal_message(
                    to_user,
                    {
                        "type": "webrtc_signal",
                        "signal": signal.dict()
                    }
                )
    
    async def toggle_video(
        self,
        room_id: str,
        user_id: str,
        enabled: bool,
        connection_manager
    ):
        """Toggle video stream for a user"""
        try:
            # Verify user is in room
            participant = await self.room_service.get_participant(room_id, user_id)
            if not participant or not participant.is_active:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": "Not authorized for this room"
                    }
                )
                return False
            
            # Update peer connection state
            if room_id in self.peer_connections and user_id in self.peer_connections[room_id]:
                self.peer_connections[room_id][user_id].video_enabled = enabled
                self.peer_connections[room_id][user_id].updated_at = datetime.utcnow()
            
            # Update participant status
            await self.room_service.update_participant_status(
                room_id=room_id,
                user_id=user_id,
                video_enabled=enabled
            )
            
            # Notify all participants
            await connection_manager.broadcast_to_room(
                room_id,
                {
                    "type": "participant_video_toggle",
                    "user_id": user_id,
                    "video_enabled": enabled
                }
            )
            
            logger.info(f"Video toggled for {user_id} in room {room_id}: {enabled}")
            return True
            
        except Exception as e:
            logger.error(f"Error toggling video: {e}")
            return False
    
    async def handle_toggle_video(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle toggling video on/off - WebSocket handler"""
        room_id = data.get("room_id")
        enabled = data.get("enabled", False)
        
        if not room_id:
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "room_id is required"
                }
            )
            return
        
        await self.toggle_video(room_id, user_id, enabled, connection_manager)
    
    async def toggle_audio(
        self,
        room_id: str,
        user_id: str,
        enabled: bool,
        connection_manager
    ):
        """Toggle audio stream for a user"""
        try:
            # Verify user is in room
            participant = await self.room_service.get_participant(room_id, user_id)
            if not participant or not participant.is_active:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": "Not authorized for this room"
                    }
                )
                return False
            
            # Update peer connection state
            if room_id in self.peer_connections and user_id in self.peer_connections[room_id]:
                self.peer_connections[room_id][user_id].audio_enabled = enabled
                self.peer_connections[room_id][user_id].updated_at = datetime.utcnow()
            
            # Update participant status
            await self.room_service.update_participant_status(
                room_id=room_id,
                user_id=user_id,
                audio_enabled=enabled
            )
            
            # Notify all participants
            await connection_manager.broadcast_to_room(
                room_id,
                {
                    "type": "participant_audio_toggle",
                    "user_id": user_id,
                    "audio_enabled": enabled
                }
            )
            
            logger.info(f"Audio toggled for {user_id} in room {room_id}: {enabled}")
            return True
            
        except Exception as e:
            logger.error(f"Error toggling audio: {e}")
            return False
    
    async def handle_toggle_audio(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle toggling audio on/off - WebSocket handler"""
        room_id = data.get("room_id")
        enabled = data.get("enabled", True)
        
        if not room_id:
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "room_id is required"
                }
            )
            return
        
        await self.toggle_audio(room_id, user_id, enabled, connection_manager)
    
    async def start_screen_share(
        self,
        room_id: str,
        user_id: str,
        connection_manager
    ):
        """Start screen sharing"""
        try:
            # Verify user is in room
            participant = await self.room_service.get_participant(room_id, user_id)
            if not participant or not participant.is_active:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": "Not authorized for this room"
                    }
                )
                return False
            
            # Check if someone else is already sharing in teaching rooms
            if room_id in self.teaching_rooms:
                for peer_id, peer in self.peer_connections.get(room_id, {}).items():
                    if peer_id != user_id and peer.screen_sharing:
                        await connection_manager.send_personal_message(
                            user_id,
                            {
                                "type": "error",
                                "message": "Another user is already sharing their screen"
                            }
                        )
                        return False
            
            # Update peer connection state
            if room_id in self.peer_connections and user_id in self.peer_connections[room_id]:
                self.peer_connections[room_id][user_id].screen_sharing = True
                self.peer_connections[room_id][user_id].updated_at = datetime.utcnow()
            
            # Update participant status
            await self.room_service.update_participant_status(
                room_id=room_id,
                user_id=user_id,
                screen_sharing=True
            )
            
            # Handle screen share in video service
            await self.video_service.handle_screen_share(
                room_id=room_id,
                user_id=user_id,
                is_sharing=True
            )
            
            # Notify all participants
            await connection_manager.broadcast_to_room(
                room_id,
                {
                    "type": "screen_share_started",
                    "user_id": user_id,
                    "user_name": participant.user_name
                }
            )
            
            logger.info(f"Screen share started by {user_id} in room {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting screen share: {e}")
            return False
    
    async def stop_screen_share(
        self,
        room_id: str,
        user_id: str,
        connection_manager
    ):
        """Stop screen sharing"""
        try:
            # Verify user is in room
            participant = await self.room_service.get_participant(room_id, user_id)
            if not participant or not participant.is_active:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": "Not authorized for this room"
                    }
                )
                return False
            
            # Update peer connection state
            if room_id in self.peer_connections and user_id in self.peer_connections[room_id]:
                self.peer_connections[room_id][user_id].screen_sharing = False
                self.peer_connections[room_id][user_id].updated_at = datetime.utcnow()
            
            # Update participant status
            await self.room_service.update_participant_status(
                room_id=room_id,
                user_id=user_id,
                screen_sharing=False
            )
            
            # Handle screen share in video service
            await self.video_service.handle_screen_share(
                room_id=room_id,
                user_id=user_id,
                is_sharing=False
            )
            
            # Notify all participants
            await connection_manager.broadcast_to_room(
                room_id,
                {
                    "type": "screen_share_stopped",
                    "user_id": user_id
                }
            )
            
            logger.info(f"Screen share stopped by {user_id} in room {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping screen share: {e}")
            return False
    
    async def handle_screen_share(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle screen sharing toggle - WebSocket handler"""
        room_id = data.get("room_id")
        is_sharing = data.get("is_sharing", False)
        
        if not room_id:
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "room_id is required"
                }
            )
            return
        
        if is_sharing:
            await self.start_screen_share(room_id, user_id, connection_manager)
        else:
            await self.stop_screen_share(room_id, user_id, connection_manager)
    
    async def handle_raise_hand(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle raise hand toggle"""
        room_id = data.get("room_id")
        raised = data.get("raised", False)
        
        if not room_id:
            return
        
        # Update participant status
        participant = await self.room_service.update_participant_status(
            room_id=room_id,
            user_id=user_id,
            hand_raised=raised
        )
        
        if participant:
            # Notify all participants including hosts
            await connection_manager.broadcast_to_room(
                room_id,
                {
                    "type": "hand_raised",
                    "user_id": user_id,
                    "user_name": participant.user_name,
                    "raised": raised
                }
            )
    
    async def start_recording(
        self,
        room_id: str,
        user_id: str,
        connection_manager
    ):
        """Start session recording"""
        try:
            # Verify user is in room and has permission
            participant = await self.room_service.get_participant(room_id, user_id)
            if not participant or not participant.is_active:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": "Not authorized for this room"
                    }
                )
                return False
            
            # Check if user is host or co-host (or teacher in teaching rooms)
            is_teacher = room_id in self.teaching_rooms and self.teaching_rooms[room_id].teacher_id == user_id
            if not is_teacher and participant.user_role not in ["HOST", "CO_HOST"]:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": "Only hosts or teachers can start recording"
                    }
                )
                return False
            
            # Check if recording is already active
            if room_id in self.active_recordings:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": "Recording is already active for this room"
                    }
                )
                return False
            
            # Start recording
            success = await self.video_service.start_recording(
                room_id=room_id,
                user_id=user_id
            )
            
            if success:
                # Track active recording
                self.active_recordings.add(room_id)
                
                # Notify all participants
                await connection_manager.broadcast_to_room(
                    room_id,
                    {
                        "type": "recording_started",
                        "started_by": user_id,
                        "started_by_name": participant.user_name,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                logger.info(f"Recording started by {user_id} in room {room_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            return False
    
    async def handle_start_recording(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle starting session recording - WebSocket handler"""
        room_id = data.get("room_id")
        
        if not room_id:
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "room_id is required"
                }
            )
            return
        
        await self.start_recording(room_id, user_id, connection_manager)
    
    async def handle_stop_recording(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle stopping session recording"""
        room_id = data.get("room_id")
        
        if not room_id:
            return
        
        # Check if user is host or co-host
        participant = await self.room_service.get_participant(room_id, user_id)
        if not participant or participant.user_role not in ["HOST", "CO_HOST"]:
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "Only hosts can stop recording"
                }
            )
            return
        
        # Stop recording
        recording_url = await self.video_service.stop_recording(
            room_id=room_id,
            user_id=user_id
        )
        
        if recording_url:
            # Notify all participants
            await connection_manager.broadcast_to_room(
                room_id,
                {
                    "type": "recording_stopped",
                    "stopped_by": user_id,
                    "recording_url": recording_url
                }
            )
    
    async def handle_quality_report(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle quality metrics reporting"""
        room_id = data.get("room_id")
        metrics = data.get("metrics", {})
        
        if not room_id:
            return
        
        # Update quality metrics
        await self.video_service.update_quality_metrics(
            room_id=room_id,
            user_id=user_id,
            metrics=metrics
        )


# Create video handler instance
video_handler = VideoHandler()

# Register event handlers
def register_video_handlers(websocket_manager):
    """Register all video-related WebSocket event handlers"""
    websocket_manager.register_handler("join_video", video_handler.handle_join_video)
    websocket_manager.register_handler("leave_video", video_handler.handle_leave_video)
    websocket_manager.register_handler("webrtc_signal", video_handler.handle_webrtc_signal)
    websocket_manager.register_handler("toggle_video", video_handler.handle_toggle_video)
    websocket_manager.register_handler("toggle_audio", video_handler.handle_toggle_audio)
    websocket_manager.register_handler("screen_share", video_handler.handle_screen_share)
    websocket_manager.register_handler("raise_hand", video_handler.handle_raise_hand)
    websocket_manager.register_handler("start_recording", video_handler.handle_start_recording)
    websocket_manager.register_handler("stop_recording", video_handler.handle_stop_recording)
    websocket_manager.register_handler("quality_report", video_handler.handle_quality_report)