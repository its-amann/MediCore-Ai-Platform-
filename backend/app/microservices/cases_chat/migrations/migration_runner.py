"""
Migration Runner for Cases Chat Database
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
import importlib
import inspect
import asyncio

from neo4j import GraphDatabase, Transaction
from neo4j.exceptions import Neo4jError

from .base_migration import BaseMigration

logger = logging.getLogger(__name__)


class MigrationRunner:
    """
    Handles execution of database migrations
    """
    
    def __init__(self, driver):
        """
        Initialize migration runner
        
        Args:
            driver: Neo4j driver instance
        """
        self.driver = driver
        self.migrations: List[BaseMigration] = []
    
    def load_migrations(self, migrations_dir: Optional[str] = None):
        """
        Load all migrations from directory
        
        Args:
            migrations_dir: Directory containing migration files
        """
        if migrations_dir is None:
            migrations_dir = os.path.dirname(__file__)
        
        migration_files = [
            f for f in os.listdir(migrations_dir)
            if f.endswith('.py') and f.startswith('migration_') and not f.startswith('__')
        ]
        
        for file in sorted(migration_files):
            module_name = file[:-3]  # Remove .py extension
            try:
                module = importlib.import_module(f'.{module_name}', package='app.microservices.cases_chat.migrations')
                
                # Find migration classes in the module
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseMigration) and 
                        obj != BaseMigration):
                        migration = obj()
                        self.migrations.append(migration)
                        logger.info(f"Loaded migration: {migration}")
                        
            except Exception as e:
                logger.error(f"Failed to load migration from {file}: {str(e)}")
    
    async def get_applied_migrations(self) -> List[str]:
        """
        Get list of already applied migrations
        
        Returns:
            List of migration IDs
        """
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (m:Migration)
                WHERE m.status = 'completed'
                RETURN m.migration_id as id
                ORDER BY m.migration_id
            """)
            
            records = await result.data()
            return [record["id"] for record in records]
    
    async def get_pending_migrations(self) -> List[BaseMigration]:
        """
        Get list of pending migrations
        
        Returns:
            List of migration objects
        """
        applied = set(await self.get_applied_migrations())
        return [m for m in self.migrations if m.migration_id not in applied]
    
    async def run_migrations(self, target: Optional[str] = None) -> Dict[str, Any]:
        """
        Run all pending migrations up to target
        
        Args:
            target: Target migration ID (runs all if None)
            
        Returns:
            Dictionary with migration results
        """
        pending = await self.get_pending_migrations()
        
        if not pending:
            logger.info("No pending migrations")
            return {
                "status": "success",
                "message": "No pending migrations",
                "migrations_run": []
            }
        
        results = {
            "status": "success",
            "migrations_run": [],
            "errors": []
        }
        
        for migration in pending:
            if target and migration.migration_id > target:
                break
            
            try:
                logger.info(f"Running migration: {migration}")
                
                async with self.driver.session() as session:
                    # Run migration in transaction
                    async with session.begin_transaction() as tx:
                        # Validate migration can be applied
                        if not await migration.validate_async(tx):
                            raise Exception(f"Migration {migration.migration_id} cannot be applied")
                        
                        # Run the migration
                        migration_result = await migration.up_async(tx)
                        
                        # Record execution
                        await migration.record_execution_async(tx)
                        
                        # Commit is automatic when exiting the context
                    
                    results["migrations_run"].append({
                        "migration_id": migration.migration_id,
                        "description": migration.description,
                        "result": migration_result
                    })
                    
                    logger.info(f"Completed migration: {migration.migration_id}")
                    
            except Exception as e:
                logger.error(f"Failed to run migration {migration.migration_id}: {str(e)}")
                results["status"] = "partial"
                results["errors"].append({
                    "migration_id": migration.migration_id,
                    "error": str(e)
                })
                # Stop on error
                break
        
        return results
    
    def _run_migration_tx(self, tx: Transaction, migration: BaseMigration) -> Dict[str, Any]:
        """
        Run a single migration in a transaction
        
        Args:
            tx: Neo4j transaction
            migration: Migration to run
            
        Returns:
            Migration result
        """
        # Validate migration can be applied
        if not migration.validate(tx):
            raise Exception(f"Migration {migration.migration_id} cannot be applied")
        
        # Run the migration
        result = migration.up(tx)
        
        # Record execution
        migration.record_execution(tx)
        
        return result
    
    def rollback_migration(self, migration_id: str) -> Dict[str, Any]:
        """
        Rollback a specific migration
        
        Args:
            migration_id: ID of migration to rollback
            
        Returns:
            Rollback result
        """
        # Find the migration
        migration = next((m for m in self.migrations if m.migration_id == migration_id), None)
        
        if not migration:
            raise ValueError(f"Migration {migration_id} not found")
        
        try:
            with self.driver.session() as session:
                result = session.execute_write(
                    self._rollback_migration_tx,
                    migration
                )
                
                logger.info(f"Rolled back migration: {migration_id}")
                return {
                    "status": "success",
                    "migration_id": migration_id,
                    "result": result
                }
                
        except Exception as e:
            logger.error(f"Failed to rollback migration {migration_id}: {str(e)}")
            return {
                "status": "error",
                "migration_id": migration_id,
                "error": str(e)
            }
    
    def _rollback_migration_tx(self, tx: Transaction, migration: BaseMigration) -> Dict[str, Any]:
        """
        Rollback a migration in a transaction
        
        Args:
            tx: Neo4j transaction
            migration: Migration to rollback
            
        Returns:
            Rollback result
        """
        # Run the rollback
        result = migration.down(tx)
        
        # Remove migration record
        tx.run("""
            MATCH (m:Migration {migration_id: $migration_id})
            DELETE m
        """, migration_id=migration.migration_id)
        
        return result
    
    def get_migration_status(self) -> Dict[str, Any]:
        """
        Get current migration status
        
        Returns:
            Dictionary with migration status
        """
        # Use synchronous methods for status check
        applied = self._get_applied_migrations_sync()
        pending = self._get_pending_migrations_sync()
        
        with self.driver.session() as session:
            # Get detailed info about applied migrations
            result = session.run("""
                MATCH (m:Migration)
                RETURN m
                ORDER BY m.migration_id
            """)
            
            applied_details = []
            for record in result:
                migration = dict(record["m"])
                applied_details.append(migration)
        
        return {
            "total_migrations": len(self.migrations),
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied_migrations": applied_details,
            "pending_migrations": [
                {
                    "migration_id": m.migration_id,
                    "description": m.description
                }
                for m in pending
            ]
        }
    
    def _get_applied_migrations_sync(self) -> List[str]:
        """
        Synchronous version to get list of already applied migrations
        
        Returns:
            List of migration IDs
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (m:Migration)
                WHERE m.status = 'completed'
                RETURN m.migration_id as id
                ORDER BY m.migration_id
            """)
            
            return [record["id"] for record in result]
    
    def _get_pending_migrations_sync(self) -> List[BaseMigration]:
        """
        Synchronous version to get list of pending migrations
        
        Returns:
            List of migration objects
        """
        applied = set(self._get_applied_migrations_sync())
        return [m for m in self.migrations if m.migration_id not in applied]
    
    def run_migrations_sync(self, target: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronous version to run all pending migrations
        
        Args:
            target: Target migration ID (runs all if None)
            
        Returns:
            Dictionary with migration results
        """
        pending = self._get_pending_migrations_sync()
        
        if not pending:
            logger.info("No pending migrations")
            return {
                "status": "success",
                "message": "No pending migrations",
                "migrations_run": []
            }
        
        results = {
            "status": "success",
            "migrations_run": [],
            "errors": []
        }
        
        for migration in pending:
            if target and migration.migration_id > target:
                break
            
            try:
                logger.info(f"Running migration: {migration}")
                
                with self.driver.session() as session:
                    # Run migration in transaction
                    result = session.execute_write(
                        self._run_migration_tx,
                        migration
                    )
                    
                    results["migrations_run"].append({
                        "migration_id": migration.migration_id,
                        "description": migration.description,
                        "result": result
                    })
                    
                    logger.info(f"Completed migration: {migration.migration_id}")
                    
            except Exception as e:
                logger.error(f"Failed to run migration {migration.migration_id}: {str(e)}")
                results["status"] = "partial"
                results["errors"].append({
                    "migration_id": migration.migration_id,
                    "error": str(e)
                })
                # Stop on error
                break
        
        return results