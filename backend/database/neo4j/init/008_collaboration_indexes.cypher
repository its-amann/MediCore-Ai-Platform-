// 008_collaboration_indexes.cypher
// Unified Medical AI Platform - Collaboration Indexes
// This script creates indexes for optimized collaboration query performance
// Run this script after collaboration constraints are created

// ==================== NOTIFICATION INDEXES ====================
CREATE INDEX notification_user IF NOT EXISTS FOR (n:Notification) ON (n.user_id);
CREATE INDEX notification_type IF NOT EXISTS FOR (n:Notification) ON (n.type);
CREATE INDEX notification_read IF NOT EXISTS FOR (n:Notification) ON (n.is_read);
CREATE INDEX notification_created IF NOT EXISTS FOR (n:Notification) ON (n.created_at);
CREATE INDEX notification_priority IF NOT EXISTS FOR (n:Notification) ON (n.priority);
CREATE INDEX notification_source IF NOT EXISTS FOR (n:Notification) ON (n.source_type);
CREATE INDEX notification_expires IF NOT EXISTS FOR (n:Notification) ON (n.expires_at);
CREATE INDEX notification_dismissed IF NOT EXISTS FOR (n:Notification) ON (n.is_dismissed);

// ==================== AI SESSION INDEXES ====================
CREATE INDEX ai_session_user IF NOT EXISTS FOR (ai:AISession) ON (ai.user_id);
CREATE INDEX ai_session_room IF NOT EXISTS FOR (ai:AISession) ON (ai.room_id);
CREATE INDEX ai_session_doctor IF NOT EXISTS FOR (ai:AISession) ON (ai.doctor_id);
CREATE INDEX ai_session_started IF NOT EXISTS FOR (ai:AISession) ON (ai.started_at);
CREATE INDEX ai_session_ended IF NOT EXISTS FOR (ai:AISession) ON (ai.ended_at);
CREATE INDEX ai_session_status IF NOT EXISTS FOR (ai:AISession) ON (ai.status);
CREATE INDEX ai_session_type IF NOT EXISTS FOR (ai:AISession) ON (ai.session_type);
CREATE INDEX ai_session_tokens IF NOT EXISTS FOR (ai:AISession) ON (ai.token_count);

// ==================== USER ACTIVITY INDEXES ====================
CREATE INDEX user_activity_user IF NOT EXISTS FOR (ua:UserActivity) ON (ua.user_id);
CREATE INDEX user_activity_room IF NOT EXISTS FOR (ua:UserActivity) ON (ua.room_id);
CREATE INDEX user_activity_status IF NOT EXISTS FOR (ua:UserActivity) ON (ua.status);
CREATE INDEX user_activity_last_seen IF NOT EXISTS FOR (ua:UserActivity) ON (ua.last_seen_at);
CREATE INDEX user_activity_device IF NOT EXISTS FOR (ua:UserActivity) ON (ua.device_type);
CREATE INDEX user_activity_platform IF NOT EXISTS FOR (ua:UserActivity) ON (ua.platform);

// ==================== ROOM MEMBERSHIP INDEXES ====================
CREATE INDEX membership_user IF NOT EXISTS FOR (rm:RoomMembership) ON (rm.user_id);
CREATE INDEX membership_room IF NOT EXISTS FOR (rm:RoomMembership) ON (rm.room_id);
CREATE INDEX membership_role IF NOT EXISTS FOR (rm:RoomMembership) ON (rm.role);
CREATE INDEX membership_joined IF NOT EXISTS FOR (rm:RoomMembership) ON (rm.joined_at);
CREATE INDEX membership_status IF NOT EXISTS FOR (rm:RoomMembership) ON (rm.status);
CREATE INDEX membership_permissions IF NOT EXISTS FOR (rm:RoomMembership) ON (rm.permissions);
CREATE INDEX membership_muted IF NOT EXISTS FOR (rm:RoomMembership) ON (rm.is_muted);

// ==================== MESSAGE REACTION INDEXES ====================
CREATE INDEX reaction_message IF NOT EXISTS FOR (mr:MessageReaction) ON (mr.message_id);
CREATE INDEX reaction_user IF NOT EXISTS FOR (mr:MessageReaction) ON (mr.user_id);
CREATE INDEX reaction_type IF NOT EXISTS FOR (mr:MessageReaction) ON (mr.reaction_type);
CREATE INDEX reaction_created IF NOT EXISTS FOR (mr:MessageReaction) ON (mr.created_at);

// ==================== MESSAGE THREAD INDEXES ====================
CREATE INDEX thread_parent_message IF NOT EXISTS FOR (mt:MessageThread) ON (mt.parent_message_id);
CREATE INDEX thread_room IF NOT EXISTS FOR (mt:MessageThread) ON (mt.room_id);
CREATE INDEX thread_created IF NOT EXISTS FOR (mt:MessageThread) ON (mt.created_at);
CREATE INDEX thread_last_reply IF NOT EXISTS FOR (mt:MessageThread) ON (mt.last_reply_at);
CREATE INDEX thread_reply_count IF NOT EXISTS FOR (mt:MessageThread) ON (mt.reply_count);
CREATE INDEX thread_participants IF NOT EXISTS FOR (mt:MessageThread) ON (mt.participant_count);

