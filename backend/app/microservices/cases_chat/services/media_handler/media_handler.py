"""
Media Handler Service for Cases Chat
Handles image processing and audio transcription using Groq
"""

import logging
import base64
import io
from typing import Optional, Tuple
from fastapi import UploadFile
from PIL import Image
from groq import Groq

from app.core.config import settings

logger = logging.getLogger(__name__)


class MediaHandler:
    """
    Service for handling media uploads (images and audio)
    """
    
    def __init__(self):
        """Initialize media handler with Groq client"""
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required for media handling")
        
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.whisper_model = getattr(settings, 'whisper_model', 'whisper-large-v3')
        
        # Media constraints with defaults
        self.max_image_size = getattr(settings, 'max_image_size', 10 * 1024 * 1024)  # 10MB
        self.max_audio_size = getattr(settings, 'max_audio_size', 50 * 1024 * 1024)  # 50MB
        self.supported_image_formats = getattr(settings, 'supported_image_formats', 
                                               ["image/jpeg", "image/png", "image/webp", "image/gif"])
        self.supported_audio_formats = getattr(settings, 'supported_audio_formats', 
                                               ["audio/mpeg", "audio/wav", "audio/ogg", "audio/x-m4a"])
    
    async def process_image(self, image_file: UploadFile) -> Optional[str]:
        """
        Process uploaded image and return base64 encoded data
        
        Args:
            image_file: Uploaded image file
            
        Returns:
            Base64 encoded image data or None
        """
        try:
            # Validate file type
            file_extension = image_file.filename.split('.')[-1].lower()
            if file_extension not in self.supported_image_formats:
                logger.error(f"Unsupported image format: {file_extension}")
                return None
            
            # Read image data
            image_data = await image_file.read()
            
            # Validate file size
            if len(image_data) > self.max_image_size:
                logger.error(f"Image size {len(image_data)} exceeds limit {self.max_image_size}")
                return None
            
            # Process image with PIL for validation and optimization
            try:
                image = Image.open(io.BytesIO(image_data))
                
                # Convert to RGB if necessary
                if image.mode not in ('RGB', 'L'):
                    image = image.convert('RGB')
                
                # Resize if too large (maintain aspect ratio)
                max_dimension = 1920
                if max(image.size) > max_dimension:
                    image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                    logger.info(f"Resized image from {image.size} to fit {max_dimension}px")
                
                # Save to bytes
                output_buffer = io.BytesIO()
                image.save(output_buffer, format='JPEG', quality=85, optimize=True)
                processed_data = output_buffer.getvalue()
                
                # Encode to base64
                base64_data = base64.b64encode(processed_data).decode('utf-8')
                
                logger.info(f"Processed image: {image_file.filename}, size: {len(processed_data)} bytes")
                return base64_data
                
            except Exception as e:
                logger.error(f"Error processing image with PIL: {str(e)}")
                # Fallback to direct base64 encoding
                base64_data = base64.b64encode(image_data).decode('utf-8')
                return base64_data
                
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            return None
    
    async def transcribe_audio(self, audio_file: UploadFile) -> Optional[str]:
        """
        Transcribe audio file using Groq's Whisper model
        
        Args:
            audio_file: Uploaded audio file
            
        Returns:
            Transcribed text or None
        """
        try:
            # Validate file type
            file_extension = audio_file.filename.split('.')[-1].lower()
            if file_extension not in self.supported_audio_formats:
                logger.error(f"Unsupported audio format: {file_extension}")
                return None
            
            # Read audio data
            audio_data = await audio_file.read()
            
            # Validate file size
            if len(audio_data) > self.max_audio_size:
                logger.error(f"Audio size {len(audio_data)} exceeds limit {self.max_audio_size}")
                return None
            
            # Create file-like object for Groq API
            audio_buffer = io.BytesIO(audio_data)
            audio_buffer.name = audio_file.filename
            
            # Transcribe using Groq's Whisper
            logger.info(f"Transcribing audio: {audio_file.filename}")
            
            transcription = self.groq_client.audio.transcriptions.create(
                model=self.whisper_model,
                file=audio_buffer,
                language="en",  # Can be made configurable
                response_format="text"
            )
            
            logger.info(f"Transcription complete: {len(transcription)} characters")
            return transcription
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return None
    
    async def validate_media(self, file: UploadFile, media_type: str) -> Tuple[bool, str]:
        """
        Validate uploaded media file
        
        Args:
            file: Uploaded file
            media_type: 'image' or 'audio'
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check file extension
            file_extension = file.filename.split('.')[-1].lower()
            
            if media_type == 'image':
                if file_extension not in self.supported_image_formats:
                    return False, f"Unsupported image format. Supported: {', '.join(self.supported_image_formats)}"
                max_size = self.max_image_size
            elif media_type == 'audio':
                if file_extension not in self.supported_audio_formats:
                    return False, f"Unsupported audio format. Supported: {', '.join(self.supported_audio_formats)}"
                max_size = self.max_audio_size
            else:
                return False, "Invalid media type"
            
            # Check file size (read a small chunk first)
            chunk = await file.read(1024)
            await file.seek(0)  # Reset file position
            
            if not chunk:
                return False, "Empty file"
            
            # Check content type
            content_type = file.content_type
            if media_type == 'image' and not content_type.startswith('image/'):
                return False, "File content does not match image type"
            elif media_type == 'audio' and not content_type.startswith('audio/'):
                return False, "File content does not match audio type"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error validating media: {str(e)}")
            return False, f"Validation error: {str(e)}"
    
    def get_media_info(self, file: UploadFile) -> dict:
        """
        Get media file information
        
        Args:
            file: Uploaded file
            
        Returns:
            Dictionary with file information
        """
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": file.size if hasattr(file, 'size') else None,
            "extension": file.filename.split('.')[-1].lower() if '.' in file.filename else None
        }
    
    async def create_thumbnail(self, image_data: str, max_size: Tuple[int, int] = (200, 200)) -> Optional[str]:
        """
        Create thumbnail from base64 image data
        
        Args:
            image_data: Base64 encoded image
            max_size: Maximum thumbnail dimensions
            
        Returns:
            Base64 encoded thumbnail or None
        """
        try:
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            
            # Open image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Create thumbnail
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save to bytes
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', quality=75, optimize=True)
            thumbnail_data = output_buffer.getvalue()
            
            # Encode to base64
            thumbnail_base64 = base64.b64encode(thumbnail_data).decode('utf-8')
            
            return thumbnail_base64
            
        except Exception as e:
            logger.error(f"Error creating thumbnail: {str(e)}")
            return None