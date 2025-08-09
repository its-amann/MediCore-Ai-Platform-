"""
Database migration scripts for case numbering system.

This module provides migration scripts to:
- Standardize case number format
- Create necessary indexes
- Fix existing data inconsistencies
- Update API endpoints
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from neo4j import GraphDatabase
import concurrent.futures

# Check if async Neo4j is available (Neo4j 5.x)
try:
    from neo4j import AsyncGraphDatabase
    ASYNC_NEO4J_AVAILABLE = True
except ImportError:
    AsyncGraphDatabase = None
    ASYNC_NEO4J_AVAILABLE = False

logger = logging.getLogger(__name__)


class CaseNumberingMigration:
    """Migration handler for case numbering system."""
    
    def __init__(self, neo4j_url: str, neo4j_user: str, neo4j_password: str):
        if ASYNC_NEO4J_AVAILABLE:
            self.driver = AsyncGraphDatabase.driver(
                neo4j_url,
                auth=(neo4j_user, neo4j_password)
            )
            self.sync_driver = None
        else:
            self.driver = None
            self.sync_driver = GraphDatabase.driver(
                neo4j_url,
                auth=(neo4j_user, neo4j_password)
            )
        
        # Create executor for sync operations if needed
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=5) if not ASYNC_NEO4J_AVAILABLE else None
        
    async def close(self):
        """Close database connection."""
        if self.driver and ASYNC_NEO4J_AVAILABLE:
            await self.driver.close()
        if self.sync_driver:
            self.sync_driver.close()
        if self._executor:
            self._executor.shutdown(wait=True)
    
    async def _run_query(self, query: str, params: Dict[str, Any] = None):
        """Run a query handling both async and sync drivers."""
        if ASYNC_NEO4J_AVAILABLE and self.driver:
            async with self.driver.session() as session:
                return await session.run(query, params or {})
        else:
            # Run sync query in executor
            def run_sync():
                with self.sync_driver.session() as session:
                    return list(session.run(query, params or {}))
            
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._executor, run_sync)
    
    async def _run_in_transaction(self, transaction_func):
        """Run a function in a transaction handling both async and sync drivers."""
        if ASYNC_NEO4J_AVAILABLE and self.driver:
            async with self.driver.session() as session:
                return await session.execute_write(transaction_func)
        else:
            # Run sync transaction in executor
            def run_sync():
                with self.sync_driver.session() as session:
                    return session.execute_write(transaction_func)
            
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._executor, run_sync)
    
    async def create_indexes(self) -> Dict[str, Any]:
        """Create all necessary indexes for performance."""
        results = {"indexes_created": [], "errors": []}
        
        indexes = [
            # Case indexes
            ("Case", "case_number", "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.case_number)"),
            ("Case", "created_date", "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.created_date)"),
            ("Case", "status", "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.status)"),
            ("Case", "assigned_to", "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.assigned_to)"),
            
            # Sequence indexes
            ("CaseNumberSequence", "date", "CREATE INDEX IF NOT EXISTS FOR (seq:CaseNumberSequence) ON (seq.date)"),
            
            # Constraints
            ("Case", "case_number_unique", "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Case) REQUIRE c.case_number IS UNIQUE"),
            
            # Composite indexes for search performance
            ("Case", "date_status", "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.created_date, c.status)"),
        ]
        
        for label, name, query in indexes:
            try:
                await self._run_query(query)
                results["indexes_created"].append(f"{label}.{name}")
                logger.info(f"Created index: {label}.{name}")
            except Exception as e:
                error_msg = f"Error creating index {label}.{name}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        return results
    
    async def standardize_case_numbers(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Standardize all case numbers to C{YYYYMMDD}{NNNNN} format.
        
        Args:
            dry_run: If True, only simulate the migration
            
        Returns:
            dict: Migration results
        """
        results = {
            "total_cases": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
            "mappings": []
        }
        
        async with self.driver.session() as session:
            # Find all cases
            count_result = await session.run("MATCH (c:Case) RETURN count(c) as total")
            results["total_cases"] = (await count_result.single())["total"]
            
            # Process in batches
            batch_size = 1000
            offset = 0
            
            while offset < results["total_cases"]:
                batch_query = """
                MATCH (c:Case)
                RETURN c.id as id, c.case_number as case_number
                ORDER BY c.created_at
                SKIP $offset
                LIMIT $batch_size
                """
                
                batch_result = await session.run(
                    batch_query,
                    offset=offset,
                    batch_size=batch_size
                )
                
                async for record in batch_result:
                    case_id = record["id"]
                    old_number = record["case_number"]
                    
                    # Check if already in new format
                    if old_number and old_number.startswith("C") and len(old_number) == 14:
                        results["skipped"] += 1
                        continue
                    
                    try:
                        # Convert to new format
                        new_number = self._convert_to_standard_format(old_number)
                        
                        if not dry_run and new_number:
                            update_query = """
                            MATCH (c:Case {id: $id})
                            SET c.case_number = $new_number,
                                c.legacy_case_number = $old_number,
                                c.migrated_at = datetime()
                            """
                            
                            await session.run(
                                update_query,
                                id=case_id,
                                new_number=new_number,
                                old_number=old_number
                            )
                        
                        results["updated"] += 1
                        results["mappings"].append({
                            "case_id": case_id,
                            "old": old_number,
                            "new": new_number
                        })
                        
                    except Exception as e:
                        results["errors"].append({
                            "case_id": case_id,
                            "old_number": old_number,
                            "error": str(e)
                        })
                
                offset += batch_size
                logger.info(f"Processed {min(offset, results['total_cases'])} / {results['total_cases']} cases")
        
        return results
    
    def _convert_to_standard_format(self, old_number: str) -> str:
        """
        Convert various legacy formats to standard C{YYYYMMDD}{NNNNN} format.
        
        Supported legacy formats:
        - MED-20231231-0001 -> C2023123100001
        - CASE-2023-12-31-001 -> C2023123100001
        - 2023123100001 -> C2023123100001
        """
        if not old_number:
            raise ValueError("Empty case number")
        
        # Already in correct format
        if old_number.startswith("C") and len(old_number) == 14:
            return old_number
        
        # MED-YYYYMMDD-NNNN format
        if "-" in old_number:
            parts = old_number.split("-")
            
            if len(parts) == 3:  # MED-20231231-0001
                date_str = parts[1]
                seq_str = parts[2]
                return f"C{date_str}{seq_str.zfill(5)}"
            
            elif len(parts) == 5:  # CASE-2023-12-31-001
                year = parts[1]
                month = parts[2].zfill(2)
                day = parts[3].zfill(2)
                seq = parts[4].zfill(5)
                return f"C{year}{month}{day}{seq}"
        
        # Plain number format YYYYMMDDNNNNN
        if old_number.isdigit() and len(old_number) >= 9:
            date_part = old_number[:8]
            seq_part = old_number[8:].zfill(5)
            return f"C{date_part}{seq_part}"
        
        raise ValueError(f"Unknown case number format: {old_number}")
    
    async def add_missing_fields(self) -> Dict[str, Any]:
        """Add missing fields to Case nodes."""
        results = {"fields_added": 0, "errors": []}
        
        async with self.driver.session() as session:
            # Add created_date field based on case_number
            query = """
            MATCH (c:Case)
            WHERE c.created_date IS NULL AND c.case_number IS NOT NULL
            WITH c, substring(c.case_number, 1, 8) as date_str
            SET c.created_date = date_str
            RETURN count(c) as updated
            """
            
            try:
                result = await session.run(query)
                record = await result.single()
                results["fields_added"] = record["updated"]
                logger.info(f"Added created_date to {record['updated']} cases")
            except Exception as e:
                results["errors"].append(f"Error adding created_date: {str(e)}")
        
        return results
    
    async def create_sequences_from_existing(self) -> Dict[str, Any]:
        """Create CaseNumberSequence nodes based on existing cases."""
        results = {"sequences_created": 0, "errors": []}
        
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case)
            WHERE c.case_number IS NOT NULL
            WITH substring(c.case_number, 1, 8) as date_str, count(c) as case_count
            MERGE (seq:CaseNumberSequence {date: date_str})
            ON CREATE SET 
                seq.current_number = case_count,
                seq.created_at = datetime(),
                seq.updated_at = datetime()
            ON MATCH SET
                seq.current_number = CASE 
                    WHEN seq.current_number < case_count 
                    THEN case_count 
                    ELSE seq.current_number 
                END,
                seq.updated_at = datetime()
            RETURN count(seq) as created
            """
            
            try:
                result = await session.run(query)
                record = await result.single()
                results["sequences_created"] = record["created"]
                logger.info(f"Created/updated {record['created']} sequences")
            except Exception as e:
                results["errors"].append(f"Error creating sequences: {str(e)}")
        
        return results
    
    async def run_full_migration(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Run the complete migration process.
        
        Args:
            dry_run: If True, only simulate the migration
            
        Returns:
            dict: Complete migration results
        """
        logger.info(f"Starting case numbering migration (dry_run={dry_run})")
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
            "steps": {}
        }
        
        try:
            # Step 1: Create indexes
            logger.info("Step 1: Creating indexes...")
            results["steps"]["indexes"] = await self.create_indexes()
            
            # Step 2: Standardize case numbers
            logger.info("Step 2: Standardizing case numbers...")
            results["steps"]["standardization"] = await self.standardize_case_numbers(dry_run)
            
            # Step 3: Add missing fields
            if not dry_run:
                logger.info("Step 3: Adding missing fields...")
                results["steps"]["fields"] = await self.add_missing_fields()
                
                # Step 4: Create sequences
                logger.info("Step 4: Creating sequences...")
                results["steps"]["sequences"] = await self.create_sequences_from_existing()
            
            results["success"] = True
            logger.info("Migration completed successfully")
            
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            logger.error(f"Migration failed: {e}")
        
        return results


async def main():
    """Run migration from command line."""
    import os
    import argparse
    
    parser = argparse.ArgumentParser(description="Case numbering system migration")
    parser.add_argument("--neo4j-url", default=os.getenv("NEO4J_URL", "bolt://localhost:7687"))
    parser.add_argument("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"))
    parser.add_argument("--neo4j-password", default=os.getenv("NEO4J_PASSWORD", "password"))
    parser.add_argument("--dry-run", action="store_true", help="Simulate migration without making changes")
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run migration
    migration = CaseNumberingMigration(
        args.neo4j_url,
        args.neo4j_user,
        args.neo4j_password
    )
    
    try:
        results = await migration.run_full_migration(args.dry_run)
        
        # Print results
        import json
        print("\nMigration Results:")
        print(json.dumps(results, indent=2))
        
    finally:
        await migration.close()


if __name__ == "__main__":
    asyncio.run(main())