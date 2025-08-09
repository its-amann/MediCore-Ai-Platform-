// Extended Collaboration Types for New Backend Features

// User Types
export enum UserType {
  DOCTOR = 'doctor',
  PATIENT = 'patient',
  STUDENT = 'student',
  TEACHER = 'teacher',
  ADMIN = 'admin'
}

// User Profile
export interface UserProfile {
  user_id: string;
  username: string;
  email: string;
  full_name?: string;
  user_type: UserType;
  profile_picture?: string;
  bio?: string;
  specialization?: string;
  institution?: string;
  license_number?: string;
  is_verified: boolean;
  verified_at?: string;
  created_at: string;
  updated_at: string;
  last_active?: string;
  profile_completion: number;
  preferences?: NotificationPreferences;
}

// Notification Types and Models
export enum NotificationType {
  JOIN_REQUEST = 'join_request',
  JOIN_APPROVED = 'join_approved',
  JOIN_REJECTED = 'join_rejected',
  ROOM_INVITE = 'room_invite',
  PARTICIPANT_JOINED = 'participant_joined',
  PARTICIPANT_LEFT = 'participant_left',
  NEW_MESSAGE = 'new_message',
  MENTION = 'mention',
  ROOM_STARTED = 'room_started',
  ROOM_CLOSING_SOON = 'room_closing_soon',
  ROOM_DISABLED = 'room_disabled',
  TEACHING_REMINDER = 'teaching_reminder',
  AI_RESPONSE = 'ai_response',
  SCREEN_SHARE_REQUEST = 'screen_share_request',
  RECORDING_STARTED = 'recording_started',
  RECORDING_STOPPED = 'recording_stopped'
}

export enum NotificationPriority {
  LOW = 'low',
  NORMAL = 'normal',
  URGENT = 'urgent'
}

export interface Notification {
  id: string;
  user_id: string;
  notification_type: NotificationType;
  priority: NotificationPriority;
  title: string;
  message: string;
  data?: Record<string, any>;
  is_read: boolean;
  read_at?: string;
  expires_at?: string;
  email_sent: boolean;
  push_sent: boolean;
  created_at: string;
}

export interface NotificationPreferences {
  user_id: string;
  email_enabled: boolean;
  push_enabled: boolean;
  urgent_only: boolean;
  quiet_hours_start: number | null | undefined;
  quiet_hours_end: number | null | undefined;
  join_requests: boolean;
  room_invitations: boolean;
  mentions: boolean;
  messages: boolean;
  ai_responses: boolean;
  teaching_reminders: boolean;
  room_updates: boolean;
  created_at: string;
  updated_at: string;
}

// Screen Sharing Models
export enum ScreenShareStatus {
  PENDING = 'pending',
  ACTIVE = 'active',
  PAUSED = 'paused',
  ENDED = 'ended',
  FAILED = 'failed'
}

export enum ScreenShareQuality {
  LOW = 'low',      // 480p
  MEDIUM = 'medium', // 720p
  HIGH = 'high',     // 1080p
  AUTO = 'auto'
}

export enum ScreenShareSourceType {
  SCREEN = 'screen',
  WINDOW = 'window',
  TAB = 'tab'
}

export interface ScreenShareSession {
  session_id: string;
  room_id: string;
  user_id: string;
  status: ScreenShareStatus;
  quality: ScreenShareQuality;
  source_type: ScreenShareSourceType;
  stream_id?: string;
  started_at: string;
  ended_at?: string;
  is_recording: boolean;
  viewers: string[];
  max_viewers: number;
  constraints?: ScreenShareConstraints;
}

export interface ScreenShareRequest {
  room_id: string;
  source_type: ScreenShareSourceType;
  quality?: ScreenShareQuality;
  record?: boolean;
  permissions?: ScreenSharePermissions;
}

export interface ScreenSharePermissions {
  can_share: boolean;
  can_view: boolean;
  can_control: boolean;
  can_record: boolean;
}

export interface ScreenShareConstraints {
  video: {
    cursor: string;
    displaySurface: string;
    width: { ideal: number; max: number };
    height: { ideal: number; max: number };
    frameRate: { ideal: number; max: number };
  };
  audio?: boolean;
}

export interface ScreenShareEvent {
  type: 'started' | 'stopped' | 'paused' | 'resumed' | 'quality_changed' | 'viewer_joined' | 'viewer_left';
  session_id: string;
  user_id: string;
  timestamp: string;
  data?: any;
}

