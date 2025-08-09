"""
Data models for the Collaboration microservice
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class RoomType(str, Enum):
    """Types of collaboration rooms"""
    CASE_DISCUSSION = "case_discussion"
    TEACHING = "teaching"


class RoomStatus(str, Enum):
    """Room status states"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CLOSED = "closed"
    SCHEDULED = "scheduled"
    DISABLED = "disabled"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MessageType(str, Enum):
    """Types of messages"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"
    SYSTEM = "system"
    AI_RESPONSE = "ai_response"


class NotificationType(str, Enum):
    """Types of notifications"""
    # Room-related
    ROOM_INVITE = "room_invite"
    ROOM_STARTED = "room_started"
    ROOM_ENDED = "room_ended"
    ROOM_DISABLED = "room_disabled"
    ROOM_CLOSING_SOON = "room_closing_soon"
    
    # Join request-related
    JOIN_REQUEST = "join_request"
    JOIN_APPROVED = "join_approved"
    JOIN_REJECTED = "join_rejected"
    
    # Participant-related
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    PARTICIPANT_JOINED = "participant_joined"
    PARTICIPANT_LEFT = "participant_left"
    
    # Message-related
    NEW_MESSAGE = "new_message"
    MENTION = "mention"
    AI_RESPONSE = "ai_response"
    
    # Teaching session-related
    TEACHING_REMINDER = "teaching_reminder"
    TEACHING_STARTED = "teaching_started"
    TEACHING_ENDED = "teaching_ended"


class NotificationPriority(str, Enum):
    """Priority levels for notifications"""
    URGENT = "urgent"
    NORMAL = "normal"
    LOW = "low"


class UserRole(str, Enum):
    """User roles in a room"""
    HOST = "host"
    CO_HOST = "co_host"
    PARTICIPANT = "participant"
    VIEWER = "viewer"


class UserType(str, Enum):
    """Types of users in the system"""
    TEACHER = "teacher"
    PATIENT = "patient"
    STUDENT = "student"
    DOCTOR = "doctor"
    ADMIN = "admin"


class UserProfile(BaseModel):
    """User profile model with type-specific information"""
    user_id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Username for the user")
    full_name: str = Field(..., description="User's full name")
    email: str = Field(..., description="User's email address")
    user_type: UserType = Field(..., description="Type of user")
    institution: Optional[str] = Field(None, description="Institution name for teachers")
    specialization: Optional[str] = Field(None, description="Medical specialization for doctors")
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    profile_picture: Optional[str] = Field(None, description="URL to profile picture")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_verified: bool = Field(default=False, description="Whether the user is verified")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    # Additional fields for different user types
    license_number: Optional[str] = Field(None, description="Medical license number for doctors")
    student_id: Optional[str] = Field(None, description="Student ID for students")
    graduation_year: Optional[int] = Field(None, description="Graduation year for students")
    department: Optional[str] = Field(None, description="Department for teachers/doctors")
    years_of_experience: Optional[int] = Field(None, description="Years of experience for teachers/doctors")
    # Statistics
    profile_completeness: float = Field(default=0.0, ge=0.0, le=100.0, description="Profile completeness percentage")
    last_login: Optional[datetime] = None
    is_active: bool = Field(default=True, description="Whether the user is active")
    # Privacy settings
    is_profile_public: bool = Field(default=True, description="Whether profile is public")
    show_email: bool = Field(default=False, description="Whether to show email publicly")
    show_institution: bool = Field(default=True, description="Whether to show institution publicly")
    show_real_name: bool = Field(default=True, description="Whether to show real name publicly")


class RequestStatus(str, Enum):
    """Status of room join requests"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ActiveUser(BaseModel):
    """Active user in a room"""
    user_id: str
    username: str
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class Room(BaseModel):
    """Collaboration room model"""
    room_id: str = Field(..., description="Unique room identifier")
    name: str = Field(..., description="Room name")
    description: Optional[str] = Field(None, description="Room description")
    room_type: RoomType = Field(..., description="Type of room")
    status: RoomStatus = Field(default=RoomStatus.ACTIVE)
    max_participants: int = Field(default=10, ge=2, le=100)
    current_participants: int = Field(default=0, ge=0)
    is_public: bool = Field(default=True)
    password_protected: bool = Field(default=False)
    room_password: Optional[str] = Field(None, description="Room password if protected")
    created_by: Dict[str, Any] = Field(..., description="User info who created the room")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    settings: Dict[str, Any] = Field(default_factory=dict, description="Additional room configurations")
    voice_enabled: bool = Field(default=False, description="Voice chat enabled for teaching rooms")
    screen_sharing: bool = Field(default=False, description="Screen sharing enabled for teaching rooms")
    recording_enabled: bool = Field(default=False, description="Recording enabled for teaching rooms")
    active_users: List[ActiveUser] = Field(default_factory=list, description="Currently active users with last seen")
    # Teaching room specific fields
    subject: Optional[str] = Field(None, description="Subject for teaching rooms")
    scheduled_start: Optional[datetime] = Field(None, description="Scheduled start time")
    scheduled_end: Optional[datetime] = Field(None, description="Scheduled end time")
    institution: Optional[str] = Field(None, description="Institution for teaching rooms")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    recording_url: Optional[str] = Field(None, description="URL to recording if available")
    class_materials: List[Dict[str, Any]] = Field(default_factory=list, description="Class materials links")
    is_class_active: bool = Field(default=False, description="Whether class is currently active")


