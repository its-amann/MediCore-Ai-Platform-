
"""
Neo4j Migration: Medical Imaging Full Text Storage
Adds fields and indexes for storing complete image analysis text content
"""

import logging
from typing import Dict, Any
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class MedicalImagingFullTextMigration:
    """
    Migration to add full text storage capabilities for medical imaging
    """
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def up(self):
        """Apply migration - add full text storage fields"""
        with self.driver.session() as session:
            # Add properties to existing ImagingReport nodes
            # This won't affect existing data, just adds capability for new fields
            
            # Create full-text search index for reports
            session.run("""
                CREATE FULLTEXT INDEX imaging_report_fulltext IF NOT EXISTS
                FOR (r:ImagingReport) 
                ON EACH [r.overall_analysis, r.clinical_impression, r.findings, 
                         r.recommendations, r.patient_name, r.full_text_content]
            """)
            
            # Create full-text search index for image analyses
            session.run("""
                CREATE FULLTEXT INDEX image_analysis_fulltext IF NOT EXISTS
                FOR (i:ImageAnalysis)
                ON EACH [i.analysis_text, i.findings, i.annotations, i.full_text_content]
            """)
            
            # Create index for study type filtering
            session.run("""
                CREATE INDEX imaging_report_study_type IF NOT EXISTS
                FOR (r:ImagingReport) ON (r.study_type)
            """)
            
            # Create index for severity filtering
            session.run("""
                CREATE INDEX imaging_report_severity IF NOT EXISTS
                FOR (r:ImagingReport) ON (r.severity)
            """)
            
            # Create index for patient ID lookups
            session.run("""
                CREATE INDEX imaging_report_patient_id IF NOT EXISTS
                FOR (r:ImagingReport) ON (r.patient_id)
            """)
            
            # Create composite index for date range queries
            session.run("""
                CREATE INDEX imaging_report_date_range IF NOT EXISTS
                FOR (r:ImagingReport) ON (r.study_date, r.created_at)
            """)
            
            # Skip relationship constraints for Community Edition
            # Community Edition doesn't support relationship property existence constraints
            logger.info("Skipping relationship constraints (requires Enterprise Edition)")
            
            # Create Finding nodes for structured findings storage
            session.run("""
                CREATE CONSTRAINT finding_id IF NOT EXISTS
                FOR (f:Finding) REQUIRE f.finding_id IS UNIQUE
            """)
            
            # Create Citation nodes for evidence-based findings
            session.run("""
                CREATE CONSTRAINT citation_id IF NOT EXISTS
                FOR (c:Citation) REQUIRE c.citation_id IS UNIQUE
            """)
            
            # Update existing reports to have full_text_content field
            session.run("""
                MATCH (r:ImagingReport)
                WHERE r.full_text_content IS NULL
                SET r.full_text_content = 
                    COALESCE(r.overall_analysis, '') + ' ' + 
                    COALESCE(r.clinical_impression, '') + ' ' + 
                    COALESCE(r.findings, '') + ' ' + 
                    COALESCE(r.recommendations, '')
            """)
            
            # Update existing image analyses to have full_text_content field
            session.run("""
                MATCH (i:ImageAnalysis)
                WHERE i.full_text_content IS NULL
                SET i.full_text_content = COALESCE(i.analysis_text, '')
            """)
            
            # Create indexes for heatmap data storage
            session.run("""
                CREATE INDEX image_analysis_heatmap IF NOT EXISTS
                FOR (i:ImageAnalysis) ON (i.heatmap_original_image)
            """)
            
            # Skip property existence constraint for Community Edition
            # Community Edition doesn't support complex property existence constraints
            logger.info("Skipping heatmap completeness constraint (requires Enterprise Edition)")
            
            # Add full text content for all reports
            session.run("""
                MATCH (r:ImagingReport)
                WHERE r.full_text_content IS NULL
                WITH r
                OPTIONAL MATCH (r)-[:CONTAINS_IMAGE]->(i:ImageAnalysis)
                WITH r, COLLECT(COALESCE(i.analysis_text, '')) as image_texts
                SET r.full_text_content = 
                    COALESCE(r.overall_analysis, '') + ' ' + 
                    COALESCE(r.clinical_impression, '') + ' ' + 
                    COALESCE(r.findings, '') + ' ' + 
                    COALESCE(r.recommendations, '') + ' ' +
                    REDUCE(s = '', text IN image_texts | s + ' ' + text)
            """)
            
            logger.info("Medical imaging full text storage migration completed successfully")
    
    def down(self):
        """Rollback migration - remove full text storage fields"""
        with self.driver.session() as session:
            # Drop full-text indexes
            session.run("DROP INDEX imaging_report_fulltext IF EXISTS")
            session.run("DROP INDEX image_analysis_fulltext IF EXISTS")
            
            # Drop other indexes
            session.run("DROP INDEX imaging_report_study_type IF EXISTS")
            session.run("DROP INDEX imaging_report_severity IF EXISTS")
            session.run("DROP INDEX imaging_report_patient_id IF EXISTS")
            session.run("DROP INDEX imaging_report_date_range IF EXISTS")
            session.run("DROP INDEX image_analysis_heatmap IF EXISTS")
            
            # Drop constraints
            session.run("DROP CONSTRAINT finding_id IF EXISTS")
            session.run("DROP CONSTRAINT citation_id IF EXISTS")
            # Skip constraints that don't exist in Community Edition
            
            # Remove full_text_content properties (optional - can keep data)
            session.run("""
                MATCH (r:ImagingReport)
                WHERE r.full_text_content IS NOT NULL
                REMOVE r.full_text_content
            """)
            
            session.run("""
                MATCH (i:ImageAnalysis)
                WHERE i.full_text_content IS NOT NULL
                REMOVE i.full_text_content
            """)
            
            logger.info("Medical imaging full text storage migration rolled back successfully")


def run_migration(uri: str, user: str, password: str, direction: str = "up"):
    """
    Run the migration
    
    Args:
        uri: Neo4j URI
        user: Neo4j username
        password: Neo4j password
        direction: "up" to apply, "down" to rollback
    """
    migration = MedicalImagingFullTextMigration(uri, user, password)
    
    try:
        if direction == "up":
            migration.up()
            print("Medical imaging full text storage migration applied successfully")
        elif direction == "down":
            migration.down()
            print("Medical imaging full text storage migration rolled back successfully")
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