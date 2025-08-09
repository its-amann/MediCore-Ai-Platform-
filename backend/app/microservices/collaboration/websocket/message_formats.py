"""
Standardized Message Formats for Collaboration WebSocket

This module defines consistent message structures for all WebSocket 
communication in the collaboration microservice.
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid


class MessageStatus(str, Enum):
    """Message delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class MessagePriority(str, Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class BaseMessage(BaseModel):
    """Base message structure for all WebSocket messages"""
    
    # Message metadata
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0")
    
    # Optional fields
    room_id: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    priority: MessagePriority = MessagePriority.NORMAL
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserMessage(BaseMessage):
    """Message sent by a user"""
    user_id: str
    username: Optional[str] = None
    user_role: Optional[str] = None
    
    @validator('user_id')
    def user_id_required(cls, v):
        if not v:
            raise ValueError('user_id is required for user messages')
        return v


class SystemMessage(BaseMessage):
    """Message sent by the system"""
    severity: str = Field(default="info", pattern="^(debug|info|warning|error|critical)$")
    source: str = Field(default="system")


class ChatMessage(UserMessage):
    """Chat message format"""
    type: str = "chat_message"
    content: str
    room_id: str
    
    # Optional fields
    reply_to: Optional[str] = None
    mentions: List[str] = Field(default_factory=list)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    edited: bool = False
    edited_at: Optional[datetime] = None
    
    # Message status
    status: MessageStatus = MessageStatus.PENDING
    read_by: List[str] = Field(default_factory=list)
    reactions: Dict[str, List[str]] = Field(default_factory=dict)
    
    @validator('content')
    def content_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v


class TypingIndicator(UserMessage):
    """Typing indicator message"""
    type: str = "typing_indicator"
    room_id: str
    is_typing: bool
    typing_in_thread: Optional[str] = None


class PresenceUpdate(UserMessage):
    """User presence update message"""
    type: str = "presence_update"
    status: str = Field(pattern="^(online|offline|away|busy|invisible)$")
    last_seen: Optional[datetime] = None
    status_message: Optional[str] = None


class RoomEvent(BaseMessage):
    """Room-related event message"""
    type: str = "room_event"
    room_id: str
    event_type: str
    data: Dict[str, Any]
    
    # Common event types
    # - user_joined
    # - user_left
    # - user_invited
    # - user_removed
    # - room_created
    # - room_updated
    # - room_deleted
    # - permissions_changed


class VideoCallSignal(UserMessage):
    """Video call signaling message"""
    type: str = "video_signal"
    room_id: str
    signal_type: str = Field(pattern="^(offer|answer|candidate|hangup|mute|unmute)$")
    target_user: Optional[str] = None
    data: Dict[str, Any]
    
    # Call metadata
    call_id: Optional[str] = None
    media_type: Optional[str] = Field(default="video", pattern="^(audio|video|screen)$")


class FileUploadNotification(UserMessage):
    """File upload notification message"""
    type: str = "file_upload"
    room_id: str
    file_id: str
    file_name: str
    file_size: int
    file_type: str
    mime_type: str
    
    # Optional fields
    thumbnail_url: Optional[str] = None
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    
    @validator('file_size')
    def validate_file_size(cls, v):
        if v <= 0:
            raise ValueError('File size must be positive')
        if v > 100 * 1024 * 1024:  # 100MB limit
            raise ValueError('File size exceeds maximum allowed (100MB)')
        return v


class ErrorMessage(SystemMessage):
    """Standardized error message"""
    type: str = "error"
    error_code: str
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retry_after: Optional[int] = None
    request_id: Optional[str] = None
    
    # User-friendly message
    user_message: Optional[str] = None
    
    @validator('user_message', always=True)
    def set_user_message(cls, v, values):
        if v:
            return v
        # Provide default user-friendly message based on error type
        error_type = values.get('error_type', '')
        defaults = {
            'authentication_error': 'Authentication failed. Please log in again.',
            'authorization_error': 'You do not have permission to perform this action.',
            'rate_limit_error': 'Too many requests. Please slow down.',
            'validation_error': 'Invalid input. Please check your data.',
            'internal_error': 'An unexpected error occurred. Please try again.'
        }
        return defaults.get(error_type, values.get('message', 'An error occurred'))


class NotificationMessage(SystemMessage):
    """System notification message"""
    type: str = "notification"
    title: str
    body: str
    category: str = Field(pattern="^(info|success|warning|error|announcement)$")
    
    # Optional fields
    icon: Optional[str] = None
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    expires_at: Optional[datetime] = None
    dismissible: bool = True


class MessageBuilder:
    """Helper class for building standardized messages"""
    
    @staticmethod
    def chat_message(
        user_id: str,
        room_id: str,
        content: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Build a chat message"""
        message = ChatMessage(
            user_id=user_id,
            room_id=room_id,
            content=content,
            **kwargs
        )
        return message.dict()
    
    @staticmethod
    def error_message(
        error_code: str,
        error_type: str,
        message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Build an error message"""
        error = ErrorMessage(
            error_code=error_code,
            error_type=error_type,
            message=message,
            **kwargs
        )
        return error.dict()
    
    @staticmethod
    def room_event(
        room_id: str,
        event_type: str,
        data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Build a room event message"""
        event = RoomEvent(
            room_id=room_id,
            event_type=event_type,
            data=data,
            **kwargs
        )
        return event.dict()
    
    @staticmethod
    def presence_update(
        user_id: str,
        status: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Build a presence update message"""
        update = PresenceUpdate(
            user_id=user_id,
            status=status,
            **kwargs
        )
        return update.dict()
    
    @staticmethod
    def typing_indicator(
        user_id: str,
        room_id: str,
        is_typing: bool,
        **kwargs
    ) -> Dict[str, Any]:
        """Build a typing indicator message"""
        indicator = TypingIndicator(
            user_id=user_id,
            room_id=room_id,
            is_typing=is_typing,
            **kwargs
        )
        return indicator.dict()
    
    @staticmethod
    def notification(
        title: str,
        body: str,
        category: str = "info",
        **kwargs
    ) -> Dict[str, Any]:
        """Build a notification message"""
        notification = NotificationMessage(
            title=title,
            body=body,
            category=category,
            **kwargs
        )
        return notification.dict()


class MessageValidator:
    """Validates incoming messages against expected formats"""
    
    # Message type to model mapping
    MESSAGE_MODELS = {
        "chat_message": ChatMessage,
        "typing_indicator": TypingIndicator,
        "presence_update": PresenceUpdate,
        "room_event": RoomEvent,
        "video_signal": VideoCallSignal,
        "file_upload": FileUploadNotification,
        "error": ErrorMessage,
        "notification": NotificationMessage
    }
    
    @classmethod
    def validate(cls, message_data: Dict[str, Any]) -> Union[BaseMessage, None]:
        """Validate a message and return the appropriate model instance"""
        message_type = message_data.get("type")
        
        if not message_type:
            raise ValueError("Message type is required")
        
        model_class = cls.MESSAGE_MODELS.get(message_type)
        if not model_class:
            # Try to validate as base message
            return BaseMessage(**message_data)
        
        try:
            return model_class(**message_data)
        except Exception as e:
            raise ValueError(f"Invalid message format for type {message_type}: {str(e)}")
    
    @classmethod
    def is_valid(cls, message_data: Dict[str, Any]) -> bool:
        """Check if a message is valid"""
        try:
            cls.validate(message_data)
            return True
        except:
            return False