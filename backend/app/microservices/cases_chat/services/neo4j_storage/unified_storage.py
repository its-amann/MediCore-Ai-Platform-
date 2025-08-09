"""
Unified Neo4j Storage Service for Cases Chat Microservice
Handles both async and sync operations with proper connection pooling and transaction support
"""

import logging
from typing import List, Dict, Any, Optional, Union, TypeVar, Callable
from datetime import datetime
import uuid
import asyncio
from contextlib import contextmanager, asynccontextmanager
from functools import wraps
import json

from neo4j import Transaction
from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired
from neo4j import unit_of_work
from pydantic import BaseModel, ValidationError

from app.microservices.cases_chat.core.database import get_neo4j_pool

from app.microservices.cases_chat.models import (
    CaseStatus, ChatSessionType, CaseCreate, CaseUpdate, 
    ChatMessage as ChatMessageModel
)
from app.core.knowledge_graph import KnowledgeGraphService, get_knowledge_graph_service

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ConnectionConfig(BaseModel):
    """Database connection configuration with validation"""
    uri: str
    user: str
    password: str
    max_connection_pool_size: int = 50
    connection_acquisition_timeout: float = 60.0
    max_connection_lifetime: float = 3600.0
    max_transaction_retry_time: float = 30.0
    connection_timeout: float = 30.0
    encrypted: bool = False
    trust: str = "TRUST_ALL_CERTIFICATES"


