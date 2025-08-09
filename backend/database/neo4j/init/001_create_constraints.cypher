// 001_create_constraints.cypher
// Unified Medical AI Platform - Neo4j Constraints
// This script creates all unique constraints for the database nodes
// Run this script first to ensure data integrity

// User Node Constraints
CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE;
CREATE CONSTRAINT username_unique IF NOT EXISTS FOR (u:User) REQUIRE u.username IS UNIQUE;

// Case Node Constraints
CREATE CONSTRAINT case_id_unique IF NOT EXISTS FOR (c:Case) REQUIRE c.case_id IS UNIQUE;
CREATE CONSTRAINT case_number_unique IF NOT EXISTS FOR (c:Case) REQUIRE c.case_number IS UNIQUE;

// Doctor (AI) Node Constraints
CREATE CONSTRAINT doctor_id_unique IF NOT EXISTS FOR (d:Doctor) REQUIRE d.doctor_id IS UNIQUE;

// Analysis Node Constraints
CREATE CONSTRAINT analysis_id_unique IF NOT EXISTS FOR (a:Analysis) REQUIRE a.analysis_id IS UNIQUE;

// Media Node Constraints
CREATE CONSTRAINT media_id_unique IF NOT EXISTS FOR (m:Media) REQUIRE m.media_id IS UNIQUE;

// Room (Collaboration) Node Constraints
CREATE CONSTRAINT room_id_unique IF NOT EXISTS FOR (r:Room) REQUIRE r.room_id IS UNIQUE;

// ChatHistory Node Constraints
CREATE CONSTRAINT chat_id_unique IF NOT EXISTS FOR (ch:ChatHistory) REQUIRE ch.chat_id IS UNIQUE;

// Invitation Node Constraints
CREATE CONSTRAINT invitation_id_unique IF NOT EXISTS FOR (inv:Invitation) REQUIRE inv.invitation_id IS UNIQUE;

// Message Node Constraints
CREATE CONSTRAINT message_id_unique IF NOT EXISTS FOR (msg:Message) REQUIRE msg.message_id IS UNIQUE;

// Report Node Constraints
CREATE CONSTRAINT report_id_unique IF NOT EXISTS FOR (rep:Report) REQUIRE rep.report_id IS UNIQUE;

// Session Node Constraints
CREATE CONSTRAINT session_id_unique IF NOT EXISTS FOR (s:Session) REQUIRE s.session_id IS UNIQUE;

// Protocol Node Constraints (for MCP integration)
CREATE CONSTRAINT protocol_id_unique IF NOT EXISTS FOR (p:Protocol) REQUIRE p.protocol_id IS UNIQUE;

// CaseNumberSequence Node Constraints
CREATE CONSTRAINT case_number_sequence_date_unique IF NOT EXISTS FOR (seq:CaseNumberSequence) REQUIRE seq.date IS UNIQUE;