class Participant(BaseModel):
    """Participant model for collaboration rooms"""
    user_id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., description="Username")
    user_type: UserType = Field(..., description="Type of user")
    role: UserRole = Field(default=UserRole.PARTICIPANT, description="Role in the room")
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    permissions: List[str] = Field(default_factory=list, description="List of permissions in the room")


class EmojiReaction(BaseModel):
    """Emoji reaction on a message"""
    emoji: str
    user_id: str
    username: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Message(BaseModel):
    """Chat message model"""
    message_id: str = Field(..., description="Unique message identifier")
    room_id: str = Field(..., description="Room ID where message was sent")
    sender_id: str = Field(..., description="ID of the message sender")
    sender_name: str = Field(..., description="Name of the sender")
    content: str = Field(..., description="Message content")
    message_type: MessageType = Field(default=MessageType.TEXT)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    edited_at: Optional[datetime] = None
    is_edited: bool = Field(default=False)
    reactions: List[EmojiReaction] = Field(default_factory=list, description="List of emoji reactions")
    thread_id: Optional[str] = Field(None, description="Thread ID for threading support")


class Notification(BaseModel):
    """Notification model"""
    id: str = Field(..., description="Unique notification identifier")
    user_id: str = Field(..., description="Recipient user ID")
    notification_type: NotificationType
    priority: NotificationPriority = Field(default=NotificationPriority.NORMAL)
    title: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    email_sent: bool = Field(default=False, description="Whether email notification was sent")
    push_sent: bool = Field(default=False, description="Whether push notification was sent")


class NotificationPreferences(BaseModel):
    """User notification preferences"""
    user_id: str = Field(..., description="User ID")
    email_enabled: bool = Field(default=True, description="Enable email notifications")
    push_enabled: bool = Field(default=True, description="Enable push notifications")
    # Notification type preferences
    join_requests: bool = Field(default=True, description="Notify for join requests")
    room_invitations: bool = Field(default=True, description="Notify for room invitations")
    mentions: bool = Field(default=True, description="Notify when mentioned")
    messages: bool = Field(default=True, description="Notify for new messages")
    ai_responses: bool = Field(default=True, description="Notify for AI responses")
    teaching_reminders: bool = Field(default=True, description="Notify for teaching session reminders")
    room_updates: bool = Field(default=True, description="Notify for room status changes")
    # Priority preferences
    urgent_only: bool = Field(default=False, description="Only notify for urgent notifications")
    quiet_hours_start: Optional[int] = Field(None, ge=0, le=23, description="Start hour for quiet mode")
    quiet_hours_end: Optional[int] = Field(None, ge=0, le=23, description="End hour for quiet mode")
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VideoSession(BaseModel):
    """Video/audio session model"""
    room_id: str
    session_id: str
    participants: List[str] = Field(default_factory=list)
    is_recording: bool = False
    recording_url: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    quality_metrics: Dict[str, Any] = Field(default_factory=dict)


