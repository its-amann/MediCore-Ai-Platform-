// 002_create_indexes.cypher
// Unified Medical AI Platform - Neo4j Indexes
// This script creates all indexes for optimized query performance
// Run this script after constraints are created

// ==================== USER INDEXES ====================
CREATE INDEX user_email IF NOT EXISTS FOR (u:User) ON (u.email);
CREATE INDEX user_role IF NOT EXISTS FOR (u:User) ON (u.role);
CREATE INDEX user_created IF NOT EXISTS FOR (u:User) ON (u.created_at);
CREATE INDEX user_active IF NOT EXISTS FOR (u:User) ON (u.is_active);
CREATE INDEX user_last_login IF NOT EXISTS FOR (u:User) ON (u.last_login);
CREATE INDEX user_specialization IF NOT EXISTS FOR (u:User) ON (u.specialization);

// ==================== CASE INDEXES ====================
CREATE INDEX case_status IF NOT EXISTS FOR (c:Case) ON (c.status);
CREATE INDEX case_priority IF NOT EXISTS FOR (c:Case) ON (c.priority);
CREATE INDEX case_category IF NOT EXISTS FOR (c:Case) ON (c.medical_category);
CREATE INDEX case_created IF NOT EXISTS FOR (c:Case) ON (c.created_at);
CREATE INDEX case_updated IF NOT EXISTS FOR (c:Case) ON (c.updated_at);
CREATE INDEX case_tags IF NOT EXISTS FOR (c:Case) ON (c.tags);
CREATE INDEX case_urgency IF NOT EXISTS FOR (c:Case) ON (c.urgency_level);
CREATE INDEX case_public IF NOT EXISTS FOR (c:Case) ON (c.is_public);
CREATE INDEX case_diagnosis IF NOT EXISTS FOR (c:Case) ON (c.diagnosis);

// ==================== DOCTOR INDEXES ====================
CREATE INDEX doctor_specialty IF NOT EXISTS FOR (d:Doctor) ON (d.specialty);
CREATE INDEX doctor_active IF NOT EXISTS FOR (d:Doctor) ON (d.is_active);
CREATE INDEX doctor_capabilities IF NOT EXISTS FOR (d:Doctor) ON (d.capabilities);
CREATE INDEX doctor_languages IF NOT EXISTS FOR (d:Doctor) ON (d.languages);
CREATE INDEX doctor_version IF NOT EXISTS FOR (d:Doctor) ON (d.version);
CREATE INDEX doctor_rating IF NOT EXISTS FOR (d:Doctor) ON (d.average_rating);

// ==================== ANALYSIS INDEXES ====================
CREATE INDEX analysis_type IF NOT EXISTS FOR (a:Analysis) ON (a.type);
CREATE INDEX analysis_status IF NOT EXISTS FOR (a:Analysis) ON (a.status);
CREATE INDEX analysis_created IF NOT EXISTS FOR (a:Analysis) ON (a.created_at);
CREATE INDEX analysis_confidence IF NOT EXISTS FOR (a:Analysis) ON (a.confidence_score);
CREATE INDEX analysis_medical_codes IF NOT EXISTS FOR (a:Analysis) ON (a.medical_codes);
CREATE INDEX analysis_severity IF NOT EXISTS FOR (a:Analysis) ON (a.severity_score);
CREATE INDEX analysis_reviewed IF NOT EXISTS FOR (a:Analysis) ON (a.is_reviewed);
CREATE INDEX analysis_model IF NOT EXISTS FOR (a:Analysis) ON (a.model_used);

// ==================== MEDIA INDEXES ====================
CREATE INDEX media_type IF NOT EXISTS FOR (m:Media) ON (m.media_type);
CREATE INDEX media_format IF NOT EXISTS FOR (m:Media) ON (m.format);
CREATE INDEX media_uploaded IF NOT EXISTS FOR (m:Media) ON (m.uploaded_at);
CREATE INDEX media_processed IF NOT EXISTS FOR (m:Media) ON (m.processing_status);
CREATE INDEX media_hash IF NOT EXISTS FOR (m:Media) ON (m.hash);
CREATE INDEX media_archived IF NOT EXISTS FOR (m:Media) ON (m.is_archived);
CREATE INDEX media_privacy IF NOT EXISTS FOR (m:Media) ON (m.privacy_level);

// ==================== ROOM INDEXES ====================
CREATE INDEX room_type IF NOT EXISTS FOR (r:Room) ON (r.type);
CREATE INDEX room_status IF NOT EXISTS FOR (r:Room) ON (r.status);
CREATE INDEX room_created IF NOT EXISTS FOR (r:Room) ON (r.created_at);
CREATE INDEX room_public IF NOT EXISTS FOR (r:Room) ON (r.is_public);
CREATE INDEX room_tags IF NOT EXISTS FOR (r:Room) ON (r.tags);
CREATE INDEX room_activity IF NOT EXISTS FOR (r:Room) ON (r.last_activity);

