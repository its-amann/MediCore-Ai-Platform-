"""
Neo4j Storage Service for Collaboration Microservice
Handles all database operations for collaboration rooms, participants, messages, and AI sessions
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from neo4j.exceptions import Neo4jError

from ..models import (
    RoomType, RoomStatus, MessageType, NotificationType,
    UserRole, UserType, RequestStatus, NotificationPriority
)

logger = logging.getLogger(__name__)


class CollaborationStorage:
    """
    Neo4j storage service for collaboration functionality
    """
    
    def __init__(self, neo4j_client=None):
        """
        Initialize Neo4j storage with optional client injection
        
        Args:
            neo4j_client: Optional Neo4j client instance. If not provided,
                         will create a direct connection.
        """
        if neo4j_client:
            self.neo4j_client = neo4j_client
            self.client = neo4j_client  # Keep client attribute for compatibility
            self.db_client = neo4j_client  # Add db_client attribute for test compatibility
            self.driver = neo4j_client.driver if hasattr(neo4j_client, 'driver') else None
            self._use_direct_connection = False
            logger.info("Collaboration Neo4j storage initialized with provided client")
        else:
            # Create direct connection
            from neo4j import GraphDatabase
            from ..config import settings
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            self.neo4j_client = None
            self.client = None
            self.db_client = None
            self._use_direct_connection = True
            logger.info(f"Collaboration Neo4j storage initialized with direct connection to {settings.NEO4J_URI}")
    
    def close(self):
        """Close the database connection"""
        if self._use_direct_connection and self.driver:
            self.driver.close()
            logger.info("Closed direct Neo4j connection")
    
    async def initialize_constraints(self):
        """Initialize database constraints and indexes for collaboration entities"""
        try:
            # Check if we have a connection
            if self._use_direct_connection:
                # Using direct driver connection
                session = self.driver.session()
            elif self.client and hasattr(self.client, 'get_session'):
                # Using unified Neo4j client
                session_context = self.client.get_session()
                session = session_context.__enter__()
            elif self.neo4j_client and hasattr(self.neo4j_client, 'driver'):
                # Using wrapper with sync driver - run in executor to avoid blocking
                import asyncio
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self._initialize_constraints_sync)
            else:
                raise Exception("No valid Neo4j connection available")
            
            try:
                # Create constraints
                constraints = [
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Room) REQUIRE r.room_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Message) REQUIRE m.message_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Notification) REQUIRE n.notification_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (jr:JoinRequest) REQUIRE jr.request_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (ai:AISession) REQUIRE ai.session_id IS UNIQUE"
                ]
                
                for constraint in constraints:
                    try:
                        session.run(constraint)
                        logger.debug(f"Created constraint: {constraint}")
                    except Neo4jError as e:
                        if "already exists" not in str(e).lower() and "equivalent" not in str(e).lower():
                            logger.error(f"Error creating constraint: {str(e)}")
                
                # Create indexes
                indexes = [
                    "CREATE INDEX IF NOT EXISTS FOR (r:Room) ON (r.status)",
                    "CREATE INDEX IF NOT EXISTS FOR (r:Room) ON (r.room_type)",
                    "CREATE INDEX IF NOT EXISTS FOR (m:Message) ON (m.room_id)",
                    "CREATE INDEX IF NOT EXISTS FOR (m:Message) ON (m.timestamp)",
                    "CREATE INDEX IF NOT EXISTS FOR (n:Notification) ON (n.user_id)",
                    "CREATE INDEX IF NOT EXISTS FOR (n:Notification) ON (n.is_read)",
                    "CREATE INDEX IF NOT EXISTS FOR (jr:JoinRequest) ON (jr.status)",
                    "CREATE INDEX IF NOT EXISTS FOR (ua:UserActivity) ON (ua.timestamp)"
                ]
                
                for index in indexes:
                    try:
                        session.run(index)
                        logger.debug(f"Created index: {index}")
                    except Neo4jError as e:
                        if "already exists" not in str(e).lower() and "equivalent" not in str(e).lower():
                            logger.error(f"Error creating index: {str(e)}")
                
                logger.info("Collaboration database constraints and indexes initialized")
            finally:
                # Clean up session
                if self._use_direct_connection:
                    session.close()
                elif self.client and hasattr(self.client, 'get_session'):
                    session_context.__exit__(None, None, None)
                
        except Exception as e:
            logger.error(f"Failed to initialize collaboration database: {str(e)}")
            raise
    
    def _initialize_constraints_sync(self):
        """Synchronous version of initialize_constraints for use with sync drivers"""
        try:
            # Use the sync driver directly
            if self.neo4j_client and hasattr(self.neo4j_client, 'driver'):
                session = self.neo4j_client.driver.session()
            elif self.driver:
                session = self.driver.session()
            else:
                raise Exception("No valid Neo4j driver available for sync initialization")
            
            try:
                # Create constraints
                constraints = [
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Room) REQUIRE r.room_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Message) REQUIRE m.message_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Notification) REQUIRE n.notification_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (jr:JoinRequest) REQUIRE jr.request_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (ai:AISession) REQUIRE ai.session_id IS UNIQUE"
                ]
                
                for constraint in constraints:
                    try:
                        session.run(constraint)
                        logger.debug(f"Created constraint: {constraint}")
                    except Neo4jError as e:
                        if "already exists" not in str(e).lower() and "equivalent" not in str(e).lower():
                            logger.error(f"Error creating constraint: {str(e)}")
                
                # Create indexes
                indexes = [
                    "CREATE INDEX IF NOT EXISTS FOR (r:Room) ON (r.status)",
                    "CREATE INDEX IF NOT EXISTS FOR (r:Room) ON (r.room_type)",
                    "CREATE INDEX IF NOT EXISTS FOR (m:Message) ON (m.room_id)",
                    "CREATE INDEX IF NOT EXISTS FOR (m:Message) ON (m.timestamp)",
                    "CREATE INDEX IF NOT EXISTS FOR (n:Notification) ON (n.user_id)",
                    "CREATE INDEX IF NOT EXISTS FOR (n:Notification) ON (n.is_read)",
                    "CREATE INDEX IF NOT EXISTS FOR (jr:JoinRequest) ON (jr.status)",
                    "CREATE INDEX IF NOT EXISTS FOR (ua:UserActivity) ON (ua.timestamp)"
                ]
                
                for index in indexes:
                    try:
                        session.run(index)
                        logger.debug(f"Created index: {index}")
                    except Neo4jError as e:
                        if "already exists" not in str(e).lower() and "equivalent" not in str(e).lower():
                            logger.error(f"Error creating index: {str(e)}")
                
                logger.info("Collaboration database constraints and indexes initialized (sync)")
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to initialize collaboration database (sync): {str(e)}")
            raise
    
    def _prepare_data_for_neo4j(self, data: dict) -> dict:
        """Prepare data for Neo4j by converting complex types to strings"""
        prepared = {}
        for key, value in data.items():
            if value is None:
                continue
            elif isinstance(value, (dict, list)):
                prepared[key] = json.dumps(value)
            elif isinstance(value, datetime):
                prepared[key] = value.isoformat()
            elif isinstance(value, (RoomType, RoomStatus, MessageType, NotificationType, 
                                  UserRole, UserType, RequestStatus, NotificationPriority)):
                prepared[key] = value.value
            else:
                prepared[key] = value
        return prepared
    
    def _parse_neo4j_data(self, data: dict) -> dict:
        """Parse data from Neo4j by converting JSON strings back to their original types"""
        parsed = {}
        json_fields = ['settings', 'tags', 'created_by', 'class_materials', 'active_users']
        
        for key, value in data.items():
            # Handle field name changes
            if key == 'type':
                # Map old 'type' field to new 'room_type' field and ensure lowercase
                if isinstance(value, str):
                    # Convert uppercase enum values to lowercase to match the enum definition
                    parsed['room_type'] = value.lower()
                else:
                    parsed['room_type'] = value
            elif key == 'room_type' and isinstance(value, str):
                # Ensure room_type is always lowercase for enum compatibility
                parsed['room_type'] = value.lower()
            elif key in json_fields and isinstance(value, str):
                try:
                    parsed[key] = json.loads(value)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON field {key}: {value}")
                    # Set appropriate default based on field
                    if key == 'tags' or key == 'class_materials' or key == 'active_users':
                        parsed[key] = []
                    elif key == 'settings' or key == 'created_by':
                        parsed[key] = {}
                    else:
                        parsed[key] = value
            else:
                parsed[key] = value
        return parsed
    
    async def run_query(self, query: str, params: dict = None):
        """Execute a read query using the Neo4j client"""
        try:
            if self._use_direct_connection:
                # Use direct driver connection like cases microservice
                with self.driver.session() as session:
                    result = session.run(query, params or {})
                    return [record.data() for record in result]
            else:
                # Call the unified client's async method
                result = await self.client.run_query(query, params or {})
                return result
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
    
    async def run_write_query(self, query: str, params: dict = None):
        """Execute a write query using the Neo4j client"""
        try:
            if self._use_direct_connection:
                # Use direct driver connection like cases microservice
                with self.driver.session() as session:
                    result = session.run(query, params or {})
                    return [record.data() for record in result]
            else:
                # Call the unified client's async method
                result = await self.client.run_write_query(query, params or {})
                return result
        except Exception as e:
            logger.error(f"Write query execution error: {str(e)}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
    
    async def create_room(self, room_data: dict) -> dict:
        """
        Create a new collaboration room
        
        Args:
            room_data: Room information dictionary
            
        Returns:
            Created room data
        """
        try:
            # Extract creator_id before preparing data
            created_by = room_data.get("created_by", {})
            logger.info(f"created_by value: {created_by}, type: {type(created_by)}")
            
            if isinstance(created_by, str):
                # If it's already a string, it's likely the user_id
                creator_id = created_by
            elif isinstance(created_by, dict):
                creator_id = created_by.get("user_id")
            else:
                logger.error(f"Unexpected created_by type: {type(created_by)}")
                creator_id = None
            
            # Prepare data
            prepared_data = self._prepare_data_for_neo4j(room_data)
            
            # First check if user exists
            check_user_query = "MATCH (u:User {user_id: $creator_id}) RETURN u"
            user_result = await self.run_query(check_user_query, {"creator_id": creator_id})
            if not user_result:
                logger.error(f"User with ID {creator_id} not found in database")
                # Try to find user by email instead
                email_query = "MATCH (u:User) WHERE u.email CONTAINS 'test' RETURN u.user_id, u.email"
                test_users = await self.run_query(email_query, {})
                logger.info(f"Found test users: {test_users}")
                raise Exception(f"User with ID {creator_id} not found")
            
            query = """
            CREATE (r:Room)
            SET r += $props
            WITH r
            MATCH (u:User {user_id: $creator_id})
            CREATE (u)-[:CREATED]->(r)
            CREATE (u)-[:MODERATES]->(r)
            CREATE (u)-[:MEMBER_OF {
                role: 'host',
                joined_at: $created_at
            }]->(r)
            RETURN r
            """
            
            # Ensure created_at is a string for the parameter
            created_at_str = prepared_data.get("created_at")
            if isinstance(created_at_str, datetime):
                created_at_str = created_at_str.isoformat()
                
            params = {
                "props": prepared_data,
                "creator_id": creator_id,
                "created_at": created_at_str
            }
            
            logger.info(f"Running create room query with params: {params}")
            result = await self.run_write_query(query, params)
            
            if result:
                logger.info(f"Query result type: {type(result)}")
                logger.info(f"Query result length: {len(result)}")
                logger.info(f"First result type: {type(result[0])}")
                logger.info(f"First result: {result[0]}")
                
                # Check if result[0] is a Record object
                if hasattr(result[0], 'data'):
                    room = dict(result[0].data()["r"])
                elif hasattr(result[0], '__getitem__'):
                    room = dict(result[0]["r"])
                else:
                    logger.error(f"Unexpected result format: {type(result[0])}")
                    raise Exception(f"Unexpected result format: {type(result[0])}")
                    
                logger.info(f"Created room: {room['room_id']}")
                # Parse Neo4j data to convert JSON strings back to proper types
                parsed_room = self._parse_neo4j_data(room)
                return parsed_room
            else:
                logger.error(f"Query returned no results. Query: {query}")
                logger.error(f"Params: {params}")
                raise Exception("Failed to create room")
                
        except Exception as e:
            logger.error(f"Error creating room: {str(e)}")
            raise
    
    async def update_room(self, room_id: str, update_data: dict) -> Optional[dict]:
        """
        Update room information
        
        Args:
            room_id: Room ID to update
            update_data: Dictionary with fields to update
            
        Returns:
            Updated room data or None
        """
        try:
            # Prepare update data
            prepared_data = self._prepare_data_for_neo4j(update_data)
            prepared_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Build SET clause dynamically
            set_clauses = [f"r.{key} = ${key}" for key in prepared_data.keys()]
            set_clause = "SET " + ", ".join(set_clauses)
            
            query = f"""
            MATCH (r:Room {{room_id: $room_id}})
            {set_clause}
            RETURN r
            """
            
            params = {"room_id": room_id}
            params.update(prepared_data)
            
            result = await self.run_query(query, params)
            
            if result:
                room = dict(result[0]["r"])
                logger.info(f"Updated room: {room_id}")
                return room
            else:
                logger.warning(f"Room not found: {room_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error updating room: {str(e)}")
            return None
    
    async def delete_room(self, room_id: str, user_id: str) -> bool:
        """
        Delete a room (only by creator or moderator)
        
        Args:
            room_id: Room ID to delete
            user_id: User ID performing deletion
            
        Returns:
            Success status
        """
        try:
            # Verify user is creator or moderator
            query = """
            MATCH (u:User {user_id: $user_id})-[rel:CREATED|MODERATES]->(r:Room {room_id: $room_id})
            WITH r
            // Delete all relationships and messages first
            OPTIONAL MATCH (r)-[rm:HAS_MESSAGE]->(m:Message)
            DETACH DELETE m
            WITH r
            OPTIONAL MATCH (r)<-[jr:REQUESTED_JOIN]-(ju:User)
            DELETE jr
            WITH r
            // Delete the room
            DETACH DELETE r
            RETURN true as success
            """
            
            result = await self.run_write_query(query, {
                "room_id": room_id,
                "user_id": user_id
            })
            
            if result:
                logger.info(f"Deleted room: {room_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting room: {str(e)}")
            return False
    
    async def add_participant(self, room_id: str, user_id: str, username: str, role: str = "participant") -> bool:
        """
        Add a participant to a room
        
        Args:
            room_id: Room ID
            user_id: User ID to add
            username: Username (for display purposes)
            role: User role in the room
            
        Returns:
            Success status
        """
        try:
            query = """
            MATCH (u:User {user_id: $user_id})
            MATCH (r:Room {room_id: $room_id})
            WHERE NOT EXISTS((u)-[:MEMBER_OF]->(r))
            CREATE (u)-[:MEMBER_OF {
                role: $role,
                joined_at: $joined_at,
                is_active: true
            }]->(r)
            SET r.current_participants = r.current_participants + 1
            RETURN u, r
            """
            
            result = await self.run_write_query(query, {
                "room_id": room_id,
                "user_id": user_id,
                "role": role,
                "joined_at": datetime.utcnow().isoformat()
            })
            
            if result:
                logger.info(f"Added participant {user_id} to room {room_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error adding participant: {str(e)}")
            return False
    
    async def remove_participant(self, room_id: str, user_id: str) -> bool:
        """
        Remove a participant from a room
        
        Args:
            room_id: Room ID
            user_id: User ID to remove
            
        Returns:
            Success status
        """
        try:
            query = """
            MATCH (u:User {user_id: $user_id})-[rel:MEMBER_OF]->(r:Room {room_id: $room_id})
            DELETE rel
            SET r.current_participants = CASE 
                WHEN r.current_participants > 0 THEN r.current_participants - 1 
                ELSE 0 
            END
            RETURN true as success
            """
            
            result = await self.run_write_query(query, {
                "room_id": room_id,
                "user_id": user_id
            })
            
            if result:
                logger.info(f"Removed participant {user_id} from room {room_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing participant: {str(e)}")
            return False
    
    async def store_message(self, message_data: dict) -> dict:
        """
        Store a message in a room
        
        Args:
            message_data: Message information
            
        Returns:
            Stored message data
        """
        try:
            prepared_data = self._prepare_data_for_neo4j(message_data)
            
            query = """
            CREATE (m:Message)
            SET m += $props
            WITH m
            MATCH (r:Room {room_id: $room_id})
            CREATE (r)-[:HAS_MESSAGE]->(m)
            WITH m, r
            MATCH (u:User {user_id: $sender_id})
            CREATE (u)-[:SENT]->(m)
            SET r.last_activity = $timestamp
            RETURN m
            """
            
            params = {
                "props": prepared_data,
                "room_id": message_data["room_id"],
                "sender_id": message_data["sender_id"],
                "timestamp": prepared_data.get("timestamp")
            }
            
            result = await self.run_write_query(query, params)
            
            if result:
                message = dict(result[0]["m"])
                logger.info(f"Stored message: {message['message_id']}")
                return message
            else:
                raise Exception("Failed to store message")
                
        except Exception as e:
            logger.error(f"Error storing message: {str(e)}")
            raise
    
    async def get_room_messages(
        self,
        room_id: str,
        limit: int = 50,
        offset: int = 0,
        before_timestamp: Optional[str] = None
    ) -> List[dict]:
        """
        Get messages from a room
        
        Args:
            room_id: Room ID
            limit: Maximum messages to retrieve
            offset: Number of messages to skip
            before_timestamp: Get messages before this timestamp
            
        Returns:
            List of messages
        """
        try:
            params = {
                "room_id": room_id,
                "limit": limit,
                "offset": offset
            }
            
            timestamp_filter = ""
            if before_timestamp:
                timestamp_filter = "AND m.timestamp < $before_timestamp"
                params["before_timestamp"] = before_timestamp
            
            query = f"""
            MATCH (r:Room {{room_id: $room_id}})-[:HAS_MESSAGE]->(m:Message)
            {timestamp_filter}
            WITH m
            MATCH (u:User)-[:SENT]->(m)
            RETURN m, u.username as sender_name, u.user_id as sender_id
            ORDER BY m.timestamp DESC
            SKIP $offset
            LIMIT $limit
            """
            
            result = await self.run_query(query, params)
            
            messages = []
            for record in result:
                message = dict(record["m"])
                message["sender_name"] = record["sender_name"]
                message["sender_id"] = record["sender_id"]
                messages.append(message)
            
            # Reverse to get chronological order
            messages.reverse()
            return messages
            
        except Exception as e:
            logger.error(f"Error getting room messages: {str(e)}")
            return []
    
    async def create_join_request(self, request_data: dict) -> dict:
        """
        Create a join request for a private room
        
        Args:
            request_data: Join request information
            
        Returns:
            Created join request
        """
        try:
            prepared_data = self._prepare_data_for_neo4j(request_data)
            
            query = """
            CREATE (jr:JoinRequest)
            SET jr += $props
            WITH jr
            MATCH (u:User {user_id: $user_id})
            MATCH (r:Room {room_id: $room_id})
            CREATE (u)-[:REQUESTED_JOIN]->(r)
            CREATE (jr)-[:FOR_ROOM]->(r)
            CREATE (u)-[:MADE_REQUEST]->(jr)
            RETURN jr
            """
            
            params = {
                "props": prepared_data,
                "user_id": request_data["user_id"],
                "room_id": request_data["room_id"]
            }
            
            result = await self.run_write_query(query, params)
            
            if result:
                request = dict(result[0]["jr"])
                logger.info(f"Created join request: {request['request_id']}")
                return request
            else:
                raise Exception("Failed to create join request")
                
        except Exception as e:
            logger.error(f"Error creating join request: {str(e)}")
            raise
    
    async def process_join_request(
        self,
        request_id: str,
        processed_by: str,
        status: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Process a join request (approve/reject)
        
        Args:
            request_id: Request ID
            processed_by: User ID processing the request
            status: New status (approved/rejected)
            reason: Optional reason for rejection
            
        Returns:
            Success status
        """
        try:
            query = """
            MATCH (jr:JoinRequest {request_id: $request_id})
            MATCH (jr)-[:FOR_ROOM]->(r:Room)
            MATCH (u:User)-[:MADE_REQUEST]->(jr)
            SET jr.status = $status,
                jr.processed_at = $processed_at,
                jr.processed_by = $processed_by,
                jr.reason = $reason
            WITH jr, r, u
            WHERE $status = 'approved'
            CREATE (u)-[:MEMBER_OF {
                role: 'participant',
                joined_at: $processed_at
            }]->(r)
            SET r.current_participants = r.current_participants + 1
            RETURN jr
            """
            
            result = await self.run_write_query(query, {
                "request_id": request_id,
                "processed_by": processed_by,
                "status": status,
                "processed_at": datetime.utcnow().isoformat(),
                "reason": reason
            })
            
            if result:
                logger.info(f"Processed join request {request_id}: {status}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error processing join request: {str(e)}")
            return False
    
    async def track_user_activity(
        self,
        user_id: str,
        room_id: str,
        activity_type: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Track user activity in a room
        
        Args:
            user_id: User ID
            room_id: Room ID
            activity_type: Type of activity
            metadata: Additional activity data
            
        Returns:
            Success status
        """
        try:
            activity_data = {
                "activity_id": str(uuid.uuid4()),
                "user_id": user_id,
                "room_id": room_id,
                "activity_type": activity_type,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": json.dumps(metadata) if metadata else "{}"
            }
            
            query = """
            CREATE (ua:UserActivity)
            SET ua += $props
            WITH ua
            MATCH (u:User {user_id: $user_id})
            MATCH (r:Room {room_id: $room_id})
            CREATE (u)-[:PERFORMED]->(ua)
            CREATE (ua)-[:IN_ROOM]->(r)
            // Update user's last seen in room
            WITH u, r
            MATCH (u)-[rel:MEMBER_OF]->(r)
            SET rel.last_seen = $timestamp
            RETURN true as success
            """
            
            result = await self.run_write_query(query, {
                "props": activity_data,
                "user_id": user_id,
                "room_id": room_id,
                "timestamp": activity_data["timestamp"]
            })
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error tracking user activity: {str(e)}")
            return False
    
    async def store_notification(self, notification_data: dict) -> dict:
        """
        Store a notification
        
        Args:
            notification_data: Notification information
            
        Returns:
            Stored notification
        """
        try:
            prepared_data = self._prepare_data_for_neo4j(notification_data)
            
            query = """
            CREATE (n:Notification)
            SET n += $props
            WITH n
            MATCH (u:User {user_id: $user_id})
            CREATE (u)-[:HAS_NOTIFICATION]->(n)
            RETURN n
            """
            
            params = {
                "props": prepared_data,
                "user_id": notification_data["user_id"]
            }
            
            result = await self.run_write_query(query, params)
            
            if result:
                notification = dict(result[0]["n"])
                logger.info(f"Stored notification: {notification['notification_id']}")
                return notification
            else:
                raise Exception("Failed to store notification")
                
        except Exception as e:
            logger.error(f"Error storing notification: {str(e)}")
            raise
    
    async def create_ai_session(self, session_data: dict) -> dict:
        """
        Create an AI assistant session for a room
        
        Args:
            session_data: AI session information
            
        Returns:
            Created AI session
        """
        try:
            prepared_data = self._prepare_data_for_neo4j(session_data)
            
            query = """
            CREATE (ai:AISession)
            SET ai += $props
            WITH ai
            MATCH (r:Room {room_id: $room_id})
            CREATE (r)-[:HAS_AI_SESSION]->(ai)
            RETURN ai
            """
            
            params = {
                "props": prepared_data,
                "room_id": session_data["room_id"]
            }
            
            result = await self.run_write_query(query, params)
            
            if result:
                ai_session = dict(result[0]["ai"])
                logger.info(f"Created AI session: {ai_session['session_id']}")
                return ai_session
            else:
                raise Exception("Failed to create AI session")
                
        except Exception as e:
            logger.error(f"Error creating AI session: {str(e)}")
            raise
    
    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """
        Get user details by ID
        
        Args:
            user_id: User ID
            
        Returns:
            User data dictionary or None if not found
        """
        try:
            query = """
            MATCH (u:User {user_id: $user_id})
            RETURN u
            """
            
            result = await self.run_query(query, {"user_id": user_id})
            
            if result:
                user_data = dict(result[0]["u"])
                return user_data
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None
    
    async def is_room_member(self, room_id: str, user_id: str) -> bool:
        """
        Check if a user is a member of a room
        
        Args:
            room_id: Room ID
            user_id: User ID
            
        Returns:
            True if user is a member, False otherwise
        """
        try:
            query = """
            MATCH (u:User {user_id: $user_id})-[:MEMBER_OF]->(r:Room {room_id: $room_id})
            RETURN COUNT(u) > 0 as is_member
            """
            
            result = await self.run_query(query, {"room_id": room_id, "user_id": user_id})
            
            if result:
                return result[0]["is_member"]
            return False
            
        except Exception as e:
            logger.error(f"Error checking room membership: {str(e)}")
            return False
    
    async def get_room_participants(self, room_id: str) -> List[dict]:
        """
        Get all participants in a room
        
        Args:
            room_id: Room ID
            
        Returns:
            List of participants with their roles
        """
        try:
            query = """
            MATCH (u:User)-[rel:MEMBER_OF]->(r:Room {room_id: $room_id})
            RETURN u, rel.role as role, rel.joined_at as joined_at, rel.last_seen as last_seen
            ORDER BY rel.joined_at
            """
            
            result = await self.run_query(query, {"room_id": room_id})
            
            participants = []
            for record in result:
                user_data = dict(record["u"])
                participant = {
                    "user_id": user_data.get("user_id"),
                    "username": user_data.get("username"),
                    "role": record["role"],
                    "joined_at": record["joined_at"],
                    "last_seen": record["last_seen"]
                }
                participants.append(participant)
            
            return participants
            
        except Exception as e:
            logger.error(f"Error getting room participants: {str(e)}")
            return []
    
    async def get_user_rooms(
        self,
        user_id: str,
        status_filter: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """
        Get all rooms a user is a member of
        
        Args:
            user_id: User ID
            status_filter: Optional list of room statuses to filter
            limit: Maximum rooms to retrieve
            offset: Number of rooms to skip
            
        Returns:
            List of rooms
        """
        try:
            params = {
                "user_id": user_id,
                "limit": limit,
                "offset": offset
            }
            
            status_clause = ""
            if status_filter:
                status_clause = "AND r.status IN $statuses"
                params["statuses"] = status_filter
            
            query = f"""
            MATCH (u:User {{user_id: $user_id}})-[rel:MEMBER_OF]->(r:Room)
            WHERE r.status <> 'archived' {status_clause}
            RETURN r, rel.role as user_role, rel.joined_at as joined_at
            ORDER BY r.last_activity DESC, r.created_at DESC
            SKIP $offset
            LIMIT $limit
            """
            
            result = await self.run_query(query, params)
            
            rooms = []
            for record in result:
                room = dict(record["r"])
                room["user_role"] = record["user_role"]
                room["user_joined_at"] = record["joined_at"]
                rooms.append(room)
            
            return rooms
            
        except Exception as e:
            logger.error(f"Error getting user rooms: {str(e)}")
            return []
    
    async def get_rooms(
        self,
        room_type: Optional[str] = None,
        status: Optional[str] = None,
        is_private: Optional[bool] = None
    ) -> List[dict]:
        """
        Get all rooms with optional filters
        
        Args:
            room_type: Filter by room type
            status: Filter by room status
            is_private: Filter by privacy setting
            
        Returns:
            List of room dictionaries
        """
        try:
            # Build the WHERE clause based on filters
            where_clauses = []
            params = {}
            
            if room_type:
                where_clauses.append("r.room_type = $room_type")
                params["room_type"] = room_type
            
            if status:
                where_clauses.append("r.status = $status")
                params["status"] = status
            
            if is_private is not None:
                where_clauses.append("r.is_private = $is_private")
                params["is_private"] = is_private
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"""
            MATCH (r:Room)
            WHERE {where_clause}
            OPTIONAL MATCH (r)<-[:CREATED]-(creator:User)
            OPTIONAL MATCH (r)<-[:MEMBER_OF]-(member:User)
            WITH r, creator, COLLECT(DISTINCT 
                CASE WHEN member.user_id IS NOT NULL AND member.username IS NOT NULL 
                THEN {{
                    user_id: member.user_id,
                    username: member.username
                }} 
                ELSE NULL END
            ) AS members_raw
            WITH r, creator, [m IN members_raw WHERE m IS NOT NULL] AS members
            RETURN r {{
                .*,
                created_by: {{
                    user_id: creator.user_id,
                    username: creator.username
                }},
                active_users: members,
                participant_count: SIZE(members)
            }} AS room
            ORDER BY r.created_at DESC
            """
            
            result = await self.run_query(query, params)
            
            if result:
                rooms = []
                for record in result:
                    room_data = record.get("room")
                    if room_data:
                        # Ensure all required fields are present
                        room_data["room_id"] = room_data.get("room_id", "")
                        room_data["name"] = room_data.get("name", "")
                        room_data["room_type"] = room_data.get("room_type", "CASE_DISCUSSION")
                        room_data["status"] = room_data.get("status", "active")
                        room_data["is_private"] = room_data.get("is_private", False)
                        room_data["created_at"] = room_data.get("created_at", datetime.utcnow().isoformat())
                        room_data["updated_at"] = room_data.get("updated_at", datetime.utcnow().isoformat())
                        # Parse Neo4j data to convert JSON strings back to proper types
                        parsed_room = self._parse_neo4j_data(room_data)
                        rooms.append(parsed_room)
                
                return rooms
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting rooms: {str(e)}")
            return []
    
    async def get_room_by_id(self, room_id: str) -> Optional[dict]:
        """
        Get room details by ID
        
        Args:
            room_id: Room ID
            
        Returns:
            Room data or None
        """
        try:
            query = """
            MATCH (r:Room {room_id: $room_id})
            OPTIONAL MATCH (u:User)-[:CREATED]->(r)
            RETURN r, u.username as creator_username, u.user_id as creator_id
            """
            
            result = await self.run_query(query, {"room_id": room_id})
            
            if result:
                room = dict(result[0]["r"])
                room["creator_username"] = result[0]["creator_username"]
                room["creator_id"] = result[0]["creator_id"]
                # Parse Neo4j data to convert JSON strings back to proper types
                parsed_room = self._parse_neo4j_data(room)
                logger.info(f"Retrieved room data: {parsed_room}")
                return parsed_room
            return None
            
        except Exception as e:
            logger.error(f"Error getting room: {str(e)}")
            return None
    
    async def update_user_role_in_room(
        self,
        room_id: str,
        user_id: str,
        new_role: str,
        updated_by: str
    ) -> bool:
        """
        Update user's role in a room
        
        Args:
            room_id: Room ID
            user_id: User ID to update
            new_role: New role for the user
            updated_by: User ID performing the update
            
        Returns:
            Success status
        """
        try:
            # Verify updater has permission (must be host or co-host)
            query = """
            MATCH (updater:User {user_id: $updated_by})-[updater_rel:MEMBER_OF]->(r:Room {room_id: $room_id})
            WHERE updater_rel.role IN ['host', 'co_host']
            MATCH (u:User {user_id: $user_id})-[rel:MEMBER_OF]->(r)
            SET rel.role = $new_role,
                rel.role_updated_at = $updated_at,
                rel.role_updated_by = $updated_by
            WITH u, r, $new_role as new_role
            WHERE new_role = 'co_host'
            CREATE (u)-[:MODERATES]->(r)
            RETURN true as success
            """
            
            result = await self.run_write_query(query, {
                "room_id": room_id,
                "user_id": user_id,
                "new_role": new_role,
                "updated_by": updated_by,
                "updated_at": datetime.utcnow().isoformat()
            })
            
            if result:
                logger.info(f"Updated user {user_id} role to {new_role} in room {room_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating user role: {str(e)}")
            return False
    
    async def get_pending_join_requests(self, room_id: str) -> List[dict]:
        """
        Get all pending join requests for a room
        
        Args:
            room_id: Room ID
            
        Returns:
            List of pending join requests
        """
        try:
            query = """
            MATCH (jr:JoinRequest {status: 'pending'})-[:FOR_ROOM]->(r:Room {room_id: $room_id})
            MATCH (u:User)-[:MADE_REQUEST]->(jr)
            RETURN jr, u.username as requester_name, u.user_id as requester_id
            ORDER BY jr.requested_at DESC
            """
            
            result = await self.run_query(query, {"room_id": room_id})
            
            requests = []
            for record in result:
                request = dict(record["jr"])
                request["requester_name"] = record["requester_name"]
                request["requester_id"] = record["requester_id"]
                requests.append(request)
            
            return requests
            
        except Exception as e:
            logger.error(f"Error getting pending join requests: {str(e)}")
            return []
    
    async def search_public_rooms(
        self,
        search_query: Optional[str] = None,
        room_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[dict]:
        """
        Search for public rooms
        
        Args:
            search_query: Optional search text
            room_type: Optional room type filter
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of public rooms
        """
        try:
            params = {
                "limit": limit,
                "offset": offset
            }
            
            where_clauses = ["r.is_public = true", "r.status = 'active'"]
            
            if search_query:
                where_clauses.append("(toLower(r.name) CONTAINS toLower($search_query) OR toLower(r.description) CONTAINS toLower($search_query))")
                params["search_query"] = search_query
            
            if room_type:
                where_clauses.append("r.room_type = $room_type")
                params["room_type"] = room_type
            
            where_clause = " AND ".join(where_clauses)
            
            query = f"""
            MATCH (r:Room)
            WHERE {where_clause}
            OPTIONAL MATCH (u:User)-[:CREATED]->(r)
            OPTIONAL MATCH (r)<-[rel:MEMBER_OF]-()
            WITH r, u.username as creator_username, COUNT(DISTINCT rel) as participant_count
            RETURN r, creator_username, participant_count
            ORDER BY r.current_participants DESC, r.created_at DESC
            SKIP $offset
            LIMIT $limit
            """
            
            result = await self.run_query(query, params)
            
            rooms = []
            for record in result:
                room = dict(record["r"])
                room["creator_username"] = record["creator_username"]
                room["participant_count"] = record["participant_count"]
                rooms.append(room)
            
            return rooms
            
        except Exception as e:
            logger.error(f"Error searching public rooms: {str(e)}")
            return []
    
    async def get_room_statistics(self, room_id: str) -> dict:
        """
        Get statistics for a room
        
        Args:
            room_id: Room ID
            
        Returns:
            Dictionary with room statistics
        """
        try:
            query = """
            MATCH (r:Room {room_id: $room_id})
            OPTIONAL MATCH (r)-[:HAS_MESSAGE]->(m:Message)
            OPTIONAL MATCH (r)<-[:MEMBER_OF]-(u:User)
            OPTIONAL MATCH (r)-[:HAS_AI_SESSION]->(ai:AISession)
            RETURN 
                r.room_id as room_id,
                COUNT(DISTINCT m) as total_messages,
                COUNT(DISTINCT u) as total_participants,
                COUNT(DISTINCT ai) as ai_sessions,
                r.created_at as created_at,
                r.last_activity as last_activity
            """
            
            result = await self.run_query(query, {"room_id": room_id})
            
            if result:
                return dict(result[0])
            return {
                "room_id": room_id,
                "total_messages": 0,
                "total_participants": 0,
                "ai_sessions": 0
            }
            
        except Exception as e:
            logger.error(f"Error getting room statistics: {str(e)}")
            return {}
    
    async def mark_notifications_as_read(
        self,
        user_id: str,
        notification_ids: List[str]
    ) -> int:
        """
        Mark multiple notifications as read
        
        Args:
            user_id: User ID
            notification_ids: List of notification IDs to mark as read
            
        Returns:
            Number of notifications marked as read
        """
        try:
            query = """
            MATCH (u:User {user_id: $user_id})-[:HAS_NOTIFICATION]->(n:Notification)
            WHERE n.notification_id IN $notification_ids AND n.is_read = false
            SET n.is_read = true,
                n.read_at = $read_at
            RETURN COUNT(n) as count
            """
            
            result = await self.run_write_query(query, {
                "user_id": user_id,
                "notification_ids": notification_ids,
                "read_at": datetime.utcnow().isoformat()
            })
            
            if result:
                count = result[0]["count"]
                logger.info(f"Marked {count} notifications as read for user {user_id}")
                return count
            return 0
            
        except Exception as e:
            logger.error(f"Error marking notifications as read: {str(e)}")
            return 0
    
    async def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """
        Get notifications for a user
        
        Args:
            user_id: User ID
            unread_only: Whether to get only unread notifications
            limit: Maximum notifications to retrieve
            offset: Number of notifications to skip
            
        Returns:
            List of notifications
        """
        try:
            params = {
                "user_id": user_id,
                "limit": limit,
                "offset": offset
            }
            
            read_filter = ""
            if unread_only:
                read_filter = "AND n.is_read = false"
            
            query = f"""
            MATCH (u:User {{user_id: $user_id}})-[:HAS_NOTIFICATION]->(n:Notification)
            WHERE n.expires_at IS NULL OR n.expires_at > datetime() {read_filter}
            RETURN n
            ORDER BY n.created_at DESC
            SKIP $offset
            LIMIT $limit
            """
            
            result = await self.run_query(query, params)
            
            notifications = []
            for record in result:
                notification = dict(record["n"])
                # Parse data field if it's a JSON string
                if notification.get("data") and isinstance(notification["data"], str):
                    try:
                        notification["data"] = json.loads(notification["data"])
                    except:
                        notification["data"] = {}
                notifications.append(notification)
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error getting user notifications: {str(e)}")
            return []
    
    # =====================================================
    # Join Request Methods
    # =====================================================
    
    async def create_join_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new join request"""
        query = """
        MATCH (r:CollaborationRoom {room_id: $room_id})
        MATCH (u:User {user_id: $user_id})
        CREATE (req:JoinRequest {
            request_id: $request_id,
            room_id: $room_id,
            user_id: $user_id,
            user_name: $user_name,
            status: $status,
            message: $message,
            requested_at: $requested_at
        })
        CREATE (u)-[:REQUESTED_JOIN]->(req)
        CREATE (req)-[:FOR_ROOM]->(r)
        RETURN req
        """
        
        try:
            with self.client.get_session() as session:
                result = session.run(query, request_data)
                record = result.single()
                if record:
                    return dict(record["req"])
                return request_data
        except Exception as e:
            logger.error(f"Failed to create join request: {e}")
            raise
    
    async def get_join_requests(
        self,
        room_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get join requests with filters"""
        conditions = []
        params = {}
        
        if room_id:
            conditions.append("req.room_id = $room_id")
            params["room_id"] = room_id
        
        if user_id:
            conditions.append("req.user_id = $user_id")
            params["user_id"] = user_id
        
        if status:
            conditions.append("req.status = $status")
            params["status"] = status
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"""
        MATCH (req:JoinRequest)
        {where_clause}
        RETURN req
        ORDER BY req.requested_at DESC
        """
        
        try:
            with self.client.get_session() as session:
                result = session.run(query, params)
                return [dict(record["req"]) for record in result]
        except Exception as e:
            logger.error(f"Failed to get join requests: {e}")
            return []
    
    async def get_join_request_by_id(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get join request by ID"""
        query = """
        MATCH (req:JoinRequest {request_id: $request_id})
        RETURN req
        """
        
        try:
            with self.client.get_session() as session:
                result = session.run(query, {"request_id": request_id})
                record = result.single()
                if record:
                    return dict(record["req"])
                return None
        except Exception as e:
            logger.error(f"Failed to get join request: {e}")
            return None
    
    async def update_join_request(
        self,
        request_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update join request"""
        set_clauses = []
        params = {"request_id": request_id}
        
        for key, value in update_data.items():
            set_clauses.append(f"req.{key} = ${key}")
            params[key] = value
        
        query = f"""
        MATCH (req:JoinRequest {{request_id: $request_id}})
        SET {', '.join(set_clauses)}
        RETURN req
        """
        
        try:
            with self.client.get_session() as session:
                result = session.run(query, params)
                record = result.single()
                if record:
                    return dict(record["req"])
                return None
        except Exception as e:
            logger.error(f"Failed to update join request: {e}")
            return None
    
    # Video Session persistence methods
    
    async def create_video_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new video session in the database"""
        query = """
        CREATE (vs:VideoSession {
            session_id: $session_id,
            room_id: $room_id,
            participants: $participants,
            is_recording: $is_recording,
            recording_url: $recording_url,
            started_at: $started_at,
            ended_at: $ended_at,
            quality_metrics: $quality_metrics,
            created_at: datetime()
        })
        RETURN vs
        """
        
        params = {
            'session_id': session_data.get('session_id'),
            'room_id': session_data.get('room_id'),
            'participants': json.dumps(session_data.get('participants', [])),
            'is_recording': session_data.get('is_recording', False),
            'recording_url': session_data.get('recording_url'),
            'started_at': session_data.get('started_at'),
            'ended_at': session_data.get('ended_at'),
            'quality_metrics': json.dumps(session_data.get('quality_metrics', {}))
        }
        
        try:
            if self._use_direct_connection:
                with self.driver.session() as session:
                    result = session.run(query, params)
                    record = result.single()
                    if record:
                        return self._parse_video_session(dict(record["vs"]))
            else:
                with self.client.get_session() as session:
                    result = session.run(query, params)
                    record = result.single()
                    if record:
                        return self._parse_video_session(dict(record["vs"]))
            return session_data
        except Exception as e:
            logger.error(f"Failed to create video session: {e}")
            raise
    
    async def get_video_session_by_room(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Get active video session for a room"""
        query = """
        MATCH (vs:VideoSession {room_id: $room_id})
        WHERE vs.ended_at IS NULL
        RETURN vs
        ORDER BY vs.started_at DESC
        LIMIT 1
        """
        
        params = {'room_id': room_id}
        
        try:
            if self._use_direct_connection:
                with self.driver.session() as session:
                    result = session.run(query, params)
                    record = result.single()
                    if record:
                        return self._parse_video_session(dict(record["vs"]))
            else:
                with self.client.get_session() as session:
                    result = session.run(query, params)
                    record = result.single()
                    if record:
                        return self._parse_video_session(dict(record["vs"]))
            return None
        except Exception as e:
            logger.error(f"Failed to get video session: {e}")
            return None
    
    async def update_video_session_participants(self, room_id: str, user_id: str, action: str) -> bool:
        """Update video session participants"""
        if action == "joined":
            # For Neo4j, we'll store participants as a JSON string
            query = """
            MATCH (vs:VideoSession {room_id: $room_id})
            WHERE vs.ended_at IS NULL
            WITH vs, apoc.convert.fromJsonList(vs.participants) as participants
            WHERE NOT $user_id IN participants
            SET vs.participants = apoc.convert.toJson(participants + [$user_id]),
                vs.updated_at = datetime()
            RETURN vs
            """
        else:  # left
            query = """
            MATCH (vs:VideoSession {room_id: $room_id})
            WHERE vs.ended_at IS NULL
            SET vs.participants = apoc.convert.toJson(
                [p IN apoc.convert.fromJsonList(vs.participants) WHERE p <> $user_id]
            ),
                vs.updated_at = datetime()
            RETURN vs
            """
        
        params = {'room_id': room_id, 'user_id': user_id}
        
        try:
            if self._use_direct_connection:
                with self.driver.session() as session:
                    result = session.run(query, params)
                    return result.single() is not None
            else:
                with self.client.get_session() as session:
                    result = session.run(query, params)
                    return result.single() is not None
        except Exception as e:
            logger.error(f"Failed to update video session participants: {e}")
            # Fallback without APOC
            return await self._update_participants_fallback(room_id, user_id, action)
    
    async def _update_participants_fallback(self, room_id: str, user_id: str, action: str) -> bool:
        """Fallback method to update participants without APOC"""
        # First get current participants
        get_query = """
        MATCH (vs:VideoSession {room_id: $room_id})
        WHERE vs.ended_at IS NULL
        RETURN vs.participants as participants
        """
        
        update_query = """
        MATCH (vs:VideoSession {room_id: $room_id})
        WHERE vs.ended_at IS NULL
        SET vs.participants = $new_participants,
            vs.updated_at = datetime()
        RETURN vs
        """
        
        try:
            if self._use_direct_connection:
                with self.driver.session() as session:
                    # Get current participants
                    result = session.run(get_query, {'room_id': room_id})
                    record = result.single()
                    
                    participants = []
                    if record and record['participants']:
                        participants = json.loads(record['participants'])
                    
                    # Update participants list
                    if action == "joined" and user_id not in participants:
                        participants.append(user_id)
                    elif action == "left" and user_id in participants:
                        participants.remove(user_id)
                    
                    # Save updated participants
                    result = session.run(update_query, {
                        'room_id': room_id,
                        'new_participants': json.dumps(participants)
                    })
                    return result.single() is not None
            else:
                with self.client.get_session() as session:
                    # Similar logic for client connection
                    result = session.run(get_query, {'room_id': room_id})
                    record = result.single()
                    
                    participants = []
                    if record and record['participants']:
                        participants = json.loads(record['participants'])
                    
                    if action == "joined" and user_id not in participants:
                        participants.append(user_id)
                    elif action == "left" and user_id in participants:
                        participants.remove(user_id)
                    
                    result = session.run(update_query, {
                        'room_id': room_id,
                        'new_participants': json.dumps(participants)
                    })
                    return result.single() is not None
        except Exception as e:
            logger.error(f"Failed to update participants (fallback): {e}")
            return False
    
    async def end_video_session(self, room_id: str) -> bool:
        """Mark video session as ended"""
        query = """
        MATCH (vs:VideoSession {room_id: $room_id})
        WHERE vs.ended_at IS NULL
        SET vs.ended_at = datetime(),
            vs.updated_at = datetime()
        RETURN vs
        """
        
        params = {'room_id': room_id}
        
        try:
            if self._use_direct_connection:
                with self.driver.session() as session:
                    result = session.run(query, params)
                    return result.single() is not None
            else:
                with self.client.get_session() as session:
                    result = session.run(query, params)
                    return result.single() is not None
        except Exception as e:
            logger.error(f"Failed to end video session: {e}")
            return False
    
    async def update_video_session_recording(
        self, 
        room_id: str, 
        is_recording: bool, 
        user_id: str, 
        recording_url: Optional[str] = None
    ) -> bool:
        """Update video session recording status"""
        query = """
        MATCH (vs:VideoSession {room_id: $room_id})
        WHERE vs.ended_at IS NULL
        SET vs.is_recording = $is_recording,
            vs.recording_started_by = CASE WHEN $is_recording THEN $user_id ELSE vs.recording_started_by END,
            vs.recording_url = CASE WHEN $recording_url IS NOT NULL THEN $recording_url ELSE vs.recording_url END,
            vs.updated_at = datetime()
        RETURN vs
        """
        
        params = {
            'room_id': room_id,
            'is_recording': is_recording,
            'user_id': user_id,
            'recording_url': recording_url
        }
        
        try:
            if self._use_direct_connection:
                with self.driver.session() as session:
                    result = session.run(query, params)
                    return result.single() is not None
            else:
                with self.client.get_session() as session:
                    result = session.run(query, params)
                    return result.single() is not None
        except Exception as e:
            logger.error(f"Failed to update video session recording: {e}")
            return False
    
    async def update_video_quality_metrics(
        self, 
        room_id: str, 
        user_id: str, 
        metrics: Dict[str, Any]
    ) -> bool:
        """Update quality metrics for a video session participant"""
        # First get current metrics
        get_query = """
        MATCH (vs:VideoSession {room_id: $room_id})
        WHERE vs.ended_at IS NULL
        RETURN vs.quality_metrics as metrics
        """
        
        update_query = """
        MATCH (vs:VideoSession {room_id: $room_id})
        WHERE vs.ended_at IS NULL
        SET vs.quality_metrics = $new_metrics,
            vs.updated_at = datetime()
        RETURN vs
        """
        
        try:
            if self._use_direct_connection:
                with self.driver.session() as session:
                    # Get current metrics
                    result = session.run(get_query, {'room_id': room_id})
                    record = result.single()
                    
                    current_metrics = {}
                    if record and record['metrics']:
                        current_metrics = json.loads(record['metrics'])
                    
                    # Update metrics
                    current_metrics[user_id] = metrics
                    
                    # Save updated metrics
                    result = session.run(update_query, {
                        'room_id': room_id,
                        'new_metrics': json.dumps(current_metrics)
                    })
                    return result.single() is not None
            else:
                with self.client.get_session() as session:
                    # Similar logic for client connection
                    result = session.run(get_query, {'room_id': room_id})
                    record = result.single()
                    
                    current_metrics = {}
                    if record and record['metrics']:
                        current_metrics = json.loads(record['metrics'])
                    
                    current_metrics[user_id] = metrics
                    
                    result = session.run(update_query, {
                        'room_id': room_id,
                        'new_metrics': json.dumps(current_metrics)
                    })
                    return result.single() is not None
        except Exception as e:
            logger.error(f"Failed to update quality metrics: {e}")
            return False
    
    async def get_video_recording_url(self, room_id: str) -> Optional[str]:
        """Get recording URL for a video session"""
        query = """
        MATCH (vs:VideoSession {room_id: $room_id})
        WHERE vs.recording_url IS NOT NULL
        RETURN vs.recording_url as url
        ORDER BY vs.started_at DESC
        LIMIT 1
        """
        
        params = {'room_id': room_id}
        
        try:
            if self._use_direct_connection:
                with self.driver.session() as session:
                    result = session.run(query, params)
                    record = result.single()
                    if record:
                        return record['url']
            else:
                with self.client.get_session() as session:
                    result = session.run(query, params)
                    record = result.single()
                    if record:
                        return record['url']
            return None
        except Exception as e:
            logger.error(f"Failed to get recording URL: {e}")
            return None
    
    def _parse_video_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse video session data from database"""
        return {
            'session_id': session_data.get('session_id'),
            'room_id': session_data.get('room_id'),
            'participants': json.loads(session_data.get('participants', '[]')),
            'is_recording': session_data.get('is_recording', False),
            'recording_url': session_data.get('recording_url'),
            'started_at': session_data.get('started_at'),
            'ended_at': session_data.get('ended_at'),
            'quality_metrics': json.loads(session_data.get('quality_metrics', '{}'))
        }


# Create global instance (will be initialized later)
collaboration_storage = None

def get_collaboration_storage():
    """Get or create the collaboration storage instance"""
    global collaboration_storage
    if collaboration_storage is None:
        collaboration_storage = CollaborationStorage()
    return collaboration_storage

def set_collaboration_storage(storage_instance):
    """Set the global collaboration storage instance"""
    global collaboration_storage
    collaboration_storage = storage_instance