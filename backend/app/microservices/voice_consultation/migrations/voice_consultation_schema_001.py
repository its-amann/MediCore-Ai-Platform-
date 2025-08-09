"""
Voice Consultation Schema Migration
Creates Neo4j schema for voice and video consultations with medical compliance
"""

from typing import List, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class VoiceConsultationMigration:
    """Migration for voice consultation schema in Neo4j with medical compliance"""
    
    def __init__(self, neo4j_client):
        self.neo4j_client = neo4j_client
        self.migration_id = "001_voice_consultation_schema"
        self.description = "Create comprehensive voice consultation schema with medical compliance, auditing, and performance optimization"
    
    def up(self) -> List[Dict[str, Any]]:
        """Apply migration - create comprehensive schema with medical compliance"""
        queries = []
        
        # Create constraints for consultation entities
        queries.extend([
            {
                "query": """
                CREATE CONSTRAINT voice_consultation_id IF NOT EXISTS
                FOR (vc:VoiceConsultation) REQUIRE vc.session_id IS UNIQUE
                """,
                "description": "Create unique constraint for VoiceConsultation session_id"
            },
            {
                "query": """
                CREATE CONSTRAINT video_consultation_id IF NOT EXISTS
                FOR (vc:VideoConsultation) REQUIRE vc.session_id IS UNIQUE
                """,
                "description": "Create unique constraint for VideoConsultation session_id"
            },
            {
                "query": """
                CREATE CONSTRAINT transcript_entry_id IF NOT EXISTS
                FOR (t:TranscriptEntry) REQUIRE t.entry_id IS UNIQUE
                """,
                "description": "Create unique constraint for TranscriptEntry entry_id"
            },
            {
                "query": """
                CREATE CONSTRAINT consultation_transcript_id IF NOT EXISTS
                FOR (ct:ConsultationTranscript) REQUIRE ct.consultation_id IS UNIQUE
                """,
                "description": "Create unique constraint for ConsultationTranscript consultation_id"
            },
            {
                "query": """
                CREATE CONSTRAINT recommendation_id IF NOT EXISTS
                FOR (r:Recommendation) REQUIRE r.recommendation_id IS UNIQUE
                """,
                "description": "Create unique constraint for Recommendation recommendation_id"
            },
            {
                "query": """
                CREATE CONSTRAINT visual_analysis_id IF NOT EXISTS
                FOR (va:VisualAnalysis) REQUIRE va.analysis_id IS UNIQUE
                """,
                "description": "Create unique constraint for VisualAnalysis analysis_id"
            },
            {
                "query": """
                CREATE CONSTRAINT audit_log_id IF NOT EXISTS
                FOR (al:AuditLog) REQUIRE al.audit_id IS UNIQUE
                """,
                "description": "Create unique constraint for AuditLog audit_id"
            },
            {
                "query": """
                CREATE CONSTRAINT ai_provider_name IF NOT EXISTS
                FOR (ap:AIProvider) REQUIRE ap.name IS UNIQUE
                """,
                "description": "Create unique constraint for AIProvider name"
            },
            {
                "query": """
                CREATE CONSTRAINT doctor_specialization_name IF NOT EXISTS
                FOR (ds:DoctorSpecialization) REQUIRE ds.name IS UNIQUE
                """,
                "description": "Create unique constraint for DoctorSpecialization name"
            }
        ])
        
        # Create performance indexes for consultations
        queries.extend([
            # Voice consultation indexes
            {
                "query": """
                CREATE INDEX voice_consultation_user_id IF NOT EXISTS
                FOR (vc:VoiceConsultation) ON (vc.user_id)
                """,
                "description": "Create index on VoiceConsultation user_id"
            },
            {
                "query": """
                CREATE INDEX voice_consultation_status IF NOT EXISTS
                FOR (vc:VoiceConsultation) ON (vc.status)
                """,
                "description": "Create index on VoiceConsultation status"
            },
            {
                "query": """
                CREATE INDEX voice_consultation_started_at IF NOT EXISTS
                FOR (vc:VoiceConsultation) ON (vc.started_at)
                """,
                "description": "Create index on VoiceConsultation started_at"
            },
            {
                "query": """
                CREATE INDEX voice_consultation_case_id IF NOT EXISTS
                FOR (vc:VoiceConsultation) ON (vc.case_id)
                """,
                "description": "Create index on VoiceConsultation case_id"
            },
            # Video consultation indexes
            {
                "query": """
                CREATE INDEX video_consultation_user_id IF NOT EXISTS
                FOR (vc:VideoConsultation) ON (vc.user_id)
                """,
                "description": "Create index on VideoConsultation user_id"
            },
            {
                "query": """
                CREATE INDEX video_consultation_status IF NOT EXISTS
                FOR (vc:VideoConsultation) ON (vc.status)
                """,
                "description": "Create index on VideoConsultation status"
            },
            {
                "query": """
                CREATE INDEX video_consultation_started_at IF NOT EXISTS
                FOR (vc:VideoConsultation) ON (vc.started_at)
                """,
                "description": "Create index on VideoConsultation started_at"
            },
            # Transcript entry indexes
            {
                "query": """
                CREATE INDEX transcript_entry_session_id IF NOT EXISTS
                FOR (t:TranscriptEntry) ON (t.session_id)
                """,
                "description": "Create index on TranscriptEntry session_id for fast retrieval"
            },
            {
                "query": """
                CREATE INDEX transcript_entry_timestamp IF NOT EXISTS
                FOR (t:TranscriptEntry) ON (t.timestamp)
                """,
                "description": "Create index on TranscriptEntry timestamp for temporal queries"
            },
            {
                "query": """
                CREATE INDEX transcript_entry_speaker IF NOT EXISTS
                FOR (t:TranscriptEntry) ON (t.speaker)
                """,
                "description": "Create index on TranscriptEntry speaker"
            },
            # Full-text search indexes
            {
                "query": """
                CREATE FULLTEXT INDEX transcript_content_search IF NOT EXISTS
                FOR (t:TranscriptEntry) ON EACH [t.content]
                """,
                "description": "Create fulltext index on TranscriptEntry content for medical term search"
            },
            {
                "query": """
                CREATE FULLTEXT INDEX consultation_summary_search IF NOT EXISTS
                FOR (n:VoiceConsultation|VideoConsultation) ON EACH [n.summary]
                """,
                "description": "Create fulltext index on consultation summaries"
            },
            # Audit log indexes
            {
                "query": """
                CREATE INDEX audit_log_user_id IF NOT EXISTS
                FOR (al:AuditLog) ON (al.user_id)
                """,
                "description": "Create index on AuditLog user_id for compliance queries"
            },
            {
                "query": """
                CREATE INDEX audit_log_timestamp IF NOT EXISTS
                FOR (al:AuditLog) ON (al.timestamp)
                """,
                "description": "Create index on AuditLog timestamp for temporal queries"
            },
            {
                "query": """
                CREATE INDEX audit_log_entity_type IF NOT EXISTS
                FOR (al:AuditLog) ON (al.entity_type)
                """,
                "description": "Create index on AuditLog entity_type"
            },
            # Composite indexes for common query patterns
            {
                "query": """
                CREATE INDEX voice_consultation_user_status IF NOT EXISTS
                FOR (vc:VoiceConsultation) ON (vc.user_id, vc.status)
                """,
                "description": "Create composite index for user consultation queries"
            },
            {
                "query": """
                CREATE INDEX video_consultation_user_status IF NOT EXISTS
                FOR (vc:VideoConsultation) ON (vc.user_id, vc.status)
                """,
                "description": "Create composite index for user video consultation queries"
            }
        ])
        
        # Create AI Provider nodes with medical context
        queries.append({
            "query": """
            UNWIND [
                {name: 'gemini', type: 'primary', capabilities: ['audio', 'vision', 'text'], 
                 medical_certified: true, max_tokens: 1000000},
                {name: 'groq', type: 'fast', capabilities: ['text'], 
                 medical_certified: false, max_tokens: 32000},
                {name: 'openrouter', type: 'versatile', capabilities: ['text'], 
                 medical_certified: false, max_tokens: 128000},
                {name: 'together', type: 'opensource', capabilities: ['text'], 
                 medical_certified: false, max_tokens: 64000}
            ] AS provider
            MERGE (ap:AIProvider {name: provider.name})
            SET ap.type = provider.type,
                ap.capabilities = provider.capabilities,
                ap.medical_certified = provider.medical_certified,
                ap.max_tokens = provider.max_tokens,
                ap.created_at = datetime(),
                ap.is_active = true
            """,
            "description": "Create AI Provider nodes with medical compliance flags"
        })
        
        # Create doctor specialization nodes with metadata
        queries.append({
            "query": """
            UNWIND [
                {name: 'General Practitioner', code: 'GP', consultation_duration: 15},
                {name: 'Cardiologist', code: 'CARDIO', consultation_duration: 30},
                {name: 'Dermatologist', code: 'DERM', consultation_duration: 20},
                {name: 'Pediatrician', code: 'PED', consultation_duration: 20},
                {name: 'Psychiatrist', code: 'PSYCH', consultation_duration: 45},
                {name: 'Obstetrician/Gynecologist', code: 'OBGYN', consultation_duration: 30},
                {name: 'Orthopedist', code: 'ORTHO', consultation_duration: 20}
            ] AS spec
            MERGE (ds:DoctorSpecialization {name: spec.name})
            SET ds.code = spec.code,
                ds.typical_consultation_duration = spec.consultation_duration,
                ds.created_at = datetime(),
                ds.is_active = true
            """,
            "description": "Create doctor specialization nodes with metadata"
        })
        
        # Note: Neo4j doesn't support triggers in the same way
        # We'll enforce user existence through application logic
        
        # Create data retention policy nodes
        queries.append({
            "query": """
            CREATE (drp:DataRetentionPolicy {
                policy_id: 'consultation_retention',
                entity_type: 'Consultation',
                retention_days: 2555,  // 7 years for medical records
                deletion_strategy: 'archive',
                created_at: datetime(),
                is_active: true
            })
            """,
            "description": "Create data retention policy for medical compliance"
        })
        
        # Execute queries
        results = []
        with self.neo4j_client.driver.session() as session:
            for query_info in queries:
                try:
                    result = session.run(query_info["query"])
                    summary = result.consume()
                    
                    # Extract counter values
                    counter_dict = {}
                    if hasattr(summary.counters, 'constraints_added'):
                        counter_dict['constraints_added'] = summary.counters.constraints_added
                    if hasattr(summary.counters, 'indexes_added'):
                        counter_dict['indexes_added'] = summary.counters.indexes_added
                    if hasattr(summary.counters, 'nodes_created'):
                        counter_dict['nodes_created'] = summary.counters.nodes_created
                    if hasattr(summary.counters, 'properties_set'):
                        counter_dict['properties_set'] = summary.counters.properties_set
                        
                    results.append({
                        "query": query_info["description"],
                        "success": True,
                        "counters": counter_dict if counter_dict else None
                    })
                    logger.info(f"Successfully executed: {query_info['description']}")
                except Exception as e:
                    logger.error(f"Failed to execute: {query_info['description']} - {str(e)}")
                    results.append({
                        "query": query_info["description"],
                        "success": False,
                        "error": str(e)
                    })
        
        return results
    
    def down(self) -> List[Dict[str, Any]]:
        """Rollback migration - drop schema"""
        queries = [
            # Drop constraints
            "DROP CONSTRAINT voice_consultation_id IF EXISTS",
            "DROP CONSTRAINT video_consultation_id IF EXISTS",
            "DROP CONSTRAINT transcript_entry_id IF EXISTS",
            "DROP CONSTRAINT consultation_transcript_id IF EXISTS",
            "DROP CONSTRAINT recommendation_id IF EXISTS",
            "DROP CONSTRAINT visual_analysis_id IF EXISTS",
            "DROP CONSTRAINT audit_log_id IF EXISTS",
            "DROP CONSTRAINT ai_provider_name IF EXISTS",
            "DROP CONSTRAINT doctor_specialization_name IF EXISTS",
            # Drop indexes
            "DROP INDEX voice_consultation_user_id IF EXISTS",
            "DROP INDEX voice_consultation_status IF EXISTS",
            "DROP INDEX voice_consultation_started_at IF EXISTS",
            "DROP INDEX voice_consultation_case_id IF EXISTS",
            "DROP INDEX video_consultation_user_id IF EXISTS",
            "DROP INDEX video_consultation_status IF EXISTS",
            "DROP INDEX video_consultation_started_at IF EXISTS",
            "DROP INDEX transcript_entry_session_id IF EXISTS",
            "DROP INDEX transcript_entry_timestamp IF EXISTS",
            "DROP INDEX transcript_entry_speaker IF EXISTS",
            "DROP INDEX audit_log_user_id IF EXISTS",
            "DROP INDEX audit_log_timestamp IF EXISTS",
            "DROP INDEX audit_log_entity_type IF EXISTS",
            "DROP INDEX voice_consultation_user_status IF EXISTS",
            "DROP INDEX video_consultation_user_status IF EXISTS",
            # Drop full-text indexes
            "DROP INDEX transcript_content_search IF EXISTS",
            "DROP INDEX consultation_summary_search IF EXISTS"
        ]
        
        results = []
        with self.neo4j_client.driver.session() as session:
            for query in queries:
                try:
                    session.run(query)
                    results.append({
                        "query": query,
                        "success": True
                    })
                except Exception as e:
                    results.append({
                        "query": query,
                        "success": False,
                        "error": str(e)
                    })
        
        return results
    
    def verify(self) -> bool:
        """Verify migration was applied successfully"""
        try:
            with self.neo4j_client.driver.session() as session:
                # Check constraints
                result = session.run("""
                    SHOW CONSTRAINTS
                    WHERE name IN [
                        'voice_consultation_id',
                        'video_consultation_id',
                        'transcript_entry_id',
                        'consultation_transcript_id',
                        'recommendation_id',
                        'visual_analysis_id',
                        'audit_log_id',
                        'ai_provider_name',
                        'doctor_specialization_name'
                    ]
                    RETURN count(*) as constraint_count
                """)
                constraint_count = result.single()["constraint_count"]
                
                # Check indexes
                result = session.run("""
                    SHOW INDEXES
                    WHERE name IN [
                        'voice_consultation_user_id',
                        'voice_consultation_status',
                        'video_consultation_user_id',
                        'video_consultation_status',
                        'transcript_entry_session_id',
                        'transcript_entry_timestamp',
                        'audit_log_user_id',
                        'transcript_content_search',
                        'consultation_summary_search'
                    ]
                    RETURN count(*) as index_count
                """)
                index_count = result.single()["index_count"]
                
                # Check AI providers
                result = session.run("MATCH (ap:AIProvider) RETURN count(ap) as count")
                provider_count = result.single()["count"]
                
                # Check doctor specializations
                result = session.run("MATCH (ds:DoctorSpecialization) RETURN count(ds) as count")
                specialization_count = result.single()["count"]
                
                # Check data retention policy
                result = session.run("MATCH (drp:DataRetentionPolicy) RETURN count(drp) as count")
                policy_count = result.single()["count"]
                
                # Log verification results
                logger.info(f"Migration verification: constraints={constraint_count}, indexes={index_count}, "
                          f"providers={provider_count}, specializations={specialization_count}, policies={policy_count}")
                
                # All checks must pass
                return (constraint_count >= 9 and 
                       index_count >= 9 and 
                       provider_count >= 4 and 
                       specialization_count >= 7 and
                       policy_count >= 1)
                       
        except Exception as e:
            logger.error(f"Migration verification failed: {str(e)}")
            return False


def get_migration():
    """Factory function to get migration instance"""
    return VoiceConsultationMigration