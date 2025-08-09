"""
Unified Knowledge Graph Service
Manages relationships across all microservices ensuring proper bidirectional connections
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager

from neo4j import GraphDatabase, Transaction
from neo4j.exceptions import Neo4jError
import concurrent.futures
from functools import wraps

# Check if async Neo4j is available (Neo4j 5.x)
try:
    from neo4j import AsyncGraphDatabase
    ASYNC_NEO4J_AVAILABLE = True
except ImportError:
    AsyncGraphDatabase = None
    ASYNC_NEO4J_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """
    Central service for managing the medical knowledge graph
    Ensures consistent relationships across User, Case, Report, and ChatSession nodes
    """
    
    def __init__(self):
        """Initialize knowledge graph service"""
        self.uri = settings.neo4j_uri
        self.username = settings.neo4j_user
        self.password = settings.neo4j_password
        self.database = getattr(settings, 'neo4j_database', 'neo4j')
        self._driver = None
        self._sync_driver = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=5) if not ASYNC_NEO4J_AVAILABLE else None
        
        logger.info(f"Knowledge Graph Service initialized (Async Neo4j: {ASYNC_NEO4J_AVAILABLE})")
    
    @property
    def driver(self):
        """Get or create driver (async if available, sync otherwise)"""
        if ASYNC_NEO4J_AVAILABLE:
            if self._driver is None:
                self._driver = AsyncGraphDatabase.driver(
                    self.uri,
                    auth=(self.username, self.password)
                )
            return self._driver
        else:
            if self._sync_driver is None:
                self._sync_driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.username, self.password)
                )
            return self._sync_driver
    
    async def close(self):
        """Close driver connection"""
        if ASYNC_NEO4J_AVAILABLE and self._driver:
            await self._driver.close()
            self._driver = None
        elif self._sync_driver:
            self._sync_driver.close()
            self._sync_driver = None
        
        if self._executor:
            self._executor.shutdown(wait=True)
    
    async def _run_sync_query(self, query: str, params: Dict[str, Any] = None):
        """Run a sync query in the executor when async is not available"""
        if ASYNC_NEO4J_AVAILABLE:
            # This should not be called when async is available
            raise RuntimeError("_run_sync_query should not be called when async Neo4j is available")
        
        def run_query():
            with self.driver.session(database=self.database) as session:
                result = session.run(query, params or {})
                return list(result)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, run_query)
    
    async def _execute_query(self, session, query: str, params: Dict[str, Any] = None):
        """Execute a query handling both async and sync sessions"""
        if ASYNC_NEO4J_AVAILABLE:
            return await session.run(query, params or {})
        else:
            # For sync session, run in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor,
                lambda: session.run(query, params or {})
            )
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session (async or sync with executor)"""
        if ASYNC_NEO4J_AVAILABLE:
            async with self.driver.session(database=self.database) as session:
                yield session
        else:
            # For sync driver, we'll use a regular session
            session = self.driver.session(database=self.database)
            try:
                yield session
            finally:
                session.close()
    
    async def ensure_indexes(self):
        """Ensure all necessary indexes and constraints exist"""
        async with self.get_session() as session:
            try:
                # User indexes
                await self._execute_query(session, """
                    CREATE CONSTRAINT user_id_unique IF NOT EXISTS
                    FOR (u:User) REQUIRE u.user_id IS UNIQUE
                """)
                
                # Case indexes
                await self._execute_query(session, """
                    CREATE CONSTRAINT case_id_unique IF NOT EXISTS
                    FOR (c:Case) REQUIRE c.case_id IS UNIQUE
                """)
                
                await self._execute_query(session, """
                    CREATE INDEX case_user_id IF NOT EXISTS
                    FOR (c:Case) ON (c.user_id)
                """)
                
                # Report indexes
                await self._execute_query(session, """
                    CREATE CONSTRAINT report_id_unique IF NOT EXISTS
                    FOR (r:MedicalReport) REQUIRE r.id IS UNIQUE
                """)
                
                await self._execute_query(session, """
                    CREATE INDEX report_case_id IF NOT EXISTS
                    FOR (r:MedicalReport) ON (r.caseId)
                """)
                
                # ChatSession indexes
                await self._execute_query(session, """
                    CREATE CONSTRAINT session_id_unique IF NOT EXISTS
                    FOR (s:ChatSession) REQUIRE s.session_id IS UNIQUE
                """)
                
                await self._execute_query(session, """
                    CREATE INDEX session_case_id IF NOT EXISTS
                    FOR (s:ChatSession) ON (s.case_id)
                """)
                
                # ChatMessage indexes
                await self._execute_query(session, """
                    CREATE INDEX message_session_id IF NOT EXISTS
                    FOR (m:ChatMessage) ON (m.session_id)
                """)
                
                await self._execute_query(session, """
                    CREATE INDEX message_case_id IF NOT EXISTS
                    FOR (m:ChatMessage) ON (m.case_id)
                """)
                
                logger.info("Knowledge graph indexes created successfully")
                
            except Exception as e:
                logger.warning(f"Error creating indexes (may already exist): {e}")
    
    # User-Case Relationships
    
    async def ensure_user_case_relationship(
        self,
        user_id: str,
        case_id: str,
        create_user_if_missing: bool = True
    ) -> bool:
        """
        Ensure bidirectional User-Case relationship exists
        
        Args:
            user_id: User ID
            case_id: Case ID
            create_user_if_missing: Whether to create user node if it doesn't exist
            
        Returns:
            True if relationship was created/verified
        """
        async with self.get_session() as session:
            try:
                if create_user_if_missing:
                    # Ensure user exists
                    await self._execute_query(session, """
                        MERGE (u:User {user_id: $user_id})
                        ON CREATE SET u.created_at = datetime()
                    """, {"user_id": user_id})
                
                # Create bidirectional relationship
                result = await self._execute_query(session, """
                    MATCH (u:User {user_id: $user_id})
                    MATCH (c:Case {case_id: $case_id})
                    MERGE (u)-[r1:OWNS]->(c)
                    MERGE (c)-[r2:OWNED_BY]->(u)
                    RETURN u.user_id as user_id, c.case_id as case_id
                """, {"user_id": user_id, "case_id": case_id})
                
                record = await result.single()
                if record:
                    logger.info(f"Ensured User-Case relationship: {user_id} <-> {case_id}")
                    return True
                return False
                
            except Neo4jError as e:
                logger.error(f"Error ensuring User-Case relationship: {e}")
                return False
    
    # Case-Report Relationships
    
    async def create_case_report_relationship(
        self,
        case_id: str,
        report_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Create bidirectional Case-Report relationship
        
        Args:
            case_id: Case ID
            report_id: Report ID
            user_id: Optional user ID to verify ownership
            
        Returns:
            True if relationship was created
        """
        async with self.get_session() as session:
            try:
                # If user_id provided, verify ownership
                if user_id:
                    ownership_check = """
                        MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_id: $case_id})
                        WITH c
                    """
                    params = {"user_id": user_id, "case_id": case_id, "report_id": report_id}
                else:
                    ownership_check = ""
                    params = {"case_id": case_id, "report_id": report_id}
                
                # Create bidirectional relationship
                result = await self._execute_query(session, f"""
                    {ownership_check}
                    MATCH (c:Case {{case_id: $case_id}})
                    MATCH (r:MedicalReport {{id: $report_id}})
                    MERGE (c)-[rel1:HAS_REPORT]->(r)
                    MERGE (r)-[rel2:BELONGS_TO_CASE]->(c)
                    SET r.caseId = $case_id
                    RETURN c.case_id as case_id, r.id as report_id
                """, params)
                
                record = await result.single()
                if record:
                    logger.info(f"Created Case-Report relationship: {case_id} <-> {report_id}")
                    return True
                return False
                
            except Neo4jError as e:
                logger.error(f"Error creating Case-Report relationship: {e}")
                return False
    
    # ChatSession-Case Relationships
    
    async def ensure_session_case_relationship(
        self,
        session_id: str,
        case_id: str
    ) -> bool:
        """
        Ensure bidirectional ChatSession-Case relationship exists
        
        Args:
            session_id: Chat session ID
            case_id: Case ID
            
        Returns:
            True if relationship was created/verified
        """
        async with self.get_session() as session:
            try:
                # Create bidirectional relationship
                result = await self._execute_query(session, """
                    MATCH (s:ChatSession {session_id: $session_id})
                    MATCH (c:Case {case_id: $case_id})
                    MERGE (c)-[r1:HAS_CHAT_SESSION]->(s)
                    MERGE (s)-[r2:BELONGS_TO_CASE]->(c)
                    RETURN s.session_id as session_id, c.case_id as case_id
                """, {"session_id": session_id, "case_id": case_id})
                
                record = await result.single()
                if record:
                    logger.info(f"Ensured Session-Case relationship: {session_id} <-> {case_id}")
                    return True
                return False
                
            except Neo4jError as e:
                logger.error(f"Error ensuring Session-Case relationship: {e}")
                return False
    
    # Patient Journey Traversal
    
    async def get_patient_journey(
        self,
        user_id: str,
        case_id: Optional[str] = None,
        include_reports: bool = True,
        include_chats: bool = True,
        include_messages: bool = False
    ) -> Dict[str, Any]:
        """
        Get complete patient journey through the knowledge graph
        
        Args:
            user_id: User ID
            case_id: Optional specific case ID (otherwise all cases)
            include_reports: Include medical reports
            include_chats: Include chat sessions
            include_messages: Include chat messages (can be large)
            
        Returns:
            Patient journey data
        """
        async with self.get_session() as session:
            try:
                # Base query for cases
                case_filter = "AND c.case_id = $case_id" if case_id else ""
                params = {"user_id": user_id}
                if case_id:
                    params["case_id"] = case_id
                
                # Build query based on what to include
                query_parts = ["""
                    MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)
                    WHERE c.status <> 'archived' %s
                """ % case_filter]
                
                optional_matches = []
                returns = ["u", "collect(DISTINCT c) as cases"]
                
                if include_reports:
                    optional_matches.append(
                        "OPTIONAL MATCH (c)-[:HAS_REPORT]->(r:MedicalReport)"
                    )
                    returns.append("collect(DISTINCT r) as reports")
                
                if include_chats:
                    optional_matches.append(
                        "OPTIONAL MATCH (c)-[:HAS_CHAT_SESSION]->(s:ChatSession)"
                    )
                    returns.append("collect(DISTINCT s) as sessions")
                
                if include_messages:
                    optional_matches.append(
                        "OPTIONAL MATCH (s)-[:HAS_MESSAGE]->(m:ChatMessage)"
                    )
                    returns.append("collect(DISTINCT m) as messages")
                
                # Combine query
                query = "\n".join(query_parts + optional_matches + [
                    "RETURN " + ", ".join(returns)
                ])
                
                result = await self._execute_query(session, query, params)
                record = await result.single()
                
                if not record:
                    return {"user_id": user_id, "cases": [], "reports": [], "sessions": []}
                
                # Format response
                journey = {
                    "user_id": user_id,
                    "user_created": dict(record["u"]).get("created_at"),
                    "cases": [dict(c) for c in record["cases"]]
                }
                
                if include_reports and "reports" in record:
                    journey["reports"] = [dict(r) for r in record["reports"]]
                
                if include_chats and "sessions" in record:
                    journey["sessions"] = [dict(s) for s in record["sessions"]]
                
                if include_messages and "messages" in record:
                    journey["messages"] = [dict(m) for m in record["messages"]]
                
                # Calculate statistics
                journey["statistics"] = {
                    "total_cases": len(journey["cases"]),
                    "active_cases": sum(1 for c in journey["cases"] if c.get("status") == "active"),
                    "total_reports": len(journey.get("reports", [])),
                    "total_sessions": len(journey.get("sessions", [])),
                    "total_messages": len(journey.get("messages", []))
                }
                
                return journey
                
            except Neo4jError as e:
                logger.error(f"Error getting patient journey: {e}")
                return {"user_id": user_id, "error": str(e)}
    
    # Relationship Validation and Repair
    
    async def validate_relationships(
        self,
        fix_issues: bool = False
    ) -> Dict[str, Any]:
        """
        Validate all relationships in the knowledge graph
        
        Args:
            fix_issues: Whether to automatically fix found issues
            
        Returns:
            Validation report with issues found and fixed
        """
        async with self.get_session() as session:
            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "issues_found": [],
                "issues_fixed": [],
                "statistics": {}
            }
            
            try:
                # 1. Check for Cases without User relationships
                orphan_cases = await self._execute_query(session, """
                    MATCH (c:Case)
                    WHERE NOT (c)<-[:OWNS]-(:User)
                    RETURN c.case_id as case_id, c.user_id as user_id
                """)
                
                orphan_case_count = 0
                async for record in orphan_cases:
                    orphan_case_count += 1
                    issue = {
                        "type": "orphan_case",
                        "case_id": record["case_id"],
                        "user_id": record["user_id"]
                    }
                    report["issues_found"].append(issue)
                    
                    if fix_issues and record["user_id"]:
                        # Fix by creating user and relationship
                        fixed = await self.ensure_user_case_relationship(
                            record["user_id"],
                            record["case_id"],
                            create_user_if_missing=True
                        )
                        if fixed:
                            report["issues_fixed"].append(issue)
                
                # 2. Check for Reports without Case relationships
                orphan_reports = await self._execute_query(session, """
                    MATCH (r:MedicalReport)
                    WHERE NOT (r)<-[:HAS_REPORT]-(:Case)
                    AND r.caseId IS NOT NULL
                    RETURN r.id as report_id, r.caseId as case_id
                """)
                
                orphan_report_count = 0
                async for record in orphan_reports:
                    orphan_report_count += 1
                    issue = {
                        "type": "orphan_report",
                        "report_id": record["report_id"],
                        "case_id": record["case_id"]
                    }
                    report["issues_found"].append(issue)
                    
                    if fix_issues and record["case_id"]:
                        # Fix by creating relationship
                        fixed = await self.create_case_report_relationship(
                            record["case_id"],
                            record["report_id"]
                        )
                        if fixed:
                            report["issues_fixed"].append(issue)
                
                # 3. Check for ChatSessions without Case relationships
                orphan_sessions = await self._execute_query(session, """
                    MATCH (s:ChatSession)
                    WHERE NOT (s)<-[:HAS_CHAT_SESSION]-(:Case)
                    RETURN s.session_id as session_id, s.case_id as case_id
                """)
                
                orphan_session_count = 0
                async for record in orphan_sessions:
                    orphan_session_count += 1
                    issue = {
                        "type": "orphan_session",
                        "session_id": record["session_id"],
                        "case_id": record["case_id"]
                    }
                    report["issues_found"].append(issue)
                    
                    if fix_issues and record["case_id"]:
                        # Fix by creating relationship
                        fixed = await self.ensure_session_case_relationship(
                            record["session_id"],
                            record["case_id"]
                        )
                        if fixed:
                            report["issues_fixed"].append(issue)
                
                # 4. Check for missing bidirectional relationships
                missing_bidirectional = await self._execute_query(session, """
                    // User-Case missing reverse
                    MATCH (u:User)-[:OWNS]->(c:Case)
                    WHERE NOT (c)-[:OWNED_BY]->(u)
                    RETURN 'user_case' as type, u.user_id as id1, c.case_id as id2
                    
                    UNION
                    
                    // Case-Report missing reverse
                    MATCH (c:Case)-[:HAS_REPORT]->(r:MedicalReport)
                    WHERE NOT (r)-[:BELONGS_TO_CASE]->(c)
                    RETURN 'case_report' as type, c.case_id as id1, r.id as id2
                    
                    UNION
                    
                    // Case-Session missing reverse
                    MATCH (c:Case)-[:HAS_CHAT_SESSION]->(s:ChatSession)
                    WHERE NOT (s)-[:BELONGS_TO_CASE]->(c)
                    RETURN 'case_session' as type, c.case_id as id1, s.session_id as id2
                """)
                
                missing_bidirectional_count = 0
                async for record in missing_bidirectional:
                    missing_bidirectional_count += 1
                    issue = {
                        "type": f"missing_bidirectional_{record['type']}",
                        "id1": record["id1"],
                        "id2": record["id2"]
                    }
                    report["issues_found"].append(issue)
                    
                    if fix_issues:
                        # Fix by creating reverse relationship
                        if record["type"] == "user_case":
                            fixed_result = await self._execute_query(session, """
                                MATCH (u:User {user_id: $id1})
                                MATCH (c:Case {case_id: $id2})
                                MERGE (c)-[:OWNED_BY]->(u)
                                RETURN true as fixed
                            """, {"id1": record["id1"], "id2": record["id2"]})
                        elif record["type"] == "case_report":
                            fixed_result = await self._execute_query(session, """
                                MATCH (c:Case {case_id: $id1})
                                MATCH (r:MedicalReport {id: $id2})
                                MERGE (r)-[:BELONGS_TO_CASE]->(c)
                                RETURN true as fixed
                            """, {"id1": record["id1"], "id2": record["id2"]})
                        elif record["type"] == "case_session":
                            fixed_result = await self._execute_query(session, """
                                MATCH (c:Case {case_id: $id1})
                                MATCH (s:ChatSession {session_id: $id2})
                                MERGE (s)-[:BELONGS_TO_CASE]->(c)
                                RETURN true as fixed
                            """, {"id1": record["id1"], "id2": record["id2"]})
                        
                        if await fixed_result.single():
                            report["issues_fixed"].append(issue)
                
                # Statistics
                report["statistics"] = {
                    "orphan_cases": orphan_case_count,
                    "orphan_reports": orphan_report_count,
                    "orphan_sessions": orphan_session_count,
                    "missing_bidirectional": missing_bidirectional_count,
                    "total_issues": len(report["issues_found"]),
                    "total_fixed": len(report["issues_fixed"])
                }
                
                logger.info(f"Validation completed: {report['statistics']}")
                return report
                
            except Neo4jError as e:
                logger.error(f"Error validating relationships: {e}")
                report["error"] = str(e)
                return report
    
    # Cross-Microservice Query Helpers
    
    async def get_case_complete_data(
        self,
        case_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get complete case data including all related entities
        
        Args:
            case_id: Case ID
            user_id: Optional user ID for ownership verification
            
        Returns:
            Complete case data with all relationships
        """
        async with self.get_session() as session:
            try:
                # Build query with optional user verification
                user_match = "MATCH (u:User {user_id: $user_id})-[:OWNS]->(c)" if user_id else "MATCH (c:Case {case_id: $case_id})"
                params = {"case_id": case_id}
                if user_id:
                    params["user_id"] = user_id
                
                query = f"""
                    {user_match}
                    WHERE c.case_id = $case_id
                    OPTIONAL MATCH (c)-[:HAS_REPORT]->(r:MedicalReport)
                    OPTIONAL MATCH (c)-[:HAS_CHAT_SESSION]->(s:ChatSession)
                    OPTIONAL MATCH (s)-[:HAS_MESSAGE]->(m:ChatMessage)
                    WITH c, 
                         collect(DISTINCT r) as reports,
                         collect(DISTINCT s) as sessions,
                         collect(DISTINCT m) as messages
                    RETURN c as case,
                           reports,
                           sessions,
                           messages,
                           size(reports) as report_count,
                           size(sessions) as session_count,
                           size(messages) as message_count
                """
                
                result = await self._execute_query(session, query, params)
                record = await result.single()
                
                if not record:
                    return None
                
                return {
                    "case": dict(record["case"]),
                    "reports": [dict(r) for r in record["reports"]],
                    "chat_sessions": [dict(s) for s in record["sessions"]],
                    "messages": [dict(m) for m in record["messages"]],
                    "statistics": {
                        "report_count": record["report_count"],
                        "session_count": record["session_count"],
                        "message_count": record["message_count"]
                    }
                }
                
            except Neo4jError as e:
                logger.error(f"Error getting complete case data: {e}")
                return None


# Singleton instance
_knowledge_graph_instance = None


def get_knowledge_graph_service() -> KnowledgeGraphService:
    """Get or create knowledge graph service instance"""
    global _knowledge_graph_instance
    if _knowledge_graph_instance is None:
        _knowledge_graph_instance = KnowledgeGraphService()
    return _knowledge_graph_instance