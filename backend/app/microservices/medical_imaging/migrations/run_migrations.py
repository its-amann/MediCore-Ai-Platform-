"""
Run all medical imaging migrations
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from app.microservices.medical_imaging.migrations.medical_imaging_schema_001 import run_migration as run_migration_001
from app.microservices.medical_imaging.migrations.medical_imaging_schema_002 import run_migration as run_migration_002
from app.microservices.medical_imaging.migrations.medical_imaging_schema_003 import run_migration as run_migration_003
from app.microservices.medical_imaging.migrations.medical_imaging_schema_004 import run_migration as run_migration_004

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_all_migrations():
    """Run all medical imaging migrations in order"""
    # Load environment variables
    load_dotenv()
    
    # Get database credentials
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    logger.info("Starting medical imaging migrations...")
    
    # Migration 001: Base schema
    try:
        logger.info("Running migration 001: Base medical imaging schema...")
        run_migration_001(neo4j_uri, neo4j_user, neo4j_password, "up")
        logger.info("✅ Migration 001 completed successfully")
    except Exception as e:
        logger.error(f"❌ Migration 001 failed: {e}")
        return False
    
    # Migration 002: Full text storage and heatmap support
    try:
        logger.info("Running migration 002: Full text storage and heatmap support...")
        run_migration_002(neo4j_uri, neo4j_user, neo4j_password, "up")
        logger.info("✅ Migration 002 completed successfully")
    except Exception as e:
        logger.error(f"❌ Migration 002 failed: {e}")
        return False
    
    # Migration 003: Property standardization and patient_id
    try:
        logger.info("Running migration 003: Property standardization and patient_id...")
        run_migration_003(neo4j_uri, neo4j_user, neo4j_password, "up")
        logger.info("✅ Migration 003 completed successfully")
    except Exception as e:
        logger.error(f"❌ Migration 003 failed: {e}")
        return False
    
    # Migration 004: Vector embedding support
    try:
        logger.info("Running migration 004: Vector embedding support for semantic search...")
        run_migration_004(neo4j_uri, neo4j_user, neo4j_password, "up")
        logger.info("✅ Migration 004 completed successfully")
    except Exception as e:
        logger.error(f"❌ Migration 004 failed: {e}")
        return False
    
    logger.info("✅ All medical imaging migrations completed successfully!")
    return True


def rollback_all_migrations():
    """Rollback all medical imaging migrations in reverse order"""
    # Load environment variables
    load_dotenv()
    
    # Get database credentials
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    logger.info("Rolling back medical imaging migrations...")
    
    # Migration 004: Vector embedding support
    try:
        logger.info("Rolling back migration 004: Vector embedding support...")
        run_migration_004(neo4j_uri, neo4j_user, neo4j_password, "down")
        logger.info("✅ Migration 004 rolled back successfully")
    except Exception as e:
        logger.error(f"❌ Migration 004 rollback failed: {e}")
    
    # Migration 003: Property standardization and patient_id
    try:
        logger.info("Rolling back migration 003: Property standardization and patient_id...")
        run_migration_003(neo4j_uri, neo4j_user, neo4j_password, "down")
        logger.info("✅ Migration 003 rolled back successfully")
    except Exception as e:
        logger.error(f"❌ Migration 003 rollback failed: {e}")
    
    # Migration 002: Full text storage and heatmap support
    try:
        logger.info("Rolling back migration 002: Full text storage and heatmap support...")
        run_migration_002(neo4j_uri, neo4j_user, neo4j_password, "down")
        logger.info("✅ Migration 002 rolled back successfully")
    except Exception as e:
        logger.error(f"❌ Migration 002 rollback failed: {e}")
    
    # Migration 001: Base schema
    try:
        logger.info("Rolling back migration 001: Base medical imaging schema...")
        run_migration_001(neo4j_uri, neo4j_user, neo4j_password, "down")
        logger.info("✅ Migration 001 rolled back successfully")
    except Exception as e:
        logger.error(f"❌ Migration 001 rollback failed: {e}")
    
    logger.info("✅ All medical imaging migrations rolled back!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_all_migrations()
    else:
        run_all_migrations()