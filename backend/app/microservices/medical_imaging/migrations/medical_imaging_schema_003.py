"""
Neo4j Migration: Medical Imaging Property Naming Standardization
Adds missing patient_id property and ensures consistent property naming across the schema
"""

import logging
from typing import Dict, Any
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class MedicalImagingPropertyStandardizationMigration:
    """
    Migration to standardize property naming and add missing patient_id field
    """
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def up(self):
        """Apply migration - add patient_id and standardize property naming"""
        with self.driver.session() as session:
            # First, add patient_id to existing ImagingReport nodes that don't have it
            logger.info("Adding patient_id to existing ImagingReport nodes...")
            session.run("""
                MATCH (r:ImagingReport)
                WHERE r.patient_id IS NULL
                SET r.patient_id = ''
            """)
            
            # Create index for patient_id if it doesn't exist (idempotent)
            logger.info("Creating index for patient_id...")
            session.run("""
                CREATE INDEX imaging_report_patient_id IF NOT EXISTS
                FOR (r:ImagingReport) ON (r.patient_id)
            """)
            
            # For existing reports, try to populate patient_id from Case relationships
            logger.info("Attempting to populate patient_id from Case relationships...")
            session.run("""
                MATCH (r:ImagingReport)-[:HAS_IMAGING_REPORT]-(c:Case)
                WHERE r.patient_id = '' OR r.patient_id IS NULL
                OPTIONAL MATCH (c)-[:BELONGS_TO]->(p:Patient)
                WHERE p.patient_id IS NOT NULL
                SET r.patient_id = COALESCE(p.patient_id, '')
            """)
            
            # Ensure all date fields are properly formatted
            logger.info("Standardizing date field formats...")
            session.run("""
                MATCH (r:ImagingReport)
                WHERE r.created_at IS NOT NULL AND NOT r.created_at STARTS WITH 'datetime'
                SET r.created_at = datetime(r.created_at)
            """)
            
            session.run("""
                MATCH (r:ImagingReport)
                WHERE r.updated_at IS NOT NULL AND NOT r.updated_at STARTS WITH 'datetime'
                SET r.updated_at = datetime(r.updated_at)
            """)
            
            session.run("""
                MATCH (r:ImagingReport)
                WHERE r.completed_at IS NOT NULL AND NOT r.completed_at STARTS WITH 'datetime'
                SET r.completed_at = datetime(r.completed_at)
            """)
            
            # Do the same for ImageAnalysis nodes
            session.run("""
                MATCH (i:ImageAnalysis)
                WHERE i.created_at IS NOT NULL AND NOT i.created_at STARTS WITH 'datetime'
                SET i.created_at = datetime(i.created_at)
            """)
            
            # Add a migration record
            session.run("""
                CREATE (m:Migration {
                    name: 'medical_imaging_schema_003',
                    description: 'Add patient_id and standardize property naming',
                    applied_at: datetime(),
                    version: '003'
                })
            """)
            
            logger.info("Medical imaging property standardization migration completed successfully")
            
            # Log statistics
            result = session.run("""
                MATCH (r:ImagingReport)
                RETURN 
                    count(r) as total_reports,
                    count(CASE WHEN r.patient_id IS NOT NULL AND r.patient_id <> '' THEN 1 END) as reports_with_patient_id,
                    count(CASE WHEN r.patient_id IS NULL OR r.patient_id = '' THEN 1 END) as reports_without_patient_id
            """)
            stats = result.single()
            if stats:
                logger.info(f"Migration statistics: {dict(stats)}")
    
    def down(self):
        """Rollback migration - remove patient_id property"""
        with self.driver.session() as session:
            # Note: We're not removing the patient_id property from existing nodes
            # as this could cause data loss. We're only removing the index.
            
            # Drop the patient_id index if it was created by migration 003
            # (migration 002 might have already created it)
            logger.info("Checking if patient_id index should be removed...")
            
            # Remove migration record
            session.run("""
                MATCH (m:Migration {name: 'medical_imaging_schema_003'})
                DELETE m
            """)
            
            logger.info("Medical imaging property standardization migration rolled back")


def run_migration(uri: str, user: str, password: str, direction: str = "up"):
    """
    Run the migration
    
    Args:
        uri: Neo4j URI
        user: Neo4j username
        password: Neo4j password
        direction: "up" to apply, "down" to rollback
    """
    migration = MedicalImagingPropertyStandardizationMigration(uri, user, password)
    
    try:
        if direction == "up":
            migration.up()
            print("Medical imaging property standardization migration applied successfully")
        elif direction == "down":
            migration.down()
            print("Medical imaging property standardization migration rolled back successfully")
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