"""
Migration to create Neo4j constraints and indexes for collaboration microservice
"""

import logging
from typing import List, Dict, Any
from neo4j import GraphDatabase, Session
from neo4j.exceptions import Neo4jError

logger = logging.getLogger(__name__)


class CollaborationConstraintsMigration:
    """
    Creates constraints and indexes for collaboration entities in Neo4j
    """
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """
        Initialize migration with Neo4j connection details
        
        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        self.migration_id = "001_collaboration_constraints"
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def close(self):
        """Close the Neo4j driver connection"""
        if self.driver:
            self.driver.close()
    
    def get_constraints(self) -> List[Dict[str, Any]]:
        """
        Define all constraints for collaboration entities
        
        Returns:
            List of constraint definitions
        """
        return [
            {
                "name": "room_id_unique",
                "query": "CREATE CONSTRAINT room_id_unique IF NOT EXISTS FOR (r:Room) REQUIRE r.room_id IS UNIQUE",
                "description": "Ensures room IDs are unique"
            },
            {
                "name": "message_id_unique",
                "query": "CREATE CONSTRAINT message_id_unique IF NOT EXISTS FOR (m:Message) REQUIRE m.message_id IS UNIQUE",
                "description": "Ensures message IDs are unique"
            },
            {
                "name": "notification_id_unique",
                "query": "CREATE CONSTRAINT notification_id_unique IF NOT EXISTS FOR (n:Notification) REQUIRE n.notification_id IS UNIQUE",
                "description": "Ensures notification IDs are unique"
            },
            {
                "name": "join_request_id_unique",
                "query": "CREATE CONSTRAINT join_request_id_unique IF NOT EXISTS FOR (jr:JoinRequest) REQUIRE jr.request_id IS UNIQUE",
                "description": "Ensures join request IDs are unique"
            },
            {
                "name": "ai_session_id_unique",
                "query": "CREATE CONSTRAINT ai_session_id_unique IF NOT EXISTS FOR (ai:AISession) REQUIRE ai.session_id IS UNIQUE",
                "description": "Ensures AI session IDs are unique"
            },
            {
                "name": "user_activity_id_unique",
                "query": "CREATE CONSTRAINT user_activity_id_unique IF NOT EXISTS FOR (ua:UserActivity) REQUIRE ua.activity_id IS UNIQUE",
                "description": "Ensures user activity IDs are unique"
            }
        ]
    
    def get_indexes(self) -> List[Dict[str, Any]]:
        """
        Define all indexes for collaboration entities
        
        Returns:
            List of index definitions
        """
        return [
            # Room indexes
            {
                "name": "room_status_index",
                "query": "CREATE INDEX room_status_index IF NOT EXISTS FOR (r:Room) ON (r.status)",
                "description": "Index for room status lookups"
            },
            {
                "name": "room_type_index",
                "query": "CREATE INDEX room_type_index IF NOT EXISTS FOR (r:Room) ON (r.type)",
                "description": "Index for room type filtering"
            },
            {
                "name": "room_created_at_index",
                "query": "CREATE INDEX room_created_at_index IF NOT EXISTS FOR (r:Room) ON (r.created_at)",
                "description": "Index for room creation time sorting"
            },
            {
                "name": "room_last_activity_index",
                "query": "CREATE INDEX room_last_activity_index IF NOT EXISTS FOR (r:Room) ON (r.last_activity)",
                "description": "Index for room activity sorting"
            },
            
            # Message indexes
            {
                "name": "message_room_id_index",
                "query": "CREATE INDEX message_room_id_index IF NOT EXISTS FOR (m:Message) ON (m.room_id)",
                "description": "Index for message room lookups"
            },
            {
                "name": "message_timestamp_index",
                "query": "CREATE INDEX message_timestamp_index IF NOT EXISTS FOR (m:Message) ON (m.timestamp)",
                "description": "Index for message chronological ordering"
            },
            {
                "name": "message_sender_id_index",
                "query": "CREATE INDEX message_sender_id_index IF NOT EXISTS FOR (m:Message) ON (m.sender_id)",
                "description": "Index for message sender lookups"
            },
            
            # Notification indexes
            {
                "name": "notification_user_id_index",
                "query": "CREATE INDEX notification_user_id_index IF NOT EXISTS FOR (n:Notification) ON (n.user_id)",
                "description": "Index for user notification lookups"
            },
            {
                "name": "notification_is_read_index",
                "query": "CREATE INDEX notification_is_read_index IF NOT EXISTS FOR (n:Notification) ON (n.is_read)",
                "description": "Index for unread notification filtering"
            },
            {
                "name": "notification_created_at_index",
                "query": "CREATE INDEX notification_created_at_index IF NOT EXISTS FOR (n:Notification) ON (n.created_at)",
                "description": "Index for notification chronological ordering"
            },
            
            # Join request indexes
            {
                "name": "join_request_status_index",
                "query": "CREATE INDEX join_request_status_index IF NOT EXISTS FOR (jr:JoinRequest) ON (jr.status)",
                "description": "Index for join request status filtering"
            },
            {
                "name": "join_request_room_id_index",
                "query": "CREATE INDEX join_request_room_id_index IF NOT EXISTS FOR (jr:JoinRequest) ON (jr.room_id)",
                "description": "Index for join request room lookups"
            },
            
            # User activity indexes
            {
                "name": "user_activity_timestamp_index",
                "query": "CREATE INDEX user_activity_timestamp_index IF NOT EXISTS FOR (ua:UserActivity) ON (ua.timestamp)",
                "description": "Index for user activity chronological ordering"
            },
            {
                "name": "user_activity_user_id_index",
                "query": "CREATE INDEX user_activity_user_id_index IF NOT EXISTS FOR (ua:UserActivity) ON (ua.user_id)",
                "description": "Index for user activity lookups"
            },
            {
                "name": "user_activity_room_id_index",
                "query": "CREATE INDEX user_activity_room_id_index IF NOT EXISTS FOR (ua:UserActivity) ON (ua.room_id)",
                "description": "Index for room activity lookups"
            }
        ]
    
    def execute_query(self, session: Session, query: str, description: str) -> bool:
        """
        Execute a single query with error handling
        
        Args:
            session: Neo4j session
            query: Cypher query to execute
            description: Description of what the query does
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session.run(query)
            logger.info(f"✓ {description}")
            return True
        except Neo4jError as e:
            if "already exists" in str(e).lower():
                logger.info(f"✓ {description} (already exists)")
                return True
            else:
                logger.error(f"✗ Failed to create {description}: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"✗ Unexpected error creating {description}: {str(e)}")
            return False
    
    def run(self) -> bool:
        """
        Run the migration to create all constraints and indexes
        
        Returns:
            True if all operations successful, False otherwise
        """
        logger.info(f"Starting migration: {self.migration_id}")
        
        success_count = 0
        total_count = 0
        
        with self.driver.session() as session:
            # Create constraints
            logger.info("\nCreating constraints...")
            constraints = self.get_constraints()
            for constraint in constraints:
                total_count += 1
                if self.execute_query(session, constraint["query"], constraint["description"]):
                    success_count += 1
            
            # Create indexes
            logger.info("\nCreating indexes...")
            indexes = self.get_indexes()
            for index in indexes:
                total_count += 1
                if self.execute_query(session, index["query"], index["description"]):
                    success_count += 1
        
        # Summary
        logger.info(f"\nMigration complete: {success_count}/{total_count} operations successful")
        
        # Mark migration as complete
        if success_count == total_count:
            self.mark_migration_complete()
            return True
        else:
            logger.warning(f"Migration partially failed: {total_count - success_count} operations failed")
            return False
    
    def mark_migration_complete(self):
        """Mark this migration as completed in the database"""
        with self.driver.session() as session:
            try:
                query = """
                MERGE (m:Migration {migration_id: $migration_id})
                SET m.completed_at = datetime(),
                    m.status = 'completed'
                """
                session.run(query, migration_id=self.migration_id)
                logger.info(f"Migration {self.migration_id} marked as complete")
            except Exception as e:
                logger.error(f"Failed to mark migration as complete: {str(e)}")
    
    def is_migration_completed(self) -> bool:
        """Check if this migration has already been completed"""
        with self.driver.session() as session:
            try:
                query = """
                MATCH (m:Migration {migration_id: $migration_id, status: 'completed'})
                RETURN m
                """
                result = session.run(query, migration_id=self.migration_id)
                return result.single() is not None
            except Exception as e:
                logger.error(f"Failed to check migration status: {str(e)}")
                return False


def main():
    """Main function to run the migration"""
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Get Neo4j connection details
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run migration
    with CollaborationConstraintsMigration(neo4j_uri, neo4j_user, neo4j_password) as migration:
        # Check if already completed
        if migration.is_migration_completed():
            logger.info(f"Migration {migration.migration_id} has already been completed")
            return
        
        # Run the migration
        if migration.run():
            logger.info("Migration completed successfully!")
        else:
            logger.error("Migration failed!")
            exit(1)


if __name__ == "__main__":
    main()