// 007_collaboration_constraints.cypher
// Unified Medical AI Platform - Collaboration Constraints
// This script creates unique constraints for collaboration-specific nodes
// Run this script after base constraints are created

// Notification Node Constraints
CREATE CONSTRAINT notification_id_unique IF NOT EXISTS FOR (n:Notification) REQUIRE n.notification_id IS UNIQUE;

// AISession Node Constraints
CREATE CONSTRAINT ai_session_id_unique IF NOT EXISTS FOR (ai:AISession) REQUIRE ai.ai_session_id IS UNIQUE;

// UserActivity Node Constraints (for tracking user presence and activity)
CREATE CONSTRAINT user_activity_id_unique IF NOT EXISTS FOR (ua:UserActivity) REQUIRE ua.activity_id IS UNIQUE;

// RoomMembership Node Constraints (for managing room member states)
CREATE CONSTRAINT membership_id_unique IF NOT EXISTS FOR (rm:RoomMembership) REQUIRE rm.membership_id IS UNIQUE;

// MessageReaction Node Constraints
CREATE CONSTRAINT reaction_id_unique IF NOT EXISTS FOR (mr:MessageReaction) REQUIRE mr.reaction_id IS UNIQUE;

// MessageThread Node Constraints (for threaded conversations)
CREATE CONSTRAINT thread_id_unique IF NOT EXISTS FOR (mt:MessageThread) REQUIRE mt.thread_id IS UNIQUE;

// Typing Indicator Node Constraints
CREATE CONSTRAINT typing_id_unique IF NOT EXISTS FOR (ti:TypingIndicator) REQUIRE ti.typing_id IS UNIQUE;

// Room Announcement Node Constraints
CREATE CONSTRAINT announcement_id_unique IF NOT EXISTS FOR (ra:RoomAnnouncement) REQUIRE ra.announcement_id IS UNIQUE;

// Collaboration Event Node Constraints (for audit trail)
CREATE CONSTRAINT collab_event_id_unique IF NOT EXISTS FOR (ce:CollaborationEvent) REQUIRE ce.event_id IS UNIQUE;

// Voice Channel Node Constraints
CREATE CONSTRAINT voice_channel_id_unique IF NOT EXISTS FOR (vc:VoiceChannel) REQUIRE vc.channel_id IS UNIQUE;

// Screen Share Session Node Constraints
CREATE CONSTRAINT screen_share_id_unique IF NOT EXISTS FOR (ss:ScreenShareSession) REQUIRE ss.session_id IS UNIQUE;

// File Share Node Constraints
CREATE CONSTRAINT file_share_id_unique IF NOT EXISTS FOR (fs:FileShare) REQUIRE fs.file_id IS UNIQUE;

// Room Pin Node Constraints (for pinned messages)
CREATE CONSTRAINT room_pin_id_unique IF NOT EXISTS FOR (rp:RoomPin) REQUIRE rp.pin_id IS UNIQUE;

// Collaboration Settings Node Constraints
CREATE CONSTRAINT collab_settings_id_unique IF NOT EXISTS FOR (cs:CollaborationSettings) REQUIRE cs.settings_id IS UNIQUE;