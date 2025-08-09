"""
Unified Neo4j storage implementation for Cases Chat microservice
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import json
import logging
from neo4j import AsyncDriver, AsyncTransaction
from neo4j.exceptions import Neo4jError

from ..base.storage_base import BaseStorage
from ...models.case_models import CaseResponse, CaseCreate, CaseUpdate
from ...models.chat_models import ChatMessage, MessageCreate
from ...core.exceptions import StorageError, CaseNotFoundError, MessageNotFoundError

logger = logging.getLogger(__name__)


class UnifiedNeo4jStorage(BaseStorage):
    """Unified Neo4j storage implementation"""
    
    def __init__(self, driver: AsyncDriver):
        self.driver = driver
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize storage and ensure database schema"""
        try:
            # Test connection
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 as health")
                record = await result.single()
                if not record or record["health"] != 1:
                    raise StorageError("Failed to connect to Neo4j")
            
            # Create constraints and indexes
            await self._create_schema()
            
            self.initialized = True
            logger.info("Neo4j storage initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j storage: {e}")
            raise StorageError(f"Storage initialization failed: {str(e)}")
    
    async def _create_schema(self) -> None:
        """Create database schema, constraints, and indexes"""
        async with self.driver.session() as session:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT case_id_unique IF NOT EXISTS FOR (c:Case) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT case_number_unique IF NOT EXISTS FOR (c:Case) REQUIRE c.case_number IS UNIQUE",
                "CREATE CONSTRAINT message_id_unique IF NOT EXISTS FOR (m:Message) REQUIRE m.id IS UNIQUE",
                "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Neo4jError as e:
                    if "already exists" not in str(e):
                        logger.warning(f"Constraint creation warning: {e}")
            
            # Create indexes
            indexes = [
                "CREATE INDEX case_patient_idx IF NOT EXISTS FOR (c:Case) ON (c.patient_id)",
                "CREATE INDEX case_status_idx IF NOT EXISTS FOR (c:Case) ON (c.status)",
                "CREATE INDEX case_created_idx IF NOT EXISTS FOR (c:Case) ON (c.created_at)",
                "CREATE INDEX message_case_idx IF NOT EXISTS FOR (m:Message) ON (m.case_id)",
                "CREATE INDEX message_timestamp_idx IF NOT EXISTS FOR (m:Message) ON (m.timestamp)",
                "CREATE INDEX message_sequence_idx IF NOT EXISTS FOR (m:Message) ON (m.sequence_number)"
            ]
            
            for index in indexes:
                try:
                    await session.run(index)
                except Neo4jError as e:
                    if "already exists" not in str(e):
                        logger.warning(f"Index creation warning: {e}")
    
    # Case Operations
    
    async def create_case(self, case_data: CaseCreate) -> CaseResponse:
        """Create a new case"""
        case_id = str(uuid.uuid4())
        case_number = await self.get_next_case_number()
        
        async with self.driver.session() as session:
            query = """
            CREATE (c:Case {
                id: $id,
                case_number: $case_number,
                title: $title,
                description: $description,
                patient_id: $patient_id,
                patient_age: $patient_age,
                patient_gender: $patient_gender,
                status: $status,
                urgency_level: $urgency_level,
                medical_category: $medical_category,
                symptoms: $symptoms,
                medical_history: $medical_history,
                current_medications: $current_medications,
                allergies: $allergies,
                created_at: datetime($created_at),
                updated_at: datetime($updated_at),
                metadata: $metadata
            })
            
            WITH c
            MERGE (u:User {id: $patient_id})
            CREATE (u)-[:HAS_CASE]->(c)
            
            RETURN c
            """
            
            params = {
                "id": case_id,
                "case_number": case_number,
                "title": case_data.title,
                "description": case_data.description,
                "patient_id": case_data.patient_id,
                "patient_age": case_data.patient_age,
                "patient_gender": case_data.patient_gender,
                "status": case_data.status,
                "urgency_level": case_data.urgency_level,
                "medical_category": case_data.medical_category,
                "symptoms": json.dumps(case_data.symptoms) if case_data.symptoms else "[]",
                "medical_history": case_data.medical_history,
                "current_medications": json.dumps(case_data.current_medications) if case_data.current_medications else "[]",
                "allergies": json.dumps(case_data.allergies) if case_data.allergies else "[]",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": json.dumps(case_data.metadata) if case_data.metadata else "{}"
            }
            
            result = await session.run(query, params)
            record = await result.single()
            
            if record:
                return self._record_to_case(record["c"])
            else:
                raise StorageError("Failed to create case")
    
    async def get_case(self, case_id: str) -> Optional[CaseResponse]:
        """Get a case by ID"""
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case {id: $case_id})
            RETURN c
            """
            
            result = await session.run(query, {"case_id": case_id})
            record = await result.single()
            
            if record:
                return self._record_to_case(record["c"])
            return None
    
    async def update_case(self, case_id: str, update_data: CaseUpdate) -> Optional[CaseResponse]:
        """Update a case"""
        async with self.driver.session() as session:
            # Build dynamic SET clause
            set_clauses = []
            params = {"case_id": case_id, "updated_at": datetime.utcnow().isoformat()}
            
            update_dict = update_data.dict(exclude_unset=True)
            for key, value in update_dict.items():
                if value is not None:
                    set_clauses.append(f"c.{key} = ${key}")
                    if isinstance(value, (list, dict)):
                        params[key] = json.dumps(value)
                    else:
                        params[key] = value
            
            if not set_clauses:
                return await self.get_case(case_id)
            
            set_clause = ", ".join(set_clauses)
            query = f"""
            MATCH (c:Case {{id: $case_id}})
            SET {set_clause}, c.updated_at = datetime($updated_at)
            RETURN c
            """
            
            result = await session.run(query, params)
            record = await result.single()
            
            if record:
                return self._record_to_case(record["c"])
            return None
    
    async def delete_case(self, case_id: str) -> bool:
        """Delete a case"""
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case {id: $case_id})
            OPTIONAL MATCH (c)<-[:HAS_MESSAGE]-(m:Message)
            DETACH DELETE c, m
            RETURN count(c) as deleted
            """
            
            result = await session.run(query, {"case_id": case_id})
            record = await result.single()
            
            return record["deleted"] > 0 if record else False
    
    async def list_cases(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[CaseResponse], int]:
        """List cases with pagination and filtering"""
        async with self.driver.session() as session:
            # Build WHERE clause
            where_clauses = []
            params = {"skip": skip, "limit": limit}
            
            if filters:
                if "status" in filters:
                    where_clauses.append("c.status = $status")
                    params["status"] = filters["status"]
                if "urgency_level" in filters:
                    where_clauses.append("c.urgency_level = $urgency_level")
                    params["urgency_level"] = filters["urgency_level"]
                if "patient_id" in filters:
                    where_clauses.append("c.patient_id = $patient_id")
                    params["patient_id"] = filters["patient_id"]
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            order_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
            
            # Count query
            count_query = f"""
            MATCH (c:Case)
            WHERE {where_clause}
            RETURN count(c) as total
            """
            
            count_result = await session.run(count_query, params)
            count_record = await count_result.single()
            total_count = count_record["total"] if count_record else 0
            
            # List query
            list_query = f"""
            MATCH (c:Case)
            WHERE {where_clause}
            RETURN c
            ORDER BY c.{sort_by} {order_direction}
            SKIP $skip
            LIMIT $limit
            """
            
            list_result = await session.run(list_query, params)
            cases = []
            async for record in list_result:
                cases.append(self._record_to_case(record["c"]))
            
            return cases, total_count
    
    # Message Operations
    
    async def store_message(self, message_data: MessageCreate) -> ChatMessage:
        """Store a chat message"""
        message_id = str(uuid.uuid4())
        
        # Get next sequence number
        sequence_number = await self._get_next_sequence_number(message_data.case_id)
        
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case {id: $case_id})
            CREATE (m:Message {
                id: $id,
                case_id: $case_id,
                content: $content,
                message_type: $message_type,
                sender_id: $sender_id,
                sender_type: $sender_type,
                timestamp: datetime($timestamp),
                sequence_number: $sequence_number,
                metadata: $metadata
            })
            CREATE (c)-[:HAS_MESSAGE {sequence: $sequence_number}]->(m)
            RETURN m
            """
            
            params = {
                "id": message_id,
                "case_id": message_data.case_id,
                "content": message_data.content,
                "message_type": message_data.message_type.value,
                "sender_id": message_data.sender_id,
                "sender_type": message_data.sender_type,
                "timestamp": message_data.timestamp.isoformat() if message_data.timestamp else datetime.utcnow().isoformat(),
                "sequence_number": sequence_number,
                "metadata": json.dumps(message_data.metadata) if message_data.metadata else "{}"
            }
            
            result = await session.run(query, params)
            record = await result.single()
            
            if record:
                return self._record_to_message(record["m"])
            else:
                raise StorageError("Failed to store message")
    
    async def get_message(self, message_id: str) -> Optional[ChatMessage]:
        """Get a message by ID"""
        async with self.driver.session() as session:
            query = """
            MATCH (m:Message {id: $message_id})
            RETURN m
            """
            
            result = await session.run(query, {"message_id": message_id})
            record = await result.single()
            
            if record:
                return self._record_to_message(record["m"])
            return None
    
    async def get_case_messages(
        self, 
        case_id: str, 
        limit: int = 100, 
        offset: int = 0,
        include_system: bool = True
    ) -> List[ChatMessage]:
        """Get messages for a case in chronological order"""
        async with self.driver.session() as session:
            system_filter = "" if include_system else "AND m.sender_type <> 'system'"
            
            query = f"""
            MATCH (c:Case {{id: $case_id}})-[:HAS_MESSAGE]->(m:Message)
            WHERE 1=1 {system_filter}
            RETURN m
            ORDER BY m.sequence_number ASC
            SKIP $offset
            LIMIT $limit
            """
            
            result = await session.run(query, {
                "case_id": case_id,
                "offset": offset,
                "limit": limit
            })
            
            messages = []
            async for record in result:
                messages.append(self._record_to_message(record["m"]))
            
            return messages
    
    async def search_messages(
        self, 
        case_id: str, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[ChatMessage]:
        """Search messages in a case"""
        async with self.driver.session() as session:
            cypher_query = """
            MATCH (c:Case {id: $case_id})-[:HAS_MESSAGE]->(m:Message)
            WHERE m.content CONTAINS $query
            """
            
            params = {"case_id": case_id, "query": query, "limit": limit}
            
            if filters:
                if "message_type" in filters:
                    cypher_query += " AND m.message_type = $message_type"
                    params["message_type"] = filters["message_type"]
                
                if "sender_type" in filters:
                    cypher_query += " AND m.sender_type = $sender_type"
                    params["sender_type"] = filters["sender_type"]
                
                if "date_from" in filters:
                    cypher_query += " AND m.timestamp >= datetime($date_from)"
                    params["date_from"] = filters["date_from"]
                
                if "date_to" in filters:
                    cypher_query += " AND m.timestamp <= datetime($date_to)"
                    params["date_to"] = filters["date_to"]
            
            cypher_query += """
            RETURN m
            ORDER BY m.timestamp DESC
            LIMIT $limit
            """
            
            result = await session.run(cypher_query, params)
            messages = []
            async for record in result:
                messages.append(self._record_to_message(record["m"]))
            
            return messages
    
    # Case Number Management
    
    async def get_next_case_number(self) -> str:
        """Get the next available case number"""
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case)
            WHERE c.case_number STARTS WITH 'CASE'
            RETURN c.case_number as case_number
            ORDER BY c.case_number DESC
            LIMIT 1
            """
            
            result = await session.run(query)
            record = await result.single()
            
            if record:
                # Extract number from last case
                last_number = record["case_number"]
                try:
                    num = int(last_number.replace("CASE", ""))
                    next_num = num + 1
                except ValueError:
                    next_num = 1
            else:
                next_num = 1
            
            return f"CASE{next_num:06d}"
    
    async def check_case_number_exists(self, case_number: str) -> bool:
        """Check if a case number already exists"""
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case {case_number: $case_number})
            RETURN count(c) as count
            """
            
            result = await session.run(query, {"case_number": case_number})
            record = await result.single()
            
            return record["count"] > 0 if record else False
    
    async def get_case_by_number(self, case_number: str) -> Optional[CaseResponse]:
        """Get a case by its case number"""
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case {case_number: $case_number})
            RETURN c
            """
            
            result = await session.run(query, {"case_number": case_number})
            record = await result.single()
            
            if record:
                return self._record_to_case(record["c"])
            return None
    
    # Statistics and Aggregations
    
    async def get_message_count(self, case_id: str) -> int:
        """Get total message count for a case"""
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case {id: $case_id})-[:HAS_MESSAGE]->(m:Message)
            RETURN count(m) as count
            """
            
            result = await session.run(query, {"case_id": case_id})
            record = await result.single()
            
            return record["count"] if record else 0
    
    async def get_latest_message(self, case_id: str) -> Optional[ChatMessage]:
        """Get the latest message in a case"""
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case {id: $case_id})-[:HAS_MESSAGE]->(m:Message)
            RETURN m
            ORDER BY m.sequence_number DESC
            LIMIT 1
            """
            
            result = await session.run(query, {"case_id": case_id})
            record = await result.single()
            
            if record:
                return self._record_to_message(record["m"])
            return None
    
    async def delete_message(self, message_id: str) -> bool:
        """Delete a message"""
        async with self.driver.session() as session:
            query = """
            MATCH (m:Message {id: $message_id})
            DETACH DELETE m
            RETURN count(m) as deleted
            """
            
            result = await session.run(query, {"message_id": message_id})
            record = await result.single()
            
            return record["deleted"] > 0 if record else False
    
    async def update_message(self, message_id: str, content: str) -> Optional[ChatMessage]:
        """Update message content"""
        async with self.driver.session() as session:
            query = """
            MATCH (m:Message {id: $message_id})
            SET m.content = $content, m.edited_at = datetime()
            RETURN m
            """
            
            result = await session.run(query, {
                "message_id": message_id,
                "content": content
            })
            record = await result.single()
            
            if record:
                return self._record_to_message(record["m"])
            return None
    
    async def add_message_metadata(self, message_id: str, metadata: Dict[str, Any]) -> bool:
        """Add metadata to a message"""
        async with self.driver.session() as session:
            query = """
            MATCH (m:Message {id: $message_id})
            SET m.metadata = $metadata
            RETURN m
            """
            
            result = await session.run(query, {
                "message_id": message_id,
                "metadata": json.dumps(metadata)
            })
            record = await result.single()
            
            return record is not None
    
    async def get_doctor_messages(self, case_id: str, doctor_id: str) -> List[ChatMessage]:
        """Get all messages from a specific doctor in a case"""
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case {id: $case_id})-[:HAS_MESSAGE]->(m:Message)
            WHERE m.sender_id = $doctor_id AND m.sender_type = 'doctor'
            RETURN m
            ORDER BY m.sequence_number ASC
            """
            
            result = await session.run(query, {
                "case_id": case_id,
                "doctor_id": doctor_id
            })
            
            messages = []
            async for record in result:
                messages.append(self._record_to_message(record["m"]))
            
            return messages
    
    async def get_user_cases(self, user_id: str, skip: int = 0, limit: int = 100) -> Tuple[List[CaseResponse], int]:
        """Get cases for a specific user"""
        return await self.list_cases(
            skip=skip,
            limit=limit,
            filters={"patient_id": user_id}
        )
    
    async def search_cases(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[CaseResponse], int]:
        """Search cases by title, description, or case number"""
        async with self.driver.session() as session:
            where_clauses = [
                "(c.title CONTAINS $query OR c.description CONTAINS $query OR c.case_number CONTAINS $query)"
            ]
            params = {"query": query, "skip": skip, "limit": limit}
            
            if filters:
                if "status" in filters:
                    where_clauses.append("c.status = $status")
                    params["status"] = filters["status"]
                if "urgency_level" in filters:
                    where_clauses.append("c.urgency_level = $urgency_level")
                    params["urgency_level"] = filters["urgency_level"]
            
            where_clause = " AND ".join(where_clauses)
            
            # Count query
            count_query = f"""
            MATCH (c:Case)
            WHERE {where_clause}
            RETURN count(c) as total
            """
            
            count_result = await session.run(count_query, params)
            count_record = await count_result.single()
            total_count = count_record["total"] if count_record else 0
            
            # Search query
            search_query = f"""
            MATCH (c:Case)
            WHERE {where_clause}
            RETURN c
            ORDER BY c.created_at DESC
            SKIP $skip
            LIMIT $limit
            """
            
            search_result = await session.run(search_query, params)
            cases = []
            async for record in search_result:
                cases.append(self._record_to_case(record["c"]))
            
            return cases, total_count
    
    async def get_case_statistics(self, case_id: str) -> Dict[str, Any]:
        """Get statistics for a case"""
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case {id: $case_id})
            OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(m:Message)
            WITH c, count(m) as message_count,
                 collect(DISTINCT m.sender_type) as sender_types,
                 max(m.timestamp) as last_message_time
            RETURN c.created_at as created_at,
                   c.updated_at as updated_at,
                   c.status as status,
                   message_count,
                   sender_types,
                   last_message_time
            """
            
            result = await session.run(query, {"case_id": case_id})
            record = await result.single()
            
            if record:
                return {
                    "case_id": case_id,
                    "created_at": record["created_at"],
                    "updated_at": record["updated_at"],
                    "status": record["status"],
                    "message_count": record["message_count"],
                    "sender_types": record["sender_types"],
                    "last_message_time": record["last_message_time"],
                    "has_doctor_response": "doctor" in record["sender_types"]
                }
            
            raise CaseNotFoundError(case_id)
    
    async def archive_case(self, case_id: str) -> bool:
        """Archive a case"""
        updated = await self.update_case(case_id, CaseUpdate(status="archived"))
        return updated is not None
    
    async def restore_case(self, case_id: str) -> bool:
        """Restore an archived case"""
        updated = await self.update_case(case_id, CaseUpdate(status="active"))
        return updated is not None
    
    async def add_case_attachment(self, case_id: str, attachment_data: Dict[str, Any]) -> str:
        """Add an attachment to a case"""
        attachment_id = str(uuid.uuid4())
        
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case {id: $case_id})
            CREATE (a:Attachment {
                id: $id,
                case_id: $case_id,
                filename: $filename,
                file_type: $file_type,
                file_size: $file_size,
                file_path: $file_path,
                uploaded_at: datetime(),
                metadata: $metadata
            })
            CREATE (c)-[:HAS_ATTACHMENT]->(a)
            RETURN a.id as attachment_id
            """
            
            params = {
                "case_id": case_id,
                "id": attachment_id,
                "filename": attachment_data.get("filename"),
                "file_type": attachment_data.get("file_type"),
                "file_size": attachment_data.get("file_size"),
                "file_path": attachment_data.get("file_path"),
                "metadata": json.dumps(attachment_data.get("metadata", {}))
            }
            
            result = await session.run(query, params)
            record = await result.single()
            
            if record:
                return record["attachment_id"]
            else:
                raise StorageError("Failed to add attachment")
    
    async def get_case_attachments(self, case_id: str) -> List[Dict[str, Any]]:
        """Get all attachments for a case"""
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case {id: $case_id})-[:HAS_ATTACHMENT]->(a:Attachment)
            RETURN a
            ORDER BY a.uploaded_at DESC
            """
            
            result = await session.run(query, {"case_id": case_id})
            attachments = []
            
            async for record in result:
                attachment = dict(record["a"])
                if "metadata" in attachment and isinstance(attachment["metadata"], str):
                    attachment["metadata"] = json.loads(attachment["metadata"])
                attachments.append(attachment)
            
            return attachments
    
    async def delete_attachment(self, case_id: str, attachment_id: str) -> bool:
        """Delete a case attachment"""
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case {id: $case_id})-[:HAS_ATTACHMENT]->(a:Attachment {id: $attachment_id})
            DETACH DELETE a
            RETURN count(a) as deleted
            """
            
            result = await session.run(query, {
                "case_id": case_id,
                "attachment_id": attachment_id
            })
            record = await result.single()
            
            return record["deleted"] > 0 if record else False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on storage system"""
        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 as health")
                record = await result.single()
                
                if record and record["health"] == 1:
                    # Get database info
                    info_result = await session.run("""
                        CALL dbms.components() 
                        YIELD name, versions, edition 
                        WHERE name = 'Neo4j Kernel' 
                        RETURN name, versions[0] as version, edition
                    """)
                    info = await info_result.single()
                    
                    return {
                        "status": "healthy",
                        "connected": True,
                        "database": "neo4j",
                        "version": info["version"] if info else "unknown",
                        "edition": info["edition"] if info else "unknown",
                        "timestamp": datetime.utcnow().isoformat()
                    }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "connected": False,
                "database": "neo4j",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def cleanup_old_data(self, days: int = 90) -> Dict[str, int]:
        """Clean up old data"""
        cutoff_date = datetime.utcnow().replace(microsecond=0) - timedelta(days=days)
        
        async with self.driver.session() as session:
            # Delete old archived cases and their messages
            query = """
            MATCH (c:Case)
            WHERE c.status = 'archived' AND c.updated_at < datetime($cutoff_date)
            OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(m:Message)
            OPTIONAL MATCH (c)-[:HAS_ATTACHMENT]->(a:Attachment)
            WITH c, collect(m) as messages, collect(a) as attachments
            DETACH DELETE c
            FOREACH (msg IN messages | DETACH DELETE msg)
            FOREACH (att IN attachments | DETACH DELETE att)
            RETURN count(c) as cases_deleted, 
                   size(messages) as messages_deleted,
                   size(attachments) as attachments_deleted
            """
            
            result = await session.run(query, {"cutoff_date": cutoff_date.isoformat()})
            record = await result.single()
            
            if record:
                return {
                    "cases_deleted": record["cases_deleted"],
                    "messages_deleted": record["messages_deleted"],
                    "attachments_deleted": record["attachments_deleted"]
                }
            
            return {"cases_deleted": 0, "messages_deleted": 0, "attachments_deleted": 0}
    
    async def optimize_storage(self) -> Dict[str, Any]:
        """Optimize storage (e.g., rebuild indexes)"""
        async with self.driver.session() as session:
            # Get index statistics
            query = """
            CALL db.indexes()
            YIELD name, state, populationPercent, type
            RETURN name, state, populationPercent, type
            """
            
            result = await session.run(query)
            indexes = []
            
            async for record in result:
                indexes.append({
                    "name": record["name"],
                    "state": record["state"],
                    "population_percent": record["populationPercent"],
                    "type": record["type"]
                })
            
            return {
                "indexes": indexes,
                "total_indexes": len(indexes),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # Helper methods
    
    async def _get_next_sequence_number(self, case_id: str) -> int:
        """Get next sequence number for a case's messages"""
        async with self.driver.session() as session:
            query = """
            MATCH (c:Case {id: $case_id})-[:HAS_MESSAGE]->(m:Message)
            RETURN max(m.sequence_number) as max_seq
            """
            
            result = await session.run(query, {"case_id": case_id})
            record = await result.single()
            
            if record and record["max_seq"] is not None:
                return record["max_seq"] + 1
            return 1
    
    def _record_to_case(self, record: Dict[str, Any]) -> CaseResponse:
        """Convert Neo4j record to Case model"""
        # Parse JSON fields
        for field in ["symptoms", "current_medications", "allergies", "metadata"]:
            if field in record and isinstance(record[field], str):
                try:
                    record[field] = json.loads(record[field])
                except json.JSONDecodeError:
                    record[field] = [] if field != "metadata" else {}
        
        # Convert datetime strings to datetime objects
        for field in ["created_at", "updated_at"]:
            if field in record and isinstance(record[field], str):
                record[field] = datetime.fromisoformat(record[field])
        
        return CaseResponse(**record)
    
    def _record_to_message(self, record: Dict[str, Any]) -> ChatMessage:
        """Convert Neo4j record to ChatMessage model"""
        # Parse metadata
        if "metadata" in record and isinstance(record["metadata"], str):
            try:
                record["metadata"] = json.loads(record["metadata"])
            except json.JSONDecodeError:
                record["metadata"] = {}
        
        # Convert timestamp
        if "timestamp" in record and isinstance(record["timestamp"], str):
            record["timestamp"] = datetime.fromisoformat(record["timestamp"])
        
        return ChatMessage(**record)


# Import timedelta for cleanup function
from datetime import timedelta