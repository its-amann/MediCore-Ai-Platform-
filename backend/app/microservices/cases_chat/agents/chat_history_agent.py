"""
Chat History Management Fix Agent
Resolves all chat history storage, retrieval, and context management issues
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from neo4j import GraphDatabase
import json
import re
from dataclasses import dataclass
from enum import Enum
import concurrent.futures

# Check if async Neo4j is available (Neo4j 5.x)
try:
    from neo4j import AsyncGraphDatabase
    ASYNC_NEO4J_AVAILABLE = True
except ImportError:
    AsyncGraphDatabase = None
    ASYNC_NEO4J_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Standardized message types"""
    USER_MESSAGE = "user_message"
    DOCTOR_RESPONSE = "doctor_response"
    SYSTEM_NOTIFICATION = "system_notification"
    MEDIA_ATTACHMENT = "media_attachment"
    DIAGNOSIS_SUMMARY = "diagnosis_summary"

@dataclass
class MessageSchema:
    """Standardized message schema"""
    id: str
    case_id: str
    content: str
    message_type: MessageType
    sender_id: str
    sender_type: str  # 'user', 'doctor', 'system'
    timestamp: datetime
    sequence_number: int
    metadata: Optional[Dict[str, Any]] = None
    reply_to_message_id: Optional[str] = None
    edit_history: Optional[List[Dict]] = None

class ContextWindowManager:
    """Manages conversation context for AI token limits"""
    
    def __init__(self, max_tokens: int = 4000, token_per_char_estimate: float = 0.25):
        self.max_tokens = max_tokens
        self.token_per_char_estimate = token_per_char_estimate
        self.max_chars = int(max_tokens / token_per_char_estimate)
    
    async def get_relevant_context(
        self, 
        messages: List[MessageSchema], 
        priority_message_types: List[MessageType] = None
    ) -> Tuple[List[MessageSchema], bool]:
        """
        Get relevant messages within token limit
        Returns: (messages, was_truncated)
        """
        if not messages:
            return [], False
        
        # Sort by timestamp descending (most recent first)
        sorted_messages = sorted(messages, key=lambda m: m.timestamp, reverse=True)
        
        # Priority message types that should be included
        if priority_message_types is None:
            priority_message_types = [MessageType.DIAGNOSIS_SUMMARY, MessageType.DOCTOR_RESPONSE]
        
        selected_messages = []
        total_chars = 0
        was_truncated = False
        
        # First pass: Include priority messages
        for msg in sorted_messages:
            if msg.message_type in priority_message_types:
                msg_chars = len(msg.content)
                if total_chars + msg_chars <= self.max_chars:
                    selected_messages.append(msg)
                    total_chars += msg_chars
        
        # Second pass: Include recent messages
        for msg in sorted_messages:
            if msg not in selected_messages:
                msg_chars = len(msg.content)
                if total_chars + msg_chars <= self.max_chars:
                    selected_messages.append(msg)
                    total_chars += msg_chars
                else:
                    was_truncated = True
                    break
        
        # Sort chronologically for context
        selected_messages.sort(key=lambda m: m.timestamp)
        
        return selected_messages, was_truncated
    
    def summarize_truncated_context(self, excluded_messages: List[MessageSchema]) -> str:
        """Generate summary of excluded messages"""
        if not excluded_messages:
            return ""
        
        summary = f"\n[Previous conversation summary: {len(excluded_messages)} messages]\n"
        
        # Count message types
        type_counts = {}
        for msg in excluded_messages:
            type_counts[msg.message_type.value] = type_counts.get(msg.message_type.value, 0) + 1
        
        for msg_type, count in type_counts.items():
            summary += f"- {count} {msg_type.replace('_', ' ').title()}\n"
        
        return summary

