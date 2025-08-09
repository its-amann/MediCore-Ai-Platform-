// 009_collaboration_relationships.cypher
// Unified Medical AI Platform - Collaboration Relationships and Initial Data
// This script defines collaboration-specific relationships and creates initial system data
// Run this script after collaboration indexes are created

// ==================== RELATIONSHIP PROPERTY DEFINITIONS ====================
// Note: Neo4j doesn't have explicit relationship constraints, but we document expected properties here

// PARTICIPATES_IN relationship properties (User -> Room)
// Properties: joined_at, role, permissions[], is_active, last_activity, notification_level

// SENT_MESSAGE relationship properties (User -> Message)
// Properties: sent_at, device_type, client_version

// HAS_MESSAGE relationship properties (Room -> Message)
// Properties: indexed_at, message_number

// NOTIFIED relationship properties (Notification -> User)
// Properties: sent_at, delivery_status, delivery_method

// REACTED_TO relationship properties (User -> Message)
// Properties: reacted_at, reaction_type, reaction_emoji

// MENTIONED_IN relationship properties (User -> Message)
// Properties: mention_type, mention_position

// REPLIED_TO relationship properties (Message -> Message)
// Properties: reply_type, reply_context

// IS_TYPING_IN relationship properties (User -> Room)
// Properties: started_typing_at, client_id

// SHARED_FILE relationship properties (User -> FileShare)
// Properties: shared_at, share_method

// PINNED_MESSAGE relationship properties (User -> Message)
// Properties: pinned_at, pin_reason

// HAS_AI_SESSION relationship properties (User -> AISession)
// Properties: session_role, interaction_count

// ASSISTS_IN relationship properties (Doctor -> AISession)
// Properties: assistance_type, started_at

// ==================== SYSTEM ROOM CREATION ====================
// Create default system rooms if they don't exist

// General Discussion Room
MERGE (r:Room {room_id: 'room_system_general'})
ON CREATE SET 
  r.name = 'General Discussion',
  r.description = 'General medical discussions and casual conversations',
  r.type = 'public',
  r.status = 'active',
  r.is_public = true,
  r.created_at = datetime(),
  r.updated_at = datetime(),
  r.member_count = 0,
  r.max_members = 1000,
  r.tags = ['general', 'discussion', 'community'],
  r.settings = {
    allow_guests: false,
    message_retention_days: 90,
    file_upload_enabled: true,
    max_file_size_mb: 50,
    voice_enabled: true,
    screen_share_enabled: true,
    ai_assistance_enabled: true,
    moderation_level: 'standard'
  },
  r.is_system_room = true;

// Emergency Consultations Room
MERGE (r:Room {room_id: 'room_system_emergency'})
ON CREATE SET 
  r.name = 'Emergency Consultations',
  r.description = 'Urgent medical case discussions requiring immediate attention',
  r.type = 'public',
  r.status = 'active',
  r.is_public = true,
  r.created_at = datetime(),
  r.updated_at = datetime(),
  r.member_count = 0,
  r.max_members = 100,
  r.tags = ['emergency', 'urgent', 'critical', 'priority'],
  r.settings = {
    allow_guests: false,
    message_retention_days: 365,
    file_upload_enabled: true,
    max_file_size_mb: 100,
    voice_enabled: true,
    screen_share_enabled: true,
    ai_assistance_enabled: true,
    moderation_level: 'minimal',
    priority_notifications: true,
    auto_escalation: true
  },
  r.is_system_room = true;

// AI Consultations Room
MERGE (r:Room {room_id: 'room_system_ai_consult'})
ON CREATE SET 
  r.name = 'AI Consultations',
  r.description = 'Dedicated room for AI-assisted medical consultations',
  r.type = 'public',
  r.status = 'active',
  r.is_public = true,
  r.created_at = datetime(),
  r.updated_at = datetime(),
  r.member_count = 0,
  r.max_members = 500,
  r.tags = ['ai', 'consultation', 'automated', 'assistance'],
  r.settings = {
    allow_guests: true,
    message_retention_days: 180,
    file_upload_enabled: true,
    max_file_size_mb: 50,
    voice_enabled: false,
    screen_share_enabled: false,
    ai_assistance_enabled: true,
    moderation_level: 'ai_enhanced',
    ai_auto_response: true,
    ai_triage_enabled: true
  },
  r.is_system_room = true;

// Case Studies Room
MERGE (r:Room {room_id: 'room_system_case_studies'})
ON CREATE SET 
  r.name = 'Case Studies',
  r.description = 'Educational discussions about interesting medical cases',
  r.type = 'public',
  r.status = 'active',
  r.is_public = true,
  r.created_at = datetime(),
  r.updated_at = datetime(),
  r.member_count = 0,
  r.max_members = 500,
  r.tags = ['education', 'case-study', 'learning', 'discussion'],
  r.settings = {
    allow_guests: true,
    message_retention_days: 730,
    file_upload_enabled: true,
    max_file_size_mb: 100,
    voice_enabled: true,
    screen_share_enabled: true,
    ai_assistance_enabled: true,
    moderation_level: 'educational',
    case_anonymization: true
  },
  r.is_system_room = true;

