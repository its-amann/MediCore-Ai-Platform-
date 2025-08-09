"""
Database initialization module for the collaboration service
"""

import os
import logging
from typing import Optional, List, Dict, Any
from neo4j import GraphDatabase, basic_auth
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """
    Handles database initialization and schema setup for the collaboration service
    """
    
    def __init__(self, uri: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize the database initializer
        
        Args:
            uri: Neo4j URI (defaults to environment variable)
            username: Neo4j username (defaults to environment variable)
            password: Neo4j password (defaults to environment variable)
        """
        self.uri = uri or os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.username = username or os.getenv('NEO4J_USERNAME', 'neo4j')
        self.password = password or os.getenv('NEO4J_PASSWORD', 'password')
        self.driver = None
        
    def connect(self):
        """Establish connection to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=basic_auth(self.username, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Successfully connected to Neo4j database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            return False
            
    def initialize_schema(self):
        """Initialize the database schema with constraints and indexes"""
        if not self.driver:
            logger.error("Database not connected. Call connect() first.")
            return False
            
        constraints = [
            # User constraints
            "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT user_email_unique IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
            "CREATE CONSTRAINT user_username_unique IF NOT EXISTS FOR (u:User) REQUIRE u.username IS UNIQUE",
            
            # Room constraints
            "CREATE CONSTRAINT room_id_unique IF NOT EXISTS FOR (r:Room) REQUIRE r.id IS UNIQUE",
            
            # Message constraints
            "CREATE CONSTRAINT message_id_unique IF NOT EXISTS FOR (m:Message) REQUIRE m.id IS UNIQUE",
            
            # Notification constraints
            "CREATE CONSTRAINT notification_id_unique IF NOT EXISTS FOR (n:Notification) REQUIRE n.id IS UNIQUE",
            
            # Join Request constraints
            "CREATE CONSTRAINT join_request_id_unique IF NOT EXISTS FOR (jr:JoinRequest) REQUIRE jr.id IS UNIQUE"
        ]
        
        indexes = [
            # User indexes
            "CREATE INDEX user_type_index IF NOT EXISTS FOR (u:User) ON (u.user_type)",
            "CREATE INDEX user_created_at_index IF NOT EXISTS FOR (u:User) ON (u.created_at)",
            
            # Room indexes
            "CREATE INDEX room_type_index IF NOT EXISTS FOR (r:Room) ON (r.type)",
            "CREATE INDEX room_status_index IF NOT EXISTS FOR (r:Room) ON (r.status)",
            "CREATE INDEX room_created_at_index IF NOT EXISTS FOR (r:Room) ON (r.created_at)",
            "CREATE INDEX room_is_public_index IF NOT EXISTS FOR (r:Room) ON (r.is_public)",
            
            # Message indexes
            "CREATE INDEX message_room_id_index IF NOT EXISTS FOR (m:Message) ON (m.room_id)",
            "CREATE INDEX message_timestamp_index IF NOT EXISTS FOR (m:Message) ON (m.timestamp)",
            
            # Notification indexes
            "CREATE INDEX notification_user_id_index IF NOT EXISTS FOR (n:Notification) ON (n.user_id)",
            "CREATE INDEX notification_created_at_index IF NOT EXISTS FOR (n:Notification) ON (n.created_at)",
            "CREATE INDEX notification_is_read_index IF NOT EXISTS FOR (n:Notification) ON (n.is_read)"
        ]
        
        try:
            with self.driver.session() as session:
                # Create constraints
                for constraint in constraints:
                    try:
                        session.run(constraint)
                        logger.info(f"Created constraint: {constraint.split(' ')[2]}")
                    except Exception as e:
                        logger.debug(f"Constraint already exists or error: {str(e)}")
                        
                # Create indexes
                for index in indexes:
                    try:
                        session.run(index)
                        logger.info(f"Created index: {index.split(' ')[2]}")
                    except Exception as e:
                        logger.debug(f"Index already exists or error: {str(e)}")
                        
            logger.info("Database schema initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize schema: {str(e)}")
            return False
            
    def create_sample_data(self):
        """Create sample data for testing"""
        try:
            with self.driver.session() as session:
                # Create sample users
                sample_users = [
                    {
                        "id": "user_teacher_001",
                        "username": "dr_smith",
                        "email": "dr.smith@medical.edu",
                        "full_name": "Dr. John Smith",
                        "user_type": "teacher",
                        "institution": "Medical University",
                        "specialization": "Cardiology",
                        "created_at": datetime.utcnow().isoformat()
                    },
                    {
                        "id": "user_student_001",
                        "username": "jane_doe",
                        "email": "jane.doe@student.edu",
                        "full_name": "Jane Doe",
                        "user_type": "student",
                        "institution": "Medical University",
                        "student_id": "MED2024001",
                        "created_at": datetime.utcnow().isoformat()
                    }
                ]
                
                for user in sample_users:
                    session.run(
                        """
                        MERGE (u:User {id: $id})
                        SET u += $props
                        """,
                        id=user["id"],
                        props=user
                    )
                    
                # Create sample room
                sample_room = {
                    "id": "room_teaching_001",
                    "name": "Cardiology Basics",
                    "description": "Introduction to Cardiology for Medical Students",
                    "type": "teaching",
                    "status": "active",
                    "max_participants": 50,
                    "is_public": True,
                    "voice_enabled": True,
                    "screen_sharing": True,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                session.run(
                    """
                    MERGE (r:Room {id: $id})
                    SET r += $props
                    """,
                    id=sample_room["id"],
                    props=sample_room
                )
                
                # Create relationship between teacher and room
                session.run(
                    """
                    MATCH (u:User {id: $teacher_id})
                    MATCH (r:Room {id: $room_id})
                    MERGE (u)-[:CREATED]->(r)
                    MERGE (u)-[:PARTICIPATES_IN {role: 'host', joined_at: $joined_at}]->(r)
                    """,
                    teacher_id="user_teacher_001",
                    room_id="room_teaching_001",
                    joined_at=datetime.utcnow().isoformat()
                )
                
                logger.info("Sample data created successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create sample data: {str(e)}")
            return False
            
    def clear_database(self):
        """Clear all data from the database (use with caution!)"""
        try:
            with self.driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
                logger.info("Database cleared successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to clear database: {str(e)}")
            return False
            
    def close(self):
        """Close the database connection"""
        if self.driver:
            self.driver.close()
            logger.info("Database connection closed")
            
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Convenience function for quick initialization
def initialize_collaboration_database():
    """
    Initialize the collaboration database with schema and optionally sample data
    """
    initializer = DatabaseInitializer()
    
    try:
        if initializer.connect():
            initializer.initialize_schema()
            logger.info("Collaboration database initialized successfully")
            return True
        else:
            logger.error("Failed to connect to database")
            return False
    finally:
        initializer.close()


if __name__ == "__main__":
    # Run initialization when module is executed directly
    logging.basicConfig(level=logging.INFO)
    
    with DatabaseInitializer() as db_init:
        if db_init.initialize_schema():
            print("Database schema initialized successfully")
            
            # Optionally create sample data
            response = input("Create sample data? (y/n): ")
            if response.lower() == 'y':
                db_init.create_sample_data()