class UnifiedCasesChatStorage:
    """
    Unified storage service supporting both async and sync operations
    with centralized connection pooling, transactions, and health checks
    """
    
    def __init__(self, config: Optional[Union[ConnectionConfig, Dict[str, Any]]] = None):
        """
        Initialize storage with configuration
        
        Args:
            config: Connection configuration object or dict (optional - uses settings if not provided)
        """
        # Get the centralized connection pool
        self._pool = get_neo4j_pool()
        
        # Store config for compatibility (if provided)
        if config:
            if isinstance(config, dict):
                self.config = ConnectionConfig(**config)
            else:
                self.config = config
        else:
            # Use default configuration from pool
            self.config = None
        
        # Initialize knowledge graph service
        self.kg_service = get_knowledge_graph_service()
        
        logger.info("Unified Neo4j storage initialized using centralized connection pool")
    
    @property
    def _sync_driver(self):
        """Get sync driver from connection pool"""
        return self._pool.sync_driver
    
    @property
    async def _async_driver(self):
        """Get async driver from connection pool"""
        return await self._pool.async_driver
    
    # Health Check Methods
    
    async def health_check_async(self) -> Dict[str, Any]:
        """
        Perform async health check on database connection
        
        Returns:
            Health status dictionary
        """
        try:
            driver = await self._async_driver
            async with driver.session() as session:
                result = await session.run("RETURN 1 as health")
                record = await result.single()
                
                if record and record["health"] == 1:
                    # Get additional database info
                    info_result = await session.run("""
                        CALL dbms.components() 
                        YIELD name, versions, edition 
                        WHERE name = 'Neo4j Kernel' 
                        RETURN name, versions[0] as version, edition
                    """)
                    info = await info_result.single()
                    
                    return {
                        "status": "healthy",
                        "database": "neo4j",
                        "version": info["version"] if info else "unknown",
                        "edition": info["edition"] if info else "unknown",
                        "connection_pool": {
                            "max_size": self.config.max_connection_pool_size,
                            "in_use": self._async_driver.get_server_info()
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "database": "neo4j",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def health_check_sync(self) -> Dict[str, Any]:
        """
        Perform sync health check on database connection
        
        Returns:
            Health status dictionary
        """
        try:
            with self._sync_driver.session() as session:
                result = session.run("RETURN 1 as health")
                record = result.single()
                
                if record and record["health"] == 1:
                    # Get additional database info
                    info_result = session.run("""
                        CALL dbms.components() 
                        YIELD name, versions, edition 
                        WHERE name = 'Neo4j Kernel' 
                        RETURN name, versions[0] as version, edition
                    """)
                    info = info_result.single()
                    
                    return {
                        "status": "healthy",
                        "database": "neo4j",
                        "version": info["version"] if info else "unknown",
                        "edition": info["edition"] if info else "unknown",
                        "connection_pool": {
                            "max_size": self.config.max_connection_pool_size
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "database": "neo4j",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # Connection Management
    
    async def close_async(self):
        """Close async driver connection"""
        # Connection pool manages lifecycle - no action needed
        logger.info("Close requested - connections managed by pool")
    
    def close_sync(self):
        """Close sync driver connection"""
        # Connection pool manages lifecycle - no action needed
        logger.info("Close requested - connections managed by pool")
    
    async def close(self):
        """Close all connections (async wrapper for compatibility)"""
        # Connection pool manages lifecycle - no action needed
        logger.info("Close requested - connections managed by pool")
    
    # Transaction Management Decorators
    
    def with_transaction(func):
        """Decorator for sync methods to run within a transaction"""
        @wraps(func)
        def wrapper(self, tx: Optional[Transaction] = None, *args, **kwargs):
            if tx:
                # Already in a transaction, just execute
                return func(self, tx, *args, **kwargs)
            else:
                # Create new transaction
                with self._sync_driver.session() as session:
                    return session.execute_write(
                        lambda tx: func(self, tx, *args, **kwargs)
                    )
        return wrapper
    
    def with_async_transaction(func):
        """Decorator for async methods to run within a transaction"""
        @wraps(func)
        async def wrapper(self, tx: Optional[Transaction] = None, *args, **kwargs):
            if tx:
                # Already in a transaction, just execute
                return await func(self, tx, *args, **kwargs)
            else:
                # Create new transaction
                driver = await self._async_driver
                async with driver.session() as session:
                    return await session.execute_write(
                        lambda tx: func(self, tx, *args, **kwargs)
                    )
        return wrapper
    
    # Data Validation Helpers
    
    def _validate_case_data(self, case_data: dict) -> dict:
        """
        Validate and normalize case data
        
        Args:
            case_data: Raw case data
            
        Returns:
            Validated case data
            
        Raises:
            ValidationError: If data is invalid
        """
        # Ensure required fields
        required_fields = ["case_id", "user_id", "chief_complaint", "status", "priority"]
        for field in required_fields:
            if field not in case_data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Use centralized normalization from validators
        return normalize_case_data_for_storage(case_data)
    
    def _validate_message_data(self, message_data: dict) -> dict:
        """
        Validate and normalize message data
        
        Args:
            message_data: Raw message data
            
        Returns:
            Validated message data
        """
        # Ensure storage-specific required fields
        storage_required_fields = ["session_id", "case_id"]
        for field in storage_required_fields:
            if field not in message_data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Use centralized normalization
        message_data = normalize_message_data_for_storage(message_data)
        
        # Handle storage-specific fields
        if "id" not in message_data and "message_id" in message_data:
            message_data["id"] = message_data["message_id"]
        elif "id" not in message_data:
            message_data["id"] = str(uuid.uuid4())
        
        # Convert created_at to timestamp for backward compatibility
        if "timestamp" not in message_data and "created_at" in message_data:
            message_data["timestamp"] = message_data["created_at"]
        
        # Ensure metadata is string (for Neo4j storage)
        if "metadata" in message_data and not isinstance(message_data["metadata"], str):
            message_data["metadata"] = json.dumps(message_data["metadata"])
        
        return message_data
    
    # Case Operations
    
    async def create_case(self, case_data: dict) -> dict:
        """
        Create a new case with transaction support
        
        Args:
            case_data: Case information dictionary
            
        Returns:
            Created case data
        """
        try:
            # Validate data
            case_data = self._validate_case_data(case_data)
            
            driver = await self._async_driver
            async with driver.session() as session:
                result = await session.execute_write(
                    self._create_case_tx,
                    case_data
                )
                
                # Ensure knowledge graph relationships are properly created
                # This is a safety measure to verify bidirectional relationships
                await self.kg_service.ensure_user_case_relationship(
                    case_data['user_id'],
                    result['case_id'],
                    create_user_if_missing=True
                )
                
                return result
        except ValidationError as e:
            logger.error(f"Validation error creating case: {str(e)}")
            raise
        except Neo4jError as e:
            logger.error(f"Neo4j error creating case: {str(e)}")
            raise
    
    @staticmethod
    async def _create_case_tx(tx: Transaction, case_data: dict) -> dict:
        """Transaction function for creating a case"""
        query = """
        // First ensure user exists (create if not)
        MERGE (u:User {user_id: $user_id})
        ON CREATE SET u.created_at = datetime()
        
        // Create the case
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
            updated_at: $updated_at
        })
        
        // Create bidirectional ownership relationships
        CREATE (u)-[:OWNS]->(c)
        CREATE (c)-[:OWNED_BY]->(u)
        
        // Create indexes if not exist (this is idempotent)
        WITH c
        CALL apoc.schema.assert(
            {Case: ['case_id', 'case_number', 'user_id', 'status']},
            {}
        ) YIELD label, key
        
        RETURN c
        """
        
        result = await tx.run(query, case_data)
        record = await result.single()
        
        if record:
            case = dict(record["c"])
            logger.info(f"Created case: {case['case_id']}")
            return case
        else:
            raise Exception("Failed to create case")
    
    def create_case_sync(self, case_data: dict) -> dict:
        """
        Create a new case (sync version)
        
        Args:
            case_data: Case information dictionary
            
        Returns:
            Created case data
        """
        try:
            # Validate data
            case_data = self._validate_case_data(case_data)
            
            with self._sync_driver.session() as session:
                result = session.execute_write(
                    self._create_case_tx_sync,
                    case_data
                )
                return result
        except ValidationError as e:
            logger.error(f"Validation error creating case: {str(e)}")
            raise
        except Neo4jError as e:
            logger.error(f"Neo4j error creating case: {str(e)}")
            raise
    
    @staticmethod
    def _create_case_tx_sync(tx: Transaction, case_data: dict) -> dict:
        """Transaction function for creating a case (sync)"""
        query = """
        // First ensure user exists (create if not)
        MERGE (u:User {user_id: $user_id})
        ON CREATE SET u.created_at = datetime()
        
        // Create the case
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
            updated_at: $updated_at
        })
        
        // Create bidirectional ownership relationships
        CREATE (u)-[:OWNS]->(c)
        CREATE (c)-[:OWNED_BY]->(u)
        
        RETURN c
        """
        
        result = tx.run(query, case_data)
        record = result.single()
        
        if record:
            case = dict(record["c"])
            logger.info(f"Created case: {case['case_id']}")
            return case
        else:
            raise Exception("Failed to create case")
    
    # Chat Message Operations with Unified Schema
    
    async def create_chat_message(
        self,
        session_id: str,
        case_id: str,
        content: str,
        role: str,
        user_id: Optional[str] = None,
        medical_insights: Optional[dict] = None,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Create a chat message with unified schema
        
        Args:
            session_id: Chat session ID
            case_id: Case ID
            content: Message content
            role: Message role (user/assistant)
            user_id: Optional user ID
            medical_insights: Optional medical insights
            metadata: Optional metadata
            
        Returns:
            Created message data
        """
        message_data = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "case_id": case_id,
            "content": content,
            "role": role,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "medical_insights": json.dumps(medical_insights) if medical_insights else "{}",
            "metadata": json.dumps(metadata) if metadata else "{}"
        }
        
        # Validate data
        message_data = self._validate_message_data(message_data)
        
        driver = await self._async_driver
        async with driver.session() as session:
            result = await session.execute_write(
                self._create_message_tx,
                message_data
            )
            return result
    
    @staticmethod
    async def _create_message_tx(tx: Transaction, message_data: dict) -> dict:
        """Transaction function for creating a chat message"""
        query = """
        // Create the message
        CREATE (m:ChatMessage {
            id: $id,
            session_id: $session_id,
            case_id: $case_id,
            content: $content,
            role: $role,
            timestamp: $timestamp,
            user_id: $user_id,
            medical_insights: $medical_insights,
            metadata: $metadata
        })
        
        WITH m
        
        // Link to session
        MATCH (s:ChatSession {session_id: $session_id})
        CREATE (s)-[:HAS_MESSAGE]->(m)
        
        // Update session
        SET s.message_count = COALESCE(s.message_count, 0) + 1,
            s.last_activity = $timestamp
        
        WITH m, s
        
        // Link to case
        MATCH (c:Case {case_id: $case_id})
        CREATE (m)-[:BELONGS_TO_CASE]->(c)
        
        RETURN m
        """
        
        result = await tx.run(query, message_data)
        record = await result.single()
        
        if record:
            message = dict(record["m"])
            logger.info(f"Created chat message: {message['id']}")
            return message
        else:
            raise Exception("Failed to create chat message")
    
    # Batch Operations with Transactions
    
    async def create_conversation_messages(
        self,
        session_id: str,
        case_id: str,
        user_message: str,
        assistant_response: str,
        user_id: str,
        metadata: Optional[dict] = None
    ) -> List[dict]:
        """
        Create both user and assistant messages in a single transaction
        
        Args:
            session_id: Chat session ID
            case_id: Case ID
            user_message: User's message
            assistant_response: Assistant's response
            user_id: User ID
            metadata: Optional metadata
            
        Returns:
            List of created messages
        """
        driver = await self._async_driver
        async with driver.session() as session:
            result = await session.execute_write(
                self._create_conversation_tx,
                session_id,
                case_id,
                user_message,
                assistant_response,
                user_id,
                metadata
            )
            return result
    
    @staticmethod
    async def _create_conversation_tx(
        tx: Transaction,
        session_id: str,
        case_id: str,
        user_message: str,
        assistant_response: str,
        user_id: str,
        metadata: Optional[dict]
    ) -> List[dict]:
        """Transaction function for creating a conversation (user + assistant messages)"""
        timestamp = datetime.utcnow().isoformat()
        user_msg_id = str(uuid.uuid4())
        assistant_msg_id = str(uuid.uuid4())
        metadata_str = json.dumps(metadata) if metadata else "{}"
        
        query = """
        // Create user message
        CREATE (user_msg:ChatMessage {
            id: $user_msg_id,
            session_id: $session_id,
            case_id: $case_id,
            content: $user_message,
            role: 'user',
            timestamp: $timestamp,
            user_id: $user_id,
            metadata: $metadata
        })
        
        // Create assistant message
        CREATE (assistant_msg:ChatMessage {
            id: $assistant_msg_id,
            session_id: $session_id,
            case_id: $case_id,
            content: $assistant_response,
            role: 'assistant',
            timestamp: $timestamp,
            metadata: $metadata
        })
        
        WITH user_msg, assistant_msg
        
        // Link to session and update count
        MATCH (s:ChatSession {session_id: $session_id})
        CREATE (s)-[:HAS_MESSAGE]->(user_msg)
        CREATE (s)-[:HAS_MESSAGE]->(assistant_msg)
        SET s.message_count = COALESCE(s.message_count, 0) + 2,
            s.last_activity = $timestamp
        
        WITH user_msg, assistant_msg
        
        // Link to case
        MATCH (c:Case {case_id: $case_id})
        CREATE (user_msg)-[:BELONGS_TO_CASE]->(c)
        CREATE (assistant_msg)-[:BELONGS_TO_CASE]->(c)
        
        RETURN user_msg, assistant_msg
        """
        
        result = await tx.run(query, {
            "user_msg_id": user_msg_id,
            "assistant_msg_id": assistant_msg_id,
            "session_id": session_id,
            "case_id": case_id,
            "user_message": user_message,
            "assistant_response": assistant_response,
            "timestamp": timestamp,
            "user_id": user_id,
            "metadata": metadata_str
        })
        
        messages = []
        async for record in result:
            messages.append(dict(record["user_msg"]))
            messages.append(dict(record["assistant_msg"]))
        
        return messages
    
    # Optimized Query Operations
    
    async def get_user_cases_with_sessions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False
    ) -> List[dict]:
        """
        Get user cases with their chat sessions in a single query
        
        Args:
            user_id: User ID
            limit: Maximum number of cases
            offset: Number of cases to skip
            include_archived: Whether to include archived cases
            
        Returns:
            List of cases with chat sessions
        """
        status_filter = "" if include_archived else "AND c.status <> 'archived'"
        
        query = f"""
        MATCH (u:User {{user_id: $user_id}})-[:OWNS]->(c:Case)
        WHERE 1=1 {status_filter}
        
        // Get chat sessions for each case
        OPTIONAL MATCH (c)-[:HAS_CHAT_SESSION]->(s:ChatSession)
        
        WITH c, u, COLLECT(s) as sessions
        ORDER BY c.created_at DESC
        SKIP $offset
        LIMIT $limit
        
        RETURN c, u.user_id as user_id, sessions
        """
        
        driver = await self._async_driver
        async with driver.session() as session:
            result = await session.run(query, {
                "user_id": user_id,
                "limit": limit,
                "offset": offset
            })
            
            cases = []
            async for record in result:
                case_data = dict(record["c"])
                case_data["user_id"] = record["user_id"]
                case_data["chat_sessions"] = [dict(s) for s in record["sessions"]]
                cases.append(case_data)
            
            return cases
    
    # Connection retry logic
    
    async def _execute_with_retry(
        self,
        operation: Callable,
        max_retries: int = 3,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute operation with retry logic for transient failures
        
        Args:
            operation: Operation to execute
            max_retries: Maximum number of retries
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Operation result
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await operation(*args, **kwargs)
            except (ServiceUnavailable, SessionExpired) as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Transient error on attempt {attempt + 1}/{max_retries}: {str(e)}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Max retries reached. Last error: {str(e)}")
        
        raise last_error
    
    # Legacy method compatibility
    
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
        Legacy method for backward compatibility
        Creates two messages (user and assistant) in a single transaction
        """
        messages = await self.create_conversation_messages(
            session_id=session_id,
            case_id=case_id,
            user_message=user_message,
            assistant_response=doctor_response,
            user_id=user_id,
            metadata={
                "doctor_type": doctor_type,
                **(metadata or {})
            }
        )
        
        # Return the assistant message for compatibility
        return messages[1] if len(messages) > 1 else messages[0]
    
    # Sync wrappers for backward compatibility
    
    def create_case(self, case_data: dict) -> dict:
        """Sync wrapper for create_case"""
        return self.create_case_sync(case_data)
    
    def get_case(self, case_id: str, user_id: str) -> Optional[dict]:
        """Get a case by ID (sync wrapper)"""
        with self._sync_driver.session() as session:
            query = """
            MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_id: $case_id})
            WHERE c.status <> 'archived'
            RETURN c, u.user_id AS user_id
            """
            
            result = session.run(query, {
                "case_id": case_id,
                "user_id": user_id
            })
            record = result.single()
            
            if record:
                case_data = dict(record["c"])
                case_data["user_id"] = record["user_id"]
                return case_data
            return None