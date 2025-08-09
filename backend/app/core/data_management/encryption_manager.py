"""
Encryption Manager
Medical Case Management System

HIPAA-compliant encryption management for medical data protection,
backup security, and data-at-rest/in-transit encryption.
"""

import os
import base64
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import aiofiles

logger = logging.getLogger(__name__)

class EncryptionType(Enum):
    AES_256_GCM = "aes_256_gcm"
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"
    FERNET = "fernet"

class DataClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"  # PHI/PII data
    TOP_SECRET = "top_secret"  # Critical medical data

@dataclass
class EncryptionKey:
    """Encryption key metadata and storage."""
    key_id: str
    encryption_type: EncryptionType
    key_data: bytes
    created_at: datetime
    expires_at: Optional[datetime]
    data_classification: DataClassification
    usage_count: int = 0
    max_usage: Optional[int] = None
    is_active: bool = True

@dataclass
class EncryptedData:
    """Encrypted data container with metadata."""
    data_id: str
    encrypted_data: bytes
    key_id: str
    encryption_type: EncryptionType
    salt: Optional[bytes]
    iv: Optional[bytes]
    metadata: Dict[str, Any]
    encrypted_at: datetime
    data_classification: DataClassification

class EncryptionManager:
    """
    HIPAA-compliant encryption manager for medical data protection.
    
    Features:
    - AES-256-GCM encryption for data at rest
    - RSA encryption for key exchange
    - Key rotation and lifecycle management
    - Data classification-based encryption
    - Audit logging for compliance
    - Performance-optimized operations
    """
    
    def __init__(self, 
                 key_storage_path: str,
                 master_key: Optional[str] = None,
                 key_rotation_days: int = 90):
        """
        Initialize encryption manager.
        
        Args:
            key_storage_path: Path to store encryption keys
            master_key: Master key for key encryption (derived if not provided)
            key_rotation_days: Days between automatic key rotation
        """
        self.key_storage_path = key_storage_path
        self.key_rotation_days = key_rotation_days
        self.keys: Dict[str, EncryptionKey] = {}
        
        # Ensure key storage directory exists
        os.makedirs(key_storage_path, exist_ok=True)
        
        # Initialize master key for key encryption
        if master_key:
            self.master_key = master_key.encode()
        else:
            self.master_key = self._derive_master_key()
        
        # Initialize key encryption cipher
        self.key_cipher = Fernet(base64.urlsafe_b64encode(self.master_key[:32]))
        
        # Load existing keys
        self._load_existing_keys()
    
    def _derive_master_key(self) -> bytes:
        """Derive master key from environment or generate new one."""
        # In production, this should come from HSM or secure key management service
        master_key_env = os.getenv("MEDICAL_AI_MASTER_KEY")
        
        if master_key_env:
            # Derive key from environment variable
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"medical_ai_salt_2025",  # Should be unique per deployment
                iterations=100000,
                backend=default_backend()
            )
            return kdf.derive(master_key_env.encode())
        else:
            # Generate new master key (for development only)
            logger.warning("No master key found in environment, generating new key")
            return secrets.token_bytes(32)
    
    def _load_existing_keys(self):
        """Load existing encryption keys from storage."""
        key_index_file = os.path.join(self.key_storage_path, "key_index.json")
        
        if os.path.exists(key_index_file):
            try:
                with open(key_index_file, 'r') as f:
                    key_index = json.load(f)
                
                for key_id, key_info in key_index.items():
                    key_file = os.path.join(self.key_storage_path, f"{key_id}.key")
                    
                    if os.path.exists(key_file):
                        with open(key_file, 'rb') as f:
                            encrypted_key_data = f.read()
                        
                        # Decrypt key data
                        key_data = self.key_cipher.decrypt(encrypted_key_data)
                        
                        # Create encryption key object
                        encryption_key = EncryptionKey(
                            key_id=key_id,
                            encryption_type=EncryptionType(key_info["encryption_type"]),
                            key_data=key_data,
                            created_at=datetime.fromisoformat(key_info["created_at"]),
                            expires_at=datetime.fromisoformat(key_info["expires_at"]) if key_info.get("expires_at") else None,
                            data_classification=DataClassification(key_info["data_classification"]),
                            usage_count=key_info.get("usage_count", 0),
                            max_usage=key_info.get("max_usage"),
                            is_active=key_info.get("is_active", True)
                        )
                        
                        self.keys[key_id] = encryption_key
                
                logger.info(f"Loaded {len(self.keys)} encryption keys")
                
            except Exception as e:
                logger.error(f"Failed to load encryption keys: {e}")
    
    def _save_key_index(self):
        """Save encryption key index to storage."""
        key_index = {}
        
        for key_id, key in self.keys.items():
            key_index[key_id] = {
                "encryption_type": key.encryption_type.value,
                "created_at": key.created_at.isoformat(),
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "data_classification": key.data_classification.value,
                "usage_count": key.usage_count,
                "max_usage": key.max_usage,
                "is_active": key.is_active
            }
        
        key_index_file = os.path.join(self.key_storage_path, "key_index.json")
        
        with open(key_index_file, 'w') as f:
            json.dump(key_index, f, indent=2)
    
    def generate_key(self, 
                    encryption_type: EncryptionType,
                    data_classification: DataClassification,
                    expires_in_days: Optional[int] = None,
                    max_usage: Optional[int] = None) -> str:
        """
        Generate new encryption key.
        
        Args:
            encryption_type: Type of encryption key
            data_classification: Data classification level
            expires_in_days: Key expiration in days
            max_usage: Maximum usage count
            
        Returns:
            Key ID
        """
        key_id = f"key_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(8)}"
        
        # Generate key based on type
        if encryption_type == EncryptionType.FERNET:
            key_data = Fernet.generate_key()
        elif encryption_type == EncryptionType.AES_256_GCM:
            key_data = secrets.token_bytes(32)  # 256-bit key
        elif encryption_type == EncryptionType.RSA_2048:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            key_data = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        elif encryption_type == EncryptionType.RSA_4096:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )
            key_data = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        else:
            raise ValueError(f"Unsupported encryption type: {encryption_type}")
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        # Create encryption key
        encryption_key = EncryptionKey(
            key_id=key_id,
            encryption_type=encryption_type,
            key_data=key_data,
            created_at=datetime.now(),
            expires_at=expires_at,
            data_classification=data_classification,
            max_usage=max_usage
        )
        
        # Store key
        self.keys[key_id] = encryption_key
        self._save_encrypted_key(encryption_key)
        self._save_key_index()
        
        logger.info(f"Generated new {encryption_type.value} key {key_id} for {data_classification.value} data")
        return key_id
    
    def _save_encrypted_key(self, encryption_key: EncryptionKey):
        """Save encrypted key to storage."""
        key_file = os.path.join(self.key_storage_path, f"{encryption_key.key_id}.key")
        
        # Encrypt key data with master key
        encrypted_key_data = self.key_cipher.encrypt(encryption_key.key_data)
        
        with open(key_file, 'wb') as f:
            f.write(encrypted_key_data)
    
    def encrypt_data(self, 
                    data: Union[str, bytes],
                    data_classification: DataClassification,
                    metadata: Optional[Dict[str, Any]] = None) -> EncryptedData:
        """
        Encrypt data based on classification level.
        
        Args:
            data: Data to encrypt
            data_classification: Data classification level
            metadata: Optional metadata
            
        Returns:
            Encrypted data container
        """
        # Convert string to bytes if necessary
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Select appropriate encryption type based on classification
        encryption_type = self._get_encryption_type_for_classification(data_classification)
        
        # Get or create encryption key
        key_id = self._get_active_key(encryption_type, data_classification)
        if not key_id:
            key_id = self.generate_key(encryption_type, data_classification, expires_in_days=self.key_rotation_days)
        
        encryption_key = self.keys[key_id]
        
        # Encrypt data
        if encryption_type == EncryptionType.FERNET:
            cipher = Fernet(encryption_key.key_data)
            encrypted_data = cipher.encrypt(data)
            salt = None
            iv = None
        elif encryption_type == EncryptionType.AES_256_GCM:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            
            # Generate IV for GCM mode
            iv = secrets.token_bytes(12)  # 96-bit IV for GCM
            salt = None
            
            cipher = Cipher(
                algorithms.AES(encryption_key.key_data),
                modes.GCM(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            encrypted_data = encryptor.update(data) + encryptor.finalize()
            
            # Append authentication tag
            encrypted_data += encryptor.tag
        else:
            raise ValueError(f"Encryption type {encryption_type} not supported for data encryption")
        
        # Update key usage
        encryption_key.usage_count += 1
        self._save_key_index()
        
        # Create encrypted data container
        data_id = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(8)}"
        
        encrypted_container = EncryptedData(
            data_id=data_id,
            encrypted_data=encrypted_data,
            key_id=key_id,
            encryption_type=encryption_type,
            salt=salt,
            iv=iv,
            metadata=metadata or {},
            encrypted_at=datetime.now(),
            data_classification=data_classification
        )
        
        return encrypted_container
    
    def decrypt_data(self, encrypted_container: EncryptedData) -> bytes:
        """
        Decrypt data from encrypted container.
        
        Args:
            encrypted_container: Encrypted data container
            
        Returns:
            Decrypted data
        """
        # Get encryption key
        if encrypted_container.key_id not in self.keys:
            raise ValueError(f"Encryption key not found: {encrypted_container.key_id}")
        
        encryption_key = self.keys[encrypted_container.key_id]
        
        # Check key status
        if not encryption_key.is_active:
            raise ValueError(f"Encryption key is inactive: {encrypted_container.key_id}")
        
        if encryption_key.expires_at and encryption_key.expires_at < datetime.now():
            raise ValueError(f"Encryption key has expired: {encrypted_container.key_id}")
        
        # Decrypt data
        if encrypted_container.encryption_type == EncryptionType.FERNET:
            cipher = Fernet(encryption_key.key_data)
            decrypted_data = cipher.decrypt(encrypted_container.encrypted_data)
        elif encrypted_container.encryption_type == EncryptionType.AES_256_GCM:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            
            # Extract authentication tag (last 16 bytes)
            encrypted_data = encrypted_container.encrypted_data[:-16]
            auth_tag = encrypted_container.encrypted_data[-16:]
            
            cipher = Cipher(
                algorithms.AES(encryption_key.key_data),
                modes.GCM(encrypted_container.iv, auth_tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
        else:
            raise ValueError(f"Decryption type {encrypted_container.encryption_type} not supported")
        
        return decrypted_data
    
    def _get_encryption_type_for_classification(self, classification: DataClassification) -> EncryptionType:
        """Get appropriate encryption type for data classification."""
        classification_mapping = {
            DataClassification.PUBLIC: EncryptionType.FERNET,
            DataClassification.INTERNAL: EncryptionType.FERNET,
            DataClassification.CONFIDENTIAL: EncryptionType.AES_256_GCM,
            DataClassification.RESTRICTED: EncryptionType.AES_256_GCM,  # PHI/PII
            DataClassification.TOP_SECRET: EncryptionType.AES_256_GCM   # Critical medical data
        }
        return classification_mapping[classification]
    
    def _get_active_key(self, 
                       encryption_type: EncryptionType,
                       data_classification: DataClassification) -> Optional[str]:
        """Get active encryption key for type and classification."""
        for key_id, key in self.keys.items():
            if (key.encryption_type == encryption_type and
                key.data_classification == data_classification and
                key.is_active and
                (not key.expires_at or key.expires_at > datetime.now()) and
                (not key.max_usage or key.usage_count < key.max_usage)):
                return key_id
        return None
    
    def rotate_keys(self, data_classification: Optional[DataClassification] = None) -> List[str]:
        """
        Rotate encryption keys.
        
        Args:
            data_classification: Specific classification to rotate (None for all)
            
        Returns:
            List of new key IDs
        """
        new_key_ids = []
        
        for key_id, key in list(self.keys.items()):
            should_rotate = False
            
            # Check if specific classification requested
            if data_classification and key.data_classification != data_classification:
                continue
            
            # Check if key needs rotation
            if key.expires_at and key.expires_at <= datetime.now():
                should_rotate = True
            elif key.max_usage and key.usage_count >= key.max_usage:
                should_rotate = True
            elif (datetime.now() - key.created_at).days >= self.key_rotation_days:
                should_rotate = True
            
            if should_rotate and key.is_active:
                # Deactivate old key
                key.is_active = False
                
                # Generate new key
                new_key_id = self.generate_key(
                    encryption_type=key.encryption_type,
                    data_classification=key.data_classification,
                    expires_in_days=self.key_rotation_days
                )
                new_key_ids.append(new_key_id)
                
                logger.info(f"Rotated key {key_id} -> {new_key_id}")
        
        if new_key_ids:
            self._save_key_index()
        
        return new_key_ids
    
    def encrypt_backup_file(self, file_path: str, output_path: str) -> str:
        """
        Encrypt backup file with appropriate security.
        
        Args:
            file_path: Source file path
            output_path: Encrypted output path
            
        Returns:
            Key ID used for encryption
        """
        # Use restricted classification for backup files
        data_classification = DataClassification.RESTRICTED
        
        # Read file data
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Encrypt file data
        encrypted_container = self.encrypt_data(
            file_data,
            data_classification,
            metadata={"original_file": file_path, "backup_type": "file"}
        )
        
        # Save encrypted container
        container_data = {
            "data_id": encrypted_container.data_id,
            "encrypted_data": base64.b64encode(encrypted_container.encrypted_data).decode('utf-8'),
            "key_id": encrypted_container.key_id,
            "encryption_type": encrypted_container.encryption_type.value,
            "salt": base64.b64encode(encrypted_container.salt).decode('utf-8') if encrypted_container.salt else None,
            "iv": base64.b64encode(encrypted_container.iv).decode('utf-8') if encrypted_container.iv else None,
            "metadata": encrypted_container.metadata,
            "encrypted_at": encrypted_container.encrypted_at.isoformat(),
            "data_classification": encrypted_container.data_classification.value
        }
        
        with open(output_path, 'w') as f:
            json.dump(container_data, f, indent=2)
        
        return encrypted_container.key_id
    
    def decrypt_backup_file(self, encrypted_file_path: str, output_path: str) -> str:
        """
        Decrypt backup file.
        
        Args:
            encrypted_file_path: Encrypted file path
            output_path: Decrypted output path
            
        Returns:
            Original file path
        """
        # Load encrypted container
        with open(encrypted_file_path, 'r') as f:
            container_data = json.load(f)
        
        # Reconstruct encrypted container
        encrypted_container = EncryptedData(
            data_id=container_data["data_id"],
            encrypted_data=base64.b64decode(container_data["encrypted_data"]),
            key_id=container_data["key_id"],
            encryption_type=EncryptionType(container_data["encryption_type"]),
            salt=base64.b64decode(container_data["salt"]) if container_data["salt"] else None,
            iv=base64.b64decode(container_data["iv"]) if container_data["iv"] else None,
            metadata=container_data["metadata"],
            encrypted_at=datetime.fromisoformat(container_data["encrypted_at"]),
            data_classification=DataClassification(container_data["data_classification"])
        )
        
        # Decrypt data
        decrypted_data = self.decrypt_data(encrypted_container)
        
        # Save decrypted file
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
        
        return container_data["metadata"].get("original_file", "unknown")
    
    def get_key_status(self) -> Dict[str, Any]:
        """Get status of all encryption keys."""
        status = {
            "total_keys": len(self.keys),
            "active_keys": 0,
            "expired_keys": 0,
            "keys_by_type": {},
            "keys_by_classification": {},
            "keys_needing_rotation": []
        }
        
        for key_id, key in self.keys.items():
            # Count active keys
            if key.is_active:
                status["active_keys"] += 1
            
            # Count expired keys
            if key.expires_at and key.expires_at <= datetime.now():
                status["expired_keys"] += 1
            
            # Count by type
            type_name = key.encryption_type.value
            status["keys_by_type"][type_name] = status["keys_by_type"].get(type_name, 0) + 1
            
            # Count by classification
            class_name = key.data_classification.value
            status["keys_by_classification"][class_name] = status["keys_by_classification"].get(class_name, 0) + 1
            
            # Check for keys needing rotation
            needs_rotation = False
            if key.expires_at and key.expires_at <= datetime.now() + timedelta(days=7):
                needs_rotation = True
            elif key.max_usage and key.usage_count >= key.max_usage * 0.9:
                needs_rotation = True
            elif (datetime.now() - key.created_at).days >= self.key_rotation_days - 7:
                needs_rotation = True
            
            if needs_rotation and key.is_active:
                status["keys_needing_rotation"].append({
                    "key_id": key_id,
                    "encryption_type": key.encryption_type.value,
                    "data_classification": key.data_classification.value,
                    "reason": "approaching_expiration" if key.expires_at else "approaching_rotation_schedule"
                })
        
        return status
    
    def cleanup_inactive_keys(self, days_to_keep: int = 365) -> int:
        """
        Clean up old inactive keys.
        
        Args:
            days_to_keep: Days to keep inactive keys
            
        Returns:
            Number of keys removed
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        keys_to_remove = []
        
        for key_id, key in self.keys.items():
            if (not key.is_active and 
                key.created_at < cutoff_date):
                keys_to_remove.append(key_id)
        
        # Remove keys
        for key_id in keys_to_remove:
            # Remove key file
            key_file = os.path.join(self.key_storage_path, f"{key_id}.key")
            if os.path.exists(key_file):
                os.remove(key_file)
            
            # Remove from memory
            del self.keys[key_id]
        
        if keys_to_remove:
            self._save_key_index()
            logger.info(f"Cleaned up {len(keys_to_remove)} inactive keys")
        
        return len(keys_to_remove)
    
    def audit_encryption_usage(self, days: int = 30) -> Dict[str, Any]:
        """
        Generate encryption usage audit report.
        
        Args:
            days: Days to include in audit
            
        Returns:
            Audit report
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        audit_report = {
            "audit_period": f"{cutoff_date.isoformat()} to {datetime.now().isoformat()}",
            "total_keys": len(self.keys),
            "encryption_operations": 0,
            "keys_by_classification": {},
            "compliance_status": "COMPLIANT",
            "recommendations": []
        }
        
        for key_id, key in self.keys.items():
            # Count encryption operations
            if key.created_at >= cutoff_date:
                audit_report["encryption_operations"] += key.usage_count
            
            # Group by classification
            class_name = key.data_classification.value
            if class_name not in audit_report["keys_by_classification"]:
                audit_report["keys_by_classification"][class_name] = {
                    "count": 0,
                    "active": 0,
                    "total_usage": 0
                }
            
            audit_report["keys_by_classification"][class_name]["count"] += 1
            audit_report["keys_by_classification"][class_name]["total_usage"] += key.usage_count
            
            if key.is_active:
                audit_report["keys_by_classification"][class_name]["active"] += 1
        
        # Generate recommendations
        if audit_report["encryption_operations"] == 0:
            audit_report["recommendations"].append("No encryption operations detected - verify encryption is being used")
        
        if DataClassification.RESTRICTED.value not in audit_report["keys_by_classification"]:
            audit_report["recommendations"].append("No keys found for RESTRICTED data - ensure PHI/PII encryption is configured")
        
        expired_keys = sum(1 for key in self.keys.values() 
                          if key.expires_at and key.expires_at <= datetime.now())
        if expired_keys > 0:
            audit_report["recommendations"].append(f"Found {expired_keys} expired keys - perform key rotation")
            audit_report["compliance_status"] = "NON_COMPLIANT"
        
        return audit_report