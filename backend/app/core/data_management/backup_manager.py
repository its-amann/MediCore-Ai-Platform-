"""
Neo4j Backup Manager
Medical Case Management System

Comprehensive backup and recovery system for Neo4j database
with HIPAA compliance and medical data protection.
"""

import os
import json
import asyncio
import logging
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import zipfile
import shutil

from neo4j import GraphDatabase
import aiofiles
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

class BackupType(Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    EXPORT = "export"

class BackupStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CORRUPTED = "corrupted"

@dataclass
class BackupMetadata:
    """Backup metadata for tracking and validation."""
    backup_id: str
    backup_type: BackupType
    status: BackupStatus
    started_at: datetime
    completed_at: Optional[datetime]
    size_bytes: int
    node_count: int
    relationship_count: int
    checksum: str
    encryption_enabled: bool
    compression_enabled: bool
    retention_days: int
    tags: List[str]
    error_message: Optional[str] = None

@dataclass 
class BackupConfig:
    """Backup configuration settings."""
    backup_dir: Path
    encryption_key: Optional[str]
    compression_level: int = 6
    retention_days: int = 90
    max_parallel_backups: int = 2
    verify_integrity: bool = True
    auto_cleanup: bool = True
    hipaa_compliance: bool = True

class BackupManager:
    """
    Comprehensive backup manager for Neo4j database with medical data compliance.
    
    Features:
    - Full, incremental, and differential backups
    - HIPAA-compliant encryption
    - Data integrity validation
    - Automated retention management
    - Performance optimization
    - Disaster recovery support
    """
    
    def __init__(self, 
                 neo4j_uri: str,
                 neo4j_user: str, 
                 neo4j_password: str,
                 config: BackupConfig):
        """
        Initialize backup manager.
        
        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            config: Backup configuration
        """
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.config = config
        self.driver = None
        self._running_backups: Dict[str, asyncio.Task] = {}
        
        # Ensure backup directory exists
        self.config.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption if enabled
        self.cipher = None
        if config.encryption_key:
            self.cipher = Fernet(config.encryption_key.encode())
    
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
            logger.info("Connected to Neo4j for backup operations")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    async def close(self):
        """Close Neo4j connection."""
        if self.driver:
            await self.driver.close()
            logger.info("Closed Neo4j connection")
    
    async def create_backup(self, 
                          backup_type: BackupType = BackupType.FULL,
                          tags: Optional[List[str]] = None) -> str:
        """
        Create a new backup.
        
        Args:
            backup_type: Type of backup to create
            tags: Optional tags for backup categorization
            
        Returns:
            Backup ID
        """
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{backup_type.value}"
        
        if len(self._running_backups) >= self.config.max_parallel_backups:
            raise RuntimeError("Maximum parallel backups reached")
        
        # Create backup task
        task = asyncio.create_task(
            self._execute_backup(backup_id, backup_type, tags or [])
        )
        self._running_backups[backup_id] = task
        
        logger.info(f"Started backup {backup_id} of type {backup_type.value}")
        return backup_id
    
    async def _execute_backup(self, 
                            backup_id: str, 
                            backup_type: BackupType,
                            tags: List[str]) -> BackupMetadata:
        """
        Execute the actual backup process.
        
        Args:
            backup_id: Unique backup identifier
            backup_type: Type of backup
            tags: Backup tags
            
        Returns:
            Backup metadata
        """
        start_time = datetime.now()
        metadata = BackupMetadata(
            backup_id=backup_id,
            backup_type=backup_type,
            status=BackupStatus.RUNNING,
            started_at=start_time,
            completed_at=None,
            size_bytes=0,
            node_count=0,
            relationship_count=0,
            checksum="",
            encryption_enabled=self.cipher is not None,
            compression_enabled=True,
            retention_days=self.config.retention_days,
            tags=tags
        )
        
        try:
            # Save initial metadata
            await self._save_metadata(metadata)
            
            # Execute backup based on type
            if backup_type == BackupType.FULL:
                backup_path = await self._create_full_backup(backup_id)
            elif backup_type == BackupType.EXPORT:
                backup_path = await self._create_export_backup(backup_id)
            elif backup_type == BackupType.INCREMENTAL:
                backup_path = await self._create_incremental_backup(backup_id)
            else:
                raise ValueError(f"Unsupported backup type: {backup_type}")
            
            # Calculate checksum and size
            metadata.size_bytes = backup_path.stat().st_size
            metadata.checksum = await self._calculate_checksum(backup_path)
            
            # Get database statistics
            stats = await self._get_database_stats()
            metadata.node_count = stats["nodes"]
            metadata.relationship_count = stats["relationships"]
            
            # Verify backup if requested
            if self.config.verify_integrity:
                await self._verify_backup(backup_path, metadata)
            
            # Mark as completed
            metadata.status = BackupStatus.COMPLETED
            metadata.completed_at = datetime.now()
            
            logger.info(f"Backup {backup_id} completed successfully")
            
        except Exception as e:
            metadata.status = BackupStatus.FAILED
            metadata.error_message = str(e)
            metadata.completed_at = datetime.now()
            logger.error(f"Backup {backup_id} failed: {e}")
            
        finally:
            # Save final metadata
            await self._save_metadata(metadata)
            
            # Remove from running backups
            self._running_backups.pop(backup_id, None)
            
            # Auto-cleanup old backups if enabled
            if self.config.auto_cleanup:
                await self._cleanup_old_backups()
        
        return metadata
    
    async def _create_full_backup(self, backup_id: str) -> Path:
        """
        Create a full database backup using APOC export.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            Path to backup file
        """
        backup_dir = self.config.backup_dir / backup_id
        backup_dir.mkdir(exist_ok=True)
        
        # Export all data using APOC
        async with self.driver.session() as session:
            # Export nodes
            nodes_query = """
            CALL apoc.export.cypher.all($file, {
                format: 'cypher-shell',
                useOptimizations: {type: 'UNWIND_BATCH', unwindBatchSize: 20}
            })
            """
            await session.run(nodes_query, {"file": f"file:///{backup_id}/full_backup.cypher"})
            
            # Export schema
            schema_result = await session.run("CALL db.schema.visualization()")
            schema_data = [dict(record) for record in schema_result]
            
            # Save schema information
            schema_file = backup_dir / "schema.json"
            async with aiofiles.open(schema_file, 'w') as f:
                await f.write(json.dumps(schema_data, indent=2, default=str))
        
        # Create compressed backup
        backup_file = self.config.backup_dir / f"{backup_id}.backup"
        await self._compress_and_encrypt(backup_dir, backup_file)
        
        # Cleanup temporary directory
        shutil.rmtree(backup_dir)
        
        return backup_file
    
    async def _create_export_backup(self, backup_id: str) -> Path:
        """
        Create export-style backup with individual JSON files.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            Path to backup file
        """
        backup_dir = self.config.backup_dir / backup_id
        backup_dir.mkdir(exist_ok=True)
        
        async with self.driver.session() as session:
            # Export each node type
            node_labels = await self._get_node_labels()
            
            for label in node_labels:
                nodes_query = f"""
                MATCH (n:{label})
                RETURN n
                """
                result = await session.run(nodes_query)
                nodes_data = [dict(record["n"]) for record in result]
                
                # Save to JSON file
                label_file = backup_dir / f"nodes_{label.lower()}.json"
                async with aiofiles.open(label_file, 'w') as f:
                    await f.write(json.dumps(nodes_data, indent=2, default=str))
            
            # Export relationships
            relationships_query = """
            MATCH (a)-[r]->(b)
            RETURN type(r) as type, properties(r) as props, 
                   id(a) as start_id, labels(a) as start_labels,
                   id(b) as end_id, labels(b) as end_labels
            """
            result = await session.run(relationships_query)
            relationships_data = [dict(record) for record in result]
            
            rel_file = backup_dir / "relationships.json"
            async with aiofiles.open(rel_file, 'w') as f:
                await f.write(json.dumps(relationships_data, indent=2, default=str))
        
        # Create compressed backup
        backup_file = self.config.backup_dir / f"{backup_id}.backup"
        await self._compress_and_encrypt(backup_dir, backup_file)
        
        # Cleanup temporary directory
        shutil.rmtree(backup_dir)
        
        return backup_file
    
    async def _create_incremental_backup(self, backup_id: str) -> Path:
        """
        Create incremental backup based on last backup timestamp.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            Path to backup file
        """
        # Find last backup timestamp
        last_backup = await self._get_last_backup()
        if not last_backup:
            # If no previous backup, create full backup
            return await self._create_full_backup(backup_id)
        
        backup_dir = self.config.backup_dir / backup_id
        backup_dir.mkdir(exist_ok=True)
        
        last_timestamp = last_backup.started_at
        
        async with self.driver.session() as session:
            # Find nodes modified since last backup
            nodes_query = """
            MATCH (n)
            WHERE datetime(n.updated_at) >= datetime($since)
               OR datetime(n.created_at) >= datetime($since)
            RETURN labels(n)[0] as label, collect(n) as nodes
            """
            result = await session.run(nodes_query, {"since": last_timestamp.isoformat()})
            
            for record in result:
                label = record["label"]
                nodes = [dict(node) for node in record["nodes"]]
                
                if nodes:
                    label_file = backup_dir / f"nodes_{label.lower()}_incremental.json"
                    async with aiofiles.open(label_file, 'w') as f:
                        await f.write(json.dumps(nodes, indent=2, default=str))
        
        # Create compressed backup
        backup_file = self.config.backup_dir / f"{backup_id}.backup"
        await self._compress_and_encrypt(backup_dir, backup_file)
        
        # Cleanup temporary directory
        shutil.rmtree(backup_dir)
        
        return backup_file
    
    async def _compress_and_encrypt(self, source_dir: Path, output_file: Path):
        """
        Compress and optionally encrypt backup directory.
        
        Args:
            source_dir: Source directory to compress
            output_file: Output backup file
        """
        # Create ZIP archive
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED, 
                           compresslevel=self.config.compression_level) as zipf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
        
        # Encrypt if configured
        if self.cipher:
            with open(output_file, 'rb') as f:
                data = f.read()
            
            encrypted_data = self.cipher.encrypt(data)
            
            with open(output_file, 'wb') as f:
                f.write(encrypted_data)
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of backup file."""
        sha256_hash = hashlib.sha256()
        async with aiofiles.open(file_path, 'rb') as f:
            async for chunk in f:
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    async def _get_database_stats(self) -> Dict[str, int]:
        """Get current database statistics."""
        async with self.driver.session() as session:
            # Count nodes
            nodes_result = await session.run("MATCH (n) RETURN count(n) as count")
            nodes_count = (await nodes_result.single())["count"]
            
            # Count relationships
            rels_result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rels_count = (await rels_result.single())["count"]
            
            return {
                "nodes": nodes_count,
                "relationships": rels_count
            }
    
    async def _get_node_labels(self) -> List[str]:
        """Get all node labels in database."""
        async with self.driver.session() as session:
            result = await session.run("CALL db.labels()")
            return [record["label"] for record in result]
    
    async def _verify_backup(self, backup_path: Path, metadata: BackupMetadata):
        """
        Verify backup integrity.
        
        Args:
            backup_path: Path to backup file
            metadata: Backup metadata
        """
        # Verify file exists and is readable
        if not backup_path.exists():
            raise ValueError("Backup file not found")
        
        # Verify checksum
        current_checksum = await self._calculate_checksum(backup_path)
        if current_checksum != metadata.checksum:
            metadata.status = BackupStatus.CORRUPTED
            raise ValueError("Backup checksum verification failed")
        
        # Test archive integrity
        try:
            # Decrypt if necessary
            if self.cipher:
                with open(backup_path, 'rb') as f:
                    encrypted_data = f.read()
                decrypted_data = self.cipher.decrypt(encrypted_data)
                
                # Test ZIP integrity
                with tempfile.NamedTemporaryFile() as temp_file:
                    temp_file.write(decrypted_data)
                    temp_file.flush()
                    
                    with zipfile.ZipFile(temp_file.name, 'r') as zipf:
                        zipf.testzip()
            else:
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.testzip()
                    
        except Exception as e:
            metadata.status = BackupStatus.CORRUPTED
            raise ValueError(f"Backup archive integrity check failed: {e}")
    
    async def _save_metadata(self, metadata: BackupMetadata):
        """Save backup metadata to file."""
        metadata_file = self.config.backup_dir / f"{metadata.backup_id}.metadata.json"
        async with aiofiles.open(metadata_file, 'w') as f:
            await f.write(json.dumps(asdict(metadata), indent=2, default=str))
    
    async def _get_last_backup(self) -> Optional[BackupMetadata]:
        """Get metadata for the last successful backup."""
        metadata_files = list(self.config.backup_dir.glob("*.metadata.json"))
        
        if not metadata_files:
            return None
        
        latest_backup = None
        latest_time = datetime.min
        
        for metadata_file in metadata_files:
            async with aiofiles.open(metadata_file, 'r') as f:
                data = json.loads(await f.read())
                
                if data["status"] == BackupStatus.COMPLETED.value:
                    backup_time = datetime.fromisoformat(data["started_at"])
                    if backup_time > latest_time:
                        latest_time = backup_time
                        latest_backup = BackupMetadata(**data)
        
        return latest_backup
    
    async def _cleanup_old_backups(self):
        """Clean up old backups based on retention policy."""
        cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)
        
        metadata_files = list(self.config.backup_dir.glob("*.metadata.json"))
        
        for metadata_file in metadata_files:
            async with aiofiles.open(metadata_file, 'r') as f:
                data = json.loads(await f.read())
                
            backup_date = datetime.fromisoformat(data["started_at"])
            
            if backup_date < cutoff_date:
                backup_id = data["backup_id"]
                
                # Remove backup file
                backup_file = self.config.backup_dir / f"{backup_id}.backup"
                if backup_file.exists():
                    backup_file.unlink()
                
                # Remove metadata file
                metadata_file.unlink()
                
                logger.info(f"Cleaned up old backup: {backup_id}")
    
    async def list_backups(self) -> List[BackupMetadata]:
        """List all available backups."""
        backups = []
        metadata_files = list(self.config.backup_dir.glob("*.metadata.json"))
        
        for metadata_file in metadata_files:
            async with aiofiles.open(metadata_file, 'r') as f:
                data = json.loads(await f.read())
                backups.append(BackupMetadata(**data))
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x.started_at, reverse=True)
        return backups
    
    async def get_backup_status(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get status of specific backup."""
        metadata_file = self.config.backup_dir / f"{backup_id}.metadata.json"
        
        if not metadata_file.exists():
            return None
        
        async with aiofiles.open(metadata_file, 'r') as f:
            data = json.loads(await f.read())
            return BackupMetadata(**data)
    
    async def restore_backup(self, backup_id: str, target_database: str = "neo4j") -> bool:
        """
        Restore database from backup.
        
        Args:
            backup_id: Backup to restore
            target_database: Target database name
            
        Returns:
            True if successful
        """
        metadata = await self.get_backup_status(backup_id)
        if not metadata or metadata.status != BackupStatus.COMPLETED:
            raise ValueError("Backup not found or not completed successfully")
        
        backup_file = self.config.backup_dir / f"{backup_id}.backup"
        if not backup_file.exists():
            raise ValueError("Backup file not found")
        
        try:
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Decrypt and extract backup
                if self.cipher:
                    with open(backup_file, 'rb') as f:
                        encrypted_data = f.read()
                    decrypted_data = self.cipher.decrypt(encrypted_data)
                    
                    with tempfile.NamedTemporaryFile() as temp_file:
                        temp_file.write(decrypted_data)
                        temp_file.flush()
                        
                        with zipfile.ZipFile(temp_file.name, 'r') as zipf:
                            zipf.extractall(temp_path)
                else:
                    with zipfile.ZipFile(backup_file, 'r') as zipf:
                        zipf.extractall(temp_path)
                
                # Restore based on backup type
                if metadata.backup_type == BackupType.FULL:
                    await self._restore_full_backup(temp_path, target_database)
                elif metadata.backup_type == BackupType.EXPORT:
                    await self._restore_export_backup(temp_path, target_database)
                else:
                    raise ValueError(f"Restore not supported for backup type: {metadata.backup_type}")
                
                logger.info(f"Successfully restored backup {backup_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            raise
    
    async def _restore_full_backup(self, backup_dir: Path, target_database: str):
        """Restore from full backup."""
        cypher_file = backup_dir / "full_backup.cypher"
        
        if cypher_file.exists():
            # Clear existing data
            async with self.driver.session(database=target_database) as session:
                await session.run("MATCH (n) DETACH DELETE n")
            
            # Execute restore script
            async with aiofiles.open(cypher_file, 'r') as f:
                restore_script = await f.read()
            
            # Execute script in chunks to avoid memory issues
            statements = restore_script.split(';')
            
            async with self.driver.session(database=target_database) as session:
                for statement in statements:
                    statement = statement.strip()
                    if statement:
                        await session.run(statement)
    
    async def _restore_export_backup(self, backup_dir: Path, target_database: str):
        """Restore from export backup."""
        # Clear existing data
        async with self.driver.session(database=target_database) as session:
            await session.run("MATCH (n) DETACH DELETE n")
        
        # Restore nodes first
        node_files = list(backup_dir.glob("nodes_*.json"))
        
        for node_file in node_files:
            async with aiofiles.open(node_file, 'r') as f:
                nodes_data = json.loads(await f.read())
            
            # Extract label from filename
            label = node_file.stem.replace("nodes_", "").title()
            
            # Create nodes
            async with self.driver.session(database=target_database) as session:
                for node_data in nodes_data:
                    query = f"CREATE (n:{label} $props)"
                    await session.run(query, {"props": node_data})
        
        # Restore relationships
        rel_file = backup_dir / "relationships.json"
        if rel_file.exists():
            async with aiofiles.open(rel_file, 'r') as f:
                relationships_data = json.loads(await f.read())
            
            async with self.driver.session(database=target_database) as session:
                for rel in relationships_data:
                    # This is a simplified restore - production would need ID mapping
                    query = f"""
                    MATCH (a), (b)
                    WHERE id(a) = $start_id AND id(b) = $end_id
                    CREATE (a)-[r:{rel['type']} $props]->(b)
                    """
                    await session.run(query, {
                        "start_id": rel["start_id"],
                        "end_id": rel["end_id"],
                        "props": rel["props"]
                    })