class AIAssistantContext(BaseModel):
    """Context for AI assistant in collaboration"""
    room_id: str
    conversation_history: List[Message] = Field(default_factory=list)
    medical_context: Dict[str, Any] = Field(default_factory=dict)
    participant_roles: Dict[str, str] = Field(default_factory=dict)
    active_case_id: Optional[str] = None
    ai_enabled: bool = True
    ai_suggestions: List[Dict[str, Any]] = Field(default_factory=list)


class RoomJoinRequest(BaseModel):
    """Room join request model"""
    request_id: str = Field(..., description="Unique request identifier")
    room_id: str = Field(..., description="Room ID for the join request")
    user_id: str = Field(..., description="User ID requesting to join")
    user_name: str = Field(..., description="User name requesting to join")
    status: RequestStatus = Field(default=RequestStatus.PENDING)
    message: Optional[str] = Field(None, description="Optional message from requester")
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    processed_by: Optional[str] = Field(None, description="User ID who processed the request")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection if applicable")


# Request/Response models

class CreateRoomRequest(BaseModel):
    """Request model for creating a room"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    type: RoomType = Field(..., alias="room_type")
    max_participants: int = Field(default=10, ge=2, le=100)
    is_public: bool = Field(default=True)
    password_protected: bool = Field(default=False)
    room_password: Optional[str] = Field(None, min_length=6)
    settings: Dict[str, Any] = Field(default_factory=dict)
    voice_enabled: bool = Field(default=False)
    screen_sharing: bool = Field(default=False)
    recording_enabled: bool = Field(default=False)
    scheduled_start: Optional[datetime] = Field(None, description="Scheduled start time")
    scheduled_end: Optional[datetime] = Field(None, description="Scheduled end time")
    # Teaching room specific fields
    subject: Optional[str] = Field(None, description="Subject for teaching rooms")
    institution: Optional[str] = Field(None, description="Institution for teaching rooms")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    require_approval: bool = Field(default=False, description="Whether join requests require approval")
    
    class Config:
        populate_by_name = True


class UpdateRoomRequest(BaseModel):
    """Request model for updating a room"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    max_participants: Optional[int] = Field(None, ge=2, le=100)
    status: Optional[RoomStatus] = None
    is_public: Optional[bool] = None
    password_protected: Optional[bool] = None
    room_password: Optional[str] = Field(None, min_length=6)
    settings: Optional[Dict[str, Any]] = None
    voice_enabled: Optional[bool] = None
    screen_sharing: Optional[bool] = None
    recording_enabled: Optional[bool] = None


class SendMessageRequest(BaseModel):
    """Request model for sending a message"""
    content: str = Field(..., min_length=1, max_length=5000)
    message_type: MessageType = MessageType.TEXT
    reply_to_id: Optional[str] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    mentions: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class JoinRoomRequest(BaseModel):
    """Request model for joining a room"""
    room_password: Optional[str] = None
    password: Optional[str] = None  # Alternative field name
    role: UserRole = UserRole.PARTICIPANT


class WebRTCSignal(BaseModel):
    """WebRTC signaling data"""
    type: str  # "offer", "answer", "ice-candidate"
    from_user: str
    to_user: str
    data: Dict[str, Any]


class TypingIndicator(BaseModel):
    """Typing indicator model"""
    room_id: str
    user_id: str
    user_name: str
    is_typing: bool


