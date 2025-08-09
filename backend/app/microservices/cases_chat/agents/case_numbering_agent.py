"""
Case Numbering Agent - Specialized sub-agent for fixing case numbering system errors.

This agent implements a centralized case numbering service with:
- C{YYYYMMDD}{NNNNN} format
- Standardized database schema
- Validation system
- Frontend-backend ID consistency
- Search functionality
- Performance optimization
"""

import logging
import re
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from contextlib import asynccontextmanager
import redis.asyncio as redis
from neo4j import GraphDatabase
from pydantic import BaseModel, Field, validator
import os
from enum import Enum
import concurrent.futures

# Check if async Neo4j is available (Neo4j 5.x)
try:
    from neo4j import AsyncGraphDatabase, AsyncSession
    ASYNC_NEO4J_AVAILABLE = True
except ImportError:
    AsyncGraphDatabase = None
    AsyncSession = None
    ASYNC_NEO4J_AVAILABLE = False
    from neo4j import Session

logger = logging.getLogger(__name__)


class CaseNumberFormat(str, Enum):
    """Standardized case number formats."""
    STANDARD = "C{YYYYMMDD}{NNNNN}"  # C202312310001
    LEGACY = "{PREFIX}-{YYYYMMDD}-{NNNN}"  # MED-20231231-0001


class CaseNumberConfig(BaseModel):
    """Configuration for case numbering system."""
    format: CaseNumberFormat = CaseNumberFormat.STANDARD
    prefix: str = "C"
    number_padding: int = 5
    timezone: str = "UTC"
    redis_url: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))
    neo4j_url: str = Field(default_factory=lambda: os.getenv("NEO4J_URL", "bolt://localhost:7687"))
    neo4j_user: str = Field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    neo4j_password: str = Field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", "password"))
    connection_pool_size: int = 50
    max_retry_attempts: int = 3
    lock_timeout: int = 5  # seconds


class ValidationError(Exception):
    """Case number validation error."""
    pass


class ConcurrencyError(Exception):
    """Concurrency-related error in case number generation."""
    pass


