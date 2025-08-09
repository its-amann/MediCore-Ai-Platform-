"""
Initial Schema Migration for Cases Chat
Creates indexes, constraints, and fixes relationships
"""

from typing import Dict, Any
from neo4j import Transaction

from .base_migration import BaseMigration


class InitialSchemaMigration(BaseMigration):
    """
    Initial schema setup with proper indexes and constraints
    """
    
    def __init__(self):
        super().__init__(
            migration_id="001_initial_schema",
            description="Create initial schema with indexes and constraints"
        )
    
    def up(self, tx: Transaction) -> Dict[str, Any]:
        """
        Apply the migration
        """
        results = {}
        
        # Create constraints
        constraints = [
            ("CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE", "user_id_unique"),
            ("CREATE CONSTRAINT case_id_unique IF NOT EXISTS FOR (c:Case) REQUIRE c.case_id IS UNIQUE", "case_id_unique"),
            ("CREATE CONSTRAINT case_number_unique IF NOT EXISTS FOR (c:Case) REQUIRE c.case_number IS UNIQUE", "case_number_unique"),
            ("CREATE CONSTRAINT session_id_unique IF NOT EXISTS FOR (s:ChatSession) REQUIRE s.session_id IS UNIQUE", "session_id_unique"),
            ("CREATE CONSTRAINT message_id_unique IF NOT EXISTS FOR (m:ChatMessage) REQUIRE m.id IS UNIQUE", "message_id_unique"),
        ]
        
        for query, name in constraints:
            try:
                tx.run(query)
                results[f"constraint_{name}"] = "created"
            except Exception as e:
                results[f"constraint_{name}"] = f"skipped: {str(e)}"
        
        # Create indexes
        indexes = [
            ("CREATE INDEX case_user_id IF NOT EXISTS FOR (c:Case) ON (c.user_id)", "case_user_id"),
            ("CREATE INDEX case_status IF NOT EXISTS FOR (c:Case) ON (c.status)", "case_status"),
            ("CREATE INDEX case_created_at IF NOT EXISTS FOR (c:Case) ON (c.created_at)", "case_created_at"),
            ("CREATE INDEX session_case_id IF NOT EXISTS FOR (s:ChatSession) ON (s.case_id)", "session_case_id"),
            ("CREATE INDEX session_user_id IF NOT EXISTS FOR (s:ChatSession) ON (s.user_id)", "session_user_id"),
            ("CREATE INDEX message_session_id IF NOT EXISTS FOR (m:ChatMessage) ON (m.session_id)", "message_session_id"),
            ("CREATE INDEX message_case_id IF NOT EXISTS FOR (m:ChatMessage) ON (m.case_id)", "message_case_id"),
            ("CREATE INDEX message_timestamp IF NOT EXISTS FOR (m:ChatMessage) ON (m.timestamp)", "message_timestamp"),
            ("CREATE INDEX message_role IF NOT EXISTS FOR (m:ChatMessage) ON (m.role)", "message_role"),
        ]
        
        for query, name in indexes:
            try:
                tx.run(query)
                results[f"index_{name}"] = "created"
            except Exception as e:
                results[f"index_{name}"] = f"skipped: {str(e)}"
        
        # Fix existing relationships (normalize HAS_SESSION vs HAS_CHAT_SESSION)
        fix_result = tx.run("""
            MATCH (c:Case)-[r:HAS_SESSION]->(s:ChatSession)
            WHERE NOT (c)-[:HAS_CHAT_SESSION]->(s)
            CREATE (c)-[:HAS_CHAT_SESSION]->(s)
            DELETE r
            RETURN COUNT(r) as fixed_relationships
        """)
        
        fixed_count = fix_result.single()
        results["fixed_relationships"] = fixed_count["fixed_relationships"] if fixed_count else 0
        
        # Create case numbering sequence node
        tx.run("""
            MERGE (seq:CaseSequence {date: date().toString()})
            ON CREATE SET seq.counter = 0
        """)
        results["case_sequence"] = "initialized"
        
        return results
    
    def down(self, tx: Transaction) -> Dict[str, Any]:
        """
        Rollback the migration
        """
        results = {}
        
        # Note: Dropping constraints will also drop associated indexes
        constraints = [
            "DROP CONSTRAINT user_id_unique IF EXISTS",
            "DROP CONSTRAINT case_id_unique IF EXISTS",
            "DROP CONSTRAINT case_number_unique IF EXISTS",
            "DROP CONSTRAINT session_id_unique IF EXISTS",
            "DROP CONSTRAINT message_id_unique IF EXISTS",
        ]
        
        for query in constraints:
            try:
                tx.run(query)
                results[query] = "dropped"
            except Exception as e:
                results[query] = f"error: {str(e)}"
        
        # Drop remaining indexes
        indexes = [
            "DROP INDEX case_user_id IF EXISTS",
            "DROP INDEX case_status IF EXISTS",
            "DROP INDEX case_created_at IF EXISTS",
            "DROP INDEX session_case_id IF EXISTS",
            "DROP INDEX session_user_id IF EXISTS",
            "DROP INDEX message_session_id IF EXISTS",
            "DROP INDEX message_case_id IF EXISTS",
            "DROP INDEX message_timestamp IF EXISTS",
            "DROP INDEX message_role IF EXISTS",
        ]
        
        for query in indexes:
            try:
                tx.run(query)
                results[query] = "dropped"
            except Exception as e:
                results[query] = f"error: {str(e)}"
        
        return results