// ==================== TYPING INDICATOR INDEXES ====================
CREATE INDEX typing_user IF NOT EXISTS FOR (ti:TypingIndicator) ON (ti.user_id);
CREATE INDEX typing_room IF NOT EXISTS FOR (ti:TypingIndicator) ON (ti.room_id);
CREATE INDEX typing_started IF NOT EXISTS FOR (ti:TypingIndicator) ON (ti.started_at);
CREATE INDEX typing_expires IF NOT EXISTS FOR (ti:TypingIndicator) ON (ti.expires_at);

// ==================== ROOM ANNOUNCEMENT INDEXES ====================
CREATE INDEX announcement_room IF NOT EXISTS FOR (ra:RoomAnnouncement) ON (ra.room_id);
CREATE INDEX announcement_author IF NOT EXISTS FOR (ra:RoomAnnouncement) ON (ra.author_id);
CREATE INDEX announcement_created IF NOT EXISTS FOR (ra:RoomAnnouncement) ON (ra.created_at);
CREATE INDEX announcement_expires IF NOT EXISTS FOR (ra:RoomAnnouncement) ON (ra.expires_at);
CREATE INDEX announcement_priority IF NOT EXISTS FOR (ra:RoomAnnouncement) ON (ra.priority);
CREATE INDEX announcement_active IF NOT EXISTS FOR (ra:RoomAnnouncement) ON (ra.is_active);

// ==================== COLLABORATION EVENT INDEXES ====================
CREATE INDEX collab_event_type IF NOT EXISTS FOR (ce:CollaborationEvent) ON (ce.event_type);
CREATE INDEX collab_event_user IF NOT EXISTS FOR (ce:CollaborationEvent) ON (ce.user_id);
CREATE INDEX collab_event_room IF NOT EXISTS FOR (ce:CollaborationEvent) ON (ce.room_id);
CREATE INDEX collab_event_timestamp IF NOT EXISTS FOR (ce:CollaborationEvent) ON (ce.timestamp);
CREATE INDEX collab_event_entity_type IF NOT EXISTS FOR (ce:CollaborationEvent) ON (ce.entity_type);
CREATE INDEX collab_event_entity_id IF NOT EXISTS FOR (ce:CollaborationEvent) ON (ce.entity_id);

// ==================== VOICE CHANNEL INDEXES ====================
CREATE INDEX voice_channel_room IF NOT EXISTS FOR (vc:VoiceChannel) ON (vc.room_id);
CREATE INDEX voice_channel_status IF NOT EXISTS FOR (vc:VoiceChannel) ON (vc.status);
CREATE INDEX voice_channel_created IF NOT EXISTS FOR (vc:VoiceChannel) ON (vc.created_at);
CREATE INDEX voice_channel_quality IF NOT EXISTS FOR (vc:VoiceChannel) ON (vc.quality_preset);
CREATE INDEX voice_channel_participants IF NOT EXISTS FOR (vc:VoiceChannel) ON (vc.participant_count);

// ==================== SCREEN SHARE SESSION INDEXES ====================
CREATE INDEX screen_share_room IF NOT EXISTS FOR (ss:ScreenShareSession) ON (ss.room_id);
CREATE INDEX screen_share_user IF NOT EXISTS FOR (ss:ScreenShareSession) ON (ss.user_id);
CREATE INDEX screen_share_status IF NOT EXISTS FOR (ss:ScreenShareSession) ON (ss.status);
CREATE INDEX screen_share_started IF NOT EXISTS FOR (ss:ScreenShareSession) ON (ss.started_at);
CREATE INDEX screen_share_quality IF NOT EXISTS FOR (ss:ScreenShareSession) ON (ss.quality);

// ==================== FILE SHARE INDEXES ====================
CREATE INDEX file_share_room IF NOT EXISTS FOR (fs:FileShare) ON (fs.room_id);
CREATE INDEX file_share_uploader IF NOT EXISTS FOR (fs:FileShare) ON (fs.uploader_id);
CREATE INDEX file_share_type IF NOT EXISTS FOR (fs:FileShare) ON (fs.file_type);
CREATE INDEX file_share_uploaded IF NOT EXISTS FOR (fs:FileShare) ON (fs.uploaded_at);
CREATE INDEX file_share_size IF NOT EXISTS FOR (fs:FileShare) ON (fs.file_size);
CREATE INDEX file_share_status IF NOT EXISTS FOR (fs:FileShare) ON (fs.status);
CREATE INDEX file_share_expires IF NOT EXISTS FOR (fs:FileShare) ON (fs.expires_at);

// ==================== ROOM PIN INDEXES ====================
CREATE INDEX room_pin_room IF NOT EXISTS FOR (rp:RoomPin) ON (rp.room_id);
CREATE INDEX room_pin_message IF NOT EXISTS FOR (rp:RoomPin) ON (rp.message_id);
CREATE INDEX room_pin_user IF NOT EXISTS FOR (rp:RoomPin) ON (rp.pinned_by);
CREATE INDEX room_pin_created IF NOT EXISTS FOR (rp:RoomPin) ON (rp.pinned_at);
CREATE INDEX room_pin_order IF NOT EXISTS FOR (rp:RoomPin) ON (rp.pin_order);

