"""
Migration runner for collaboration microservice
Executes all migration files in order and tracks which have been run
"""

import os
import sys
import logging
import importlib.util
from pathlib import Path
from typing import List, Dict, Any
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))  # Go up to backend directory

from app.microservices.collaboration.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationRunner:
    """
    Runs database migrations for the collaboration microservice
    """
    
    def __init__(self, driver=None):
        """Initialize the migration runner with Neo4j connection"""
        if driver:
            # Use provided driver (from unified connection)
            self.driver = driver
            self.owns_driver = False
        else:
            # Create own driver (for standalone execution)
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            self.owns_driver = True
        self.migrations_dir = Path(__file__).parent
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def close(self):
        """Close the Neo4j driver connection"""
        if self.driver and self.owns_driver:
            self.driver.close()
    
    def get_migration_files(self) -> List[Path]:
        """
        Get all migration files in order
        
        Returns:
            List of migration file paths sorted by name
        """
        migration_files = []
        
        for file in self.migrations_dir.glob("*.py"):
            # Skip this runner script and __init__.py
            if file.name in ["run_migrations.py", "__init__.py"]:
                continue
            
            # Only include files that start with numbers (migration pattern)
            if file.stem[0].isdigit():
                migration_files.append(file)
        
        # Sort by filename to ensure correct order
        migration_files.sort()
        return migration_files
    
    def load_migration_module(self, file_path: Path) -> Any:
        """
        Dynamically load a migration module
        
        Args:
            file_path: Path to the migration file
            
        Returns:
            Loaded module or None if failed
        """
        try:
            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            logger.error(f"Failed to load migration {file_path.name}: {str(e)}")
            return None
    
    def get_completed_migrations(self) -> List[str]:
        """
        Get list of already completed migrations
        
        Returns:
            List of completed migration IDs
        """
        with self.driver.session() as session:
            try:
                query = """
                MATCH (m:Migration {status: 'completed'})
                RETURN m.migration_id as migration_id
                ORDER BY m.migration_id
                """
                result = session.run(query)
                return [record["migration_id"] for record in result]
            except Exception as e:
                logger.warning(f"Failed to get completed migrations: {str(e)}")
                return []
    
    def create_migration_tracking(self):
        """Create the migration tracking constraint if it doesn't exist"""
        with self.driver.session() as session:
            try:
                query = """
                CREATE CONSTRAINT migration_id_unique IF NOT EXISTS 
                FOR (m:Migration) REQUIRE m.migration_id IS UNIQUE
                """
                session.run(query)
                logger.info("Migration tracking constraint created or already exists")
            except Exception as e:
                logger.warning(f"Could not create migration tracking constraint: {str(e)}")
    
    def run_migration(self, file_path: Path) -> bool:
        """
        Run a single migration file
        
        Args:
            file_path: Path to the migration file
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"\nRunning migration: {file_path.name}")
        
        # Load the migration module
        module = self.load_migration_module(file_path)
        if not module:
            return False
        
        # Find the migration class (should have 'Migration' in the name)
        migration_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                'Migration' in attr_name and 
                hasattr(attr, 'run')):
                migration_class = attr
                break
        
        if not migration_class:
            logger.error(f"No migration class found in {file_path.name}")
            return False
        
        # Run the migration
        try:
            with migration_class(
                settings.NEO4J_URI,
                settings.NEO4J_USER,
                settings.NEO4J_PASSWORD
            ) as migration:
                # Check if already completed
                if hasattr(migration, 'is_migration_completed') and migration.is_migration_completed():
                    logger.info(f"Migration {file_path.stem} already completed, skipping...")
                    return True
                
                # Run the migration
                if migration.run():
                    logger.info(f"Migration {file_path.stem} completed successfully!")
                    return True
                else:
                    logger.error(f"Migration {file_path.stem} failed!")
                    return False
        except Exception as e:
            logger.error(f"Error running migration {file_path.name}: {str(e)}")
            return False
    
    def run_all_migrations(self) -> Dict[str, Any]:
        """
        Run all pending migrations
        
        Returns:
            Dictionary with migration results
        """
        logger.info("Starting collaboration microservice migrations...")
        
        # Create migration tracking
        self.create_migration_tracking()
        
        # Get migration files
        migration_files = self.get_migration_files()
        if not migration_files:
            logger.info("No migration files found")
            return {"total": 0, "successful": 0, "failed": 0, "skipped": 0}
        
        logger.info(f"Found {len(migration_files)} migration files")
        
        # Get completed migrations
        completed = self.get_completed_migrations()
        logger.info(f"Already completed migrations: {len(completed)}")
        
        # Run migrations
        results = {
            "total": len(migration_files),
            "successful": 0,
            "failed": 0,
            "skipped": 0
        }
        
        for file_path in migration_files:
            # Check if already completed
            migration_id = file_path.stem
            if migration_id in completed:
                logger.info(f"Skipping already completed migration: {migration_id}")
                results["skipped"] += 1
                continue
            
            # Run the migration
            if self.run_migration(file_path):
                results["successful"] += 1
            else:
                results["failed"] += 1
                # Stop on first failure
                logger.error("Stopping migrations due to failure")
                break
        
        # Summary
        logger.info("\n" + "="*50)
        logger.info("Migration Summary:")
        logger.info(f"  Total migrations: {results['total']}")
        logger.info(f"  Successful: {results['successful']}")
        logger.info(f"  Failed: {results['failed']}")
        logger.info(f"  Skipped: {results['skipped']}")
        logger.info("="*50)
        
        return results
    
    def verify_database_state(self):
        """Verify the database state after migrations"""
        with self.driver.session() as session:
            try:
                # Check constraints
                constraints_query = """
                SHOW CONSTRAINTS
                """
                constraints = list(session.run(constraints_query))
                logger.info(f"\nDatabase has {len(constraints)} constraints")
                
                # Check indexes
                indexes_query = """
                SHOW INDEXES
                """
                indexes = list(session.run(indexes_query))
                logger.info(f"Database has {len(indexes)} indexes")
                
                # Check migrations
                migrations_query = """
                MATCH (m:Migration)
                RETURN m.migration_id as id, m.status as status, m.completed_at as completed_at
                ORDER BY m.migration_id
                """
                migrations = list(session.run(migrations_query))
                logger.info(f"\nCompleted migrations:")
                for m in migrations:
                    logger.info(f"  - {m['id']}: {m['status']} ({m['completed_at']})")
                    
            except Exception as e:
                logger.error(f"Failed to verify database state: {str(e)}")


def main():
    """Main function to run all migrations"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run database migrations for the collaboration microservice"
    )
    
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify the current database state without running migrations"
    )
    
    parser.add_argument(
        "--specific",
        type=str,
        help="Run a specific migration file by name (e.g., 001_collaboration_constraints)"
    )
    
    args = parser.parse_args()
    
    try:
        with MigrationRunner() as runner:
            if args.verify_only:
                runner.verify_database_state()
            elif args.specific:
                # Run a specific migration
                migration_file = runner.migrations_dir / f"{args.specific}.py"
                if migration_file.exists():
                    if runner.run_migration(migration_file):
                        logger.info("Migration completed successfully!")
                    else:
                        logger.error("Migration failed!")
                        sys.exit(1)
                else:
                    logger.error(f"Migration file not found: {args.specific}.py")
                    sys.exit(1)
            else:
                # Run all migrations
                results = runner.run_all_migrations()
                
                # Verify state after migrations
                runner.verify_database_state()
                
                # Exit with error if any migrations failed
                if results["failed"] > 0:
                    sys.exit(1)
                    
    except Exception as e:
        logger.error(f"Migration runner failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()