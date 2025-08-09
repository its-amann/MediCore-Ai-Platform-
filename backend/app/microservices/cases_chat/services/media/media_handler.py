"""
Media file handling service
"""
from typing import Dict, Any, Tuple, Optional
import os
import shutil
import logging
from pathlib import Path
import mimetypes
from datetime import datetime
import uuid
from fastapi import UploadFile

from ...core.config import Settings
from ..storage.neo4j_storage import UnifiedNeo4jStorage
from ...core.exceptions import MediaError, CaseNotFoundError

logger = logging.getLogger(__name__)


class MediaHandler:
    """Handles media file uploads and processing"""
    
    def __init__(self, storage: UnifiedNeo4jStorage, settings: Settings):
        self.storage = storage
        self.settings = settings
        self.upload_path = Path(settings.media_upload_path)
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize media handler and ensure directories exist"""
        # Create upload directory if it doesn't exist
        self.upload_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        (self.upload_path / "images").mkdir(exist_ok=True)
        (self.upload_path / "documents").mkdir(exist_ok=True)
        (self.upload_path / "other").mkdir(exist_ok=True)
        
        self.initialized = True
        logger.info(f"Media handler initialized with upload path: {self.upload_path}")
    
    async def upload_file(
        self,
        case_id: str,
        file: UploadFile,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file and attach it to a case
        
        Args:
            case_id: Case ID to attach file to
            file: File to upload
            description: Optional file description
            
        Returns:
            Upload details including attachment ID and file info
        """
        # Validate case exists
        case = await self.storage.get_case(case_id)
        if not case:
            raise CaseNotFoundError(case_id)
        
        # Validate file
        await self._validate_file(file)
        
        # Generate unique filename
        file_ext = Path(file.filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Determine subdirectory based on file type
        subdir = self._get_file_subdirectory(file_ext)
        file_path = self.upload_path / subdir / unique_filename
        
        try:
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Get file size
            file_size = file_path.stat().st_size
            
            # Create attachment record
            attachment_data = {
                "filename": file.filename,
                "file_type": file_ext,
                "file_size": file_size,
                "file_path": str(file_path),
                "content_type": file.content_type or mimetypes.guess_type(file.filename)[0],
                "description": description,
                "uploaded_by": "user",  # Could be enhanced with actual user info
                "metadata": {
                    "original_filename": file.filename,
                    "unique_filename": unique_filename,
                    "subdirectory": subdir
                }
            }
            
            # Store in database
            attachment_id = await self.storage.add_case_attachment(case_id, attachment_data)
            
            logger.info(f"Uploaded file {file.filename} as {attachment_id} for case {case_id}")
            
            return {
                "attachment_id": attachment_id,
                "filename": file.filename,
                "file_size": file_size,
                "content_type": attachment_data["content_type"],
                "uploaded_at": datetime.utcnow().isoformat(),
                "url": f"{self.settings.media_url_prefix}/{attachment_id}"
            }
            
        except Exception as e:
            # Clean up file if database operation failed
            if file_path.exists():
                file_path.unlink()
            
            logger.error(f"Failed to upload file: {e}")
            raise MediaError(f"Failed to upload file: {str(e)}")
    
    async def get_file(self, attachment_id: str) -> Tuple[str, str, str]:
        """
        Get file path and info for download
        
        Args:
            attachment_id: Attachment ID
            
        Returns:
            Tuple of (file_path, filename, content_type)
        """
        # Get all cases and find the attachment
        # This is inefficient but works with current storage design
        # Could be optimized with a direct attachment query
        
        # For now, we'll need to search through cases
        # In production, you'd want a direct attachment lookup
        attachment = None
        
        # Search recent cases (this is a limitation of current design)
        cases, _ = await self.storage.list_cases(limit=1000)
        
        for case in cases:
            attachments = await self.storage.get_case_attachments(case.id)
            for att in attachments:
                if att["id"] == attachment_id:
                    attachment = att
                    break
            if attachment:
                break
        
        if not attachment:
            raise MediaError(f"Attachment {attachment_id} not found")
        
        file_path = Path(attachment["file_path"])
        if not file_path.exists():
            raise MediaError(f"File not found: {file_path}")
        
        return (
            str(file_path),
            attachment["filename"],
            attachment.get("content_type", "application/octet-stream")
        )
    
    async def analyze_media(self, attachment_id: str) -> Dict[str, Any]:
        """
        Analyze a medical image or document
        
        Args:
            attachment_id: Attachment ID to analyze
            
        Returns:
            Analysis results
        """
        # Get file info
        file_path, filename, content_type = await self.get_file(attachment_id)
        
        # Determine analysis type based on content type
        if content_type.startswith("image/"):
            return await self._analyze_image(file_path, filename)
        elif content_type in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            return await self._analyze_document(file_path, filename)
        else:
            raise MediaError(f"Unsupported file type for analysis: {content_type}")
    
    async def _validate_file(self, file: UploadFile) -> None:
        """
        Validate uploaded file
        
        Args:
            file: File to validate
            
        Raises:
            MediaError: If validation fails
        """
        # Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > self.settings.max_file_size:
            raise MediaError(
                f"File too large. Maximum size is {self.settings.max_file_size / 1024 / 1024:.1f}MB"
            )
        
        if file_size == 0:
            raise MediaError("File is empty")
        
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.settings.allowed_file_types:
            raise MediaError(
                f"File type not allowed. Allowed types: {', '.join(self.settings.allowed_file_types)}"
            )
        
        # Additional validation for images
        if file_ext in [".jpg", ".jpeg", ".png"]:
            # Could add image dimension validation here
            pass
    
    def _get_file_subdirectory(self, file_ext: str) -> str:
        """
        Determine subdirectory based on file type
        
        Args:
            file_ext: File extension
            
        Returns:
            Subdirectory name
        """
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp"]
        document_extensions = [".pdf", ".doc", ".docx", ".txt", ".md"]
        
        if file_ext in image_extensions:
            return "images"
        elif file_ext in document_extensions:
            return "documents"
        else:
            return "other"
    
    async def _analyze_image(self, file_path: str, filename: str) -> Dict[str, Any]:
        """
        Analyze medical image
        
        Args:
            file_path: Path to image file
            filename: Original filename
            
        Returns:
            Analysis results
        """
        # Placeholder for image analysis
        # In production, this would integrate with medical image analysis APIs
        # or AI services that can analyze medical images
        
        analysis = {
            "filename": filename,
            "type": "image_analysis",
            "status": "pending",
            "message": "Medical image analysis is not yet implemented",
            "placeholder_results": {
                "detected_features": [],
                "confidence_scores": {},
                "recommendations": ["Please consult with a radiologist for professional analysis"]
            }
        }
        
        # If media analysis is enabled in settings, we could integrate with
        # services like Google Cloud Vision API, AWS Rekognition, or specialized
        # medical image analysis services
        
        if self.settings.enable_media_analysis:
            # TODO: Implement actual image analysis
            pass
        
        return analysis
    
    async def _analyze_document(self, file_path: str, filename: str) -> Dict[str, Any]:
        """
        Analyze medical document
        
        Args:
            file_path: Path to document file
            filename: Original filename
            
        Returns:
            Analysis results
        """
        # Placeholder for document analysis
        # In production, this would extract text and analyze medical information
        
        analysis = {
            "filename": filename,
            "type": "document_analysis",
            "status": "pending",
            "message": "Medical document analysis is not yet implemented",
            "placeholder_results": {
                "extracted_text": "",
                "key_findings": [],
                "medical_terms": [],
                "recommendations": ["Document content should be reviewed by medical professional"]
            }
        }
        
        # If media analysis is enabled, we could use OCR and NLP services
        # to extract and analyze document content
        
        if self.settings.enable_media_analysis:
            # TODO: Implement actual document analysis
            # Could use services like Google Document AI, AWS Textract, etc.
            pass
        
        return analysis
    
    async def delete_file(self, attachment_id: str) -> bool:
        """
        Delete a file and its attachment record
        
        Args:
            attachment_id: Attachment ID
            
        Returns:
            Success status
        """
        try:
            # Get file info first
            file_path, _, _ = await self.get_file(attachment_id)
            
            # Delete physical file
            Path(file_path).unlink(missing_ok=True)
            
            logger.info(f"Deleted file for attachment {attachment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False