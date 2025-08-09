"""
Neo4j Storage Service for Cases Chat Microservice - Synchronous Version
Handles all database operations for cases, chat sessions, and chat history
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

from app.microservices.cases_chat.models import CaseStatus, ChatSessionType

logger = logging.getLogger(__name__)


class CasesChatStorageSync:
    """
    Neo4j storage service for cases and chat functionality (synchronous version)
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
        logger.info(f"Neo4j storage initialized with URI: {uri}")
    
    def close(self):
        """Close Neo4j connection"""
        self.driver.close()
    
    def create_case(self, case_data: dict) -> dict:
        """Create a new case in Neo4j (async wrapper for compatibility)"""
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
        """Get a case by ID (async wrapper for compatibility)"""
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
                
            except Exception as e:
                logger.error(f"Error getting case: {e}")
                return None
    
    def get_case_by_number(self, case_number: str, user_id: str) -> Optional[dict]:
        """Get a case by its case number"""
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
                
            except Exception as e:
                logger.error(f"Error getting case by number: {e}")
                return None
    
    def update_case(self, case_id: str, user_id: str, update_data: dict) -> Optional[dict]:
        """Update a case (async wrapper for compatibility)"""
        with self.driver.session() as session:
            try:
                # Build SET clause dynamically
                set_clauses = []
                for key in update_data:
                    if key not in ["case_id", "user_id", "created_at"]:
                        set_clauses.append(f"c.{key} = ${key}")
                
                if not set_clauses:
                    return None
                
                query = f"""
                MATCH (u:User {{user_id: $user_id}})-[:OWNS]->(c:Case {{case_id: $case_id}})
                SET {', '.join(set_clauses)}, c.updated_at = $updated_at
                RETURN c
                """
                
                params = {**update_data, "case_id": case_id, "user_id": user_id, "updated_at": datetime.utcnow().isoformat()}
                result = session.run(query, params)
                record = result.single()
                
                if record:
                    return dict(record["c"])
                return None
                
            except Exception as e:
                logger.error(f"Error updating case: {e}")
                return None
    
    def list_user_cases(self, user_id: str, status: Optional[str] = None, 
                              skip: int = 0, limit: int = 20) -> List[dict]:
        """List user's cases (async wrapper for compatibility)"""
        with self.driver.session() as session:
            try:
                if status:
                    query = """
                    MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {status: $status})
                    RETURN c
                    ORDER BY c.created_at DESC
                    SKIP $skip LIMIT $limit
                    """
                    params = {"user_id": user_id, "status": status, "skip": skip, "limit": limit}
                else:
                    query = """
                    MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)
                    RETURN c
                    ORDER BY c.created_at DESC
                    SKIP $skip LIMIT $limit
                    """
                    params = {"user_id": user_id, "skip": skip, "limit": limit}
                
                result = session.run(query, params)
                cases = [dict(record["c"]) for record in result]
                return cases
                
            except Exception as e:
                logger.error(f"Error listing cases: {e}")
                return []
    
    def create_chat_session(self, case_id: str, user_id: str, session_type: str, session_id: str = None) -> dict:
        """Create a new chat session (async wrapper for compatibility)"""
        with self.driver.session() as session:
            try:
                if not session_id:
                    session_id = str(uuid.uuid4())
                query = """
                MATCH (c:Case {case_id: $case_id})
                CREATE (s:ChatSession {
                    session_id: $session_id,
                    case_id: $case_id,
                    user_id: $user_id,
                    session_type: $session_type,
                    created_at: $created_at,
                    last_activity: $created_at,
                    is_active: true,
                    participating_doctors: [],
                    message_count: 0
                })
                CREATE (c)-[:HAS_SESSION]->(s)
                RETURN s
                """
                
                params = {
                    "session_id": session_id,
                    "case_id": case_id,
                    "user_id": user_id,
                    "session_type": session_type,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                result = session.run(query, params)
                record = result.single()
                
                if record:
                    return dict(record["s"])
                else:
                    raise Exception("Failed to create chat session")
                    
            except Exception as e:
                logger.error(f"Error creating chat session: {e}")
                raise
    
    def store_chat_message(self, session_id: str, case_id: str, user_id: str,
                                 user_message: str, doctor_type: str, doctor_response: str,
                                 metadata: dict = None) -> dict:
        """Store a chat message (async wrapper for compatibility)"""
        with self.driver.session() as session:
            try:
                message_id = str(uuid.uuid4())
                query = """
                MATCH (s:ChatSession {session_id: $session_id})
                CREATE (m:ChatMessage {
                    message_id: $message_id,
                    session_id: $session_id,
                    case_id: $case_id,
                    user_id: $user_id,
                    user_message: $user_message,
                    doctor_type: $doctor_type,
                    doctor_response: $doctor_response,
                    created_at: $created_at,
                    metadata: $metadata_json
                })
                CREATE (s)-[:HAS_MESSAGE]->(m)
                
                WITH s, m, $doctor_type as doc_type
                SET s.last_activity = $created_at,
                    s.message_count = s.message_count + 1,
                    s.participating_doctors = CASE 
                        WHEN NOT doc_type IN s.participating_doctors 
                        THEN s.participating_doctors + doc_type 
                        ELSE s.participating_doctors 
                    END
                
                RETURN m
                """
                
                # Convert metadata to JSON string for Neo4j
                import json
                # Ensure all metadata values are JSON-serializable
                if metadata:
                    # Convert all values to strings to ensure Neo4j compatibility
                    safe_metadata = {}
                    for key, value in metadata.items():
                        if isinstance(value, (int, float, bool)):
                            safe_metadata[key] = str(value)
                        else:
                            safe_metadata[key] = str(value)
                    metadata_json = json.dumps(safe_metadata)
                else:
                    metadata_json = json.dumps({})
                
                params = {
                    "message_id": message_id,
                    "session_id": session_id,
                    "case_id": case_id,
                    "user_id": user_id,
                    "user_message": user_message,
                    "doctor_type": doctor_type,
                    "doctor_response": doctor_response,
                    "created_at": datetime.utcnow().isoformat(),
                    "metadata_json": metadata_json
                }
                
                result = session.run(query, params)
                record = result.single()
                
                if record:
                    return dict(record["m"])
                else:
                    raise Exception("Failed to store chat message")
                    
            except Exception as e:
                logger.error(f"Error storing chat message: {e}")
                raise
    
    def get_conversation_context(self, session_id: str, limit: int = 10) -> List[dict]:
        """Get recent conversation context (async wrapper for compatibility)"""
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
                    msg = dict(record["m"])
                    # Parse metadata JSON if it exists
                    if msg.get("metadata") and isinstance(msg["metadata"], str):
                        try:
                            import json
                            msg["metadata"] = json.loads(msg["metadata"])
                        except:
                            msg["metadata"] = {}
                    messages.append(msg)
                
                # Return in chronological order
                return list(reversed(messages))
                
            except Exception as e:
                logger.error(f"Error getting conversation context: {e}")
                return []
    
    def get_case_chat_sessions(self, case_id: str) -> List[dict]:
        """Get all chat sessions for a case (async wrapper for compatibility)"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (c:Case {case_id: $case_id})-[:HAS_SESSION]->(s:ChatSession)
                RETURN s
                ORDER BY s.created_at DESC
                """
                
                result = session.run(query, {"case_id": case_id})
                sessions = [dict(record["s"]) for record in result]
                return sessions
                
            except Exception as e:
                logger.error(f"Error getting case chat sessions: {e}")
                return []
    
    def get_case_chat_history(self, case_id: str, session_id: Optional[str] = None,
                                    doctor_type: Optional[str] = None, limit: int = 50) -> List[dict]:
        """Get chat history for a case (async wrapper for compatibility)"""
        with self.driver.session() as session:
            try:
                if session_id:
                    query = """
                    MATCH (s:ChatSession {session_id: $session_id})-[:HAS_MESSAGE]->(m:ChatMessage)
                    RETURN m
                    ORDER BY m.created_at ASC
                    LIMIT $limit
                    """
                    params = {"session_id": session_id, "limit": limit}
                elif doctor_type:
                    query = """
                    MATCH (c:Case {case_id: $case_id})-[:HAS_SESSION]->(s:ChatSession)-[:HAS_MESSAGE]->(m:ChatMessage {doctor_type: $doctor_type})
                    RETURN m
                    ORDER BY m.created_at ASC
                    LIMIT $limit
                    """
                    params = {"case_id": case_id, "doctor_type": doctor_type, "limit": limit}
                else:
                    query = """
                    MATCH (c:Case {case_id: $case_id})-[:HAS_SESSION]->(s:ChatSession)-[:HAS_MESSAGE]->(m:ChatMessage)
                    RETURN m
                    ORDER BY m.created_at ASC
                    LIMIT $limit
                    """
                    params = {"case_id": case_id, "limit": limit}
                
                result = session.run(query, params)
                messages = []
                for record in result:
                    msg = dict(record["m"])
                    # Parse metadata JSON if it exists
                    if msg.get("metadata") and isinstance(msg["metadata"], str):
                        try:
                            import json
                            msg["metadata"] = json.loads(msg["metadata"])
                        except:
                            msg["metadata"] = {}
                    messages.append(msg)
                return messages
                
            except Exception as e:
                logger.error(f"Error getting case chat history: {e}")
                return []
    
    def get_user_cases(self, user_id: str, limit: int = 50, offset: int = 0) -> List[dict]:
        """Get all cases for a specific user (async wrapper for compatibility)"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)
                WHERE c.status <> 'archived'
                RETURN c, u.user_id AS user_id
                ORDER BY c.created_at DESC
                SKIP $offset
                LIMIT $limit
                """
                
                result = session.run(query, {
                    "user_id": user_id,
                    "limit": limit,
                    "offset": offset
                })
                
                cases = []
                for record in result:
                    case_data = dict(record["c"])
                    case_data["user_id"] = record["user_id"]
                    cases.append(case_data)
                
                return cases
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting user cases: {e}")
                return []
    
    def find_similar_cases(self, user_id: str, symptoms: List[str], 
                                 chief_complaint: str, limit: int = 5) -> List[dict]:
        """Find similar cases based on symptoms and chief complaint (async wrapper for compatibility)"""
        with self.driver.session() as session:
            try:
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
                
                result = session.run(query, {
                    "user_id": user_id,
                    "symptoms": symptoms,
                    "chief_complaint": chief_complaint,
                    "limit": limit
                })
                
                similar_cases = []
                for record in result:
                    similar_cases.append(dict(record["c"]))
                
                return similar_cases
                
            except Neo4jError as e:
                logger.error(f"Neo4j error finding similar cases: {e}")
                return []
    
    def archive_case(self, case_id: str, user_id: str) -> bool:
        """Archive a case (soft delete) - async wrapper for compatibility"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_id: $case_id})
                SET c.status = 'archived',
                    c.updated_at = $updated_at,
                    c.closed_at = $updated_at
                RETURN c.case_id as case_id
                """
                
                result = session.run(query, {
                    "case_id": case_id,
                    "user_id": user_id,
                    "updated_at": datetime.utcnow().isoformat()
                })
                
                record = result.single()
                if record:
                    logger.info(f"Archived case: {case_id}")
                    return True
                return False
                
            except Neo4jError as e:
                logger.error(f"Neo4j error archiving case: {e}")
                return False
    
    def get_user_comprehensive_medical_history(self, user_id: str, limit: int = 100, 
                                                include_cases: bool = True, 
                                                include_chat: bool = True) -> dict:
        """
        Get comprehensive medical history for a user across ALL their cases
        This includes case details, symptoms, diagnoses, and chat messages
        """
        with self.driver.session() as session:
            try:
                # Get all user cases with basic information
                cases_query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)
                WHERE c.status <> 'archived'
                RETURN c
                ORDER BY c.created_at DESC
                LIMIT $limit
                """
                
                case_result = session.run(cases_query, {"user_id": user_id, "limit": limit})
                cases = []
                case_ids = []
                
                for record in case_result:
                    case_data = dict(record["c"])
                    cases.append(case_data)
                    case_ids.append(case_data["case_id"])
                
                logger.info(f"Found {len(cases)} cases for user {user_id}")
                
                # Get ALL chat messages from ALL cases if requested
                all_messages = []
                if include_chat and case_ids:
                    messages_query = """
                    MATCH (c:Case)-[:HAS_SESSION]->(s:ChatSession)-[:HAS_MESSAGE]->(m:ChatMessage)
                    WHERE c.case_id IN $case_ids
                    RETURN m, c.case_id as case_id, c.title as case_title, c.chief_complaint as chief_complaint
                    ORDER BY m.created_at ASC
                    LIMIT $message_limit
                    """
                    
                    message_result = session.run(messages_query, {
                        "case_ids": case_ids,
                        "message_limit": limit * 2  # Allow more messages since it's across multiple cases
                    })
                    
                    for record in message_result:
                        msg = dict(record["m"])
                        msg["case_id"] = record["case_id"]
                        msg["case_title"] = record["case_title"]
                        msg["chief_complaint"] = record["chief_complaint"]
                        
                        # Parse metadata JSON if it exists
                        if msg.get("metadata") and isinstance(msg["metadata"], str):
                            try:
                                import json
                                msg["metadata"] = json.loads(msg["metadata"])
                            except:
                                msg["metadata"] = {}
                        
                        all_messages.append(msg)
                
                logger.info(f"Retrieved {len(all_messages)} messages across all cases for user {user_id}")
                
                # Create comprehensive summary
                medical_history = {
                    "user_id": user_id,
                    "total_cases": len(cases),
                    "cases": cases if include_cases else [],
                    "total_messages": len(all_messages),
                    "messages": all_messages if include_chat else [],
                    "summary": {
                        "most_common_symptoms": self._extract_common_symptoms(cases),
                        "case_timeline": [
                            {
                                "case_id": case["case_id"],
                                "title": case.get("title", "Untitled"),
                                "chief_complaint": case.get("chief_complaint", ""),
                                "symptoms": case.get("symptoms", []),
                                "created_at": case.get("created_at", ""),
                                "status": case.get("status", "unknown")
                            }
                            for case in cases[:10]  # Last 10 cases for timeline
                        ]
                    }
                }
                
                return medical_history
                
            except Neo4jError as e:
                logger.error(f"Neo4j error getting comprehensive medical history: {e}")
                return {
                    "user_id": user_id,
                    "total_cases": 0,
                    "cases": [],
                    "total_messages": 0,
                    "messages": [],
                    "summary": {"most_common_symptoms": [], "case_timeline": []},
                    "error": str(e)
                }
    
    def _extract_common_symptoms(self, cases: List[dict]) -> List[dict]:
        """Extract and count common symptoms across cases"""
        symptom_count = {}
        for case in cases:
            symptoms = case.get("symptoms", [])
            if isinstance(symptoms, list):
                for symptom in symptoms:
                    if symptom:
                        symptom_lower = symptom.lower().strip()
                        symptom_count[symptom_lower] = symptom_count.get(symptom_lower, 0) + 1
        
        # Sort by frequency and return top 10
        common_symptoms = [
            {"symptom": symptom, "frequency": count}
            for symptom, count in sorted(symptom_count.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        return common_symptoms
    
    def delete_message(self, message_id: str, user_id: str) -> bool:
        """Soft delete a message by marking it as deleted"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (m:ChatMessage {message_id: $message_id})
                MATCH (c:Case {case_id: m.case_id})
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c)
                SET m.is_deleted = true,
                    m.deleted_at = $deleted_at,
                    m.deleted_by = $user_id
                RETURN m.message_id as message_id
                """
                
                result = session.run(query, {
                    "message_id": message_id,
                    "user_id": user_id,
                    "deleted_at": datetime.utcnow().isoformat()
                })
                
                record = result.single()
                if record:
                    logger.info(f"Soft deleted message: {message_id}")
                    return True
                return False
                
            except Neo4jError as e:
                logger.error(f"Neo4j error deleting message: {e}")
                return False
    
    def update_message(self, message_id: str, user_id: str, update_data: dict) -> Optional[dict]:
        """Update a message with audit trail"""
        with self.driver.session() as session:
            try:
                # First, verify ownership and get current message
                verify_query = """
                MATCH (m:ChatMessage {message_id: $message_id})
                MATCH (c:Case {case_id: m.case_id})
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c)
                RETURN m
                """
                
                result = session.run(verify_query, {
                    "message_id": message_id,
                    "user_id": user_id
                })
                
                record = result.single()
                if not record:
                    return None
                
                current_message = dict(record["m"])
                
                # Create audit record
                audit_query = """
                MATCH (m:ChatMessage {message_id: $message_id})
                CREATE (a:MessageAudit {
                    audit_id: $audit_id,
                    message_id: $message_id,
                    original_user_message: m.user_message,
                    original_doctor_response: m.doctor_response,
                    updated_by: $user_id,
                    updated_at: $updated_at,
                    changes: $changes
                })
                CREATE (m)-[:HAS_AUDIT]->(a)
                """
                
                import json
                changes = json.dumps(update_data)
                
                session.run(audit_query, {
                    "audit_id": str(uuid.uuid4()),
                    "message_id": message_id,
                    "user_id": user_id,
                    "updated_at": datetime.utcnow().isoformat(),
                    "changes": changes
                })
                
                # Update the message
                update_parts = []
                params = {"message_id": message_id}
                
                if "user_message" in update_data:
                    update_parts.append("m.user_message = $user_message")
                    params["user_message"] = update_data["user_message"]
                
                if "doctor_response" in update_data:
                    update_parts.append("m.doctor_response = $doctor_response")
                    params["doctor_response"] = update_data["doctor_response"]
                
                update_parts.append("m.updated_at = $updated_at")
                update_parts.append("m.updated_by = $updated_by")
                params["updated_at"] = datetime.utcnow().isoformat()
                params["updated_by"] = user_id
                
                update_query = f"""
                MATCH (m:ChatMessage {{message_id: $message_id}})
                SET {', '.join(update_parts)}
                RETURN m
                """
                
                result = session.run(update_query, params)
                record = result.single()
                
                if record:
                    return dict(record["m"])
                return None
                
            except Neo4jError as e:
                logger.error(f"Neo4j error updating message: {e}")
                return None
    
    def search_messages(self, user_id: str, query: str, filters: dict = None) -> List[dict]:
        """Search messages across user's cases with filters"""
        with self.driver.session() as session:
            try:
                # Base query to search in user's messages
                cypher_query = """
                MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)
                MATCH (c)-[:HAS_SESSION]->(s:ChatSession)-[:HAS_MESSAGE]->(m:ChatMessage)
                WHERE (m.user_message CONTAINS $search_query 
                       OR m.doctor_response CONTAINS $search_query)
                       AND (m.is_deleted IS NULL OR m.is_deleted = false)
                """
                
                params = {
                    "user_id": user_id,
                    "search_query": query
                }
                
                # Add filters
                if filters:
                    if filters.get("case_id"):
                        cypher_query += " AND c.case_id = $case_id"
                        params["case_id"] = filters["case_id"]
                    
                    if filters.get("doctor_type"):
                        cypher_query += " AND m.doctor_type = $doctor_type"
                        params["doctor_type"] = filters["doctor_type"]
                    
                    if filters.get("start_date"):
                        cypher_query += " AND m.created_at >= $start_date"
                        params["start_date"] = filters["start_date"]
                    
                    if filters.get("end_date"):
                        cypher_query += " AND m.created_at <= $end_date"
                        params["end_date"] = filters["end_date"]
                
                # Add ordering and limits
                cypher_query += """
                RETURN m, c.case_id as case_id, c.title as case_title, 
                       c.case_number as case_number
                ORDER BY m.created_at DESC
                """
                
                if filters and filters.get("limit"):
                    cypher_query += " LIMIT $limit"
                    params["limit"] = filters["limit"]
                
                if filters and filters.get("offset"):
                    cypher_query += " SKIP $offset"
                    params["offset"] = filters["offset"]
                
                result = session.run(cypher_query, params)
                
                messages = []
                for record in result:
                    message = dict(record["m"])
                    message["case_id"] = record["case_id"]
                    message["case_title"] = record["case_title"]
                    message["case_number"] = record["case_number"]
                    messages.append(message)
                
                return messages
                
            except Neo4jError as e:
                logger.error(f"Neo4j error searching messages: {e}")
                return []