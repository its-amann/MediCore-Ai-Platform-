"""
Neo4j Migration: Medical Imaging Vector Embeddings Support
Adds vector embedding storage and indexing capabilities for semantic search
"""

import logging
from typing import Dict, Any
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class MedicalImagingVectorEmbeddingMigration:
    """
    Migration to add vector embedding support for medical imaging reports
    """
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def up(self):
        """Apply migration - add vector embedding support"""
        with self.driver.session() as session:
            # Add vector embedding properties to ImagingReport nodes
            logger.info("Adding vector embedding properties to ImagingReport nodes...")
            
            # Ensure report_embedding property exists for all ImagingReport nodes
            session.run("""
                MATCH (r:ImagingReport)
                WHERE r.report_embedding IS NULL
                SET r.report_embedding = []
            """)
            
            # Add embedding_model property if missing
            session.run("""
                MATCH (r:ImagingReport)
                WHERE r.embedding_model IS NULL
                SET r.embedding_model = 'gemini-embedding-001'
            """)
            
            # Add embedding_version property for tracking
            session.run("""
                MATCH (r:ImagingReport)
                WHERE r.embedding_version IS NULL
                SET r.embedding_version = '1.0'
            """)
            
            # Create standard indexes for embedding metadata
            logger.info("Creating indexes for embedding metadata...")
            session.run("""
                CREATE INDEX imaging_report_embedding_model IF NOT EXISTS
                FOR (r:ImagingReport) ON (r.embedding_model)
            """)
            
            session.run("""
                CREATE INDEX imaging_report_embedding_version IF NOT EXISTS
                FOR (r:ImagingReport) ON (r.embedding_version)
            """)
            
            # Add vector embedding properties to ImageAnalysis nodes
            logger.info("Adding vector embedding properties to ImageAnalysis nodes...")
            session.run("""
                MATCH (i:ImageAnalysis)
                WHERE i.analysis_embedding IS NULL
                SET i.analysis_embedding = []
            """)
            
            session.run("""
                MATCH (i:ImageAnalysis)
                WHERE i.embedding_model IS NULL
                SET i.embedding_model = 'gemini-embedding-001'
            """)
            
            # Create VectorSearchNode for optimized vector searches
            logger.info("Creating VectorSearchNode for optimized vector operations...")
            session.run("""
                CREATE CONSTRAINT vector_search_node_id IF NOT EXISTS
                FOR (v:VectorSearchNode) REQUIRE v.node_id IS UNIQUE
            """)
            
            # Add semantic search metadata
            session.run("""
                MATCH (r:ImagingReport)
                WHERE r.semantic_search_enabled IS NULL
                SET r.semantic_search_enabled = true
            """)
            
            # Create index for semantic search flag
            session.run("""
                CREATE INDEX imaging_report_semantic_search IF NOT EXISTS
                FOR (r:ImagingReport) ON (r.semantic_search_enabled)
            """)
            
            # Add vector dimension tracking
            session.run("""
                MATCH (r:ImagingReport)
                WHERE r.embedding_dimension IS NULL
                SET r.embedding_dimension = 768
            """)
            
            # Try to create vector index if GDS is available
            try:
                # Check if GDS is available
                result = session.run("CALL gds.version()")
                gds_version = result.single()
                logger.info(f"GDS version: {gds_version}")
                
                # Create vector index for ImagingReport embeddings
                logger.info("Creating vector index for ImagingReport embeddings...")
                session.run("""
                    CALL db.index.vector.createNodeIndex(
                        'imaging_report_embeddings',
                        'ImagingReport',
                        'report_embedding',
                        768,
                        'cosine'
                    )
                """)
                
                # Create vector index for ImageAnalysis embeddings
                logger.info("Creating vector index for ImageAnalysis embeddings...")
                session.run("""
                    CALL db.index.vector.createNodeIndex(
                        'image_analysis_embeddings',
                        'ImageAnalysis',
                        'analysis_embedding',
                        768,
                        'cosine'
                    )
                """)
                
                logger.info("Vector indexes created successfully")
                
            except Exception as e:
                logger.warning(f"GDS/Vector index not available, skipping vector index creation: {e}")
                logger.info("Note: Vector similarity search will use fallback methods without dedicated indexes")
            
            # Create helper stored procedures for vector operations
            logger.info("Creating helper relationships for vector search...")
            
            # Create a migration record
            session.run("""
                CREATE (m:Migration {
                    name: 'medical_imaging_schema_004',
                    description: 'Add vector embedding support for semantic search',
                    applied_at: datetime(),
                    version: '004'
                })
            """)
            
            logger.info("Medical imaging vector embedding migration completed successfully")
            
            # Log statistics
            result = session.run("""
                MATCH (r:ImagingReport)
                RETURN 
                    count(r) as total_reports,
                    count(CASE WHEN size(r.report_embedding) > 0 THEN 1 END) as reports_with_embeddings,
                    count(CASE WHEN r.semantic_search_enabled = true THEN 1 END) as semantic_search_enabled
            """)
            stats = result.single()
            if stats:
                logger.info(f"Migration statistics: {dict(stats)}")
    
    def down(self):
        """Rollback migration - remove vector embedding support"""
        with self.driver.session() as session:
            logger.info("Rolling back vector embedding support...")
            
            # Drop vector indexes if they exist
            try:
                session.run("CALL db.index.vector.drop('imaging_report_embeddings')")
                logger.info("Dropped imaging_report_embeddings vector index")
            except:
                pass
            
            try:
                session.run("CALL db.index.vector.drop('image_analysis_embeddings')")
                logger.info("Dropped image_analysis_embeddings vector index")
            except:
                pass
            
            # Drop regular indexes
            session.run("DROP INDEX imaging_report_embedding_model IF EXISTS")
            session.run("DROP INDEX imaging_report_embedding_version IF EXISTS")
            session.run("DROP INDEX imaging_report_semantic_search IF EXISTS")
            
            # Drop constraint
            session.run("DROP CONSTRAINT vector_search_node_id IF EXISTS")
            
            # Note: We're not removing the embedding properties from nodes
            # as this could cause data loss
            
            # Remove migration record
            session.run("""
                MATCH (m:Migration {name: 'medical_imaging_schema_004'})
                DELETE m
            """)
            
            logger.info("Medical imaging vector embedding migration rolled back")


def run_migration(uri: str, user: str, password: str, direction: str = "up"):
    """
    Run the migration
    
    Args:
        uri: Neo4j URI
        user: Neo4j username
        password: Neo4j password
        direction: "up" to apply, "down" to rollback
    """
    migration = MedicalImagingVectorEmbeddingMigration(uri, user, password)
    
    try:
        if direction == "up":
            migration.up()
            print("Medical imaging vector embedding migration applied successfully")
        elif direction == "down":
            migration.down()
            print("Medical imaging vector embedding migration rolled back successfully")
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