# User Profile Request/Response models

class CreateUserProfileRequest(BaseModel):
    """Request model for creating a user profile"""
    user_id: str = Field(..., description="Unique user identifier")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    full_name: str = Field(..., min_length=1, max_length=100, description="Full name")
    email: str = Field(..., description="Email address")
    user_type: UserType = Field(..., description="Type of user")
    institution: Optional[str] = Field(None, max_length=200, description="Institution for teachers")
    specialization: Optional[str] = Field(None, max_length=100, description="Specialization for doctors")
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")


class UpdateUserProfileRequest(BaseModel):
    """Request model for updating user profile"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    profile_picture: Optional[str] = None
    institution: Optional[str] = Field(None, max_length=200)
    specialization: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    years_of_experience: Optional[int] = Field(None, ge=0, le=100)
    is_profile_public: Optional[bool] = None
    show_email: Optional[bool] = None
    show_institution: Optional[bool] = None


class SetUserTypeRequest(BaseModel):
    """Request model for changing user type"""
    user_type: UserType = Field(..., description="New user type")
    verification_data: Optional[Dict[str, Any]] = Field(None, description="Verification data if required")


class TeacherVerificationRequest(BaseModel):
    """Request model for teacher verification"""
    institution_name: str = Field(..., min_length=1, max_length=200)
    institution_email: Optional[str] = Field(None, description="Institutional email")
    institution_id: Optional[str] = Field(None, description="Institution ID")
    verification_document: Optional[str] = Field(None, description="Document URL for verification")


class CreateJoinRequestModel(BaseModel):
    """Request model for creating a join request"""
    message: Optional[str] = Field(None, max_length=500, description="Optional message to room creator")


class ProcessJoinRequestModel(BaseModel):
    """Request model for processing (approving/rejecting) a join request"""
    approve: bool = Field(..., description="Whether to approve or reject the request")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for rejection")


class StartClassRequest(BaseModel):
    """Request model for starting a teaching class"""
    enable_recording: bool = Field(default=False, description="Whether to record the class")
    enable_chat: bool = Field(default=True, description="Whether to enable chat during class")
    enable_qa: bool = Field(default=True, description="Whether to enable Q&A during class")


class UpdatePreferencesRequest(BaseModel):
    """Request model for updating user preferences"""
    language: Optional[str] = Field(None, min_length=2, max_length=5)
    timezone: Optional[str] = Field(None, max_length=50)
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    theme: Optional[str] = Field(None, description="UI theme")
    accessibility_mode: Optional[bool] = None
    teaching_availability: Optional[Dict[str, Any]] = None
    consultation_hours: Optional[Dict[str, Any]] = None
    additional_preferences: Optional[Dict[str, Any]] = Field(None, description="Other preferences")


class UserSearchRequest(BaseModel):
    """Request model for searching users"""
    query: str = Field(..., min_length=1, max_length=100, description="Search query")
    user_types: Optional[List[UserType]] = Field(None, description="Filter by user types")
    limit: int = Field(default=50, ge=1, le=200, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")


# Additional models for room_service.py

class RoomService(BaseModel):
    """Room model for room service (simplified version)"""
    id: str
    name: str
    description: Optional[str] = None
    room_type: RoomType
    creator_id: str
    max_participants: int = 10
    is_public: bool = True
    password: Optional[str] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    status: RoomStatus = RoomStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RoomParticipant(BaseModel):
    """Room participant model for room service"""
    room_id: str
    user_id: str
    user_name: str
    user_role: UserRole = UserRole.PARTICIPANT
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    left_at: Optional[datetime] = None
    is_active: bool = True
    video_enabled: bool = False
    audio_enabled: bool = False
    screen_sharing: bool = False
    hand_raised: bool = False
    # Enhanced tracking fields
    last_seen: Optional[datetime] = None
    is_currently_active: bool = True
    last_login: Optional[datetime] = None