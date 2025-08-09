#!/usr/bin/env python3
"""
Migration script to add case numbers to existing cases in Neo4j
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from neo4j import GraphDatabase

# Add the backend directory to the Python path
backend_dir = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(backend_dir))

from app.microservices.cases_chat.services.case_numbering import CaseNumberGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CaseNumberMigration:
    """Handles migration of existing cases to add case numbers"""
    
    def __init__(self, uri: str, username: str, password: str):
        """
        Initialize the migration
        
        Args:
            uri: Neo4j connection URI
            username: Neo4j username
            password: Neo4j password
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.driver = None
        self.case_number_generator = None
        
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        
    def connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            
            self.case_number_generator = CaseNumberGenerator(self.driver)
            logger.info(f"Successfully connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
            
    def close(self):
        """Close the Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Closed Neo4j connection")
    
    def add_case_number_constraint(self):
        """Add unique constraint for case_number if it doesn't exist"""
        with self.driver.session() as session:
            try:
                query = """
                CREATE CONSTRAINT case_number_unique IF NOT EXISTS 
                FOR (c:Case) REQUIRE c.case_number IS UNIQUE
                """
                session.run(query)
                logger.info("Case number constraint created or already exists")
            except Exception as e:
                logger.warning(f"Could not create constraint: {e}")
    
    def get_cases_without_numbers(self, limit: int = None) -> list:
        """Get all cases that don't have case numbers"""
        with self.driver.session() as session:
            query = """
            MATCH (c:Case)
            WHERE c.case_number IS NULL OR c.case_number = ''
            RETURN c.case_id as case_id, c.created_at as created_at
            ORDER BY c.created_at ASC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            result = session.run(query)
            cases = []
            for record in result:
                cases.append({
                    'case_id': record['case_id'],
                    'created_at': record['created_at']
                })
            
            return cases
    
    def generate_case_number_for_date(self, date_str: str) -> str:
        """Generate a case number for a specific date"""
        # Parse the date
        if isinstance(date_str, str):
            try:
                # Try to parse ISO format
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                # Fallback to current date
                date = datetime.utcnow()
        else:
            date = datetime.utcnow()
        
        # Format date for case number
        formatted_date = date.strftime("%Y%m%d")
        
        # Get the next sequence number for that date
        with self.driver.session() as session:
            # Use a separate sequence for migration to avoid conflicts
            query = """
            MERGE (seq:CaseNumberSequence {date: $date})
            ON CREATE SET seq.current_number = 0, seq.created_at = datetime()
            WITH seq
            SET seq.current_number = seq.current_number + 1
            RETURN seq.current_number as next_number
            """
            
            result = session.run(query, {"date": formatted_date})
            record = result.single()
            
            if record:
                next_number = record["next_number"]
                case_number = f"MED-{formatted_date}-{str(next_number).zfill(4)}"
                return case_number
            else:
                raise Exception("Failed to generate sequence number")
    
    def update_case_with_number(self, case_id: str, case_number: str) -> bool:
        """Update a single case with a case number"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (c:Case {case_id: $case_id})
                SET c.case_number = $case_number
                RETURN c.case_id as case_id
                """
                
                result = session.run(query, {
                    "case_id": case_id,
                    "case_number": case_number
                })
                
                return result.single() is not None
            except Exception as e:
                logger.error(f"Error updating case {case_id}: {e}")
                return False
    
    def migrate_cases(self, batch_size: int = 100, dry_run: bool = False):
        """
        Migrate all cases without case numbers
        
        Args:
            batch_size: Number of cases to process at a time
            dry_run: If True, only simulate the migration
        """
        logger.info("Starting case number migration...")
        
        if not dry_run:
            # Add constraint first
            self.add_case_number_constraint()
        
        # Get all cases without numbers
        cases = self.get_cases_without_numbers()
        total_cases = len(cases)
        
        if total_cases == 0:
            logger.info("No cases need migration")
            return
        
        logger.info(f"Found {total_cases} cases without case numbers")
        
        # Process in batches
        success_count = 0
        error_count = 0
        
        for i, case in enumerate(cases):
            try:
                # Generate case number based on created date
                case_number = self.generate_case_number_for_date(case['created_at'])
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would assign {case_number} to case {case['case_id']}")
                    success_count += 1
                else:
                    # Update the case
                    if self.update_case_with_number(case['case_id'], case_number):
                        logger.info(f"Assigned {case_number} to case {case['case_id']}")
                        success_count += 1
                    else:
                        logger.error(f"Failed to update case {case['case_id']}")
                        error_count += 1
                
                # Progress indicator
                if (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i + 1}/{total_cases} cases processed")
                    
            except Exception as e:
                logger.error(f"Error processing case {case['case_id']}: {e}")
                error_count += 1
        
        # Summary
        logger.info(f"\nMigration complete:")
        logger.info(f"  Total cases: {total_cases}")
        logger.info(f"  Successful: {success_count}")
        logger.info(f"  Errors: {error_count}")
        
        if not dry_run and success_count > 0:
            # Verify migration
            remaining = len(self.get_cases_without_numbers())
            logger.info(f"  Cases still without numbers: {remaining}")
    
    def verify_migration(self):
        """Verify the migration was successful"""
        with self.driver.session() as session:
            # Count cases with and without case numbers
            query = """
            MATCH (c:Case)
            RETURN 
                count(c) as total_cases,
                sum(CASE WHEN c.case_number IS NOT NULL AND c.case_number <> '' THEN 1 ELSE 0 END) as with_numbers,
                sum(CASE WHEN c.case_number IS NULL OR c.case_number = '' THEN 1 ELSE 0 END) as without_numbers
            """
            
            result = session.run(query)
            record = result.single()
            
            if record:
                logger.info("\nMigration verification:")
                logger.info(f"  Total cases: {record['total_cases']}")
                logger.info(f"  With case numbers: {record['with_numbers']}")
                logger.info(f"  Without case numbers: {record['without_numbers']}")
                
                # Check for duplicates
                dup_query = """
                MATCH (c:Case)
                WHERE c.case_number IS NOT NULL
                WITH c.case_number as case_number, count(*) as count
                WHERE count > 1
                RETURN case_number, count
                ORDER BY count DESC
                """
                
                dup_result = session.run(dup_query)
                duplicates = list(dup_result)
                
                if duplicates:
                    logger.warning(f"\nFound {len(duplicates)} duplicate case numbers:")
                    for dup in duplicates[:5]:  # Show first 5
                        logger.warning(f"  {dup['case_number']}: {dup['count']} occurrences")
                else:
                    logger.info("\nNo duplicate case numbers found ✓")


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate existing cases to add case numbers"
    )
    
    parser.add_argument(
        "--host",
        default=os.getenv("NEO4J_HOST", "localhost"),
        help="Neo4j host (default: localhost)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("NEO4J_PORT", "7687")),
        help="Neo4j bolt port (default: 7687)"
    )
    
    parser.add_argument(
        "--username",
        default=os.getenv("NEO4J_USERNAME", "neo4j"),
        help="Neo4j username (default: neo4j)"
    )
    
    parser.add_argument(
        "--password",
        default=os.getenv("NEO4J_PASSWORD", "password"),
        help="Neo4j password"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without making changes"
    )
    
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing migration"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of cases to process at a time (default: 100)"
    )
    
    args = parser.parse_args()
    
    # Build connection URI
    uri = f"bolt://{args.host}:{args.port}"
    
    try:
        with CaseNumberMigration(uri, args.username, args.password) as migration:
            if args.verify_only:
                migration.verify_migration()
            else:
                migration.migrate_cases(
                    batch_size=args.batch_size,
                    dry_run=args.dry_run
                )
                
                if not args.dry_run:
                    migration.verify_migration()
                    
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()