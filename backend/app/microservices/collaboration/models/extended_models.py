"""
Extended models for the collaboration microservice with additional fields
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

from .models import MessageType, EmojiReaction


class ExtendedMessage(BaseModel):
    """Extended message model with all fields used by chat service"""
    # Core fields from base Message
    message_id: str = Field(..., description="Unique message identifier")
    room_id: str = Field(..., description="Room ID where message was sent")
    sender_id: str = Field(..., description="ID of the message sender")
    sender_name: str = Field(..., description="Name of the sender")
    content: str = Field(..., description="Message content")
    message_type: MessageType = Field(default=MessageType.TEXT)
    
    # Extended fields for chat service
    reply_to_id: Optional[str] = Field(None, description="ID of message being replied to")
    attachments: List[Dict[str, Any]] = Field(default_factory=list, description="File attachments")
    mentions: List[str] = Field(default_factory=list, description="List of mentioned user IDs")
    reactions: Dict[str, List[str]] = Field(default_factory=dict, description="Reactions as emoji->user_ids mapping")
    
    # Status fields
    is_edited: bool = Field(default=False, description="Whether message has been edited")
    is_deleted: bool = Field(default=False, description="Whether message has been deleted")
    
    # Timestamp fields - using created_at instead of timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When message was created")
    edited_at: Optional[datetime] = Field(None, description="When message was last edited")
    deleted_at: Optional[datetime] = Field(None, description="When message was deleted")
    
    # For backward compatibility with different field names
    @property
    def timestamp(self) -> datetime:
        """Alias for created_at for backward compatibility"""
        return self.created_at
    
    @property
    def id(self) -> str:
        """Alias for message_id for backward compatibility"""
        return self.message_id
    
    class Config:
        # Allow using both field names
        populate_by_name = True


class ScreenShareStatus(str, Enum):
    """Screen share status states"""
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    ERROR = "error"


class ScreenShareQuality(str, Enum):
    """Screen share quality levels"""
    LOW = "low"       # 480p, 15fps, 500kbps
    MEDIUM = "medium" # 720p, 30fps, 1500kbps
    HIGH = "high"     # 1080p, 30fps, 3000kbps
    AUTO = "auto"     # Adaptive based on network


class ScreenShareSession(BaseModel):
    """Screen sharing session model"""
    session_id: str = Field(..., description="Unique screen share session ID")
    room_id: str = Field(..., description="Room ID where screen is being shared")
    user_id: str = Field(..., description="User ID sharing the screen")
    status: ScreenShareStatus = Field(default=ScreenShareStatus.INACTIVE)
    quality: ScreenShareQuality = Field(default=ScreenShareQuality.AUTO)
    
    # Stream details
    stream_id: Optional[str] = Field(None, description="WebRTC stream ID")
    track_id: Optional[str] = Field(None, description="WebRTC track ID")
    source_type: str = Field(default="screen", description="Source type: screen, window, tab")
    source_id: Optional[str] = Field(None, description="Specific source ID if applicable")
    
    # Quality metrics
    resolution: Optional[Dict[str, int]] = Field(None, description="Current resolution (width, height)")
    frame_rate: Optional[int] = Field(None, description="Current frame rate")
    bitrate: Optional[int] = Field(None, description="Current bitrate in kbps")
    packet_loss: Optional[float] = Field(None, description="Packet loss percentage")
    
    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    stopped_at: Optional[datetime] = None
    last_quality_update: Optional[datetime] = None
    
    # Permissions
    can_control: List[str] = Field(default_factory=list, description="User IDs who can control shared screen")
    viewers: List[str] = Field(default_factory=list, description="User IDs currently viewing")
    
    # Recording
    is_recording: bool = Field(default=False)
    recording_url: Optional[str] = None


class ScreenShareRequest(BaseModel):
    """Request to start screen sharing"""
    quality: ScreenShareQuality = Field(default=ScreenShareQuality.AUTO)
    source_type: str = Field(default="screen", description="screen, window, or tab")
    source_id: Optional[str] = Field(None, description="Specific source to share")
    enable_audio: bool = Field(default=False, description="Share system audio")
    allow_control: List[str] = Field(default_factory=list, description="User IDs allowed to control")


class ScreenSharePermission(BaseModel):
    """Screen share permission model"""
    room_id: str
    user_id: str
    can_share: bool = Field(default=True, description="Can start screen sharing")
    can_view: bool = Field(default=True, description="Can view screen shares")
    can_control: bool = Field(default=False, description="Can control shared screens")
    can_record: bool = Field(default=False, description="Can record screen shares")
    granted_by: str = Field(..., description="User ID who granted permission")
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class ScreenShareEvent(BaseModel):
    """Screen share event for notifications"""
    event_type: str = Field(..., description="start, stop, quality_change, error")
    room_id: str
    user_id: str
    user_name: str
    session_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ScreenShareConstraints(BaseModel):
    """WebRTC constraints for screen capture"""
    video: Dict[str, Any] = Field(
        default_factory=lambda: {
            "cursor": "always",
            "displaySurface": "monitor",
            "logicalSurface": True,
            "width": {"ideal": 1920, "max": 3840},
            "height": {"ideal": 1080, "max": 2160},
            "frameRate": {"ideal": 30, "max": 60}
        }
    )
    audio: Dict[str, Any] = Field(
        default_factory=lambda: {
            "echoCancellation": False,
            "noiseSuppression": False,
            "autoGainControl": False
        }
    )