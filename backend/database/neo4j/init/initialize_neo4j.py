#!/usr/bin/env python3
"""
Neo4j Database Initialization Script
Unified Medical AI Platform

This script automatically initializes the Neo4j database with all required
constraints, indexes, and seed data.
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
from neo4j import GraphDatabase, exceptions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Neo4jInitializer:
    """Handles Neo4j database initialization."""
    
    def __init__(self, uri: str, username: str, password: str):
        """
        Initialize the Neo4j connection.
        
        Args:
            uri: Neo4j connection URI
            username: Neo4j username
            password: Neo4j password
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.driver = None
        
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        
    def connect(self):
        """Establish connection to Neo4j."""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"Successfully connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
            
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Closed Neo4j connection")
            
    def execute_cypher_file(self, file_path: Path) -> bool:
        """
        Execute a Cypher script file.
        
        Args:
            file_path: Path to the Cypher file
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Executing script: {file_path.name}")
        
        try:
            # Read the Cypher script
            with open(file_path, 'r', encoding='utf-8') as f:
                cypher_script = f.read()
                
            # Split by semicolons to handle multiple statements
            # Remove comments and empty lines
            statements = []
            for line in cypher_script.split('\n'):
                line = line.strip()
                if line and not line.startswith('//'):
                    statements.append(line)
            
            # Join and split by semicolons
            full_script = ' '.join(statements)
            individual_statements = [s.strip() for s in full_script.split(';') if s.strip()]
            
            # Execute each statement
            with self.driver.session() as session:
                for i, statement in enumerate(individual_statements):
                    if statement:
                        try:
                            session.run(statement)
                            logger.debug(f"Executed statement {i+1}/{len(individual_statements)}")
                        except exceptions.ClientError as e:
                            # Handle "already exists" errors gracefully
                            if "already exists" in str(e).lower():
                                logger.debug(f"Constraint/Index already exists (statement {i+1})")
                            else:
                                logger.error(f"Error executing statement {i+1}: {e}")
                                raise
                                
            logger.info(f"✓ Successfully executed {file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to execute {file_path.name}: {e}")
            return False
            
    def verify_initialization(self) -> Dict[str, int]:
        """
        Verify the database initialization by checking counts.
        
        Returns:
            Dictionary with node and relationship counts
        """
        counts = {}
        
        with self.driver.session() as session:
            # Count nodes by label
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY label
            """)
            
            logger.info("\nNode counts:")
            for record in result:
                label = record["label"]
                count = record["count"]
                counts[f"node_{label}"] = count
                logger.info(f"  {label}: {count}")
                
            # Count relationships by type
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY type
            """)
            
            logger.info("\nRelationship counts:")
            for record in result:
                rel_type = record["type"]
                count = record["count"]
                counts[f"rel_{rel_type}"] = count
                logger.info(f"  {rel_type}: {count}")
                
            # Count constraints
            result = session.run("SHOW CONSTRAINTS")
            constraint_count = len(list(result))
            counts["constraints"] = constraint_count
            logger.info(f"\nConstraints: {constraint_count}")
            
            # Count indexes
            result = session.run("SHOW INDEXES")
            index_count = len(list(result))
            counts["indexes"] = index_count
            logger.info(f"Indexes: {index_count}")
            
        return counts
        
    def wait_for_neo4j(self, max_attempts: int = 30, delay: int = 2) -> bool:
        """
        Wait for Neo4j to be ready.
        
        Args:
            max_attempts: Maximum number of connection attempts
            delay: Delay between attempts in seconds
            
        Returns:
            True if connection successful, False otherwise
        """
        logger.info(f"Waiting for Neo4j to be ready at {self.uri}...")
        
        for attempt in range(max_attempts):
            try:
                self.connect()
                return True
            except Exception as e:
                if attempt < max_attempts - 1:
                    logger.debug(f"Attempt {attempt + 1}/{max_attempts} failed, retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Neo4j not ready after {max_attempts} attempts")
                    return False
                    
        return False

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Initialize Neo4j database for Unified Medical AI Platform"
    )
    
    parser.add_argument(
        "--host",
        default=os.getenv("NEO4J_HOST", "localhost"),
        help="Neo4j host (default: localhost)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("NEO4J_PORT", "7687")),
        help="Neo4j bolt port (default: 7687)"
    )
    
    parser.add_argument(
        "--username",
        default=os.getenv("NEO4J_USERNAME", "neo4j"),
        help="Neo4j username (default: neo4j)"
    )
    
    parser.add_argument(
        "--password",
        default=os.getenv("NEO4J_PASSWORD", "password"),
        help="Neo4j password"
    )
    
    parser.add_argument(
        "--skip-test-data",
        action="store_true",
        help="Skip test data seeding (for production)"
    )
    
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for Neo4j to be ready before initializing"
    )
    
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing initialization"
    )
    
    args = parser.parse_args()
    
    # Build connection URI
    uri = f"bolt://{args.host}:{args.port}"
    
    # Get script directory
    script_dir = Path(__file__).parent
    
    # Define initialization scripts in order
    scripts = [
        "001_create_constraints.cypher",
        "002_create_indexes.cypher",
        "003_create_vector_indexes.cypher",
        "004_seed_doctors.cypher"
    ]
    
    if not args.skip_test_data:
        scripts.append("005_seed_test_data.cypher")
        
    scripts.extend([
        "006_create_functions.cypher",
        "007_collaboration_constraints.cypher",
        "008_collaboration_indexes.cypher",
        "009_collaboration_relationships.cypher"
    ])
    
    try:
        with Neo4jInitializer(uri, args.username, args.password) as initializer:
            # Wait for Neo4j if requested
            if args.wait:
                if not initializer.wait_for_neo4j():
                    logger.error("Failed to connect to Neo4j")
                    sys.exit(1)
                    
            if args.verify_only:
                # Only verify existing initialization
                logger.info("Verifying database initialization...")
                counts = initializer.verify_initialization()
                
                # Check if initialization seems complete
                if counts.get("node_Doctor", 0) == 0:
                    logger.warning("Database appears to be uninitialized (no Doctor nodes found)")
                    sys.exit(1)
                else:
                    logger.info("Database initialization verified successfully")
                    sys.exit(0)
                    
            # Execute initialization scripts
            logger.info(f"Starting Neo4j initialization at {uri}")
            logger.info(f"Executing {len(scripts)} initialization scripts...")
            
            success_count = 0
            for script_name in scripts:
                script_path = script_dir / script_name
                if script_path.exists():
                    if initializer.execute_cypher_file(script_path):
                        success_count += 1
                    else:
                        logger.error(f"Failed to execute {script_name}")
                        # Continue with other scripts
                else:
                    logger.warning(f"Script not found: {script_path}")
                    
            logger.info(f"\nInitialization complete: {success_count}/{len(scripts)} scripts executed successfully")
            
            # Verify initialization
            logger.info("\nVerifying initialization...")
            counts = initializer.verify_initialization()
            
            # Summary
            if success_count == len(scripts):
                logger.info("\n✓ Neo4j database initialized successfully!")
                sys.exit(0)
            else:
                logger.error(f"\n✗ Initialization completed with errors ({len(scripts) - success_count} scripts failed)")
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()