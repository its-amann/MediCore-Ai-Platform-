"""
Unified Neo4j Storage Service for Cases Chat Microservice
Handles all database operations using the unified database manager
"""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timezone, timedelta
import uuid
from neo4j import Driver
from neo4j.exceptions import Neo4jError

from app.microservices.cases_chat.models import CaseStatus, ChatSessionType

logger = logging.getLogger(__name__)


class UnifiedCasesChatStorage:
    """
    Neo4j storage service for cases and chat functionality using unified database manager
    """
    
    def __init__(self, driver: Driver):
        """
        Initialize with Neo4j driver from unified database manager
        
        Args:
            driver: Neo4j driver instance from unified database manager
        """
        self.driver = driver
        logger.info("Unified Cases Chat storage initialized with shared driver")
    
    def create_case(self, case_data: dict) -> dict:
        """Create a new case in Neo4j"""
        with self.driver.session() as session:
            try:
                query = """
                CREATE (c:Case {
                    case_id: $case_id,
                    case_number: $case_number,
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
                
                result = session.run(query, case_data)
                record = result.single()
                
                if record:
                    case = dict(record["c"])
                    logger.info(f"Created case: {case['case_id']}")
                    return case
                else:
                    raise Exception("Failed to create case")
                    
            except Neo4jError as e:
                logger.error(f"Neo4j error creating case: {e}")
                raise
            except Exception as e:
                logger.error(f"Error creating case: {e}")
                raise
    
    def get_case(self, case_id: str, user_id: str) -> Optional[dict]:
        """Get a case by ID"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_id: $case_id})
                RETURN c
                """
                
                result = session.run(query, {"case_id": case_id, "user_id": user_id})
                record = result.single()
                
                if record:
                    return dict(record["c"])
                return None
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting case: {e}")
                raise
    
    def get_user_cases(self, user_id: str, skip: int = 0, limit: int = 10) -> List[dict]:
        """Get all cases for a user with pagination"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)
                RETURN c
                ORDER BY c.created_at DESC
                SKIP $skip
                LIMIT $limit
                """
                
                result = session.run(query, {
                    "user_id": user_id,
                    "skip": skip,
                    "limit": limit
                })
                
                cases = []
                for record in result:
                    cases.append(dict(record["c"]))
                
                return cases
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting user cases: {e}")
                raise
    
    def update_case(self, case_id: str, user_id: str, update_data: dict) -> Optional[dict]:
        """Update a case"""
        with self.driver.session() as session:
            try:
                # Build SET clause dynamically
                set_clauses = []
                params = {"case_id": case_id, "user_id": user_id}
                
                for key, value in update_data.items():
                    if key not in ["case_id", "user_id", "created_at"]:
                        set_clauses.append(f"c.{key} = ${key}")
                        params[key] = value
                
                if not set_clauses:
                    return self.get_case(case_id, user_id)
                
                set_clause = ", ".join(set_clauses)
                params["updated_at"] = datetime.utcnow().isoformat()
                
                query = f"""
                MATCH (u:User {{user_id: $user_id}})-[:OWNS]->(c:Case {{case_id: $case_id}})
                SET {set_clause}, c.updated_at = $updated_at
                RETURN c
                """
                
                result = session.run(query, params)
                record = result.single()
                
                if record:
                    return dict(record["c"])
                return None
                
            except Neo4jError as e:
                logger.error(f"Neo4j error updating case: {e}")
                raise
    
    def delete_case(self, case_id: str, user_id: str) -> bool:
        """Delete a case and all related data"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_id: $case_id})
                OPTIONAL MATCH (c)-[:HAS_SESSION]->(s:ChatSession)
                OPTIONAL MATCH (s)-[:HAS_MESSAGE]->(m:ChatMessage)
                DETACH DELETE c, s, m
                """
                
                result = session.run(query, {
                    "case_id": case_id,
                    "user_id": user_id
                })
                
                summary = result.consume()
                return summary.counters.nodes_deleted > 0
                
            except Neo4jError as e:
                logger.error(f"Neo4j error deleting case: {e}")
                raise
    
    def create_chat_session(self, case_id: str, user_id: str = None, session_type: str = None, session_id: str = None, session_data: dict = None) -> dict:
        """
        Create a new chat session for a case
        Supports both old signature (individual params) and new signature (session_data dict)
        """
        # Handle backward compatibility
        if session_data is None and session_id:
            session_data = {
                "session_id": session_id,
                "case_id": case_id,
                "doctor_type": "general",  # Default
                "doctor_name": "Dr. General Practitioner",  # Default
                "session_type": session_type or "consultation",
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        
        return self._create_chat_session_internal(case_id, session_data)
    
    def _create_chat_session_internal(self, case_id: str, session_data: dict) -> dict:
        """Create a new chat session for a case"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (c:Case {case_id: $case_id})
                CREATE (s:ChatSession {
                    session_id: $session_id,
                    case_id: $case_id,
                    doctor_type: $doctor_type,
                    doctor_name: $doctor_name,
                    session_type: $session_type,
                    status: $status,
                    created_at: $created_at
                })
                CREATE (c)-[:HAS_SESSION]->(s)
                RETURN s
                """
                
                result = session.run(query, session_data)
                record = result.single()
                
                if record:
                    chat_session = dict(record["s"])
                    logger.info(f"Created chat session: {chat_session['session_id']}")
                    return chat_session
                else:
                    raise Exception("Failed to create chat session")
                    
            except Neo4jError as e:
                logger.error(f"Neo4j error creating chat session: {e}")
                raise
    
    def add_chat_message(self, session_id: str, message_data: dict) -> dict:
        """Add a message to a chat session"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (s:ChatSession {session_id: $session_id})
                CREATE (m:ChatMessage {
                    message_id: $message_id,
                    session_id: $session_id,
                    content: $content,
                    sender: $sender,
                    sender_type: $sender_type,
                    created_at: $created_at,
                    metadata: $metadata
                })
                CREATE (s)-[:HAS_MESSAGE]->(m)
                RETURN m
                """
                
                # Handle metadata
                if "metadata" not in message_data:
                    message_data["metadata"] = "{}"
                elif isinstance(message_data["metadata"], dict):
                    import json
                    message_data["metadata"] = json.dumps(message_data["metadata"])
                
                result = session.run(query, message_data)
                record = result.single()
                
                if record:
                    message = dict(record["m"])
                    logger.info(f"Added message to session: {session_id}")
                    return message
                else:
                    raise Exception("Failed to add message")
                    
            except Neo4jError as e:
                logger.error(f"Neo4j error adding message: {e}")
                raise
    
    def get_chat_history(self, session_id: str) -> List[dict]:
        """Get all messages for a chat session"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (s:ChatSession {session_id: $session_id})-[:HAS_MESSAGE]->(m:ChatMessage)
                RETURN m
                ORDER BY m.created_at ASC
                """
                
                result = session.run(query, {"session_id": session_id})
                
                messages = []
                for record in result:
                    message = dict(record["m"])
                    # Parse metadata if it's a string
                    if isinstance(message.get("metadata"), str):
                        import json
                        try:
                            message["metadata"] = json.loads(message["metadata"])
                        except:
                            message["metadata"] = {}
                    messages.append(message)
                
                return messages
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting chat history: {e}")
                raise
    
    def get_case_with_chat_history(self, case_id: str, user_id: str) -> Optional[dict]:
        """Get a case with all its chat sessions and messages"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_id: $case_id})
                OPTIONAL MATCH (c)-[:HAS_SESSION]->(s:ChatSession)
                OPTIONAL MATCH (s)-[:HAS_MESSAGE]->(m:ChatMessage)
                WITH c, s, collect(m) as messages
                WITH c, collect({
                    session: s,
                    messages: messages
                }) as sessions
                RETURN c, sessions
                """
                
                result = session.run(query, {
                    "case_id": case_id,
                    "user_id": user_id
                })
                record = result.single()
                
                if record:
                    case = dict(record["c"])
                    sessions_data = record["sessions"]
                    
                    # Process sessions and messages
                    case["chat_sessions"] = []
                    for session_info in sessions_data:
                        if session_info["session"]:
                            session_dict = dict(session_info["session"])
                            session_dict["messages"] = []
                            
                            # Sort messages by created_at
                            messages = sorted(
                                [dict(m) for m in session_info["messages"] if m],
                                key=lambda x: x.get("created_at", "")
                            )
                            
                            for msg in messages:
                                # Parse metadata if it's a string
                                if isinstance(msg.get("metadata"), str):
                                    import json
                                    try:
                                        msg["metadata"] = json.loads(msg["metadata"])
                                    except:
                                        msg["metadata"] = {}
                                session_dict["messages"].append(msg)
                            
                            case["chat_sessions"].append(session_dict)
                    
                    return case
                return None
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting case with history: {e}")
                raise
    
    def get_case_by_number(self, case_number: str, user_id: str) -> Optional[dict]:
        """Get a case by case number"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_number: $case_number})
                RETURN c
                """
                
                result = session.run(query, {"case_number": case_number, "user_id": user_id})
                record = result.single()
                
                if record:
                    return dict(record["c"])
                return None
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting case by number: {e}")
                raise
    
    def list_user_cases(self, user_id: str, status: Optional[str] = None, 
                       priority: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[dict]:
        """List user cases with optional filters"""
        with self.driver.session() as session:
            try:
                # Build WHERE clauses
                where_clauses = []
                params = {"user_id": user_id, "limit": limit, "offset": offset}
                
                if status:
                    where_clauses.append("c.status = $status")
                    params["status"] = status
                
                if priority:
                    where_clauses.append("c.priority = $priority")
                    params["priority"] = priority
                
                where_clause = " AND ".join(where_clauses) if where_clauses else ""
                if where_clause:
                    where_clause = " AND " + where_clause
                
                query = f"""
                MATCH (u:User {{user_id: $user_id}})-[:OWNS]->(c:Case)
                WHERE true{where_clause}
                RETURN c
                ORDER BY c.created_at DESC
                SKIP $offset
                LIMIT $limit
                """
                
                result = session.run(query, params)
                
                cases = []
                for record in result:
                    cases.append(dict(record["c"]))
                
                return cases
                
            except Neo4jError as e:
                logger.error(f"Neo4j error listing user cases: {e}")
                raise
    
    def store_chat_message(self, session_id: str, case_id: str, user_id: str,
                          content: str, sender: str, sender_type: str,
                          metadata: Optional[dict] = None) -> dict:
        """Store a chat message in a session"""
        with self.driver.session() as session:
            try:
                message_id = str(uuid.uuid4())
                created_at = datetime.now(timezone.utc).isoformat()
                
                # Verify ownership
                verify_query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_id: $case_id})
                MATCH (c)-[:HAS_SESSION]->(s:ChatSession {session_id: $session_id})
                RETURN s
                """
                
                result = session.run(verify_query, {
                    "user_id": user_id,
                    "case_id": case_id,
                    "session_id": session_id
                })
                
                if not result.single():
                    raise ValueError("Session not found or access denied")
                
                # Create message
                message_data = {
                    "message_id": message_id,
                    "session_id": session_id,
                    "content": content,
                    "sender": sender,
                    "sender_type": sender_type,
                    "created_at": created_at,
                    "metadata": metadata if metadata else {}
                }
                
                return self.add_chat_message(session_id, message_data)
                
            except Neo4jError as e:
                logger.error(f"Neo4j error storing chat message: {e}")
                raise
    
    def get_conversation_context(self, session_id: str, limit: int = 10) -> List[dict]:
        """Get recent conversation context from a session"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (s:ChatSession {session_id: $session_id})-[:HAS_MESSAGE]->(m:ChatMessage)
                RETURN m
                ORDER BY m.created_at DESC
                LIMIT $limit
                """
                
                result = session.run(query, {"session_id": session_id, "limit": limit})
                
                messages = []
                for record in result:
                    message = dict(record["m"])
                    # Parse metadata if it's a string
                    if isinstance(message.get("metadata"), str):
                        import json
                        try:
                            message["metadata"] = json.loads(message["metadata"])
                        except:
                            message["metadata"] = {}
                    messages.append(message)
                
                # Return in chronological order
                return list(reversed(messages))
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting conversation context: {e}")
                raise
    
    def get_case_chat_sessions(self, case_id: str) -> List[dict]:
        """Get all chat sessions for a case"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (c:Case {case_id: $case_id})-[:HAS_SESSION]->(s:ChatSession)
                OPTIONAL MATCH (s)-[:HAS_MESSAGE]->(m:ChatMessage)
                WITH s, count(m) as message_count, max(m.created_at) as last_message_at
                RETURN s, message_count, last_message_at
                ORDER BY s.created_at DESC
                """
                
                result = session.run(query, {"case_id": case_id})
                
                sessions = []
                for record in result:
                    session_data = dict(record["s"])
                    session_data["message_count"] = record["message_count"]
                    session_data["last_message_at"] = record["last_message_at"]
                    sessions.append(session_data)
                
                return sessions
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting case chat sessions: {e}")
                raise
    
    def get_case_chat_history(self, case_id: str, session_id: Optional[str] = None,
                             limit: int = 100, offset: int = 0) -> List[dict]:
        """Get chat history for a case, optionally filtered by session"""
        with self.driver.session() as session:
            try:
                if session_id:
                    query = """
                    MATCH (c:Case {case_id: $case_id})-[:HAS_SESSION]->(s:ChatSession {session_id: $session_id})
                    MATCH (s)-[:HAS_MESSAGE]->(m:ChatMessage)
                    RETURN m, s.doctor_type as doctor_type, s.doctor_name as doctor_name
                    ORDER BY m.created_at ASC
                    SKIP $offset
                    LIMIT $limit
                    """
                    params = {"case_id": case_id, "session_id": session_id, "limit": limit, "offset": offset}
                else:
                    query = """
                    MATCH (c:Case {case_id: $case_id})-[:HAS_SESSION]->(s:ChatSession)
                    MATCH (s)-[:HAS_MESSAGE]->(m:ChatMessage)
                    RETURN m, s.doctor_type as doctor_type, s.doctor_name as doctor_name
                    ORDER BY m.created_at ASC
                    SKIP $offset
                    LIMIT $limit
                    """
                    params = {"case_id": case_id, "limit": limit, "offset": offset}
                
                result = session.run(query, params)
                
                messages = []
                for record in result:
                    message = dict(record["m"])
                    message["doctor_type"] = record["doctor_type"]
                    message["doctor_name"] = record["doctor_name"]
                    # Parse metadata if it's a string
                    if isinstance(message.get("metadata"), str):
                        import json
                        try:
                            message["metadata"] = json.loads(message["metadata"])
                        except:
                            message["metadata"] = {}
                    messages.append(message)
                
                return messages
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting case chat history: {e}")
                raise
    
    def find_similar_cases(self, user_id: str, symptoms: List[str], 
                          medical_category: Optional[str] = None, limit: int = 5) -> List[dict]:
        """Find similar cases based on symptoms and medical category"""
        with self.driver.session() as session:
            try:
                # Build query to find cases with similar symptoms
                params = {"user_id": user_id, "symptoms": symptoms, "limit": limit}
                
                if medical_category:
                    category_clause = "AND c.medical_category = $medical_category"
                    params["medical_category"] = medical_category
                else:
                    category_clause = ""
                
                query = f"""
                MATCH (u:User {{user_id: $user_id}})-[:OWNS]->(c:Case)
                WHERE ANY(symptom IN $symptoms WHERE symptom IN c.symptoms)
                {category_clause}
                WITH c, SIZE([s IN c.symptoms WHERE s IN $symptoms]) AS matching_symptoms
                WHERE matching_symptoms > 0
                RETURN c, matching_symptoms
                ORDER BY matching_symptoms DESC, c.created_at DESC
                LIMIT $limit
                """
                
                result = session.run(query, params)
                
                similar_cases = []
                for record in result:
                    case = dict(record["c"])
                    case["matching_symptoms_count"] = record["matching_symptoms"]
                    case["similarity_score"] = record["matching_symptoms"] / len(symptoms)
                    similar_cases.append(case)
                
                return similar_cases
                
            except Neo4jError as e:
                logger.error(f"Neo4j error finding similar cases: {e}")
                raise
    
    def archive_case(self, case_id: str, user_id: str) -> bool:
        """Archive a case"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_id: $case_id})
                SET c.status = 'archived', c.archived_at = $archived_at
                RETURN c
                """
                
                result = session.run(query, {
                    "case_id": case_id,
                    "user_id": user_id,
                    "archived_at": datetime.now(timezone.utc).isoformat()
                })
                
                return result.single() is not None
                
            except Neo4jError as e:
                logger.error(f"Neo4j error archiving case: {e}")
                raise
    
    def get_user_comprehensive_medical_history(self, user_id: str, limit: int = 100, 
                                              include_archived: bool = False) -> Dict[str, Any]:
        """Get comprehensive medical history for a user - Used by MCP for doctors"""
        with self.driver.session() as session:
            try:
                # Build status filter
                if include_archived:
                    status_filter = ""
                else:
                    status_filter = "AND c.status <> 'archived'"
                
                # Get all cases with basic stats
                query = f"""
                MATCH (u:User {{user_id: $user_id}})-[:OWNS]->(c:Case)
                WHERE true {status_filter}
                OPTIONAL MATCH (c)-[:HAS_SESSION]->(s:ChatSession)
                OPTIONAL MATCH (s)-[:HAS_MESSAGE]->(m:ChatMessage)
                WITH c, count(DISTINCT s) as session_count, count(m) as message_count
                RETURN c, session_count, message_count
                ORDER BY c.created_at DESC
                LIMIT $limit
                """
                
                result = session.run(query, {"user_id": user_id, "limit": limit})
                
                cases = []
                all_symptoms = []
                conditions = {}
                medications = set()
                allergies = set()
                
                for record in result:
                    case = dict(record["c"])
                    case["session_count"] = record["session_count"]
                    case["message_count"] = record["message_count"]
                    cases.append(case)
                    
                    # Aggregate data
                    if case.get("symptoms"):
                        all_symptoms.extend(case["symptoms"])
                    
                    if case.get("medical_category"):
                        conditions[case["medical_category"]] = conditions.get(case["medical_category"], 0) + 1
                    
                    if case.get("current_medications") and case["current_medications"] != "None":
                        medications.add(case["current_medications"])
                    
                    if case.get("allergies") and case["allergies"] != "None":
                        allergies.add(case["allergies"])
                
                # Calculate symptom frequency
                symptom_frequency = {}
                for symptom in all_symptoms:
                    symptom_frequency[symptom] = symptom_frequency.get(symptom, 0) + 1
                
                # Sort symptoms by frequency
                common_symptoms = sorted(symptom_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
                
                return {
                    "user_id": user_id,
                    "total_cases": len(cases),
                    "cases": cases,
                    "common_symptoms": common_symptoms,
                    "medical_conditions": conditions,
                    "current_medications": list(medications),
                    "known_allergies": list(allergies),
                    "summary": {
                        "total_sessions": sum(c["session_count"] for c in cases),
                        "total_messages": sum(c["message_count"] for c in cases),
                        "active_cases": len([c for c in cases if c.get("status") == "active"]),
                        "resolved_cases": len([c for c in cases if c.get("status") == "resolved"])
                    }
                }
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting comprehensive medical history: {e}")
                raise
    
    def search_cases(self, user_id: str, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search cases based on query and filters - MCP method for doctors"""
        with self.driver.session() as session:
            try:
                # Build query with filters
                where_clauses = ["c.user_id = $user_id"]
                params = {"user_id": user_id, "search_pattern": f"(?i).*{query}.*", "limit": limit}
                
                if filters:
                    if "status" in filters:
                        where_clauses.append("c.status = $status")
                        params["status"] = filters["status"]
                    if "priority" in filters:
                        where_clauses.append("c.priority = $priority")
                        params["priority"] = filters["priority"]
                    if "date_from" in filters:
                        where_clauses.append("c.created_at >= $date_from")
                        params["date_from"] = filters["date_from"]
                    if "date_to" in filters:
                        where_clauses.append("c.created_at <= $date_to")
                        params["date_to"] = filters["date_to"]
                
                where_clause = " AND ".join(where_clauses)
                
                result = session.run(f"""
                    MATCH (c:Case)
                    WHERE {where_clause} AND (
                        c.chief_complaint =~ $search_pattern OR 
                        c.description =~ $search_pattern OR
                        ANY(symptom IN c.symptoms WHERE symptom =~ $search_pattern)
                    )
                    OPTIONAL MATCH (c)-[:HAS_SESSION]->(s:ChatSession)-[:HAS_MESSAGE]->(m:ChatMessage)
                    WITH c, count(m) as message_count
                    RETURN c, message_count
                    ORDER BY c.created_at DESC
                    LIMIT $limit
                """, **params)
                
                cases = []
                for record in result:
                    case = dict(record["c"])
                    case["message_count"] = record["message_count"]
                    cases.append(case)
                
                return cases
                
            except Neo4jError as e:
                logger.error(f"Neo4j error searching cases: {e}")
                raise
    
    def get_patient_timeline(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get patient's medical timeline for the past N days - MCP method"""
        with self.driver.session() as session:
            try:
                cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
                
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)
                WHERE c.created_at >= $cutoff_date
                OPTIONAL MATCH (c)-[:HAS_SESSION]->(s:ChatSession)-[:HAS_MESSAGE]->(m:ChatMessage)
                WITH c, s, collect(m) as messages
                WITH c, collect({session: s, messages: messages}) as sessions
                RETURN c, sessions
                ORDER BY c.created_at DESC
                """
                
                result = session.run(query, {
                    "user_id": user_id,
                    "cutoff_date": cutoff_date
                })
                
                timeline = []
                for record in result:
                    case = dict(record["c"])
                    case["sessions"] = []
                    
                    for session_data in record["sessions"]:
                        if session_data["session"]:
                            session = dict(session_data["session"])
                            session["message_count"] = len(session_data["messages"])
                            case["sessions"].append(session)
                    
                    timeline.append(case)
                
                return timeline
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting patient timeline: {e}")
                raise