// Announcements Room
MERGE (r:Room {room_id: 'room_system_announcements'})
ON CREATE SET 
  r.name = 'System Announcements',
  r.description = 'Important platform updates and announcements',
  r.type = 'announcement',
  r.status = 'active',
  r.is_public = true,
  r.created_at = datetime(),
  r.updated_at = datetime(),
  r.member_count = 0,
  r.max_members = 10000,
  r.tags = ['announcements', 'updates', 'system', 'news'],
  r.settings = {
    allow_guests: true,
    message_retention_days: 365,
    file_upload_enabled: false,
    max_file_size_mb: 0,
    voice_enabled: false,
    screen_share_enabled: false,
    ai_assistance_enabled: false,
    moderation_level: 'admin_only',
    read_only: true,
    auto_subscribe_new_users: true
  },
  r.is_system_room = true;

// ==================== DEFAULT COLLABORATION SETTINGS ====================
// Create default collaboration settings template
MERGE (cs:CollaborationSettings {settings_id: 'default_user_settings'})
ON CREATE SET
  cs.settings_type = 'user_default',
  cs.notification_preferences = {
    mentions: true,
    direct_messages: true,
    room_invites: true,
    ai_responses: true,
    case_updates: true,
    emergency_alerts: true,
    system_announcements: true,
    email_notifications: false,
    push_notifications: true,
    sound_enabled: true,
    desktop_notifications: true
  },
  cs.privacy_settings = {
    show_online_status: true,
    show_typing_indicator: true,
    show_read_receipts: true,
    allow_direct_messages: true,
    allow_room_invites: true,
    profile_visibility: 'all_users'
  },
  cs.interface_preferences = {
    theme: 'system',
    message_density: 'comfortable',
    timestamp_format: '24h',
    language: 'en',
    timezone: 'UTC',
    emoji_style: 'native',
    markdown_enabled: true,
    code_highlighting: true
  },
  cs.ai_preferences = {
    auto_suggestions: true,
    smart_replies: true,
    case_summaries: true,
    medical_term_tooltips: true,
    translation_enabled: false,
    preferred_ai_doctors: []
  },
  cs.created_at = datetime(),
  cs.updated_at = datetime();

// ==================== SYSTEM NOTIFICATIONS SETUP ====================
// Create system notification templates
MERGE (n:Notification {notification_id: 'template_welcome'})
ON CREATE SET
  n.type = 'system_template',
  n.title = 'Welcome to Unified Medical AI Platform',
  n.content = 'Welcome! Start by joining rooms, creating cases, or consulting with our AI doctors.',
  n.priority = 'medium',
  n.category = 'onboarding',
  n.is_template = true,
  n.created_at = datetime();

MERGE (n:Notification {notification_id: 'template_case_assigned'})
ON CREATE SET
  n.type = 'system_template',
  n.title = 'New Case Assigned',
  n.content = 'You have been assigned to case {{case_number}}: {{case_title}}',
  n.priority = 'high',
  n.category = 'case_management',
  n.is_template = true,
  n.action_url = '/cases/{{case_id}}',
  n.created_at = datetime();

MERGE (n:Notification {notification_id: 'template_emergency_alert'})
ON CREATE SET
  n.type = 'system_template',
  n.title = 'Emergency Case Alert',
  n.content = 'Emergency case requires immediate attention: {{case_title}}',
  n.priority = 'urgent',
  n.category = 'emergency',
  n.is_template = true,
  n.action_url = '/emergency/{{case_id}}',
  n.requires_acknowledgment = true,
  n.created_at = datetime();

// ==================== ACTIVITY TRACKING SETUP ====================
// Create activity type definitions
MERGE (at:ActivityType {type_id: 'user_joined_room'})
ON CREATE SET
  at.name = 'User Joined Room',
  at.description = 'Tracks when a user joins a room',
  at.category = 'room_activity',
  at.is_trackable = true,
  at.is_public = true;

MERGE (at:ActivityType {type_id: 'user_left_room'})
ON CREATE SET
  at.name = 'User Left Room',
  at.description = 'Tracks when a user leaves a room',
  at.category = 'room_activity',
  at.is_trackable = true,
  at.is_public = true;

MERGE (at:ActivityType {type_id: 'message_sent'})
ON CREATE SET
  at.name = 'Message Sent',
  at.description = 'Tracks when a user sends a message',
  at.category = 'messaging',
  at.is_trackable = true,
  at.is_public = false;

MERGE (at:ActivityType {type_id: 'ai_consultation_started'})
ON CREATE SET
  at.name = 'AI Consultation Started',
  at.description = 'Tracks when an AI consultation begins',
  at.category = 'ai_interaction',
  at.is_trackable = true,
  at.is_public = false;

// ==================== COLLABORATION INDICES REFRESH ====================
// Call db.awaitIndexes() to ensure all indexes are online
CALL db.awaitIndexes();