"""
Fix Property Naming Inconsistencies
Standardizes property names across all nodes
"""

from typing import Dict, Any
from neo4j import Transaction

from .base_migration import BaseMigration


class FixPropertyNamesMigration(BaseMigration):
    """
    Fixes inconsistent property naming across nodes
    """
    
    def __init__(self):
        super().__init__(
            migration_id="002_fix_property_names",
            description="Standardize property names for consistency"
        )
    
    def up(self, tx: Transaction) -> Dict[str, Any]:
        """
        Apply the migration
        """
        results = {}
        
        # Fix ChatMessage properties
        # Standardize to use 'id' instead of 'message_id'
        message_id_fix = tx.run("""
            MATCH (m:ChatMessage)
            WHERE m.message_id IS NOT NULL AND m.id IS NULL
            SET m.id = m.message_id
            REMOVE m.message_id
            RETURN COUNT(m) as fixed_count
        """)
        
        result = message_id_fix.single()
        results["message_id_to_id"] = result["fixed_count"] if result else 0
        
        # Standardize timestamp properties
        # Convert 'created_at' to 'timestamp' for messages
        timestamp_fix = tx.run("""
            MATCH (m:ChatMessage)
            WHERE m.created_at IS NOT NULL AND m.timestamp IS NULL
            SET m.timestamp = m.created_at
            REMOVE m.created_at
            RETURN COUNT(m) as fixed_count
        """)
        
        result = timestamp_fix.single()
        results["created_at_to_timestamp"] = result["fixed_count"] if result else 0
        
        # Consolidate user_message/doctor_response into content with role
        content_fix = tx.run("""
            MATCH (m:ChatMessage)
            WHERE (m.user_message IS NOT NULL OR m.doctor_response IS NOT NULL) 
            AND m.content IS NULL
            SET m.content = CASE 
                WHEN m.user_message IS NOT NULL THEN m.user_message
                WHEN m.doctor_response IS NOT NULL THEN m.doctor_response
                ELSE m.content
            END,
            m.role = CASE
                WHEN m.user_message IS NOT NULL AND m.role IS NULL THEN 'user'
                WHEN m.doctor_response IS NOT NULL AND m.role IS NULL THEN 'assistant'
                ELSE m.role
            END
            WITH m
            WHERE m.content IS NOT NULL
            RETURN COUNT(m) as fixed_count
        """)
        
        result = content_fix.single()
        results["content_consolidation"] = result["fixed_count"] if result else 0
        
        # Add doctor_type to metadata if missing
        doctor_type_fix = tx.run("""
            MATCH (m:ChatMessage)
            WHERE m.doctor_type IS NOT NULL
            SET m.metadata = CASE
                WHEN m.metadata IS NULL OR m.metadata = '{}' 
                THEN '{"doctor_type": "' + m.doctor_type + '"}'
                ELSE m.metadata
            END
            RETURN COUNT(m) as fixed_count
        """)
        
        result = doctor_type_fix.single()
        results["doctor_type_to_metadata"] = result["fixed_count"] if result else 0
        
        # Ensure all ChatSessions have required properties
        session_fix = tx.run("""
            MATCH (s:ChatSession)
            WHERE s.message_count IS NULL
            SET s.message_count = 0
            RETURN COUNT(s) as fixed_count
        """)
        
        result = session_fix.single()
        results["session_message_count"] = result["fixed_count"] if result else 0
        
        # Ensure all Cases have required properties
        case_fix = tx.run("""
            MATCH (c:Case)
            WHERE c.updated_at IS NULL
            SET c.updated_at = COALESCE(c.created_at, datetime().toString())
            RETURN COUNT(c) as fixed_count
        """)
        
        result = case_fix.single()
        results["case_updated_at"] = result["fixed_count"] if result else 0
        
        return results
    
    def down(self, tx: Transaction) -> Dict[str, Any]:
        """
        Rollback the migration
        """
        results = {}
        
        # Restore message_id from id
        tx.run("""
            MATCH (m:ChatMessage)
            WHERE m.id IS NOT NULL
            SET m.message_id = m.id
        """)
        results["restore_message_id"] = "completed"
        
        # Restore created_at from timestamp
        tx.run("""
            MATCH (m:ChatMessage)
            WHERE m.timestamp IS NOT NULL
            SET m.created_at = m.timestamp
        """)
        results["restore_created_at"] = "completed"
        
        # Note: We don't reverse the content consolidation as it would lose data
        results["content_consolidation"] = "not reversed (would lose data)"
        
        return results