// ==================== COLLABORATION SETTINGS INDEXES ====================
CREATE INDEX collab_settings_user IF NOT EXISTS FOR (cs:CollaborationSettings) ON (cs.user_id);
CREATE INDEX collab_settings_room IF NOT EXISTS FOR (cs:CollaborationSettings) ON (cs.room_id);
CREATE INDEX collab_settings_type IF NOT EXISTS FOR (cs:CollaborationSettings) ON (cs.settings_type);
CREATE INDEX collab_settings_updated IF NOT EXISTS FOR (cs:CollaborationSettings) ON (cs.updated_at);

// ==================== ENHANCED ROOM INDEXES FOR COLLABORATION ====================
CREATE INDEX room_name IF NOT EXISTS FOR (r:Room) ON (r.name);
CREATE INDEX room_description IF NOT EXISTS FOR (r:Room) ON (r.description);
CREATE INDEX room_max_members IF NOT EXISTS FOR (r:Room) ON (r.max_members);
CREATE INDEX room_member_count IF NOT EXISTS FOR (r:Room) ON (r.member_count);
CREATE INDEX room_is_archived IF NOT EXISTS FOR (r:Room) ON (r.is_archived);
CREATE INDEX room_archived_at IF NOT EXISTS FOR (r:Room) ON (r.archived_at);
CREATE INDEX room_settings IF NOT EXISTS FOR (r:Room) ON (r.settings);

// ==================== ENHANCED MESSAGE INDEXES FOR COLLABORATION ====================
CREATE INDEX message_room_id IF NOT EXISTS FOR (m:Message) ON (m.room_id);
CREATE INDEX message_sender_id IF NOT EXISTS FOR (m:Message) ON (m.sender_id);
CREATE INDEX message_parent_thread IF NOT EXISTS FOR (m:Message) ON (m.thread_id);
CREATE INDEX message_is_edited IF NOT EXISTS FOR (m:Message) ON (m.is_edited);
CREATE INDEX message_edited_at IF NOT EXISTS FOR (m:Message) ON (m.edited_at);
CREATE INDEX message_is_pinned IF NOT EXISTS FOR (m:Message) ON (m.is_pinned);
CREATE INDEX message_mentions IF NOT EXISTS FOR (m:Message) ON (m.mentions);
CREATE INDEX message_attachments IF NOT EXISTS FOR (m:Message) ON (m.has_attachments);

// ==================== COMPOSITE INDEXES FOR COLLABORATION ====================
// Room search optimization
CREATE INDEX room_search IF NOT EXISTS FOR (r:Room) ON (r.name, r.type, r.status, r.is_public);
CREATE INDEX room_active_public IF NOT EXISTS FOR (r:Room) ON (r.is_public, r.status) WHERE r.status = 'active';

// Message query optimization
CREATE INDEX message_room_timestamp IF NOT EXISTS FOR (m:Message) ON (m.room_id, m.timestamp);
CREATE INDEX message_room_type_timestamp IF NOT EXISTS FOR (m:Message) ON (m.room_id, m.message_type, m.timestamp);

// Notification query optimization
CREATE INDEX notification_user_unread IF NOT EXISTS FOR (n:Notification) ON (n.user_id, n.is_read);
CREATE INDEX notification_user_type_created IF NOT EXISTS FOR (n:Notification) ON (n.user_id, n.type, n.created_at);
CREATE INDEX notification_user_priority_unread IF NOT EXISTS FOR (n:Notification) ON (n.user_id, n.priority, n.is_read);

// User activity tracking optimization
CREATE INDEX activity_room_status IF NOT EXISTS FOR (ua:UserActivity) ON (ua.room_id, ua.status);
CREATE INDEX activity_user_last_seen IF NOT EXISTS FOR (ua:UserActivity) ON (ua.user_id, ua.last_seen_at);

// Room membership optimization
CREATE INDEX membership_room_user IF NOT EXISTS FOR (rm:RoomMembership) ON (rm.room_id, rm.user_id);
CREATE INDEX membership_room_role_status IF NOT EXISTS FOR (rm:RoomMembership) ON (rm.room_id, rm.role, rm.status);

// AI session optimization
CREATE INDEX ai_session_user_status IF NOT EXISTS FOR (ai:AISession) ON (ai.user_id, ai.status);
CREATE INDEX ai_session_room_active IF NOT EXISTS FOR (ai:AISession) ON (ai.room_id, ai.status) WHERE ai.status = 'active';

// Thread activity optimization
CREATE INDEX thread_room_activity IF NOT EXISTS FOR (mt:MessageThread) ON (mt.room_id, mt.last_reply_at);

// File share optimization
CREATE INDEX file_share_room_type IF NOT EXISTS FOR (fs:FileShare) ON (fs.room_id, fs.file_type);
CREATE INDEX file_share_room_status_uploaded IF NOT EXISTS FOR (fs:FileShare) ON (fs.room_id, fs.status, fs.uploaded_at);