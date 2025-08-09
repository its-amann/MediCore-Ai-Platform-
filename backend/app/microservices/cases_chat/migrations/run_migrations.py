"""
Script to run Cases Chat database migrations
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from neo4j import GraphDatabase
from app.core.config import settings
from app.microservices.cases_chat.migrations import MigrationRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run database migrations"""
    
    # Create driver
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        max_connection_pool_size=50
    )
    
    try:
        # Create migration runner
        runner = MigrationRunner(driver)
        
        # Load migrations
        logger.info("Loading migrations...")
        runner.load_migrations()
        
        # Get current status
        status = runner.get_migration_status()
        logger.info(f"Migration status: {status['applied_count']} applied, {status['pending_count']} pending")
        
        if status['pending_count'] > 0:
            logger.info("Pending migrations:")
            for migration in status['pending_migrations']:
                logger.info(f"  - {migration['migration_id']}: {migration['description']}")
            
            # Run migrations
            logger.info("Running migrations...")
            result = runner.run_migrations_sync()
            
            if result['status'] == 'success':
                logger.info(f"Successfully ran {len(result['migrations_run'])} migrations")
            else:
                logger.error(f"Migration run completed with errors: {result['errors']}")
                
        else:
            logger.info("No pending migrations to run")
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise
    finally:
        driver.close()


if __name__ == "__main__":
    main()