"""
Neo4j Migration: Medical Imaging Schema
Creates nodes, relationships, and constraints for medical imaging data
"""

import logging
from typing import Dict, Any
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class MedicalImagingMigration:
    """
    Migration to create medical imaging schema in Neo4j
    """
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def up(self):
        """Apply migration - create schema"""
        with self.driver.session() as session:
            # Create constraints for ImagingReport
            session.run("""
                CREATE CONSTRAINT imaging_report_id IF NOT EXISTS
                FOR (r:ImagingReport) REQUIRE r.report_id IS UNIQUE
            """)
            
            # Create constraints for ImageAnalysis
            session.run("""
                CREATE CONSTRAINT image_analysis_id IF NOT EXISTS
                FOR (i:ImageAnalysis) REQUIRE i.image_id IS UNIQUE
            """)
            
            # Create indexes for better query performance
            session.run("""
                CREATE INDEX imaging_report_case_id IF NOT EXISTS
                FOR (r:ImagingReport) ON (r.case_id)
            """)
            
            session.run("""
                CREATE INDEX imaging_report_user_id IF NOT EXISTS
                FOR (r:ImagingReport) ON (r.user_id)
            """)
            
            session.run("""
                CREATE INDEX imaging_report_status IF NOT EXISTS
                FOR (r:ImagingReport) ON (r.status)
            """)
            
            session.run("""
                CREATE INDEX imaging_report_created_at IF NOT EXISTS
                FOR (r:ImagingReport) ON (r.created_at)
            """)
            
            # Create vector index for embeddings if GDS is available
            try:
                session.run("""
                    CALL gds.version()
                """)
                
                # GDS is available, create vector index
                session.run("""
                    CREATE INDEX imaging_report_embedding IF NOT EXISTS
                    FOR (r:ImagingReport) ON (r.embedding)
                """)
                
                logger.info("Created vector index for imaging report embeddings")
            except Exception as e:
                logger.warning(f"GDS not available, skipping vector index: {e}")
            
            logger.info("Medical imaging schema migration completed successfully")
    
    def down(self):
        """Rollback migration - remove schema"""
        with self.driver.session() as session:
            # Drop constraints
            session.run("DROP CONSTRAINT imaging_report_id IF EXISTS")
            session.run("DROP CONSTRAINT image_analysis_id IF EXISTS")
            
            # Drop indexes
            session.run("DROP INDEX imaging_report_case_id IF EXISTS")
            session.run("DROP INDEX imaging_report_user_id IF EXISTS")
            session.run("DROP INDEX imaging_report_status IF EXISTS")
            session.run("DROP INDEX imaging_report_created_at IF EXISTS")
            session.run("DROP INDEX imaging_report_embedding IF EXISTS")
            
            logger.info("Medical imaging schema migration rolled back successfully")


def run_migration(uri: str, user: str, password: str, direction: str = "up"):
    """
    Run the migration
    
    Args:
        uri: Neo4j URI
        user: Neo4j username
        password: Neo4j password
        direction: "up" to apply, "down" to rollback
    """
    migration = MedicalImagingMigration(uri, user, password)
    
    try:
        if direction == "up":
            migration.up()
            print("Medical imaging schema migration applied successfully")
        elif direction == "down":
            migration.down()
            print("Medical imaging schema migration rolled back successfully")
        else:
            raise ValueError(f"Invalid direction: {direction}")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"Migration failed: {e}")
        raise
    finally:
        migration.close()


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Get database credentials from environment
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    # Run migration
    run_migration(neo4j_uri, neo4j_user, neo4j_password, "up")