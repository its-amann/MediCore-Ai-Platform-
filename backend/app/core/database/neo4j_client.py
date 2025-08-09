"""
Neo4j Client for Database Operations
"""
import logging
import json
from datetime import datetime
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
from contextlib import contextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j database client"""
    
    def __init__(self):
        """Initialize Neo4j client"""
        self.uri = settings.neo4j_uri
        self.user = settings.neo4j_user
        self.password = settings.neo4j_password
        self.driver = None
        
    def connect(self):
        """Connect to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"Connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise
    
    def disconnect(self):
        """Disconnect from Neo4j database"""
        if self.driver:
            self.driver.close()
            logger.info("Disconnected from Neo4j")
    
    def is_connected(self) -> bool:
        """Check if connected to Neo4j"""
        try:
            if not self.driver:
                return False
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False
    
    @contextmanager
    def get_session(self):
        """Get a Neo4j session"""
        if not self.driver:
            self.connect()
        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()
    
    def initialize_constraints(self):
        """Initialize database constraints and indexes"""
        try:
            with self.get_session() as session:
                # Create constraints
                constraints = [
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Case) REQUIRE c.case_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (s:ChatSession) REQUIRE s.session_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (m:ChatMessage) REQUIRE m.message_id IS UNIQUE"
                ]
                
                for constraint in constraints:
                    try:
                        session.run(constraint)
                    except Neo4jError as e:
                        if "already exists" not in str(e):
                            logger.error(f"Error creating constraint: {str(e)}")
                
                # Create indexes
                indexes = [
                    "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.user_id)",
                    "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.status)",
                    "CREATE INDEX IF NOT EXISTS FOR (m:ChatMessage) ON (m.session_id)",
                    "CREATE INDEX IF NOT EXISTS FOR (m:ChatMessage) ON (m.created_at)"
                ]
                
                for index in indexes:
                    try:
                        session.run(index)
                    except Neo4jError as e:
                        if "already exists" not in str(e):
                            logger.error(f"Error creating index: {str(e)}")
                
                logger.info("Database constraints and indexes initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    async def close(self):
        """Close database connection"""
        self.disconnect()
    
    async def verify_connectivity(self):
        """Verify database connectivity"""
        try:
            with self.get_session() as session:
                result = session.run("RETURN 1 AS connected")
                return result.single()["connected"] == 1
        except Exception as e:
            logger.error(f"Connectivity check failed: {str(e)}")
            return False
    
    async def get_user_by_username(self, username: str):
        """Get user by username"""
        try:
            with self.get_session() as session:
                result = session.run(
                    """
                    MATCH (u:User {username: $username})
                    RETURN u
                    """,
                    username=username
                )
                record = result.single()
                if record:
                    user_node = record["u"]
                    user_data = dict(user_node)
                    # Ensure all required fields are present
                    user_data.setdefault("role", "patient")
                    user_data.setdefault("is_active", True)
                    user_data.setdefault("preferences", "{}")
                    return user_data
                return None
        except Exception as e:
            logger.error(f"Error getting user by username: {str(e)}")
            return None
    
    async def create_user(self, user_data: dict):
        """Create a new user"""
        try:
            with self.get_session() as session:
                result = session.run(
                    """
                    CREATE (u:User {
                        user_id: $user_id,
                        username: $username,
                        email: $email,
                        first_name: $first_name,
                        last_name: $last_name,
                        role: $role,
                        password_hash: $password_hash,
                        is_active: $is_active,
                        created_at: $created_at,
                        last_login: $last_login,
                        preferences: $preferences
                    })
                    RETURN u
                    """,
                    **user_data
                )
                record = result.single()
                if record:
                    return dict(record["u"])
                return None
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    async def run_query(self, query: str, params: dict = None):
        """Run a read query and return list of records"""
        try:
            with self.get_session() as session:
                result = session.run(query, params or {})
                # Convert to list to avoid result consumption issues
                return list(result)
        except Exception as e:
            logger.error(f"Error running query: {str(e)}")
            raise
    
    async def run_write_query(self, query: str, params: dict = None):
        """Run a write query"""
        try:
            with self.get_session() as session:
                result = session.run(query, params or {})
                # Convert to list for write queries too
                return list(result)
        except Exception as e:
            logger.error(f"Error running write query: {str(e)}")
            raise
    
    def is_connected(self) -> bool:
        """Check if Neo4j database is connected"""
        try:
            if not self.driver:
                return False
            with self.driver.session() as session:
                result = session.run("RETURN 1")
                return result.single()["1"] == 1
        except Exception as e:
            logger.debug(f"Connection check failed: {str(e)}")
            return False
    
    async def create_chat_history(self, chat_data: dict):
        """Create a chat history record"""
        try:
            # Prepare data for Neo4j
            prepared_data = self._prepare_data_for_neo4j(chat_data.copy())
            
            query = """
            CREATE (ch:ChatHistory)
            SET ch += $props
            RETURN ch
            """
            
            with self.get_session() as session:
                result = session.run(query, {"props": prepared_data})
                record = result.single()
                if record:
                    return dict(record["ch"])
                return None
        except Exception as e:
            logger.error(f"Error creating chat history: {str(e)}")
            raise
    
    def _prepare_data_for_neo4j(self, data: dict) -> dict:
        """Prepare data for Neo4j by converting complex types to strings"""
        prepared = {}
        for key, value in data.items():
            if value is None:
                continue
            elif isinstance(value, (dict, list)):
                # Convert complex types to JSON strings
                prepared[key] = json.dumps(value)
            elif isinstance(value, datetime):
                # Convert datetime to ISO format string
                prepared[key] = value.isoformat()
            else:
                prepared[key] = value
        return prepared


# Create global instance
neo4j_client = Neo4jClient()