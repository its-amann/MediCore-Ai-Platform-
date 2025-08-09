"""
Database client for collaboration microservice
Provides a unified interface to Neo4j storage
"""

import logging
from typing import Optional
from neo4j import GraphDatabase
from .neo4j_storage import get_collaboration_storage

logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    Database client that wraps Neo4j storage for collaboration microservice
    """
    
    def __init__(self, neo4j_driver=None):
        """
        Initialize database client with Neo4j storage
        
        Args:
            neo4j_driver: Optional Neo4j driver instance. If not provided,
                         will create a connection using configuration settings.
        """
        self.storage = get_collaboration_storage()
        self._neo4j_driver = neo4j_driver
        self._connected = False
        logger.info("Database client initialized with Neo4j storage")
    
    async def connect(self):
        """
        Connect to the database and initialize constraints
        """
        try:
            # If a driver was provided during initialization, use it
            if self._neo4j_driver:
                # Test the provided connection
                try:
                    with self._neo4j_driver.session() as session:
                        session.run("RETURN 1")
                    logger.info("Using provided Neo4j driver")
                    
                    # Update storage instance with the driver
                    if hasattr(self.storage, 'driver'):
                        self.storage.driver = self._neo4j_driver
                    if hasattr(self.storage, 'neo4j_client'):
                        # Create a minimal client wrapper for compatibility
                        class ClientWrapper:
                            def __init__(self, driver):
                                self.driver = driver
                            
                            def is_connected(self):
                                try:
                                    with self.driver.session() as session:
                                        session.run("RETURN 1")
                                    return True
                                except:
                                    return False
                            
                            def get_session(self):
                                return self.driver.session()
                        
                        self.storage.neo4j_client = ClientWrapper(self._neo4j_driver)
                        self.storage.client = self.storage.neo4j_client
                except Exception as e:
                    logger.error(f"Provided Neo4j driver test failed: {e}")
                    raise
            else:
                # Create a new connection using configuration
                from ..config import settings
                logger.info(f"Creating new Neo4j connection to {settings.NEO4J_URI}")
                
                self._neo4j_driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                )
                
                # Test the connection
                with self._neo4j_driver.session() as session:
                    session.run("RETURN 1")
                
                logger.info("Direct Neo4j connection established successfully")
                
                # Update storage to use this driver
                if hasattr(self.storage, 'driver'):
                    self.storage.driver = self._neo4j_driver
                self.storage._use_direct_connection = True
            
            # Initialize our collaboration-specific constraints
            # Check if we need to run sync or async initialization
            if self._neo4j_driver:
                # We have a sync driver, run sync initialization
                import asyncio
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._initialize_constraints_sync)
            else:
                # Run async initialization
                await self.storage.initialize_constraints()
            self._connected = True
            logger.info("Database client connected and constraints initialized")
            
        except Exception as e:
            logger.error(f"Failed to connect database client: {str(e)}")
            self._connected = False
            raise
    
    async def disconnect(self):
        """
        Disconnect from the database
        """
        # Only close the driver if we created it ourselves
        if self._neo4j_driver and hasattr(self.storage, '_use_direct_connection') and self.storage._use_direct_connection:
            self._neo4j_driver.close()
            logger.info("Closed direct Neo4j connection")
        
        self._connected = False
        logger.info("Database client disconnected")
    
    async def is_connected(self) -> bool:
        """
        Check if database is connected
        
        Returns:
            True if connected, False otherwise
        """
        if not self._connected:
            return False
            
        try:
            # Test the connection
            if self._neo4j_driver:
                with self._neo4j_driver.session() as session:
                    session.run("RETURN 1")
                return True
            else:
                return False
        except:
            return False
    
    def _initialize_constraints_sync(self):
        """Synchronous version of constraint initialization for sync drivers"""
        try:
            with self._neo4j_driver.session() as session:
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
                    except Exception as e:
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
                    except Exception as e:
                        if "already exists" not in str(e).lower() and "equivalent" not in str(e).lower():
                            logger.error(f"Error creating index: {str(e)}")
                
                logger.info("Collaboration database constraints and indexes initialized (sync)")
                
        except Exception as e:
            logger.error(f"Failed to initialize collaboration constraints (sync): {str(e)}")
            raise
    
    # Room methods
    async def create_room(self, room_data: dict) -> dict:
        """Create a new room"""
        return await self.storage.create_room(room_data)
    
    async def update_room(self, room_id: str, update_data: dict) -> Optional[dict]:
        """Update room information"""
        return await self.storage.update_room(room_id, update_data)
    
    async def delete_room(self, room_id: str, user_id: str) -> bool:
        """Delete a room"""
        return await self.storage.delete_room(room_id, user_id)
    
    async def get_room_by_id(self, room_id: str) -> Optional[dict]:
        """Get room by ID"""
        return await self.storage.get_room_by_id(room_id)
    
    async def get_user_rooms(self, user_id: str, status_filter=None, limit=50, offset=0):
        """Get rooms for a user"""
        return await self.storage.get_user_rooms(user_id, status_filter, limit, offset)
    
    async def search_public_rooms(self, search_query=None, room_type=None, limit=20, offset=0):
        """Search public rooms"""
        return await self.storage.search_public_rooms(search_query, room_type, limit, offset)
    
    # Participant methods
    async def add_participant(self, room_id: str, user_id: str, username: str, role: str = "participant") -> bool:
        """Add participant to room"""
        return await self.storage.add_participant(room_id, user_id, username, role)
    
    async def remove_participant(self, room_id: str, user_id: str) -> bool:
        """Remove participant from room"""
        return await self.storage.remove_participant(room_id, user_id)
    
    async def get_room_participants(self, room_id: str):
        """Get all participants in a room"""
        return await self.storage.get_room_participants(room_id)
    
    async def update_user_role_in_room(self, room_id: str, user_id: str, new_role: str, updated_by: str) -> bool:
        """Update user role in room"""
        return await self.storage.update_user_role_in_room(room_id, user_id, new_role, updated_by)
    
    # Message methods
    async def store_message(self, message_data: dict) -> dict:
        """Store a message"""
        return await self.storage.store_message(message_data)
    
    async def get_room_messages(self, room_id: str, limit=50, offset=0, before_timestamp=None):
        """Get messages from a room"""
        return await self.storage.get_room_messages(room_id, limit, offset, before_timestamp)
    
    # Join request methods
    async def create_join_request(self, request_data: dict) -> dict:
        """Create a join request"""
        return await self.storage.create_join_request(request_data)
    
    async def process_join_request(self, request_id: str, processed_by: str, status: str, reason=None) -> bool:
        """Process a join request"""
        return await self.storage.process_join_request(request_id, processed_by, status, reason)
    
    async def get_pending_join_requests(self, room_id: str):
        """Get pending join requests for a room"""
        return await self.storage.get_pending_join_requests(room_id)
    
    # User activity methods
    async def track_user_activity(self, user_id: str, room_id: str, activity_type: str, metadata=None) -> bool:
        """Track user activity"""
        return await self.storage.track_user_activity(user_id, room_id, activity_type, metadata)
    
    # Notification methods
    async def store_notification(self, notification_data: dict) -> dict:
        """Store a notification"""
        return await self.storage.store_notification(notification_data)
    
    async def get_user_notifications(self, user_id: str, unread_only=False, limit=50, offset=0):
        """Get user notifications"""
        return await self.storage.get_user_notifications(user_id, unread_only, limit, offset)
    
    async def mark_notifications_as_read(self, user_id: str, notification_ids: list) -> int:
        """Mark notifications as read"""
        return await self.storage.mark_notifications_as_read(user_id, notification_ids)
    
    # AI session methods
    async def create_ai_session(self, session_data: dict) -> dict:
        """Create an AI session"""
        return await self.storage.create_ai_session(session_data)
    
    # Statistics methods
    async def get_room_statistics(self, room_id: str) -> dict:
        """Get room statistics"""
        return await self.storage.get_room_statistics(room_id)