"""
Voice Consultation Schema Migration
Creates necessary nodes, relationships, and constraints for voice consultations
Uses shared database manager for consistency
"""

import logging
from datetime import datetime
from typing import Optional
import sys
import os

# Add parent path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from app.core.services.database_manager import get_database_manager
from app.core.unified_logging import get_logger

logger = get_logger(__name__)


class VoiceConsultationMigration:
    """Migration for voice consultation schema"""
    
    def __init__(self):
        """Initialize migration with shared database manager"""
        self.db_manager = get_database_manager()
        self.driver = None
        
    def connect(self):
        """Connect to database using shared manager"""
        self.driver = self.db_manager.connect_sync()
        if not self.driver:
            raise RuntimeError("Failed to connect to Neo4j database")
        logger.info("Connected to Neo4j for voice consultation migration")
        
    def run_migration(self):
        """Run the voice consultation schema migration"""
        if not self.driver:
            self.connect()
            
        try:
            with self.driver.session() as session:
                # Create constraints for VoiceConsultation nodes
                logger.info("Creating VoiceConsultation constraints...")
                session.run("""
                    CREATE CONSTRAINT voice_consultation_id_unique IF NOT EXISTS 
                    FOR (vc:VoiceConsultation) 
                    REQUIRE vc.consultation_id IS UNIQUE
                """)
                
                # Create constraints for ConversationEntry nodes (chat history)
                logger.info("Creating ConversationEntry constraints...")
                session.run("""
                    CREATE CONSTRAINT conversation_entry_id_unique IF NOT EXISTS 
                    FOR (ce:ConversationEntry) 
                    REQUIRE ce.entry_id IS UNIQUE
                """)
                
                # Create indexes for better query performance
                logger.info("Creating indexes...")
                session.run("""
                    CREATE INDEX voice_consultation_user_idx IF NOT EXISTS 
                    FOR (vc:VoiceConsultation) 
                    ON (vc.user_id)
                """)
                
                session.run("""
                    CREATE INDEX voice_consultation_status_idx IF NOT EXISTS 
                    FOR (vc:VoiceConsultation) 
                    ON (vc.status)
                """)
                
                session.run("""
                    CREATE INDEX conversation_entry_timestamp_idx IF NOT EXISTS 
                    FOR (ce:ConversationEntry) 
                    ON (ce.timestamp)
                """)
                
                # Create relationship indexes
                logger.info("Creating relationship indexes...")
                session.run("""
                    CREATE INDEX rel_has_consultation_idx IF NOT EXISTS 
                    FOR ()-[r:HAS_VOICE_CONSULTATION]->() 
                    ON (r.created_at)
                """)
                
                session.run("""
                    CREATE INDEX rel_has_conversation_idx IF NOT EXISTS 
                    FOR ()-[r:HAS_CONVERSATION]->() 
                    ON (r.sequence)
                """)
                
                logger.info("Voice consultation schema migration completed successfully")
                
                # Log the schema structure
                result = session.run("""
                    CALL db.constraints() YIELD description
                    WHERE description CONTAINS 'VoiceConsultation' 
                       OR description CONTAINS 'ConversationEntry'
                    RETURN description
                """)
                
                constraints = [record["description"] for record in result]
                logger.info(f"Created constraints: {constraints}")
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
            
    def verify_migration(self):
        """Verify the migration was successful"""
        if not self.driver:
            self.connect()
            
        try:
            with self.driver.session() as session:
                # Check constraints
                result = session.run("""
                    CALL db.constraints() YIELD name, description
                    WHERE name IN [
                        'voice_consultation_id_unique',
                        'conversation_entry_id_unique'
                    ]
                    RETURN count(*) as constraint_count
                """)
                
                constraint_count = result.single()["constraint_count"]
                
                # Check indexes
                result = session.run("""
                    CALL db.indexes() YIELD name
                    WHERE name IN [
                        'voice_consultation_user_idx',
                        'voice_consultation_status_idx',
                        'conversation_entry_timestamp_idx'
                    ]
                    RETURN count(*) as index_count
                """)
                
                index_count = result.single()["index_count"]
                
                logger.info(f"Verification: {constraint_count} constraints, {index_count} indexes")
                
                return constraint_count >= 2 and index_count >= 3
                
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
            
    def rollback(self):
        """Rollback the migration if needed"""
        if not self.driver:
            self.connect()
            
        try:
            with self.driver.session() as session:
                # Drop constraints
                logger.info("Rolling back voice consultation schema...")
                
                # Note: Neo4j doesn't support IF EXISTS for DROP CONSTRAINT
                # We need to check existence first
                constraints_to_drop = [
                    'voice_consultation_id_unique',
                    'conversation_entry_id_unique'
                ]
                
                for constraint_name in constraints_to_drop:
                    try:
                        session.run(f"DROP CONSTRAINT {constraint_name}")
                        logger.info(f"Dropped constraint: {constraint_name}")
                    except:
                        pass  # Constraint might not exist
                        
                # Drop indexes
                indexes_to_drop = [
                    'voice_consultation_user_idx',
                    'voice_consultation_status_idx',
                    'conversation_entry_timestamp_idx',
                    'rel_has_consultation_idx',
                    'rel_has_conversation_idx'
                ]
                
                for index_name in indexes_to_drop:
                    try:
                        session.run(f"DROP INDEX {index_name}")
                        logger.info(f"Dropped index: {index_name}")
                    except:
                        pass  # Index might not exist
                        
                logger.info("Rollback completed")
                
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise


def main():
    """Run the migration"""
    migration = VoiceConsultationMigration()
    
    try:
        logger.info("Starting voice consultation schema migration...")
        migration.run_migration()
        
        if migration.verify_migration():
            logger.info("Migration verified successfully")
        else:
            logger.warning("Migration verification failed, attempting rollback...")
            migration.rollback()
            raise RuntimeError("Migration verification failed")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        if migration.driver:
            migration.driver.close()
            

if __name__ == "__main__":
    main()