// ==================== CHAT HISTORY INDEXES ====================
CREATE INDEX chat_conversation IF NOT EXISTS FOR (ch:ChatHistory) ON (ch.conversation_id);
CREATE INDEX chat_timestamp IF NOT EXISTS FOR (ch:ChatHistory) ON (ch.timestamp);
CREATE INDEX chat_doctor_specialty IF NOT EXISTS FOR (ch:ChatHistory) ON (ch.doctor_specialty);
CREATE INDEX chat_message_type IF NOT EXISTS FOR (ch:ChatHistory) ON (ch.message_type);
CREATE INDEX chat_session IF NOT EXISTS FOR (ch:ChatHistory) ON (ch.session_id);
CREATE INDEX chat_sentiment IF NOT EXISTS FOR (ch:ChatHistory) ON (ch.user_sentiment);
CREATE INDEX chat_voice IF NOT EXISTS FOR (ch:ChatHistory) ON (ch.is_voice_message);

// ==================== INVITATION INDEXES ====================
CREATE INDEX invitation_status IF NOT EXISTS FOR (inv:Invitation) ON (inv.status);
CREATE INDEX invitation_invitee IF NOT EXISTS FOR (inv:Invitation) ON (inv.invitee_id);
CREATE INDEX invitation_inviter IF NOT EXISTS FOR (inv:Invitation) ON (inv.inviter_id);
CREATE INDEX invitation_room IF NOT EXISTS FOR (inv:Invitation) ON (inv.room_id);
CREATE INDEX invitation_expires IF NOT EXISTS FOR (inv:Invitation) ON (inv.expires_at);
CREATE INDEX invitation_type IF NOT EXISTS FOR (inv:Invitation) ON (inv.invitation_type);
CREATE INDEX invitation_urgency IF NOT EXISTS FOR (inv:Invitation) ON (inv.urgency_level);

// ==================== MESSAGE INDEXES ====================
CREATE INDEX message_type IF NOT EXISTS FOR (m:Message) ON (m.message_type);
CREATE INDEX message_timestamp IF NOT EXISTS FOR (m:Message) ON (m.timestamp);
CREATE INDEX message_sender_type IF NOT EXISTS FOR (m:Message) ON (m.sender_type);
CREATE INDEX message_deleted IF NOT EXISTS FOR (m:Message) ON (m.is_deleted);
CREATE INDEX message_reply IF NOT EXISTS FOR (m:Message) ON (m.reply_to);

// ==================== REPORT INDEXES ====================
CREATE INDEX report_type IF NOT EXISTS FOR (r:Report) ON (r.report_type);
CREATE INDEX report_status IF NOT EXISTS FOR (r:Report) ON (r.status);
CREATE INDEX report_created IF NOT EXISTS FOR (r:Report) ON (r.created_at);
CREATE INDEX report_confidential IF NOT EXISTS FOR (r:Report) ON (r.is_confidential);
CREATE INDEX report_access IF NOT EXISTS FOR (r:Report) ON (r.access_level);
CREATE INDEX report_format IF NOT EXISTS FOR (r:Report) ON (r.format);
CREATE INDEX report_language IF NOT EXISTS FOR (r:Report) ON (r.language);

// ==================== SESSION INDEXES ====================
CREATE INDEX session_type IF NOT EXISTS FOR (s:Session) ON (s.session_type);
CREATE INDEX session_status IF NOT EXISTS FOR (s:Session) ON (s.status);
CREATE INDEX session_started IF NOT EXISTS FOR (s:Session) ON (s.started_at);
CREATE INDEX session_recording IF NOT EXISTS FOR (s:Session) ON (s.recording_available);
CREATE INDEX session_transcript IF NOT EXISTS FOR (s:Session) ON (s.transcript_available);

// ==================== COMPOSITE INDEXES ====================
// Optimized for common query patterns
CREATE INDEX user_case_lookup IF NOT EXISTS FOR (u:User) ON (u.username, u.is_active);
CREATE INDEX case_status_date IF NOT EXISTS FOR (c:Case) ON (c.status, c.created_at);
CREATE INDEX analysis_type_confidence IF NOT EXISTS FOR (a:Analysis) ON (a.type, a.confidence_score);
CREATE INDEX room_type_status IF NOT EXISTS FOR (r:Room) ON (r.type, r.status);
CREATE INDEX invitation_invitee_status IF NOT EXISTS FOR (inv:Invitation) ON (inv.invitee_id, inv.status);

// ==================== SPECIALIZED INDEXES ====================
// For performance optimization on specific query patterns
CREATE INDEX case_user_status IF NOT EXISTS FOR (c:Case) ON (c.status) WHERE EXISTS((User)-[:OWNS]->(c));
CREATE INDEX analysis_case_type IF NOT EXISTS FOR (a:Analysis) ON (a.type) WHERE EXISTS((Case)-[:HAS_ANALYSIS]->(a));
CREATE INDEX message_room_timestamp IF NOT EXISTS FOR (m:Message) ON (m.timestamp) WHERE EXISTS((Room)-[:HAS_MESSAGE]->(m));