"""
Models package for the collaboration microservice
"""

from .models import (
    # Enums
    RoomType,
    RoomStatus,
    MessageType,
    NotificationType,
    NotificationPriority,
    UserRole,
    UserType,
    RequestStatus,
    
    # Models
    UserProfile,
    ActiveUser,
    Room,
    Participant,
    EmojiReaction,
    Message,
    Notification,
    NotificationPreferences,
    VideoSession,
    AIAssistantContext,
    CreateRoomRequest,
    UpdateRoomRequest,
    SendMessageRequest,
    JoinRoomRequest,
    RoomJoinRequest,
    CreateJoinRequestModel,
    ProcessJoinRequestModel,
    StartClassRequest,
    WebRTCSignal,
    TypingIndicator,
    CreateUserProfileRequest,
    UpdateUserProfileRequest,
    SetUserTypeRequest,
    TeacherVerificationRequest,
    UpdatePreferencesRequest,
    UserSearchRequest,
    RoomService,
    RoomParticipant
)

from .extended_models import (
    ExtendedMessage,
    ScreenShareStatus,
    ScreenShareQuality,
    ScreenShareSession,
    ScreenShareRequest,
    ScreenSharePermission,
    ScreenShareEvent,
    ScreenShareConstraints
)

__all__ = [
    # Enums
    'RoomType',
    'RoomStatus',
    'MessageType',
    'NotificationType',
    'NotificationPriority',
    'UserRole',
    'UserType',
    'RequestStatus',
    
    # Models
    'UserProfile',
    'ActiveUser',
    'Room',
    'Participant',
    'EmojiReaction',
    'Message',
    'Notification',
    'NotificationPreferences',
    'VideoSession',
    'AIAssistantContext',
    'CreateRoomRequest',
    'UpdateRoomRequest',
    'SendMessageRequest',
    'JoinRoomRequest',
    'RoomJoinRequest',
    'CreateJoinRequestModel',
    'ProcessJoinRequestModel',
    'StartClassRequest',
    'WebRTCSignal',
    'TypingIndicator',
    'CreateUserProfileRequest',
    'UpdateUserProfileRequest',
    'SetUserTypeRequest',
    'TeacherVerificationRequest',
    'UpdatePreferencesRequest',
    'UserSearchRequest',
    'RoomService',
    'RoomParticipant',
    
    # Extended models
    'ExtendedMessage',
    'ScreenShareStatus',
    'ScreenShareQuality',
    'ScreenShareSession',
    'ScreenShareRequest',
    'ScreenSharePermission',
    'ScreenShareEvent',
    'ScreenShareConstraints'
]