// Extended Message Types
export interface ExtendedMessage {
  id: string;
  room_id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  message_type: 'text' | 'file' | 'image' | 'code' | 'system' | 'ai_response';
  timestamp: string;
  edited_at?: string;
  is_deleted: boolean;
  
  // New features
  reply_to?: string; // Message ID being replied to
  thread_id?: string;
  thread_count?: number;
  reactions: MessageReaction[];
  mentions: string[]; // User IDs mentioned
  attachments: MessageAttachment[];
  metadata?: Record<string, any>;
}

export interface MessageReaction {
  emoji: string;
  users: string[];
  count: number;
}

export interface MessageAttachment {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  url: string;
  thumbnail_url?: string;
  uploaded_at: string;
}

// WebRTC Models
export interface WebRTCSignal {
  type: 'offer' | 'answer' | 'ice-candidate' | 'media-state' | 'screen-share-offer' | 'screen-share-answer' | 'screen-share-candidate';
  from_user: string;
  to_user: string;
  data: any;
}

export interface VideoSession {
  session_id: string;
  room_id: string;
  participants: string[];
  started_at: string;
  ended_at?: string;
  is_recording: boolean;
  recording_url?: string;
  quality_metrics?: Record<string, any>;
}

export interface MediaState {
  video: boolean;
  audio: boolean;
  screen: boolean;
}

// Gemini Live Integration
export enum GeminiLiveMode {
  VOICE_CONVERSATION = 'voice_conversation',
  SCREEN_UNDERSTANDING = 'screen_understanding',
  MEDICAL_ANALYSIS = 'medical_analysis',
  TEACHING_ASSISTANT = 'teaching_assistant',
  CASE_DISCUSSION = 'case_discussion'
}

export interface GeminiLiveSession {
  session_id: string;
  room_id: string;
  mode: GeminiLiveMode;
  initiator_id: string;
  started_at: string;
  ended_at?: string;
  is_active: boolean;
  participants: string[];
  summary?: GeminiSessionSummary;
}

export interface GeminiSessionSummary {
  duration_seconds: number;
  mode: GeminiLiveMode;
  participants_count: number;
  key_topics: string[];
  key_insights: string[];
  action_items: string[];
  resources_mentioned: string[];
}

// AI Integration
export interface AIResponse {
  type: 'text' | 'audio' | 'medical_analysis' | 'teaching_assistance' | 'screen_analysis';
  content: string;
  metadata?: {
    confidence?: number;
    references?: string[];
    suggestions?: string[];
    visual_aids?: string[];
  };
  timestamp: string;
}

// Room Updates
export interface RoomUpdate {
  room_id: string;
  update_type: 'status' | 'settings' | 'participants' | 'permissions';
  updated_by: string;
  changes: Record<string, any>;
  timestamp: string;
}

// Enhanced Room Settings
export interface EnhancedRoomSettings {
  require_approval: boolean;
  auto_record: boolean;
  default_quality: ScreenShareQuality;
  max_screen_shares: number;
  ai_assistant_enabled: boolean;
  ai_mode?: GeminiLiveMode;
  notification_settings: {
    notify_on_join: boolean;
    notify_on_leave: boolean;
    notify_on_mention: boolean;
  };
  permissions: {
    can_share_screen: UserType[];
    can_use_ai: UserType[];
    can_record: UserType[];
    can_moderate: UserType[];
  };
}

// WebSocket Events
export interface CollaborationWebSocketEvent {
  type: string;
  room_id?: string;
  user_id?: string;
  data: any;
  timestamp: string;
}

// API Response Types
export interface NotificationListResponse {
  notifications: Notification[];
  total: number;
  unread_count: number;
}

export interface ScreenShareStatusResponse {
  active_sessions: ScreenShareSession[];
  permissions: ScreenSharePermissions;
}

export interface UserProfileResponse {
  profile: UserProfile;
  rooms: string[];
  stats: {
    total_sessions: number;
    total_messages: number;
    last_active: string;
  };
}

// Form/Request Types
export interface UpdateProfileRequest {
  full_name?: string;
  bio?: string;
  specialization?: string;
  institution?: string;
  user_type?: UserType;
}

export interface ScreenShareControlRequest {
  action: 'pause' | 'resume' | 'stop' | 'change_quality';
  quality?: ScreenShareQuality;
}

export interface NotificationActionRequest {
  action: 'mark_read' | 'mark_all_read' | 'delete';
  notification_ids?: string[];
}