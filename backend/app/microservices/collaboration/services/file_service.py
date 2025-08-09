"""
File service for handling medical document uploads and storage
"""

import uuid
import os
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FileService:
    """Service for managing file uploads and storage"""
    
    def __init__(self, storage_path: str = "./uploads"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    async def store_file(
        self,
        file_bytes: bytes,
        file_name: str,
        file_type: str,
        user_id: str,
        room_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store uploaded file and return file information
        
        Args:
            file_bytes: File content as bytes
            file_name: Original file name
            file_type: MIME type of the file
            user_id: ID of the user uploading the file
            room_id: ID of the room where file is uploaded
            metadata: Additional metadata about the file
            
        Returns:
            Dictionary containing file information
        """
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Create room-specific directory
            room_dir = os.path.join(self.storage_path, room_id)
            os.makedirs(room_dir, exist_ok=True)
            
            # Save file with unique name
            file_extension = os.path.splitext(file_name)[1]
            stored_name = f"{file_id}{file_extension}"
            file_path = os.path.join(room_dir, stored_name)
            
            # Write file to disk
            with open(file_path, 'wb') as f:
                f.write(file_bytes)
            
            # Generate URL (in production, this would be a proper URL)
            file_url = f"/files/{room_id}/{stored_name}"
            
            # Create thumbnail URL for images
            thumbnail_url = None
            if file_type and file_type.startswith('image/'):
                # In production, generate actual thumbnail
                thumbnail_url = f"/thumbnails/{room_id}/{stored_name}"
            
            # Store file metadata (in production, save to database)
            file_info = {
                "file_id": file_id,
                "original_name": file_name,
                "stored_name": stored_name,
                "file_type": file_type,
                "file_size": len(file_bytes),
                "user_id": user_id,
                "room_id": room_id,
                "url": file_url,
                "thumbnail_url": thumbnail_url,
                "uploaded_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            logger.info(f"File stored successfully: {file_id} - {file_name}")
            return file_info
            
        except Exception as e:
            logger.error(f"Error storing file: {e}", exc_info=True)
            raise
    
    async def get_file(self, room_id: str, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve file information
        
        Args:
            room_id: The room ID
            file_id: The file ID
            
        Returns:
            File information or None if not found
        """
        # In production, retrieve from database
        # For now, return placeholder
        return None
    
    async def delete_file(self, room_id: str, file_id: str) -> bool:
        """
        Delete a file
        
        Args:
            room_id: The room ID
            file_id: The file ID
            
        Returns:
            True if successful, False otherwise
        """
        # In production, delete from storage and database
        # For now, return success
        return True