class MessageSearchService:
    """Handles message search and filtering"""
    
    def __init__(self, agent):
        self.agent = agent
    
    @property
    def driver(self):
        """Get driver from agent"""
        return self.agent.driver
    
    async def search_messages(
        self,
        case_id: str,
        query: Optional[str] = None,
        sender_type: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search messages with various filters"""
        
        where_clauses = ["m.case_id = $case_id"]
        params = {"case_id": case_id, "limit": limit, "offset": offset}
        
        if query:
            where_clauses.append("m.content CONTAINS $query")
            params["query"] = query
        
        if sender_type:
            where_clauses.append("m.sender_type = $sender_type")
            params["sender_type"] = sender_type
        
        if message_type:
            where_clauses.append("m.message_type = $message_type")
            params["message_type"] = message_type.value
        
        if start_date:
            where_clauses.append("m.timestamp >= $start_date")
            params["start_date"] = start_date.isoformat()
        
        if end_date:
            where_clauses.append("m.timestamp <= $end_date")
            params["end_date"] = end_date.isoformat()
        
        where_clause = " AND ".join(where_clauses)
        
        query_str = f"""
        MATCH (m:Message)
        WHERE {where_clause}
        RETURN m
        ORDER BY m.timestamp DESC
        SKIP $offset
        LIMIT $limit
        """
        
        async with self.driver.session() as session:
            result = await session.run(query_str, params)
            messages = []
            async for record in result:
                messages.append(dict(record["m"]))
            return messages

class ChatSessionManager:
    """Manages chat session lifecycle"""
    
    def __init__(self, agent):
        self.agent = agent
    
    @property
    def driver(self):
        """Get driver from agent"""
        return self.agent.driver
    
    async def start_chat_session(
        self, 
        case_id: str, 
        user_id: str,
        session_type: str = "consultation"
    ) -> str:
        """Start a new chat session"""
        session_id = f"session_{case_id}_{int(datetime.now().timestamp())}"
        
        query = """
        MATCH (c:Case {case_id: $case_id})
        CREATE (s:ChatSession {
            session_id: $session_id,
            case_id: $case_id,
            user_id: $user_id,
            session_type: $session_type,
            started_at: datetime($started_at),
            status: 'active',
            message_count: 0
        })
        CREATE (c)-[:HAS_SESSION]->(s)
        RETURN s
        """
        
        params = {
            "case_id": case_id,
            "session_id": session_id,
            "user_id": user_id,
            "session_type": session_type,
            "started_at": datetime.now().isoformat()
        }
        
        async with self.driver.session() as session:
            await session.run(query, params)
            
        logger.info(f"Started chat session {session_id} for case {case_id}")
        return session_id
    
    async def end_chat_session(self, session_id: str) -> Dict[str, Any]:
        """End a chat session and generate summary"""
        
        # Get session messages
        messages_query = """
        MATCH (s:ChatSession {session_id: $session_id})-[:CONTAINS]->(m:Message)
        RETURN m
        ORDER BY m.timestamp
        """
        
        async with self.driver.session() as session:
            result = await session.run(messages_query, {"session_id": session_id})
            messages = []
            async for record in result:
                messages.append(dict(record["m"]))
        
        # Generate summary
        summary = {
            "total_messages": len(messages),
            "user_messages": len([m for m in messages if m.get("sender_type") == "user"]),
            "doctor_messages": len([m for m in messages if m.get("sender_type") == "doctor"]),
            "duration_minutes": 0
        }
        
        if messages:
            start_time = datetime.fromisoformat(messages[0]["timestamp"])
            end_time = datetime.fromisoformat(messages[-1]["timestamp"])
            summary["duration_minutes"] = (end_time - start_time).total_seconds() / 60
        
        # Update session status
        update_query = """
        MATCH (s:ChatSession {session_id: $session_id})
        SET s.status = 'completed',
            s.ended_at = datetime($ended_at),
            s.summary = $summary
        RETURN s
        """
        
        params = {
            "session_id": session_id,
            "ended_at": datetime.now().isoformat(),
            "summary": json.dumps(summary)
        }
        
        async with self.driver.session() as session:
            await session.run(update_query, params)
        
        logger.info(f"Ended chat session {session_id}")
        return summary

class ChatHistoryAgent:
    """Main agent for fixing chat history management issues"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        if ASYNC_NEO4J_AVAILABLE:
            self.driver = AsyncGraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password),
                max_connection_pool_size=50
            )
        else:
            self.driver = None
            
        self.sync_driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password),
            max_connection_pool_size=50
        )
        
        # Use sync driver if async is not available
        active_driver = self.driver if ASYNC_NEO4J_AVAILABLE else self.sync_driver
        
        self.context_manager = ContextWindowManager()
        self.search_service = MessageSearchService(active_driver)
        self.session_manager = ChatSessionManager(active_driver)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=5) if not ASYNC_NEO4J_AVAILABLE else None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.driver and ASYNC_NEO4J_AVAILABLE:
            await self.driver.close()
        if self.sync_driver:
            self.sync_driver.close()
        if self._executor:
            self._executor.shutdown(wait=True)
    
    async def standardize_message_schema(self, dry_run: bool = True) -> Dict[str, Any]:
        """Standardize all message properties to consistent schema"""
        logger.info("Starting message schema standardization...")
        
        # Step 1: Count messages with inconsistent schemas
        count_query = """
        MATCH (m:Message)
        RETURN 
            COUNT(CASE WHEN m.content IS NOT NULL THEN 1 END) as has_content,
            COUNT(CASE WHEN m.text IS NOT NULL THEN 1 END) as has_text,
            COUNT(CASE WHEN m.message_content IS NOT NULL THEN 1 END) as has_message_content,
            COUNT(CASE WHEN m.timestamp IS NOT NULL THEN 1 END) as has_timestamp,
            COUNT(CASE WHEN m.created_at IS NOT NULL THEN 1 END) as has_created_at,
            COUNT(CASE WHEN m.sent_time IS NOT NULL THEN 1 END) as has_sent_time,
            COUNT(*) as total
        """
        
        async with self.driver.session() as session:
            result = await session.run(count_query)
            counts = await result.single()
        
        logger.info(f"Found {counts['total']} total messages")
        logger.info(f"Schema variations: content={counts['has_content']}, "
                   f"text={counts['has_text']}, message_content={counts['has_message_content']}")
        
        if dry_run:
            logger.info("DRY RUN - No changes made")
            return {
                "total_messages": counts['total'],
                "would_standardize": counts['total'] - counts['has_content'],
                "dry_run": True
            }
        
        # Step 2: Standardize message properties
        standardize_query = """
        MATCH (m:Message)
        SET m.content = COALESCE(m.content, m.text, m.message_content, ''),
            m.timestamp = COALESCE(m.timestamp, m.created_at, m.sent_time, datetime()),
            m.sender_id = COALESCE(m.sender_id, m.sender, m.user_id, m.from_user, 'unknown'),
            m.message_type = COALESCE(m.message_type, 
                CASE 
                    WHEN m.sender_type = 'user' THEN 'user_message'
                    WHEN m.sender_type = 'doctor' THEN 'doctor_response'
                    ELSE 'system_notification'
                END
            ),
            m.sender_type = COALESCE(m.sender_type,
                CASE
                    WHEN m.from_user IS NOT NULL THEN 'user'
                    WHEN m.doctor_type IS NOT NULL THEN 'doctor'
                    ELSE 'system'
                END
            )
        REMOVE m.text, m.message_content, m.created_at, m.sent_time, 
               m.user_id, m.from_user, m.sender, m.doctor_type
        RETURN COUNT(*) as standardized
        """
        
        async with self.driver.session() as session:
            result = await session.run(standardize_query)
            standardized = await result.single()
        
        logger.info(f"Standardized {standardized['standardized']} messages")
        
        return {
            "total_messages": counts['total'],
            "standardized": standardized['standardized'],
            "dry_run": False
        }
    
    async def add_sequence_numbers(self) -> Dict[str, Any]:
        """Add sequence numbers to all messages for proper ordering"""
        logger.info("Adding sequence numbers to messages...")
        
        # Get all cases
        cases_query = """
        MATCH (c:Case)
        RETURN c.case_id as case_id
        """
        
        async with self.driver.session() as session:
            result = await session.run(cases_query)
            cases = [record['case_id'] async for record in result]
        
        total_updated = 0
        
        for case_id in cases:
            # Get messages for case ordered by timestamp
            messages_query = """
            MATCH (c:Case {case_id: $case_id})-[:HAS_MESSAGE]->(m:Message)
            RETURN m
            ORDER BY m.timestamp
            """
            
            async with self.driver.session() as session:
                result = await session.run(messages_query, {"case_id": case_id})
                messages = []
                async for record in result:
                    messages.append(record["m"])
            
            # Update with sequence numbers
            for idx, message in enumerate(messages):
                update_query = """
                MATCH (m:Message {id: $message_id})
                SET m.sequence_number = $sequence
                """
                
                async with self.driver.session() as session:
                    await session.run(update_query, {
                        "message_id": message["id"],
                        "sequence": idx + 1
                    })
                
                total_updated += 1
        
        logger.info(f"Added sequence numbers to {total_updated} messages")
        
        return {
            "cases_processed": len(cases),
            "messages_updated": total_updated
        }
    
    async def create_performance_indexes(self) -> Dict[str, Any]:
        """Create database indexes for optimal performance"""
        logger.info("Creating performance indexes...")
        
        indexes = [
            ("message_case_timestamp", "Message", ["case_id", "timestamp"]),
            ("message_sequence", "Message", ["case_id", "sequence_number"]),
            ("message_sender", "Message", ["sender_id"]),
            ("message_type", "Message", ["message_type"]),
            ("session_case", "ChatSession", ["case_id"]),
            ("session_status", "ChatSession", ["status"])
        ]
        
        constraints = [
            ("message_id_unique", "Message", "id"),
            ("session_id_unique", "ChatSession", "session_id")
        ]
        
        created_indexes = []
        created_constraints = []
        
        # Create indexes
        for index_name, label, properties in indexes:
            try:
                props_str = ", ".join([f"n.{prop}" for prop in properties])
                query = f"CREATE INDEX {index_name} IF NOT EXISTS FOR (n:{label}) ON ({props_str})"
                
                with self.sync_driver.session() as session:
                    session.run(query)
                
                created_indexes.append(index_name)
                logger.info(f"Created index: {index_name}")
            except Exception as e:
                logger.warning(f"Failed to create index {index_name}: {e}")
        
        # Create constraints
        for constraint_name, label, property in constraints:
            try:
                query = f"CREATE CONSTRAINT {constraint_name} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{property} IS UNIQUE"
                
                with self.sync_driver.session() as session:
                    session.run(query)
                
                created_constraints.append(constraint_name)
                logger.info(f"Created constraint: {constraint_name}")
            except Exception as e:
                logger.warning(f"Failed to create constraint {constraint_name}: {e}")
        
        # Create full-text index for message search
        try:
            fulltext_query = """
            CALL db.index.fulltext.createNodeIndex(
                'messageContent',
                ['Message'],
                ['content'],
                {analyzer: 'standard'}
            )
            """
            
            with self.sync_driver.session() as session:
                session.run(fulltext_query)
            
            logger.info("Created full-text index for message content")
        except Exception as e:
            logger.warning(f"Failed to create full-text index: {e}")
        
        return {
            "indexes_created": created_indexes,
            "constraints_created": created_constraints
        }
    
    async def migrate_message_relationships(self) -> Dict[str, Any]:
        """Ensure all messages have proper relationships"""
        logger.info("Migrating message relationships...")
        
        # Find orphaned messages
        orphaned_query = """
        MATCH (m:Message)
        WHERE NOT (()-[:HAS_MESSAGE]->(m))
        AND m.case_id IS NOT NULL
        RETURN m
        """
        
        async with self.driver.session() as session:
            result = await session.run(orphaned_query)
            orphaned_messages = []
            async for record in result:
                orphaned_messages.append(dict(record["m"]))
        
        logger.info(f"Found {len(orphaned_messages)} orphaned messages")
        
        # Create relationships for orphaned messages
        fixed_count = 0
        for message in orphaned_messages:
            if 'case_id' in message:
                create_rel_query = """
                MATCH (c:Case {case_id: $case_id})
                MATCH (m:Message {id: $message_id})
                CREATE (c)-[:HAS_MESSAGE {sequence: COALESCE(m.sequence_number, 0)}]->(m)
                """
                
                async with self.driver.session() as session:
                    await session.run(create_rel_query, {
                        "case_id": message['case_id'],
                        "message_id": message['id']
                    })
                
                fixed_count += 1
        
        logger.info(f"Fixed relationships for {fixed_count} messages")
        
        return {
            "orphaned_messages_found": len(orphaned_messages),
            "relationships_created": fixed_count
        }
    
    async def apply_all_fixes(self, dry_run: bool = True) -> Dict[str, Any]:
        """Apply all chat history fixes"""
        logger.info("Applying all chat history fixes...")
        
        results = {
            "schema_standardization": await self.standardize_message_schema(dry_run),
            "sequence_numbers": await self.add_sequence_numbers() if not dry_run else {"skipped": True},
            "performance_indexes": await self.create_performance_indexes() if not dry_run else {"skipped": True},
            "relationship_migration": await self.migrate_message_relationships() if not dry_run else {"skipped": True}
        }
        
        logger.info("All fixes applied successfully!")
        return results
    
    # Helper method for testing
    async def test_context_window(self, case_id: str) -> None:
        """Test context window management"""
        # Get messages
        query = """
        MATCH (c:Case {case_id: $case_id})-[:HAS_MESSAGE]->(m:Message)
        RETURN m
        ORDER BY m.timestamp DESC
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, {"case_id": case_id})
            messages = []
            async for record in result:
                msg_dict = dict(record["m"])
                messages.append(MessageSchema(
                    id=msg_dict.get('id', ''),
                    case_id=msg_dict.get('case_id', ''),
                    content=msg_dict.get('content', ''),
                    message_type=MessageType(msg_dict.get('message_type', 'user_message')),
                    sender_id=msg_dict.get('sender_id', ''),
                    sender_type=msg_dict.get('sender_type', 'user'),
                    timestamp=datetime.fromisoformat(msg_dict.get('timestamp', datetime.now().isoformat())),
                    sequence_number=msg_dict.get('sequence_number', 0),
                    metadata=msg_dict.get('metadata')
                ))
        
        # Test context window
        selected, was_truncated = await self.context_manager.get_relevant_context(messages)
        
        logger.info(f"Total messages: {len(messages)}")
        logger.info(f"Selected for context: {len(selected)}")
        logger.info(f"Was truncated: {was_truncated}")
        
        if was_truncated:
            excluded = [m for m in messages if m not in selected]
            summary = self.context_manager.summarize_truncated_context(excluded)
            logger.info(f"Truncation summary: {summary}")

# Usage example
async def main():
    # Initialize agent
    agent = ChatHistoryAgent(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password"
    )
    
    async with agent:
        # Apply all fixes
        results = await agent.apply_all_fixes(dry_run=False)
        print(json.dumps(results, indent=2))
        
        # Test context window management
        # await agent.test_context_window("test-case-id")
        
        # Test search
        # search_results = await agent.search_service.search_messages(
        #     case_id="test-case-id",
        #     query="diagnosis",
        #     message_type=MessageType.DOCTOR_RESPONSE
        # )
        # print(f"Search results: {len(search_results)} messages found")

if __name__ == "__main__":
    asyncio.run(main())