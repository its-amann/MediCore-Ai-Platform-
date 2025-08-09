"""
Base Migration Class for Cases Chat Database Schema
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from neo4j import GraphDatabase, Transaction

logger = logging.getLogger(__name__)


class BaseMigration(ABC):
    """
    Abstract base class for database migrations
    """
    
    def __init__(self, migration_id: str, description: str):
        """
        Initialize migration
        
        Args:
            migration_id: Unique migration identifier (e.g., "001_initial_schema")
            description: Human-readable description of the migration
        """
        self.migration_id = migration_id
        self.description = description
        self.executed_at = None
    
    @abstractmethod
    def up(self, tx: Transaction) -> Dict[str, Any]:
        """
        Apply the migration
        
        Args:
            tx: Neo4j transaction
            
        Returns:
            Dictionary with migration results
        """
        pass
    
    @abstractmethod
    def down(self, tx: Transaction) -> Dict[str, Any]:
        """
        Rollback the migration
        
        Args:
            tx: Neo4j transaction
            
        Returns:
            Dictionary with rollback results
        """
        pass
    
    def validate(self, tx: Transaction) -> bool:
        """
        Validate if migration can be applied
        
        Args:
            tx: Neo4j transaction
            
        Returns:
            True if migration can be applied
        """
        # Check if migration already applied
        result = tx.run("""
            MATCH (m:Migration {migration_id: $migration_id})
            RETURN m
        """, migration_id=self.migration_id)
        
        return result.single() is None
    
    def record_execution(self, tx: Transaction, status: str = "completed"):
        """
        Record migration execution in database
        
        Args:
            tx: Neo4j transaction
            status: Migration status
        """
        self.executed_at = datetime.utcnow()
        
        tx.run("""
            CREATE (m:Migration {
                migration_id: $migration_id,
                description: $description,
                executed_at: $executed_at,
                status: $status
            })
        """, 
        migration_id=self.migration_id,
        description=self.description,
        executed_at=self.executed_at.isoformat(),
        status=status
        )
    
    async def validate_async(self, tx) -> bool:
        """
        Async version of validate method for async driver
        
        Args:
            tx: Neo4j async transaction
            
        Returns:
            True if migration can be applied
        """
        # Check if migration already applied
        result = await tx.run("""
            MATCH (m:Migration {migration_id: $migration_id})
            RETURN m
        """, migration_id=self.migration_id)
        
        data = await result.single()
        return data is None
    
    async def record_execution_async(self, tx, status: str = "completed"):
        """
        Async version of record_execution for async driver
        
        Args:
            tx: Neo4j async transaction
            status: Migration status
        """
        self.executed_at = datetime.utcnow()
        
        await tx.run("""
            CREATE (m:Migration {
                migration_id: $migration_id,
                description: $description,
                executed_at: $executed_at,
                status: $status
            })
        """, 
        migration_id=self.migration_id,
        description=self.description,
        executed_at=self.executed_at.isoformat(),
        status=status
        )
    
    async def up_async(self, tx) -> Dict[str, Any]:
        """
        Async version of up method - to be implemented by subclasses
        Default implementation calls the sync version
        """
        # This is a fallback - migrations should override this
        raise NotImplementedError("Async up method not implemented")
    
    async def down_async(self, tx) -> Dict[str, Any]:
        """
        Async version of down method - to be implemented by subclasses
        Default implementation calls the sync version
        """
        # This is a fallback - migrations should override this
        raise NotImplementedError("Async down method not implemented")
    
    def __str__(self):
        return f"{self.migration_id}: {self.description}"