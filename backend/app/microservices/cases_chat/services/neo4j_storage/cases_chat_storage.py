"""
Neo4j Storage Service for Cases Chat Microservice
Handles all database operations for cases, chat sessions, and chat history
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
import asyncio

from app.microservices.cases_chat.models import CaseStatus, ChatSessionType
from app.core.knowledge_graph import get_knowledge_graph_service

logger = logging.getLogger(__name__)


class CasesChatStorage:
    """
    Neo4j storage service for cases and chat functionality
    """
    
    def __init__(self, uri: str, user: str, password: str):
        """
        Initialize Neo4j connection
        
        Args:
            uri: Neo4j URI (e.g., bolt://localhost:7687)
            user: Neo4j username
            password: Neo4j password
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.kg_service = get_knowledge_graph_service()
        logger.info(f"Neo4j storage initialized with URI: {uri}")
    
    async def close(self):
        """Close Neo4j connection"""
        self.driver.close()
    
    def _run_sync_query(self, query: str, params: dict = None):
        """Run a synchronous query and return results"""
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]
    
    async def _run_async_query(self, query: str, params: dict = None):
        """Run a query asynchronously using executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run_sync_query, query, params)
    
    async def create_case(self, case_data: dict) -> dict:
        """
        Create a new case in Neo4j
        
        Args:
            case_data: Case information dictionary
            
        Returns:
            Created case data
        """
        async with self.driver.session() as session:
            try:
                query = """
                CREATE (c:Case {
                    case_id: $case_id,
                    user_id: $user_id,
                    title: $title,
                    description: $description,
                    chief_complaint: $chief_complaint,
                    symptoms: $symptoms,
                    status: $status,
                    priority: $priority,
                    patient_age: $patient_age,
                    patient_gender: $patient_gender,
                    past_medical_history: $past_medical_history,
                    current_medications: $current_medications,
                    allergies: $allergies,
                    medical_category: $medical_category,
                    created_at: $created_at,
                    updated_at: $created_at
                })
                WITH c
                OPTIONAL MATCH (u:User {user_id: $user_id})
                FOREACH (x IN CASE WHEN u IS NOT NULL THEN [1] ELSE [] END |
                    CREATE (u)-[:OWNS]->(c)
                )
                RETURN c
                """
                
                result = await session.run(query, case_data)
                record = await result.single()
                
                if record:
                    case = dict(record["c"])
                    logger.info(f"Created case: {case['case_id']}")
                    return case
                else:
                    raise Exception("Failed to create case")
                    
            except Neo4jError as e:
                logger.error(f"Neo4j error creating case: {str(e)}")
                raise
    
    async def get_case(self, case_id: str, user_id: str) -> Optional[dict]:
        """
        Get a case by ID with ownership verification
        Excludes archived cases
        
        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            
        Returns:
            Case data or None
        """
        async with self.driver.session() as session:
            try:
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_id: $case_id})
                WHERE c.status <> 'archived'
                RETURN c, u.user_id AS user_id
                """
                
                result = await session.run(query, {
                    "case_id": case_id,
                    "user_id": user_id
                })
                record = await result.single()
                
                if record:
                    case_data = dict(record["c"])
                    case_data["user_id"] = record["user_id"]  # Add user_id from query result
                    return case_data
                return None
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting case: {str(e)}")
                return None
    
    async def get_user_cases(self, user_id: str, limit: int = 50, offset: int = 0) -> List[dict]:
        """
        Get all cases for a specific user
        Excludes archived cases by default
        
        Args:
            user_id: User ID
            limit: Maximum number of cases to return
            offset: Number of cases to skip
            
        Returns:
            List of case data dictionaries
        """
        async with self.driver.session() as session:
            try:
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)
                WHERE c.status <> 'archived'
                RETURN c, u.user_id AS user_id
                ORDER BY c.created_at DESC
                SKIP $offset
                LIMIT $limit
                """
                
                result = await session.run(query, {
                    "user_id": user_id,
                    "limit": limit,
                    "offset": offset
                })
                
                cases = []
                async for record in result:
                    case_data = dict(record["c"])
                    case_data["user_id"] = record["user_id"]  # Add user_id from query result
                    cases.append(case_data)
                
                return cases
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting user cases: {str(e)}")
                return []
    
    async def create_chat_session(self, case_id: str, user_id: str, session_type: str = "multi_doctor", session_id: str = None) -> dict:
        """
        Create a new chat session for a case
        
        Args:
            case_id: Case ID
            user_id: User ID
            session_type: Type of chat session
            session_id: Optional session ID (will generate if not provided)
            
        Returns:
            Created chat session data
        """
        async with self.driver.session() as session:
            try:
                if not session_id:
                    session_id = str(uuid.uuid4())
                    
                session_data = {
                    "session_id": session_id,
                    "case_id": case_id,
                    "user_id": user_id,
                    "session_type": session_type,
                    "created_at": datetime.utcnow().isoformat(),
                    "is_active": True,
                    "message_count": 0
                }
                
                query = """
                CREATE (s:ChatSession {
                    session_id: $session_id,
                    case_id: $case_id,
                    user_id: $user_id,
                    session_type: $session_type,
                    created_at: $created_at,
                    is_active: $is_active,
                    message_count: $message_count
                })
                WITH s
                MATCH (c:Case {case_id: $case_id})
                CREATE (c)-[:HAS_CHAT_SESSION]->(s)
                CREATE (s)-[:BELONGS_TO_CASE]->(c)
                RETURN s
                """
                
                result = await session.run(query, session_data)
                record = await result.single()
                
                if record:
                    created_session = dict(record["s"])
                    logger.info(f"Created chat session: {created_session['session_id']}")
                    
                    # Ensure knowledge graph relationships are properly created
                    try:
                        loop = asyncio.get_event_loop()
                        loop.run_until_complete(
                            self.kg_service.ensure_session_case_relationship(
                                created_session['session_id'],
                                case_id
                            )
                        )
                    except Exception as kg_error:
                        logger.warning(f"Failed to ensure KG relationships: {kg_error}")
                    
                    return created_session
                else:
                    raise Exception("Failed to create chat session")
                    
            except Neo4jError as e:
                logger.error(f"Neo4j error creating chat session: {str(e)}")
                raise
    
    async def store_chat_message(
        self,
        session_id: str,
        case_id: str,
        user_id: str,
        user_message: str,
        doctor_type: str,
        doctor_response: str,
        metadata: dict = None
    ) -> dict:
        """
        Store a chat message in Neo4j (Legacy method - kept for backward compatibility)
        Creates two separate messages: one for user and one for assistant
        
        Args:
            session_id: Chat session ID
            case_id: Case ID
            user_id: User ID
            user_message: User's message
            doctor_type: Type of doctor responding
            doctor_response: Doctor's response
            metadata: Additional metadata
            
        Returns:
            Stored message data
        """
        async with self.driver.session() as session:
            try:
                # Create user message
                user_msg_data = {
                    "id": str(uuid.uuid4()),
                    "message_id": str(uuid.uuid4()),  # Keep for backward compatibility
                    "session_id": session_id,
                    "case_id": case_id,
                    "user_id": user_id,
                    "content": user_message,
                    "user_message": user_message,  # Keep for backward compatibility
                    "role": "user",
                    "timestamp": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),  # Keep for backward compatibility
                    "doctor_type": doctor_type,
                    "metadata": str(metadata) if metadata else "{}"
                }
                
                # Create assistant message
                assistant_msg_data = {
                    "id": str(uuid.uuid4()),
                    "message_id": str(uuid.uuid4()),  # Keep for backward compatibility
                    "session_id": session_id,
                    "case_id": case_id,
                    "user_id": user_id,
                    "content": doctor_response,
                    "doctor_response": doctor_response,  # Keep for backward compatibility
                    "role": "assistant",
                    "timestamp": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),  # Keep for backward compatibility
                    "doctor_type": doctor_type,
                    "metadata": str(metadata) if metadata else "{}"
                }
                
                # Combined query to create both messages
                query = """
                // Create user message
                CREATE (user_msg:ChatMessage {
                    id: $user_msg.id,
                    message_id: $user_msg.message_id,
                    session_id: $user_msg.session_id,
                    case_id: $user_msg.case_id,
                    user_id: $user_msg.user_id,
                    content: $user_msg.content,
                    user_message: $user_msg.user_message,
                    role: $user_msg.role,
                    timestamp: $user_msg.timestamp,
                    created_at: $user_msg.created_at,
                    doctor_type: $user_msg.doctor_type,
                    metadata: $user_msg.metadata
                })
                
                // Create assistant message
                CREATE (assistant_msg:ChatMessage {
                    id: $assistant_msg.id,
                    message_id: $assistant_msg.message_id,
                    session_id: $assistant_msg.session_id,
                    case_id: $assistant_msg.case_id,
                    user_id: $assistant_msg.user_id,
                    content: $assistant_msg.content,
                    doctor_response: $assistant_msg.doctor_response,
                    role: $assistant_msg.role,
                    timestamp: $assistant_msg.timestamp,
                    created_at: $assistant_msg.created_at,
                    doctor_type: $assistant_msg.doctor_type,
                    metadata: $assistant_msg.metadata
                })
                
                WITH user_msg, assistant_msg
                MATCH (s:ChatSession {session_id: $session_id})
                CREATE (s)-[:HAS_MESSAGE]->(user_msg)
                CREATE (s)-[:HAS_MESSAGE]->(assistant_msg)
                SET s.message_count = s.message_count + 2,
                    s.last_activity = $assistant_msg.timestamp
                    
                WITH user_msg, assistant_msg, s
                MATCH (c:Case {case_id: $case_id})
                CREATE (user_msg)-[:BELONGS_TO_CASE]->(c)
                CREATE (assistant_msg)-[:BELONGS_TO_CASE]->(c)
                
                RETURN assistant_msg
                """
                
                result = await session.run(query, {
                    "user_msg": user_msg_data,
                    "assistant_msg": assistant_msg_data,
                    "session_id": session_id,
                    "case_id": case_id
                })
                record = await result.single()
                
                if record:
                    message = dict(record["assistant_msg"])
                    logger.info(f"Stored chat messages (user and assistant): {message['message_id']}")
                    return message
                else:
                    raise Exception("Failed to store chat message")
                    
            except Neo4jError as e:
                logger.error(f"Neo4j error storing chat message: {str(e)}")
                raise
    
    async def get_conversation_context(self, session_id: str, limit: int = 10) -> List[dict]:
        """
        Get conversation context (recent messages) for a session
        
        Args:
            session_id: Chat session ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of recent messages
        """
        async with self.driver.session() as session:
            try:
                query = """
                MATCH (s:ChatSession {session_id: $session_id})-[:HAS_MESSAGE]->(m:ChatMessage)
                RETURN m
                ORDER BY m.created_at DESC
                LIMIT $limit
                """
                
                result = await session.run(query, {
                    "session_id": session_id,
                    "limit": limit
                })
                
                messages = []
                async for record in result:
                    messages.append(dict(record["m"]))
                
                # Reverse to get chronological order
                messages.reverse()
                return messages
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting conversation context: {str(e)}")
                return []
    
    async def get_case_chat_sessions(self, case_id: str) -> List[dict]:
        """
        Get all chat sessions for a case
        
        Args:
            case_id: Case ID
            
        Returns:
            List of chat sessions
        """
        async with self.driver.session() as session:
            try:
                query = """
                MATCH (c:Case {case_id: $case_id})-[:HAS_CHAT_SESSION]->(s:ChatSession)
                RETURN s
                ORDER BY s.created_at DESC
                """
                
                result = await session.run(query, {"case_id": case_id})
                
                sessions = []
                async for record in result:
                    sessions.append(dict(record["s"]))
                
                return sessions
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting chat sessions: {str(e)}")
                return []
    
    async def get_case_chat_history(
        self,
        case_id: str,
        session_id: Optional[str] = None,
        doctor_type: Optional[str] = None,
        limit: int = 50
    ) -> List[dict]:
        """
        Get chat history for a case with optional filters
        
        Args:
            case_id: Case ID
            session_id: Optional session ID filter
            doctor_type: Optional doctor type filter
            limit: Maximum messages to retrieve
            
        Returns:
            List of chat messages
        """
        async with self.driver.session() as session:
            try:
                # Build query based on filters
                base_query = "MATCH (m:ChatMessage)-[:BELONGS_TO_CASE]->(c:Case {case_id: $case_id})"
                params = {"case_id": case_id, "limit": limit}
                
                conditions = []
                if session_id:
                    conditions.append("m.session_id = $session_id")
                    params["session_id"] = session_id
                
                if doctor_type:
                    conditions.append("m.doctor_type = $doctor_type")
                    params["doctor_type"] = doctor_type
                
                if conditions:
                    base_query += " WHERE " + " AND ".join(conditions)
                
                query = base_query + """
                RETURN m
                ORDER BY m.created_at DESC
                LIMIT $limit
                """
                
                result = await session.run(query, params)
                
                messages = []
                async for record in result:
                    messages.append(dict(record["m"]))
                
                return messages
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting chat history: {str(e)}")
                return []
    
    async def find_similar_cases(
        self,
        user_id: str,
        symptoms: List[str],
        chief_complaint: str,
        limit: int = 5
    ) -> List[dict]:
        """
        Find similar cases based on symptoms and chief complaint
        This will be enhanced with MCP server integration
        
        Args:
            user_id: User ID
            symptoms: List of symptoms
            chief_complaint: Chief complaint
            limit: Maximum cases to return
            
        Returns:
            List of similar cases
        """
        async with self.driver.session() as session:
            try:
                # Simple similarity search - will be enhanced with vector search
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)
                WHERE c.status <> 'archived'
                AND (
                    ANY(symptom IN $symptoms WHERE symptom IN c.symptoms)
                    OR toLower(c.chief_complaint) CONTAINS toLower($chief_complaint)
                )
                WITH c, 
                     SIZE([s IN $symptoms WHERE s IN c.symptoms]) as symptom_match_count,
                     CASE WHEN toLower(c.chief_complaint) CONTAINS toLower($chief_complaint) 
                          THEN 1 ELSE 0 END as complaint_match
                WHERE symptom_match_count > 0 OR complaint_match > 0
                RETURN c
                ORDER BY symptom_match_count DESC, complaint_match DESC, c.created_at DESC
                LIMIT $limit
                """
                
                result = await session.run(query, {
                    "user_id": user_id,
                    "symptoms": symptoms,
                    "chief_complaint": chief_complaint,
                    "limit": limit
                })
                
                similar_cases = []
                async for record in result:
                    similar_cases.append(dict(record["c"]))
                
                return similar_cases
                
            except Neo4jError as e:
                logger.error(f"Neo4j error finding similar cases: {str(e)}")
                return []
    
    async def archive_case(self, case_id: str, user_id: str) -> bool:
        """
        Archive a case (soft delete)
        
        Args:
            case_id: Case ID
            user_id: User ID for ownership verification
            
        Returns:
            Success status
        """
        async with self.driver.session() as session:
            try:
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_id: $case_id})
                SET c.status = 'archived',
                    c.updated_at = $updated_at,
                    c.closed_at = $updated_at
                RETURN c.case_id as case_id
                """
                
                result = await session.run(query, {
                    "case_id": case_id,
                    "user_id": user_id,
                    "updated_at": datetime.utcnow().isoformat()
                })
                
                record = await result.single()
                if record:
                    logger.info(f"Archived case: {case_id}")
                    return True
                return False
                
            except Neo4jError as e:
                logger.error(f"Neo4j error archiving case: {str(e)}")
                return False
    
    async def create_case_relationship(
        self,
        case_id_1: str,
        case_id_2: str,
        relationship_type: str = "RELATED_TO"
    ) -> bool:
        """
        Create a relationship between two cases
        
        Args:
            case_id_1: First case ID
            case_id_2: Second case ID
            relationship_type: Type of relationship
            
        Returns:
            Success status
        """
        async with self.driver.session() as session:
            try:
                query = f"""
                MATCH (c1:Case {{case_id: $case_id_1}})
                MATCH (c2:Case {{case_id: $case_id_2}})
                CREATE (c1)-[:{relationship_type}]->(c2)
                RETURN c1.case_id as case1, c2.case_id as case2
                """
                
                result = await session.run(query, {
                    "case_id_1": case_id_1,
                    "case_id_2": case_id_2
                })
                
                record = await result.single()
                if record:
                    logger.info(f"Created relationship between cases: {case_id_1} -> {case_id_2}")
                    return True
                return False
                
            except Neo4jError as e:
                logger.error(f"Neo4j error creating case relationship: {str(e)}")
                return False
    
    async def get_case_statistics(self, user_id: str) -> dict:
        """
        Get case statistics for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with statistics
        """
        async with self.driver.session() as session:
            try:
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)
                WITH c
                RETURN 
                    COUNT(c) as total_cases,
                    COUNT(CASE WHEN c.status = 'active' THEN 1 END) as active_cases,
                    COUNT(CASE WHEN c.status = 'closed' THEN 1 END) as closed_cases,
                    COUNT(CASE WHEN c.status = 'archived' THEN 1 END) as archived_cases,
                    COUNT(CASE WHEN c.priority = 'critical' THEN 1 END) as critical_cases,
                    COUNT(CASE WHEN c.priority = 'high' THEN 1 END) as high_priority_cases
                """
                
                result = await session.run(query, {"user_id": user_id})
                record = await result.single()
                
                if record:
                    return dict(record)
                return {
                    "total_cases": 0,
                    "active_cases": 0,
                    "closed_cases": 0,
                    "archived_cases": 0,
                    "critical_cases": 0,
                    "high_priority_cases": 0
                }
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting case statistics: {str(e)}")
                return {}
    
    async def create_chat_message(
        self,
        session_id: str,
        case_id: str,
        content: str,
        role: str,
        medical_insights: Optional[dict] = None,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Create a new chat message in Neo4j
        
        Args:
            session_id: Chat session ID
            case_id: Case ID
            content: Message content
            role: Message role (user/assistant)
            medical_insights: Optional medical insights extracted from the message
            metadata: Additional metadata
            
        Returns:
            Created message data
        """
        async with self.driver.session() as session:
            try:
                message_data = {
                    "id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "case_id": case_id,
                    "content": content,
                    "role": role,
                    "timestamp": datetime.utcnow().isoformat(),
                    "medical_insights": str(medical_insights) if medical_insights else "{}",
                    "metadata": str(metadata) if metadata else "{}"
                }
                
                query = """
                CREATE (m:ChatMessage {
                    id: $id,
                    session_id: $session_id,
                    case_id: $case_id,
                    content: $content,
                    role: $role,
                    timestamp: $timestamp,
                    medical_insights: $medical_insights,
                    metadata: $metadata
                })
                WITH m
                MATCH (s:ChatSession {session_id: $session_id})
                CREATE (s)-[:HAS_MESSAGE]->(m)
                SET s.message_count = s.message_count + 1,
                    s.last_activity = $timestamp
                WITH m, s
                MATCH (c:Case {case_id: $case_id})
                CREATE (m)-[:BELONGS_TO_CASE]->(c)
                RETURN m
                """
                
                result = await session.run(query, message_data)
                record = await result.single()
                
                if record:
                    message = dict(record["m"])
                    logger.info(f"Created chat message: {message['id']}")
                    return message
                else:
                    raise Exception("Failed to create chat message")
                    
            except Neo4jError as e:
                logger.error(f"Neo4j error creating chat message: {str(e)}")
                raise
    
    async def get_chat_messages(
        self,
        session_id: Optional[str] = None,
        case_id: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "timestamp",
        order_desc: bool = True
    ) -> List[dict]:
        """
        Get chat messages with flexible filtering
        
        Args:
            session_id: Optional session ID filter
            case_id: Optional case ID filter
            role: Optional role filter (user/assistant)
            limit: Maximum messages to retrieve
            offset: Number of messages to skip
            order_by: Field to order by (timestamp)
            order_desc: Order descending if True
            
        Returns:
            List of chat messages
        """
        async with self.driver.session() as session:
            try:
                # Build query based on filters
                conditions = []
                params = {"limit": limit, "offset": offset}
                
                if session_id:
                    conditions.append("m.session_id = $session_id")
                    params["session_id"] = session_id
                
                if case_id:
                    conditions.append("m.case_id = $case_id")
                    params["case_id"] = case_id
                
                if role:
                    conditions.append("m.role = $role")
                    params["role"] = role
                
                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
                order_direction = "DESC" if order_desc else "ASC"
                
                query = f"""
                MATCH (m:ChatMessage)
                {where_clause}
                RETURN m
                ORDER BY m.{order_by} {order_direction}
                SKIP $offset
                LIMIT $limit
                """
                
                result = await session.run(query, params)
                
                messages = []
                async for record in result:
                    messages.append(dict(record["m"]))
                
                return messages
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting chat messages: {str(e)}")
                return []
    
    async def get_case_chat_history(
        self,
        case_id: str,
        session_id: Optional[str] = None,
        include_medical_insights: bool = True,
        limit: int = 100
    ) -> List[dict]:
        """
        Get complete chat history for a case
        
        Args:
            case_id: Case ID
            session_id: Optional session ID to filter by
            include_medical_insights: Whether to include medical insights
            limit: Maximum messages to retrieve
            
        Returns:
            List of chat messages with full conversation history
        """
        async with self.driver.session() as session:
            try:
                # Build query
                params = {"case_id": case_id, "limit": limit}
                session_filter = ""
                
                if session_id:
                    session_filter = "AND m.session_id = $session_id"
                    params["session_id"] = session_id
                
                query = f"""
                MATCH (c:Case {{case_id: $case_id}})
                MATCH (m:ChatMessage)-[:BELONGS_TO_CASE]->(c)
                {session_filter}
                WITH m
                ORDER BY m.timestamp ASC
                RETURN m
                LIMIT $limit
                """
                
                result = await session.run(query, params)
                
                messages = []
                async for record in result:
                    message_data = dict(record["m"])
                    
                    # Parse medical insights if needed
                    if include_medical_insights and message_data.get("medical_insights"):
                        try:
                            import json
                            message_data["medical_insights"] = json.loads(message_data["medical_insights"])
                        except:
                            message_data["medical_insights"] = {}
                    
                    messages.append(message_data)
                
                logger.info(f"Retrieved {len(messages)} messages for case {case_id}")
                return messages
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting case chat history: {str(e)}")
                return []
    
    async def update_chat_session(
        self,
        session_id: str,
        update_data: dict
    ) -> Optional[dict]:
        """
        Update chat session information
        
        Args:
            session_id: Session ID to update
            update_data: Dictionary with fields to update (message_count, last_activity, etc.)
            
        Returns:
            Updated session data or None
        """
        async with self.driver.session() as session:
            try:
                # Build SET clause dynamically
                set_clauses = []
                params = {"session_id": session_id}
                
                allowed_fields = [
                    "message_count", "last_activity", "is_active", 
                    "participating_doctors", "metadata"
                ]
                
                for field, value in update_data.items():
                    if field in allowed_fields:
                        set_clauses.append(f"s.{field} = ${field}")
                        params[field] = value
                
                if not set_clauses:
                    logger.warning("No valid fields to update")
                    return None
                
                set_clause = "SET " + ", ".join(set_clauses)
                
                query = f"""
                MATCH (s:ChatSession {{session_id: $session_id}})
                {set_clause}
                RETURN s
                """
                
                result = await session.run(query, params)
                record = await result.single()
                
                if record:
                    updated_session = dict(record["s"])
                    logger.info(f"Updated chat session: {session_id}")
                    return updated_session
                else:
                    logger.warning(f"Chat session not found: {session_id}")
                    return None
                    
            except Neo4jError as e:
                logger.error(f"Neo4j error updating chat session: {str(e)}")
                return None
    
    async def get_message_count_by_role(
        self,
        case_id: str,
        session_id: Optional[str] = None
    ) -> dict:
        """
        Get message count grouped by role for a case
        
        Args:
            case_id: Case ID
            session_id: Optional session ID filter
            
        Returns:
            Dictionary with message counts by role
        """
        async with self.driver.session() as session:
            try:
                params = {"case_id": case_id}
                session_filter = ""
                
                if session_id:
                    session_filter = "AND m.session_id = $session_id"
                    params["session_id"] = session_id
                
                query = f"""
                MATCH (c:Case {{case_id: $case_id}})
                MATCH (m:ChatMessage)-[:BELONGS_TO_CASE]->(c)
                {session_filter}
                RETURN m.role as role, COUNT(m) as count
                """
                
                result = await session.run(query, params)
                
                counts = {"user": 0, "assistant": 0}
                async for record in result:
                    counts[record["role"]] = record["count"]
                
                return counts
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting message counts: {str(e)}")
                return {"user": 0, "assistant": 0}
    
    async def delete_chat_message(
        self,
        message_id: str,
        case_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a chat message (with ownership verification)
        
        Args:
            message_id: Message ID to delete
            case_id: Case ID for verification
            user_id: User ID for ownership verification
            
        Returns:
            Success status
        """
        async with self.driver.session() as session:
            try:
                # Verify ownership and delete
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_id: $case_id})
                MATCH (m:ChatMessage {id: $message_id})-[:BELONGS_TO_CASE]->(c)
                MATCH (s:ChatSession {session_id: m.session_id})
                SET s.message_count = s.message_count - 1
                DETACH DELETE m
                RETURN true as success
                """
                
                result = await session.run(query, {
                    "message_id": message_id,
                    "case_id": case_id,
                    "user_id": user_id
                })
                
                record = await result.single()
                if record:
                    logger.info(f"Deleted chat message: {message_id}")
                    return True
                return False
                
            except Neo4jError as e:
                logger.error(f"Neo4j error deleting chat message: {str(e)}")
                return False