"""
Data Migration Manager
Medical Case Management System

Comprehensive data migration capabilities for schema updates,
system upgrades, and data transformations with medical compliance.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import yaml

from neo4j import GraphDatabase
import aiofiles

logger = logging.getLogger(__name__)

class MigrationType(Enum):
    SCHEMA_UPDATE = "schema_update"
    DATA_TRANSFORMATION = "data_transformation"
    VERSION_UPGRADE = "version_upgrade"
    INDEX_REBUILD = "index_rebuild"
    CONSTRAINT_MODIFICATION = "constraint_modification"

class MigrationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class MigrationStep:
    """Individual migration step definition."""
    step_id: str
    description: str
    forward_cypher: str
    rollback_cypher: Optional[str]
    validation_cypher: Optional[str]
    required_data: Optional[Dict[str, Any]] = None
    timeout_seconds: int = 300

@dataclass
class Migration:
    """Complete migration definition."""
    migration_id: str
    version_from: str
    version_to: str
    migration_type: MigrationType
    description: str
    steps: List[MigrationStep]
    dependencies: List[str] = None
    auto_rollback: bool = True
    backup_required: bool = True

@dataclass
class MigrationRecord:
    """Migration execution record."""
    migration_id: str
    status: MigrationStatus
    started_at: datetime
    completed_at: Optional[datetime]
    executed_steps: List[str]
    failed_step: Optional[str] = None
    error_message: Optional[str] = None
    rollback_completed: bool = False

class MigrationManager:
    """
    Comprehensive data migration manager for medical case management system.
    
    Features:
    - Schema versioning and updates
    - Data transformation pipelines
    - Automatic rollback capabilities
    - Validation and integrity checks
    - Medical data compliance
    - Performance optimization
    """
    
    def __init__(self, 
                 neo4j_uri: str,
                 neo4j_user: str,
                 neo4j_password: str,
                 migrations_dir: Path):
        """
        Initialize migration manager.
        
        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            migrations_dir: Directory containing migration definitions
        """
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.migrations_dir = migrations_dir
        self.driver = None
        
        # Ensure migrations directory exists
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize migration tracking
        self._migration_records: Dict[str, MigrationRecord] = {}
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def connect(self):
        """Connect to Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            # Test connection
            async with self.driver.session() as session:
                await session.run("RETURN 1")
            
            # Initialize migration tracking
            await self._initialize_migration_tracking()
            logger.info("Connected to Neo4j for migration operations")
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    async def close(self):
        """Close Neo4j connection."""
        if self.driver:
            await self.driver.close()
            logger.info("Closed Neo4j connection")
    
    async def _initialize_migration_tracking(self):
        """Initialize migration tracking in database."""
        async with self.driver.session() as session:
            # Create migration tracking nodes if they don't exist
            await session.run("""
                MERGE (mt:MigrationTracker {id: 'system'})
                ON CREATE SET 
                    mt.created_at = datetime(),
                    mt.current_version = '1.0.0',
                    mt.migrations_applied = []
            """)
            
            # Load existing migration records
            result = await session.run("""
                MATCH (mr:MigrationRecord)
                RETURN mr
            """)
            
            async for record in result:
                migration_data = dict(record["mr"])
                migration_record = MigrationRecord(
                    migration_id=migration_data["migration_id"],
                    status=MigrationStatus(migration_data["status"]),
                    started_at=datetime.fromisoformat(migration_data["started_at"]),
                    completed_at=datetime.fromisoformat(migration_data["completed_at"]) if migration_data.get("completed_at") else None,
                    executed_steps=migration_data.get("executed_steps", []),
                    failed_step=migration_data.get("failed_step"),
                    error_message=migration_data.get("error_message"),
                    rollback_completed=migration_data.get("rollback_completed", False)
                )
                self._migration_records[migration_record.migration_id] = migration_record
    
    async def load_migration(self, migration_file: Path) -> Migration:
        """
        Load migration definition from YAML file.
        
        Args:
            migration_file: Path to migration YAML file
            
        Returns:
            Migration object
        """
        async with aiofiles.open(migration_file, 'r') as f:
            migration_data = yaml.safe_load(await f.read())
        
        # Parse migration steps
        steps = []
        for step_data in migration_data.get("steps", []):
            step = MigrationStep(
                step_id=step_data["step_id"],
                description=step_data["description"],
                forward_cypher=step_data["forward_cypher"],
                rollback_cypher=step_data.get("rollback_cypher"),
                validation_cypher=step_data.get("validation_cypher"),
                required_data=step_data.get("required_data"),
                timeout_seconds=step_data.get("timeout_seconds", 300)
            )
            steps.append(step)
        
        migration = Migration(
            migration_id=migration_data["migration_id"],
            version_from=migration_data["version_from"],
            version_to=migration_data["version_to"],
            migration_type=MigrationType(migration_data["migration_type"]),
            description=migration_data["description"],
            steps=steps,
            dependencies=migration_data.get("dependencies", []),
            auto_rollback=migration_data.get("auto_rollback", True),
            backup_required=migration_data.get("backup_required", True)
        )
        
        return migration
    
    async def discover_migrations(self) -> List[Migration]:
        """
        Discover all available migrations in migrations directory.
        
        Returns:
            List of available migrations
        """
        migrations = []
        migration_files = list(self.migrations_dir.glob("*.yml")) + list(self.migrations_dir.glob("*.yaml"))
        
        for migration_file in migration_files:
            try:
                migration = await self.load_migration(migration_file)
                migrations.append(migration)
            except Exception as e:
                logger.error(f"Failed to load migration {migration_file}: {e}")
        
        # Sort by version
        migrations.sort(key=lambda m: m.version_to)
        return migrations
    
    async def get_current_version(self) -> str:
        """Get current database schema version."""
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (mt:MigrationTracker {id: 'system'})
                RETURN mt.current_version as version
            """)
            
            record = await result.single()
            return record["version"] if record else "1.0.0"
    
    async def get_pending_migrations(self, target_version: Optional[str] = None) -> List[Migration]:
        """
        Get migrations that need to be applied.
        
        Args:
            target_version: Target version to migrate to
            
        Returns:
            List of pending migrations
        """
        current_version = await self.get_current_version()
        all_migrations = await self.discover_migrations()
        
        # Filter migrations that haven't been applied
        pending = []
        for migration in all_migrations:
            if migration.migration_id not in self._migration_records:
                # Check version constraints
                if self._should_apply_migration(migration, current_version, target_version):
                    pending.append(migration)
            elif self._migration_records[migration.migration_id].status == MigrationStatus.FAILED:
                # Include failed migrations for retry
                pending.append(migration)
        
        return pending
    
    def _should_apply_migration(self, migration: Migration, current_version: str, target_version: Optional[str]) -> bool:
        """Check if migration should be applied based on version constraints."""
        # Simple version comparison (in production, use proper semver library)
        if migration.version_from <= current_version:
            if target_version is None or migration.version_to <= target_version:
                return True
        return False
    
    async def execute_migration(self, migration: Migration) -> MigrationRecord:
        """
        Execute a single migration.
        
        Args:
            migration: Migration to execute
            
        Returns:
            Migration execution record
        """
        migration_record = MigrationRecord(
            migration_id=migration.migration_id,
            status=MigrationStatus.RUNNING,
            started_at=datetime.now(),
            completed_at=None,
            executed_steps=[]
        )
        
        try:
            logger.info(f"Starting migration {migration.migration_id}: {migration.description}")
            
            # Save initial record
            await self._save_migration_record(migration_record)
            
            # Check dependencies
            await self._check_dependencies(migration)
            
            # Create backup if required
            if migration.backup_required:
                await self._create_migration_backup(migration.migration_id)
            
            # Execute migration steps
            async with self.driver.session() as session:
                for step in migration.steps:
                    logger.info(f"Executing step {step.step_id}: {step.description}")
                    
                    try:
                        # Execute forward migration
                        await asyncio.wait_for(
                            session.run(step.forward_cypher, step.required_data or {}),
                            timeout=step.timeout_seconds
                        )
                        
                        # Validate step if validation query provided
                        if step.validation_cypher:
                            validation_result = await session.run(step.validation_cypher)
                            validation_record = await validation_result.single()
                            if not validation_record or not validation_record.get("valid", True):
                                raise ValueError(f"Step validation failed: {step.step_id}")
                        
                        migration_record.executed_steps.append(step.step_id)
                        await self._save_migration_record(migration_record)
                        
                        logger.info(f"Completed step {step.step_id}")
                        
                    except Exception as e:
                        migration_record.failed_step = step.step_id
                        migration_record.error_message = str(e)
                        migration_record.status = MigrationStatus.FAILED
                        
                        logger.error(f"Step {step.step_id} failed: {e}")
                        
                        # Attempt rollback if enabled
                        if migration.auto_rollback:
                            await self._rollback_migration(migration, migration_record)
                        
                        raise
            
            # Update version if successful
            await self._update_database_version(migration.version_to)
            
            migration_record.status = MigrationStatus.COMPLETED
            migration_record.completed_at = datetime.now()
            
            logger.info(f"Migration {migration.migration_id} completed successfully")
            
        except Exception as e:
            migration_record.status = MigrationStatus.FAILED
            migration_record.completed_at = datetime.now()
            migration_record.error_message = str(e)
            
            logger.error(f"Migration {migration.migration_id} failed: {e}")
            
        finally:
            await self._save_migration_record(migration_record)
            self._migration_records[migration.migration_id] = migration_record
        
        return migration_record
    
    async def _check_dependencies(self, migration: Migration):
        """Check if migration dependencies are satisfied."""
        if not migration.dependencies:
            return
        
        for dependency_id in migration.dependencies:
            if dependency_id not in self._migration_records:
                raise ValueError(f"Missing dependency: {dependency_id}")
            
            dependency_record = self._migration_records[dependency_id]
            if dependency_record.status != MigrationStatus.COMPLETED:
                raise ValueError(f"Dependency {dependency_id} not completed successfully")
    
    async def _create_migration_backup(self, migration_id: str):
        """Create backup before migration."""
        # This would integrate with BackupManager
        logger.info(f"Creating backup before migration {migration_id}")
        # Implementation would depend on BackupManager integration
    
    async def _rollback_migration(self, migration: Migration, migration_record: MigrationRecord):
        """
        Rollback migration steps that were executed.
        
        Args:
            migration: Migration definition
            migration_record: Current migration record
        """
        logger.info(f"Rolling back migration {migration.migration_id}")
        
        try:
            async with self.driver.session() as session:
                # Rollback executed steps in reverse order
                executed_steps = migration_record.executed_steps
                
                for step_id in reversed(executed_steps):
                    # Find the step definition
                    step = next((s for s in migration.steps if s.step_id == step_id), None)
                    
                    if step and step.rollback_cypher:
                        logger.info(f"Rolling back step {step_id}")
                        
                        await asyncio.wait_for(
                            session.run(step.rollback_cypher, step.required_data or {}),
                            timeout=step.timeout_seconds
                        )
                        
                        logger.info(f"Rolled back step {step_id}")
                    else:
                        logger.warning(f"No rollback defined for step {step_id}")
            
            migration_record.status = MigrationStatus.ROLLED_BACK
            migration_record.rollback_completed = True
            
            logger.info(f"Migration {migration.migration_id} rolled back successfully")
            
        except Exception as e:
            logger.error(f"Rollback failed for migration {migration.migration_id}: {e}")
            migration_record.error_message = f"Rollback failed: {e}"
    
    async def _update_database_version(self, new_version: str):
        """Update current database version."""
        async with self.driver.session() as session:
            await session.run("""
                MATCH (mt:MigrationTracker {id: 'system'})
                SET mt.current_version = $version,
                    mt.updated_at = datetime()
            """, {"version": new_version})
    
    async def _save_migration_record(self, migration_record: MigrationRecord):
        """Save migration record to database."""
        async with self.driver.session() as session:
            await session.run("""
                MERGE (mr:MigrationRecord {migration_id: $migration_id})
                SET mr.status = $status,
                    mr.started_at = $started_at,
                    mr.completed_at = $completed_at,
                    mr.executed_steps = $executed_steps,
                    mr.failed_step = $failed_step,
                    mr.error_message = $error_message,
                    mr.rollback_completed = $rollback_completed
            """, {
                "migration_id": migration_record.migration_id,
                "status": migration_record.status.value,
                "started_at": migration_record.started_at.isoformat(),
                "completed_at": migration_record.completed_at.isoformat() if migration_record.completed_at else None,
                "executed_steps": migration_record.executed_steps,
                "failed_step": migration_record.failed_step,
                "error_message": migration_record.error_message,
                "rollback_completed": migration_record.rollback_completed
            })
    
    async def migrate_to_version(self, target_version: str) -> List[MigrationRecord]:
        """
        Migrate database to specific version.
        
        Args:
            target_version: Target version to migrate to
            
        Returns:
            List of migration records
        """
        pending_migrations = await self.get_pending_migrations(target_version)
        
        if not pending_migrations:
            logger.info(f"Database is already at version {target_version}")
            return []
        
        logger.info(f"Found {len(pending_migrations)} migrations to execute")
        
        migration_records = []
        
        for migration in pending_migrations:
            try:
                record = await self.execute_migration(migration)
                migration_records.append(record)
                
                if record.status != MigrationStatus.COMPLETED:
                    logger.error(f"Migration {migration.migration_id} failed, stopping migration process")
                    break
                    
            except Exception as e:
                logger.error(f"Failed to execute migration {migration.migration_id}: {e}")
                break
        
        current_version = await self.get_current_version()
        logger.info(f"Migration process completed. Current version: {current_version}")
        
        return migration_records
    
    async def get_migration_history(self) -> List[MigrationRecord]:
        """Get complete migration history."""
        return list(self._migration_records.values())
    
    async def create_migration_template(self, 
                                     migration_id: str,
                                     version_from: str,
                                     version_to: str,
                                     migration_type: MigrationType,
                                     description: str) -> Path:
        """
        Create migration template file.
        
        Args:
            migration_id: Unique migration identifier
            version_from: Source version
            version_to: Target version
            migration_type: Type of migration
            description: Migration description
            
        Returns:
            Path to created migration file
        """
        template = {
            "migration_id": migration_id,
            "version_from": version_from,
            "version_to": version_to,
            "migration_type": migration_type.value,
            "description": description,
            "dependencies": [],
            "auto_rollback": True,
            "backup_required": True,
            "steps": [
                {
                    "step_id": "step_001",
                    "description": "Example migration step",
                    "forward_cypher": "// Add your forward migration Cypher here",
                    "rollback_cypher": "// Add your rollback Cypher here (optional)",
                    "validation_cypher": "// Add validation Cypher here (optional)",
                    "timeout_seconds": 300
                }
            ]
        }
        
        migration_file = self.migrations_dir / f"{migration_id}.yml"
        
        async with aiofiles.open(migration_file, 'w') as f:
            await f.write(yaml.dump(template, default_flow_style=False, indent=2))
        
        logger.info(f"Created migration template: {migration_file}")
        return migration_file
    
    async def validate_migration(self, migration: Migration) -> List[str]:
        """
        Validate migration definition.
        
        Args:
            migration: Migration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check basic structure
        if not migration.migration_id:
            errors.append("Migration ID is required")
        
        if not migration.steps:
            errors.append("At least one migration step is required")
        
        # Check step definitions
        step_ids = set()
        for step in migration.steps:
            if not step.step_id:
                errors.append("Step ID is required for all steps")
            elif step.step_id in step_ids:
                errors.append(f"Duplicate step ID: {step.step_id}")
            else:
                step_ids.add(step.step_id)
            
            if not step.forward_cypher or step.forward_cypher.strip() == "":
                errors.append(f"Forward Cypher is required for step {step.step_id}")
        
        # Check dependencies exist
        if migration.dependencies:
            all_migrations = await self.discover_migrations()
            available_ids = {m.migration_id for m in all_migrations}
            
            for dep_id in migration.dependencies:
                if dep_id not in available_ids:
                    errors.append(f"Dependency not found: {dep_id}")
        
        return errors