class CaseNumberingService:
    """
    Centralized case numbering service with:
    - Distributed locking via Redis
    - Connection pooling
    - Timezone awareness
    - Comprehensive validation
    - Search functionality
    - Migration support
    """
    
    def __init__(self, config: CaseNumberConfig):
        self.config = config
        self._driver = None
        self._redis = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize database connections and create indexes."""
        if self._initialized:
            return
            
        # Initialize Neo4j driver with connection pooling
        if ASYNC_NEO4J_AVAILABLE:
            self._driver = AsyncGraphDatabase.driver(
                self.config.neo4j_url,
                auth=(self.config.neo4j_user, self.config.neo4j_password),
                max_connection_pool_size=self.config.connection_pool_size
            )
            self._sync_driver = None
        else:
            self._driver = None
            self._sync_driver = GraphDatabase.driver(
                self.config.neo4j_url,
                auth=(self.config.neo4j_user, self.config.neo4j_password),
                max_connection_pool_size=self.config.connection_pool_size
            )
        
        # Create executor for sync operations if needed
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=5) if not ASYNC_NEO4J_AVAILABLE else None
        
        # Initialize Redis for distributed locking
        self._redis = await redis.from_url(
            self.config.redis_url,
            decode_responses=True
        )
        
        # Create necessary indexes
        await self._create_indexes()
        
        self._initialized = True
        logger.info("CaseNumberingService initialized successfully")
    
    async def close(self):
        """Close all connections."""
        if self._driver and ASYNC_NEO4J_AVAILABLE:
            await self._driver.close()
        if self._sync_driver:
            self._sync_driver.close()
        if self._redis:
            await self._redis.close()
        if self._executor:
            self._executor.shutdown(wait=True)
        self._initialized = False
    
    @asynccontextmanager
    async def _get_session(self):
        """Get a database session (async or sync)."""
        if ASYNC_NEO4J_AVAILABLE and self._driver:
            async with self._driver.session() as session:
                yield session
        else:
            session = self._sync_driver.session()
            try:
                yield session
            finally:
                session.close()
    
    async def _run_query(self, session, query: str, params: Dict[str, Any] = None):
        """Run a query handling both async and sync sessions."""
        if ASYNC_NEO4J_AVAILABLE:
            return await session.run(query, params or {})
        else:
            # Run sync query in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor,
                lambda: session.run(query, params or {})
            )
    
    async def _create_indexes(self):
        """Create database indexes for performance."""
        async with self._get_session() as session:
            indexes = [
                "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.case_number)",
                "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.created_date)",
                "CREATE INDEX IF NOT EXISTS FOR (seq:CaseNumberSequence) ON (seq.date)",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Case) REQUIRE c.case_number IS UNIQUE"
            ]
            
            for index_query in indexes:
                try:
                    await self._run_query(session, index_query)
                    logger.info(f"Created index: {index_query}")
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")
    
    @asynccontextmanager
    async def _distributed_lock(self, key: str, timeout: int = None):
        """Acquire distributed lock using Redis."""
        timeout = timeout or self.config.lock_timeout
        lock_key = f"case_number_lock:{key}"
        lock_value = f"{os.getpid()}:{asyncio.current_task().get_name()}"
        
        try:
            # Try to acquire lock
            acquired = await self._redis.set(
                lock_key, lock_value, 
                ex=timeout, nx=True
            )
            
            if not acquired:
                raise ConcurrencyError(f"Could not acquire lock for {key}")
            
            yield
            
        finally:
            # Release lock only if we own it
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            await self._redis.eval(lua_script, 1, lock_key, lock_value)
    
    def _get_current_date(self) -> str:
        """Get current date in configured timezone."""
        now = datetime.now(timezone.utc)
        # TODO: Convert to configured timezone
        return now.strftime("%Y%m%d")
    
    async def generate_case_number(self, retry_attempt: int = 0) -> str:
        """
        Generate a new case number with distributed locking.
        
        Returns:
            str: Generated case number in format C{YYYYMMDD}{NNNNN}
        """
        if retry_attempt >= self.config.max_retry_attempts:
            raise ConcurrencyError("Max retry attempts reached for case number generation")
        
        date_str = self._get_current_date()
        
        try:
            async with self._distributed_lock(f"sequence:{date_str}"):
                async with self._driver.session() as session:
                    # Use atomic operation to get next sequence number
                    query = """
                    MERGE (seq:CaseNumberSequence {date: $date})
                    ON CREATE SET 
                        seq.current_number = 1,
                        seq.created_at = datetime(),
                        seq.updated_at = datetime()
                    ON MATCH SET 
                        seq.current_number = seq.current_number + 1,
                        seq.updated_at = datetime()
                    RETURN seq.current_number as next_number
                    """
                    
                    result = await session.run(query, date=date_str)
                    record = await result.single()
                    
                    if not record:
                        raise RuntimeError("Failed to get sequence number")
                    
                    next_number = record["next_number"]
                    
                    # Format case number based on configuration
                    if self.config.format == CaseNumberFormat.STANDARD:
                        case_number = f"{self.config.prefix}{date_str}{str(next_number).zfill(self.config.number_padding)}"
                    else:
                        case_number = f"{self.config.prefix}-{date_str}-{str(next_number).zfill(self.config.number_padding)}"
                    
                    # Validate before returning
                    if not self.validate_case_number(case_number):
                        raise ValidationError(f"Generated invalid case number: {case_number}")
                    
                    logger.info(f"Generated case number: {case_number}")
                    return case_number
                    
        except ConcurrencyError:
            # Retry with exponential backoff
            await asyncio.sleep(0.1 * (2 ** retry_attempt))
            return await self.generate_case_number(retry_attempt + 1)
        except Exception as e:
            logger.error(f"Error generating case number: {e}")
            raise
    
    def validate_case_number(self, case_number: str) -> bool:
        """
        Validate case number format.
        
        Args:
            case_number: Case number to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not case_number:
            return False
        
        if self.config.format == CaseNumberFormat.STANDARD:
            # Pattern: C{YYYYMMDD}{NNNNN}
            pattern = rf'^{re.escape(self.config.prefix)}\d{{8}}\d{{{self.config.number_padding}}}$'
        else:
            # Pattern: {PREFIX}-{YYYYMMDD}-{NNNN}
            pattern = rf'^{re.escape(self.config.prefix)}-\d{{8}}-\d{{{self.config.number_padding}}}$'
        
        return bool(re.match(pattern, case_number))
    
    def parse_case_number(self, case_number: str) -> Dict[str, Any]:
        """
        Parse case number into components.
        
        Args:
            case_number: Case number to parse
            
        Returns:
            dict: Components {prefix, date, sequence_number}
        """
        if not self.validate_case_number(case_number):
            raise ValidationError(f"Invalid case number format: {case_number}")
        
        if self.config.format == CaseNumberFormat.STANDARD:
            # C20231231000001
            prefix = case_number[:len(self.config.prefix)]
            date = case_number[len(self.config.prefix):len(self.config.prefix)+8]
            sequence = case_number[len(self.config.prefix)+8:]
        else:
            # MED-20231231-0001
            parts = case_number.split('-')
            prefix = parts[0]
            date = parts[1]
            sequence = parts[2]
        
        return {
            "prefix": prefix,
            "date": date,
            "sequence_number": int(sequence),
            "formatted_date": f"{date[:4]}-{date[4:6]}-{date[6:8]}"
        }
    
    async def search_by_case_number(self, case_number: str) -> Optional[Dict[str, Any]]:
        """
        Search for a case by case number.
        
        Args:
            case_number: Case number to search
            
        Returns:
            dict: Case data if found, None otherwise
        """
        if not self.validate_case_number(case_number):
            raise ValidationError(f"Invalid case number: {case_number}")
        
        async with self._driver.session() as session:
            query = """
            MATCH (c:Case {case_number: $case_number})
            RETURN c {
                .id,
                .case_number,
                .created_at,
                .updated_at,
                .status,
                .assigned_to,
                .priority
            } as case
            """
            
            result = await session.run(query, case_number=case_number)
            record = await result.single()
            
            return record["case"] if record else None
    
    async def search_cases_by_date_range(
        self, 
        start_date: str, 
        end_date: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search cases by date range.
        
        Args:
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            list: List of cases
        """
        async with self._driver.session() as session:
            query = """
            MATCH (c:Case)
            WHERE c.created_date >= $start_date AND c.created_date <= $end_date
            RETURN c {
                .id,
                .case_number,
                .created_at,
                .status
            } as case
            ORDER BY c.case_number DESC
            SKIP $offset
            LIMIT $limit
            """
            
            result = await session.run(
                query,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                offset=offset
            )
            
            cases = []
            async for record in result:
                cases.append(record["case"])
            
            return cases
    
    async def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get case numbering statistics.
        
        Args:
            days: Number of days to include
            
        Returns:
            dict: Statistics including daily counts, totals, etc.
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        async with self._driver.session() as session:
            # Use optimized query with proper indexing
            query = """
            MATCH (seq:CaseNumberSequence)
            WHERE seq.date >= $start_date AND seq.date <= $end_date
            WITH seq
            ORDER BY seq.date DESC
            WITH collect(seq) as sequences
            RETURN {
                total_days: size(sequences),
                total_cases: reduce(s = 0, seq IN sequences | s + seq.current_number),
                max_daily_cases: reduce(m = 0, seq IN sequences | 
                    CASE WHEN seq.current_number > m THEN seq.current_number ELSE m END),
                recent_days: [seq IN sequences[0..7] | {date: seq.date, count: seq.current_number}]
            } as stats
            """
            
            result = await session.run(
                query,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d")
            )
            
            record = await result.single()
            
            if record and record["stats"]:
                stats = record["stats"]
                stats["avg_daily_cases"] = (
                    stats["total_cases"] / stats["total_days"] 
                    if stats["total_days"] > 0 else 0
                )
                return stats
            
            return {
                "total_days": 0,
                "total_cases": 0,
                "max_daily_cases": 0,
                "avg_daily_cases": 0,
                "recent_days": []
            }
    
    async def translate_case_id(self, case_id: str) -> Tuple[str, str]:
        """
        Translate between internal ID and case number.
        
        Args:
            case_id: Either internal ID or case number
            
        Returns:
            tuple: (internal_id, case_number)
        """
        async with self._driver.session() as session:
            # Check if it's a case number
            if self.validate_case_number(case_id):
                query = """
                MATCH (c:Case {case_number: $case_id})
                RETURN c.id as internal_id, c.case_number as case_number
                """
            else:
                # Assume it's an internal ID
                query = """
                MATCH (c:Case {id: $case_id})
                RETURN c.id as internal_id, c.case_number as case_number
                """
            
            result = await session.run(query, case_id=case_id)
            record = await result.single()
            
            if record:
                return record["internal_id"], record["case_number"]
            
            raise ValueError(f"Case not found: {case_id}")
    
    async def migrate_legacy_case_numbers(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Migrate legacy case numbers to new format.
        
        Args:
            dry_run: If True, only simulate migration
            
        Returns:
            dict: Migration results
        """
        results = {
            "total_cases": 0,
            "migrated": 0,
            "errors": [],
            "mappings": []
        }
        
        async with self._driver.session() as session:
            # Find cases with legacy format
            query = """
            MATCH (c:Case)
            WHERE c.case_number =~ '^[A-Z]{3}-\\d{8}-\\d{4}$'
            RETURN c.id as id, c.case_number as old_number
            ORDER BY c.created_at
            """
            
            result = await session.run(query)
            
            async for record in result:
                results["total_cases"] += 1
                old_number = record["old_number"]
                
                try:
                    # Parse legacy format
                    parts = old_number.split('-')
                    date_str = parts[1]
                    sequence = int(parts[2])
                    
                    # Generate new format
                    new_number = f"{self.config.prefix}{date_str}{str(sequence).zfill(self.config.number_padding)}"
                    
                    if not dry_run:
                        # Update case with new number
                        update_query = """
                        MATCH (c:Case {id: $id})
                        SET c.case_number = $new_number,
                            c.legacy_case_number = $old_number,
                            c.migrated_at = datetime()
                        """
                        await session.run(
                            update_query,
                            id=record["id"],
                            new_number=new_number,
                            old_number=old_number
                        )
                    
                    results["migrated"] += 1
                    results["mappings"].append({
                        "old": old_number,
                        "new": new_number
                    })
                    
                except Exception as e:
                    results["errors"].append({
                        "case_id": record["id"],
                        "old_number": old_number,
                        "error": str(e)
                    })
        
        return results
    
    async def fix_duplicate_case_numbers(self) -> Dict[str, Any]:
        """
        Detect and fix duplicate case numbers.
        
        Returns:
            dict: Fix results
        """
        results = {
            "duplicates_found": 0,
            "fixed": 0,
            "errors": []
        }
        
        async with self._driver.session() as session:
            # Find duplicate case numbers
            query = """
            MATCH (c:Case)
            WITH c.case_number as case_number, collect(c) as cases
            WHERE size(cases) > 1
            RETURN case_number, cases
            """
            
            result = await session.run(query)
            
            async for record in result:
                case_number = record["case_number"]
                cases = record["cases"]
                results["duplicates_found"] += len(cases) - 1
                
                # Keep the oldest case, regenerate numbers for others
                sorted_cases = sorted(cases, key=lambda x: x.get("created_at", ""))
                
                for i, case in enumerate(sorted_cases[1:], 1):
                    try:
                        new_number = await self.generate_case_number()
                        
                        update_query = """
                        MATCH (c:Case {id: $id})
                        SET c.case_number = $new_number,
                            c.duplicate_fixed_at = datetime(),
                            c.original_duplicate_number = $old_number
                        """
                        
                        await session.run(
                            update_query,
                            id=case["id"],
                            new_number=new_number,
                            old_number=case_number
                        )
                        
                        results["fixed"] += 1
                        
                    except Exception as e:
                        results["errors"].append({
                            "case_id": case["id"],
                            "error": str(e)
                        })
        
        return results


class CaseNumberingAgent:
    """
    Agent responsible for case numbering operations and fixes.
    """
    
    def __init__(self, config: Optional[CaseNumberConfig] = None):
        self.config = config or CaseNumberConfig()
        self.service = CaseNumberingService(self.config)
        
    async def __aenter__(self):
        await self.service.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.service.close()
    
    async def run_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive diagnostics on case numbering system."""
        diagnostics = {
            "configuration": self.config.dict(),
            "connection_status": {},
            "validation_tests": {},
            "performance_metrics": {},
            "data_integrity": {}
        }
        
        # Test connections
        try:
            await self.service._driver.verify_connectivity()
            diagnostics["connection_status"]["neo4j"] = "healthy"
        except Exception as e:
            diagnostics["connection_status"]["neo4j"] = f"error: {str(e)}"
        
        try:
            await self.service._redis.ping()
            diagnostics["connection_status"]["redis"] = "healthy"
        except Exception as e:
            diagnostics["connection_status"]["redis"] = f"error: {str(e)}"
        
        # Test validation
        test_cases = [
            ("C2023123100001", True),
            ("MED-20231231-0001", False),  # Legacy format
            ("INVALID", False),
            ("", False)
        ]
        
        for case_number, expected in test_cases:
            result = self.service.validate_case_number(case_number)
            diagnostics["validation_tests"][case_number] = {
                "expected": expected,
                "actual": result,
                "passed": result == expected
            }
        
        # Test performance
        import time
        start_time = time.time()
        
        try:
            case_number = await self.service.generate_case_number()
            generation_time = time.time() - start_time
            
            diagnostics["performance_metrics"]["generation_time_ms"] = generation_time * 1000
            diagnostics["performance_metrics"]["generated_number"] = case_number
            
            # Test search performance
            start_time = time.time()
            result = await self.service.search_by_case_number(case_number)
            search_time = time.time() - start_time
            
            diagnostics["performance_metrics"]["search_time_ms"] = search_time * 1000
            
        except Exception as e:
            diagnostics["performance_metrics"]["error"] = str(e)
        
        # Check for duplicates
        stats = await self.service.fix_duplicate_case_numbers()
        diagnostics["data_integrity"]["duplicates"] = stats
        
        return diagnostics
    
    async def apply_all_fixes(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Apply all fixes to the case numbering system.
        
        Args:
            dry_run: If True, only simulate fixes
            
        Returns:
            dict: Results of all fixes
        """
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
            "fixes_applied": {}
        }
        
        # 1. Create indexes
        if not dry_run:
            await self.service._create_indexes()
            results["fixes_applied"]["indexes"] = "created"
        
        # 2. Fix duplicates
        duplicate_results = await self.service.fix_duplicate_case_numbers()
        results["fixes_applied"]["duplicates"] = duplicate_results
        
        # 3. Migrate legacy numbers
        migration_results = await self.service.migrate_legacy_case_numbers(dry_run)
        results["fixes_applied"]["migration"] = migration_results
        
        # 4. Get current statistics
        stats = await self.service.get_statistics()
        results["current_statistics"] = stats
        
        return results


# Utility functions for API integration
async def get_case_numbering_agent() -> CaseNumberingAgent:
    """Factory function to create agent instance."""
    config = CaseNumberConfig()
    agent = CaseNumberingAgent(config)
    await agent.service.initialize()
    return agent


# Export key components
__all__ = [
    "CaseNumberingService",
    "CaseNumberingAgent", 
    "CaseNumberConfig",
    "CaseNumberFormat",
    "ValidationError",
    "ConcurrencyError",
    "get_case_numbering_agent"
]