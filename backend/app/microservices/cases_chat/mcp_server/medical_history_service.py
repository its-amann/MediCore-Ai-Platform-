"""
Medical History Service
Provides case history retrieval and analysis capabilities for AI doctors
Simplified version for HTTP/WebSocket integration
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass, asdict

from neo4j import GraphDatabase
from app.core.config import settings

# Try to use dependency injection
try:
    from app.microservices.cases_chat.core.database import get_neo4j_pool
    USE_POOL = True
except ImportError:
    USE_POOL = False

logger = logging.getLogger(__name__)


@dataclass
class CaseContext:
    """Represents a medical case with full context"""
    case_id: str
    user_id: str
    chief_complaint: str
    symptoms: List[str]
    description: str
    priority: str
    past_medical_history: str
    current_medications: str
    allergies: str
    created_at: str
    messages: List[Dict[str, str]]
    
    def to_dict(self):
        return asdict(self)


@dataclass
class SimilarCase:
    """Represents a similar case with relevance score"""
    case: CaseContext
    relevance_score: float
    matching_symptoms: List[str]
    matching_patterns: List[str]


class MedicalHistoryService:
    """
    Service for retrieving medical history and related cases from Neo4j
    Simplified for integration with existing HTTP/WebSocket endpoints
    """
    
    def __init__(self):
        """Initialize service with Neo4j connection"""
        if USE_POOL:
            # Use centralized connection pool if available
            self._pool = get_neo4j_pool()
            self._use_pool = True
            logger.info("Using centralized connection pool")
        else:
            # Create own driver for standalone usage
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            self._use_pool = False
            logger.info("Using direct Neo4j connection")
        self.symptom_embeddings = self._initialize_symptom_embeddings()
    
    @property
    def driver(self):
        """Get driver from pool or direct connection"""
        if self._use_pool:
            return self._pool.sync_driver
        return self._driver
    
    def _initialize_symptom_embeddings(self) -> Dict[str, List[float]]:
        """Initialize simple symptom embeddings for similarity calculation"""
        # In production, use actual medical embeddings from a trained model
        symptom_groups = {
            "neurological": ["headache", "dizziness", "blurred_vision", "confusion", "seizure"],
            "respiratory": ["cough", "shortness_of_breath", "wheezing", "chest_tightness"],
            "cardiovascular": ["chest_pain", "palpitations", "irregular_heartbeat", "edema"],
            "gastrointestinal": ["nausea", "vomiting", "abdominal_pain", "diarrhea"],
            "systemic": ["fever", "fatigue", "body_aches", "weakness", "chills"],
            "psychological": ["anxiety", "depression", "insomnia", "panic"]
        }
        
        embeddings = {}
        for group_idx, (group, symptoms) in enumerate(symptom_groups.items()):
            for symptom in symptoms:
                # Simple embedding based on group membership
                embedding = [0.0] * len(symptom_groups)
                embedding[group_idx] = 1.0
                embeddings[symptom] = embedding
        
        return embeddings
    
    async def search_cases(
        self,
        user_id: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search cases based on query and filters
        
        Args:
            user_id: User ID for access control
            query: Search query
            filters: Optional filters (status, priority, date range)
            limit: Maximum results
            
        Returns:
            List of matching cases
        """
        with self.driver.session(database="neo4j") as session:
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
                case["relevance_score"] = self._calculate_relevance(case, query)
                cases.append(case)
            
            # Sort by relevance
            cases.sort(key=lambda x: x["relevance_score"], reverse=True)
            return cases
    
    async def get_case_history(
        self,
        case_id: str,
        user_id: str,
        include_chat: bool = True,
        include_analysis: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete history for a specific case
        
        Args:
            case_id: Case ID
            user_id: User ID for access control
            include_chat: Include chat history
            include_analysis: Include analysis data
            
        Returns:
            Complete case history or None if not found/unauthorized
        """
        with self.driver.session(database="neo4j") as session:
            # Get case with access control
            result = session.run("""
                MATCH (c:Case {case_id: $case_id, user_id: $user_id})
                RETURN c
            """, case_id=case_id, user_id=user_id)
            
            record = result.single()
            if not record:
                return None
            
            case = dict(record["c"])
            history = {
                "case": case,
                "timeline": []
            }
            
            if include_chat:
                # Get chat messages
                chat_result = session.run("""
                    MATCH (c:Case {case_id: $case_id})-[:HAS_SESSION]->(s:ChatSession)-[:HAS_MESSAGE]->(m:ChatMessage)
                    OPTIONAL MATCH (m)-[:IN_SESSION]->(s:ChatSession)
                    RETURN m, s.session_id as session_id
                    ORDER BY m.created_at DESC
                    LIMIT 100
                """, case_id=case_id)
                
                consultations = {}
                for msg_record in chat_result:
                    msg = dict(msg_record["m"])
                    doctor_type = msg.get("doctor_type", "unknown")
                    
                    if doctor_type not in consultations:
                        consultations[doctor_type] = []
                    
                    consultations[doctor_type].append({
                        "timestamp": msg.get("created_at"),
                        "user_message": msg.get("user_message"),
                        "doctor_response": msg.get("doctor_response"),
                        "session_id": msg_record["session_id"],
                        "metadata": msg.get("metadata", {})
                    })
                    
                    # Add to timeline
                    history["timeline"].append({
                        "timestamp": msg.get("created_at"),
                        "event_type": "consultation",
                        "doctor": doctor_type,
                        "summary": (msg.get("user_message", "")[:100] + "...") if msg.get("user_message") else ""
                    })
                
                history["consultations"] = consultations
            
            # Sort timeline
            history["timeline"].sort(key=lambda x: x["timestamp"], reverse=True)
            
            return history
    
    async def find_similar_cases(
        self,
        case_id: Optional[str] = None,
        symptoms: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        similarity_threshold: float = 0.5,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find cases similar to a given case or set of symptoms
        
        Args:
            case_id: Reference case ID
            symptoms: List of symptoms to match
            user_id: User ID for filtering (None = all users)
            similarity_threshold: Minimum similarity score
            limit: Maximum results
            
        Returns:
            List of similar cases with similarity scores
        """
        # Get reference case if case_id provided
        if case_id and not symptoms:
            with self.driver.session(database="neo4j") as session:
                result = session.run("""
                    MATCH (c:Case {case_id: $case_id})
                    RETURN c.symptoms as symptoms
                """, case_id=case_id)
                
                record = result.single()
                if record:
                    symptoms = record["symptoms"]
        
        if not symptoms:
            return []
        
        with self.driver.session(database="neo4j") as session:
            # Build query
            where_clauses = []
            params = {"limit": limit * 3}  # Get more to filter by threshold
            
            if case_id:
                where_clauses.append("c.case_id <> $case_id")
                params["case_id"] = case_id
            
            if user_id:
                where_clauses.append("c.user_id = $user_id")
                params["user_id"] = user_id
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "true"
            
            result = session.run(f"""
                MATCH (c:Case)
                WHERE {where_clause}
                RETURN c
                ORDER BY c.created_at DESC
                LIMIT $limit
            """, **params)
            
            similar_cases = []
            for record in result:
                case = dict(record["c"])
                case_symptoms = case.get("symptoms", [])
                
                # Calculate similarity
                similarity = self._calculate_symptom_similarity(symptoms, case_symptoms)
                
                if similarity >= similarity_threshold:
                    matching_symptoms = list(set(symptoms) & set(case_symptoms))
                    
                    similar_cases.append({
                        **case,
                        "similarity_score": similarity,
                        "matching_symptoms": matching_symptoms
                    })
            
            # Sort by similarity and limit
            similar_cases.sort(key=lambda x: x["similarity_score"], reverse=True)
            return similar_cases[:limit]
    
    async def get_patient_timeline(
        self,
        user_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get timeline of all cases for a user
        
        Args:
            user_id: User ID
            date_from: Start date filter
            date_to: End date filter
            
        Returns:
            Timeline of case events
        """
        with self.driver.session(database="neo4j") as session:
            params = {"user_id": user_id}
            date_filter = ""
            
            if date_from:
                date_filter += " AND c.created_at >= $date_from"
                params["date_from"] = date_from
            
            if date_to:
                date_filter += " AND c.created_at <= $date_to"
                params["date_to"] = date_to
            
            result = session.run(f"""
                MATCH (c:Case {{user_id: $user_id}})
                WHERE true {date_filter}
                OPTIONAL MATCH (c)-[:HAS_SESSION]->(s:ChatSession)-[:HAS_MESSAGE]->(m:ChatMessage)
                WITH c, count(m) as consultation_count, 
                     collect(DISTINCT m.doctor_type) as consulted_doctors
                RETURN c, consultation_count, consulted_doctors
                ORDER BY c.created_at DESC
            """, **params)
            
            timeline = []
            for record in result:
                case = dict(record["c"])
                timeline.append({
                    "timestamp": case["created_at"],
                    "event_type": "case_created",
                    "case_id": case["case_id"],
                    "title": case.get("title", case.get("chief_complaint", "Case")),
                    "status": case["status"],
                    "consultation_count": record["consultation_count"],
                    "consulted_doctors": [d for d in record["consulted_doctors"] if d]
                })
            
            return timeline
    
    async def analyze_patterns(
        self,
        user_id: str,
        pattern_type: str = "symptoms"
    ) -> Dict[str, Any]:
        """
        Analyze patterns in user's medical history
        
        Args:
            user_id: User ID
            pattern_type: Type of pattern to analyze
            
        Returns:
            Pattern analysis results
        """
        with self.driver.session(database="neo4j") as session:
            if pattern_type == "symptoms":
                result = session.run("""
                    MATCH (c:Case {user_id: $user_id})
                    UNWIND c.symptoms as symptom
                    WITH symptom, count(c) as frequency
                    RETURN symptom, frequency
                    ORDER BY frequency DESC
                    LIMIT 20
                """, user_id=user_id)
                
                symptoms = []
                for record in result:
                    symptoms.append({
                        "symptom": record["symptom"],
                        "frequency": record["frequency"]
                    })
                
                return {
                    "pattern_type": pattern_type,
                    "user_id": user_id,
                    "common_symptoms": symptoms
                }
            
            # Add more pattern types as needed
            return {"pattern_type": pattern_type, "user_id": user_id}
    
    async def get_case_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistical insights about cases"""
        with self.driver.session(database="neo4j") as session:
            if user_id:
                result = session.run("""
                    MATCH (c:Case {user_id: $user_id})
                    WITH count(c) as total_cases,
                         count(CASE WHEN c.status = 'active' THEN 1 END) as active_cases,
                         count(CASE WHEN c.status = 'resolved' THEN 1 END) as resolved_cases
                    RETURN total_cases, active_cases, resolved_cases
                """, user_id=user_id)
            else:
                result = session.run("""
                    MATCH (c:Case)
                    WITH count(c) as total_cases,
                         count(CASE WHEN c.status = 'active' THEN 1 END) as active_cases,
                         count(CASE WHEN c.status = 'resolved' THEN 1 END) as resolved_cases
                    RETURN total_cases, active_cases, resolved_cases
                """)
            
            record = result.single()
            if not record:
                return {"total_cases": 0, "active_cases": 0, "resolved_cases": 0}
            
            return {
                "total_cases": record["total_cases"],
                "active_cases": record["active_cases"],
                "resolved_cases": record["resolved_cases"]
            }
    
    # Helper methods
    
    def _calculate_relevance(self, case: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for search results"""
        score = 0.0
        query_lower = query.lower()
        
        # Check chief complaint
        if query_lower in case.get("chief_complaint", "").lower():
            score += 0.5
        
        # Check symptoms
        for symptom in case.get("symptoms", []):
            if query_lower in symptom.lower():
                score += 0.3
                break
        
        # Check description
        if query_lower in case.get("description", "").lower():
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_symptom_similarity(self, symptoms1: List[str], symptoms2: List[str]) -> float:
        """Calculate similarity between two sets of symptoms"""
        if not symptoms1 or not symptoms2:
            return 0.0
        
        # Direct symptom overlap (Jaccard similarity)
        set1, set2 = set(symptoms1), set(symptoms2)
        overlap = len(set1 & set2)
        union = len(set1 | set2)
        direct_similarity = overlap / union if union > 0 else 0
        
        # Semantic similarity using embeddings
        semantic_similarity = 0.0
        count = 0
        
        for s1 in symptoms1:
            if s1.lower() in self.symptom_embeddings:
                for s2 in symptoms2:
                    if s2.lower() in self.symptom_embeddings:
                        # Simple cosine similarity
                        emb1 = np.array(self.symptom_embeddings[s1.lower()])
                        emb2 = np.array(self.symptom_embeddings[s2.lower()])
                        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                        semantic_similarity += similarity
                        count += 1
        
        if count > 0:
            semantic_similarity /= count
        
        # Weighted combination
        return 0.7 * direct_similarity + 0.3 * semantic_similarity
    
    async def close(self):
        """Close the database connection"""
        if self.driver:
            self.driver.close()


# Singleton instance
_service_instance: Optional[MedicalHistoryService] = None


def get_medical_history_service() -> MedicalHistoryService:
    """Get the singleton medical history service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = MedicalHistoryService()
    return _service_instance