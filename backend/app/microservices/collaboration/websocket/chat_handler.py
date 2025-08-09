"""
WebSocket handler for chat functionality in medical case discussions
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import logging
import re
import mimetypes
import base64
from pathlib import Path

from ..services.chat_service import ChatService
from ..services.room_service import RoomService
from ..services.file_service import FileService
from ..models import SendMessageRequest, MessageType

logger = logging.getLogger(__name__)


class ChatHandler:
    """Handles WebSocket events for medical case discussion chat functionality"""
    
    # Medical file formats
    MEDICAL_IMAGE_FORMATS = {
        '.dcm', '.dicom',  # DICOM files
        '.jpg', '.jpeg', '.png',  # Standard images
        '.tiff', '.tif',  # High-quality medical images
        '.nii', '.nii.gz',  # Neuroimaging
        '.pdf',  # Medical reports
    }
    
    # Medical terms for highlighting (common medical abbreviations and terms)
    MEDICAL_TERMS_PATTERN = re.compile(
        r'\b(BP|HR|RR|O2|SpO2|ECG|EKG|MRI|CT|X-ray|CBC|WBC|RBC|'
        r'Hgb|Hct|PLT|BUN|Cr|Na|K|Cl|CO2|glucose|INR|PT|PTT|'
        r'diagnosis|symptoms|treatment|medication|dosage|'
        r'patient|history|examination|laboratory|imaging|'
        r'acute|chronic|bilateral|unilateral|'
        r'mg|mcg|mL|kg|mmHg|bpm|breaths/min)\b',
        re.IGNORECASE
    )
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB for medical images
    MAX_TEXT_FILE_SIZE = 10 * 1024 * 1024  # 10MB for documents
    
    def __init__(self):
        self.chat_service = ChatService()
        self.room_service = RoomService()
        self.file_service = FileService()
    
    async def handle_chat_message(
        self,
        room_id: str,
        user_id: str,
        message_data: Dict[str, Any],
        connection_manager=None
    ) -> Optional[Dict[str, Any]]:
        """
        Process incoming chat messages with medical context awareness
        
        Args:
            room_id: The room identifier
            user_id: The sender's user ID
            message_data: Message content and metadata
            connection_manager: WebSocket connection manager (optional for standalone use)
            
        Returns:
            Processed message dict or None if failed
        """
        try:
            content = message_data.get("content", "")
            message_type = MessageType(message_data.get("message_type", "text"))
            
            # Validate required fields
            if not room_id or not content:
                error_msg = "room_id and content are required"
                if connection_manager:
                    await connection_manager.send_personal_message(
                        user_id,
                        {"type": "error", "message": error_msg}
                    )
                return None
            
            # Verify user is in room
            participant = await self.room_service.get_participant(room_id, user_id)
            if not participant or not participant.is_active:
                error_msg = "Not a member of this room"
                if connection_manager:
                    await connection_manager.send_personal_message(
                        user_id,
                        {"type": "error", "message": error_msg}
                    )
                return None
            
            # Process content based on type
            processed_content = content
            highlighted_terms = []
            
            if message_type == MessageType.TEXT:
                # Highlight medical terms
                processed_content, highlighted_terms = self._highlight_medical_terms(content)
                
                # Process case references (e.g., #CASE-123)
                processed_content = self._process_case_references(processed_content)
            
            # Extract and validate mentions
            mentions = self._extract_mentions(processed_content)
            mentions.extend(message_data.get("mentions", []))
            mentions = list(set(mentions))  # Remove duplicates
            
            # Validate attachments
            attachments = message_data.get("attachments", [])
            if attachments:
                attachments = await self._validate_attachments(attachments, user_id)
            
            # Create message request
            request = SendMessageRequest(
                content=processed_content,
                message_type=message_type,
                reply_to_id=message_data.get("reply_to_id"),
                attachments=attachments,
                mentions=mentions
            )
            
            # Add metadata for medical context
            request.metadata = {
                "highlighted_terms": highlighted_terms,
                "case_references": self._extract_case_references(content),
                "original_content": content
            }
            
            # Send message
            message = await self.chat_service.send_message(
                room_id=room_id,
                sender_id=user_id,
                sender_name=participant.user_name,
                request=request
            )
            
            # Prepare response
            message_dict = message.dict()
            message_dict["highlighted_terms"] = highlighted_terms
            
            # Broadcast to room members if connection manager provided
            if connection_manager:
                await connection_manager.broadcast_to_room(
                    room_id,
                    {
                        "type": "new_message",
                        "message": message_dict
                    }
                )
            
            return message_dict
            
        except Exception as e:
            logger.error(f"Error handling chat message: {e}", exc_info=True)
            if connection_manager:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": f"Failed to send message: {str(e)}"
                    }
                )
            return None
    
    async def handle_send_message(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle sending a chat message - wrapper for backward compatibility"""
        room_id = data.get("room_id")
        await self.handle_chat_message(room_id, user_id, data, connection_manager)
    
    async def handle_typing_indicator(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle typing indicator"""
        room_id = data.get("room_id")
        is_typing = data.get("is_typing", False)
        
        if not room_id:
            return
        
        # Get user info
        participant = await self.room_service.get_participant(room_id, user_id)
        if not participant:
            return
        
        # Broadcast to other room members
        await connection_manager.broadcast_to_room(
            room_id,
            {
                "type": "typing_indicator",
                "room_id": room_id,
                "user_id": user_id,
                "user_name": participant.user_name,
                "is_typing": is_typing
            },
            exclude_user=user_id
        )
    
    async def handle_message_read(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle message read receipt"""
        message_id = data.get("message_id")
        room_id = data.get("room_id")
        
        if not message_id or not room_id:
            return
        
        # Broadcast read receipt to sender
        message = await self.chat_service.get_message(message_id)
        if message and message.sender_id != user_id:
            await connection_manager.send_personal_message(
                message.sender_id,
                {
                    "type": "message_read",
                    "message_id": message_id,
                    "reader_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    async def add_reaction(
        self,
        message_id: str,
        user_id: str,
        emoji: str
    ) -> bool:
        """
        Add emoji reaction to a message
        
        Args:
            message_id: The message to react to
            user_id: The user adding the reaction
            emoji: The emoji reaction
            
        Returns:
            True if successful, False otherwise
        """
        return await self.chat_service.add_reaction(message_id, user_id, emoji)
    
    async def handle_add_reaction(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle adding a reaction to a message"""
        message_id = data.get("message_id")
        emoji = data.get("emoji")
        room_id = data.get("room_id")
        
        if not message_id or not emoji or not room_id:
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "message_id, emoji, and room_id are required"
                }
            )
            return
        
        # Medical-specific reaction validation
        medical_reactions = ['👍', '👎', '❤️', '🔍', '⚠️', '✅', '❌', '📋', '💊', '🩺', '🏥', '🚑']
        
        # Add reaction
        success = await self.add_reaction(
            message_id=message_id,
            user_id=user_id,
            emoji=emoji
        )
        
        if success:
            # Get participant info for display
            participant = await self.room_service.get_participant(room_id, user_id)
            
            # Broadcast to room
            await connection_manager.broadcast_to_room(
                room_id,
                {
                    "type": "reaction_added",
                    "message_id": message_id,
                    "user_id": user_id,
                    "user_name": participant.user_name if participant else "Unknown",
                    "emoji": emoji,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    async def handle_remove_reaction(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle removing a reaction from a message"""
        message_id = data.get("message_id")
        emoji = data.get("emoji")
        room_id = data.get("room_id")
        
        if not message_id or not emoji or not room_id:
            return
        
        # Remove reaction
        success = await self.chat_service.remove_reaction(
            message_id=message_id,
            user_id=user_id,
            emoji=emoji
        )
        
        if success:
            # Broadcast to room
            await connection_manager.broadcast_to_room(
                room_id,
                {
                    "type": "reaction_removed",
                    "message_id": message_id,
                    "user_id": user_id,
                    "emoji": emoji
                }
            )
    
    async def edit_message(
        self,
        message_id: str,
        user_id: str,
        new_content: str
    ) -> Optional[Dict[str, Any]]:
        """
        Edit an existing message
        
        Args:
            message_id: The message to edit
            user_id: The user editing the message
            new_content: New content for the message
            
        Returns:
            Updated message dict or None if failed
        """
        try:
            message = await self.chat_service.update_message(
                message_id=message_id,
                user_id=user_id,
                new_content=new_content
            )
            
            if message:
                # Re-process medical terms
                if message.message_type == MessageType.TEXT:
                    _, highlighted_terms = self._highlight_medical_terms(new_content)
                    message_dict = message.dict()
                    message_dict["highlighted_terms"] = highlighted_terms
                    return message_dict
                    
                return message.dict()
            
            return None
            
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            raise
    
    async def handle_edit_message(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle editing a message"""
        message_id = data.get("message_id")
        new_content = data.get("content")
        room_id = data.get("room_id")
        
        if not message_id or not new_content or not room_id:
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "message_id, content, and room_id are required"
                }
            )
            return
        
        try:
            # Edit message
            message_dict = await self.edit_message(
                message_id=message_id,
                user_id=user_id,
                new_content=new_content
            )
            
            if message_dict:
                # Broadcast to room
                await connection_manager.broadcast_to_room(
                    room_id,
                    {
                        "type": "message_edited",
                        "message": message_dict,
                        "edited_by": user_id,
                        "edited_at": datetime.utcnow().isoformat()
                    }
                )
        except PermissionError:
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "You can only edit your own messages"
                }
            )
    
    async def delete_message(
        self,
        message_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a message (soft delete)
        
        Args:
            message_id: The message to delete
            user_id: The user deleting the message
            
        Returns:
            True if successful, False otherwise
        """
        return await self.chat_service.delete_message(
            message_id=message_id,
            user_id=user_id
        )
    
    async def handle_delete_message(
        self,
        user_id: str,
        data: Dict[str, Any],
        connection_manager
    ):
        """Handle deleting a message (soft delete)"""
        message_id = data.get("message_id")
        room_id = data.get("room_id")
        
        if not message_id or not room_id:
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "message_id and room_id are required"
                }
            )
            return
        
        try:
            # Delete message
            success = await self.delete_message(
                message_id=message_id,
                user_id=user_id
            )
            
            if success:
                # Get participant info for display
                participant = await self.room_service.get_participant(room_id, user_id)
                
                # Broadcast to room
                await connection_manager.broadcast_to_room(
                    room_id,
                    {
                        "type": "message_deleted",
                        "message_id": message_id,
                        "deleted_by": user_id,
                        "deleted_by_name": participant.user_name if participant else "Unknown",
                        "deleted_at": datetime.utcnow().isoformat()
                    }
                )
                
                # Send system message for audit trail
                await self.handle_system_message(
                    room_id=room_id,
                    message_type="message_deletion",
                    content=f"Message deleted by {participant.user_name if participant else 'Unknown'}",
                    metadata={
                        "message_id": message_id,
                        "deleted_by": user_id
                    }
                )
                
        except PermissionError:
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "You can only delete your own messages"
                }
            )
        except Exception as e:
            logger.error(f"Error deleting message: {e}", exc_info=True)
            await connection_manager.send_personal_message(
                user_id,
                {
                    "type": "error",
                    "message": "Failed to delete message"
                }
            )
    
    async def handle_file_upload(
        self,
        room_id: str,
        user_id: str,
        file_data: Dict[str, Any],
        connection_manager=None
    ) -> Optional[Dict[str, Any]]:
        """
        Handle medical document uploads including DICOM images, reports, etc.
        
        Args:
            room_id: The room identifier
            user_id: The uploader's user ID
            file_data: File information including content, name, type
            connection_manager: WebSocket connection manager
            
        Returns:
            File upload result or None if failed
        """
        try:
            # Validate required fields
            file_name = file_data.get("name")
            file_content = file_data.get("content")  # Base64 encoded
            file_type = file_data.get("type", "")
            
            if not file_name or not file_content:
                error_msg = "File name and content are required"
                if connection_manager:
                    await connection_manager.send_personal_message(
                        user_id,
                        {"type": "error", "message": error_msg}
                    )
                return None
            
            # Decode base64 content
            try:
                file_bytes = base64.b64decode(file_content)
            except Exception as e:
                error_msg = "Invalid file content encoding"
                logger.error(f"Base64 decode error: {e}")
                if connection_manager:
                    await connection_manager.send_personal_message(
                        user_id,
                        {"type": "error", "message": error_msg}
                    )
                return None
            
            # Check file size
            file_size = len(file_bytes)
            file_extension = Path(file_name).suffix.lower()
            
            if file_extension in self.MEDICAL_IMAGE_FORMATS:
                max_size = self.MAX_FILE_SIZE
            else:
                max_size = self.MAX_TEXT_FILE_SIZE
            
            if file_size > max_size:
                error_msg = f"File too large. Maximum size: {max_size // (1024*1024)}MB"
                if connection_manager:
                    await connection_manager.send_personal_message(
                        user_id,
                        {"type": "error", "message": error_msg}
                    )
                return None
            
            # Validate file type for medical context
            if not file_type:
                file_type, _ = mimetypes.guess_type(file_name)
            
            # Additional validation for medical files
            is_medical_file = (
                file_extension in self.MEDICAL_IMAGE_FORMATS or
                file_type in ['application/pdf', 'text/plain', 'application/dicom']
            )
            
            # Store file
            file_info = await self.file_service.store_file(
                file_bytes=file_bytes,
                file_name=file_name,
                file_type=file_type,
                user_id=user_id,
                room_id=room_id,
                metadata={
                    "is_medical": is_medical_file,
                    "file_extension": file_extension,
                    "original_size": file_size
                }
            )
            
            # Create file attachment info
            attachment = {
                "id": file_info["file_id"],
                "name": file_name,
                "type": file_type,
                "size": file_size,
                "url": file_info["url"],
                "thumbnail_url": file_info.get("thumbnail_url"),
                "is_medical": is_medical_file,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            
            # Send file message
            message_data = {
                "content": f"Uploaded file: {file_name}",
                "message_type": "file",
                "attachments": [attachment]
            }
            
            # Send as a chat message
            message_result = await self.handle_chat_message(
                room_id, user_id, message_data, connection_manager
            )
            
            return {
                "success": True,
                "attachment": attachment,
                "message": message_result
            }
            
        except Exception as e:
            logger.error(f"Error handling file upload: {e}", exc_info=True)
            if connection_manager:
                await connection_manager.send_personal_message(
                    user_id,
                    {
                        "type": "error",
                        "message": f"Failed to upload file: {str(e)}"
                    }
                )
            return None
    
    async def get_message_history(
        self,
        room_id: str,
        limit: int = 50,
        before_timestamp: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve chat history with medical context
        
        Args:
            room_id: The room identifier
            limit: Maximum number of messages to retrieve
            before_timestamp: Get messages before this timestamp
            
        Returns:
            List of formatted messages
        """
        try:
            # Parse timestamp if provided
            before_dt = None
            if before_timestamp:
                before_dt = datetime.fromisoformat(before_timestamp.replace('Z', '+00:00'))
            
            # Get messages from service
            messages = await self.chat_service.get_messages(
                room_id=room_id,
                limit=limit,
                before_timestamp=before_dt
            )
            
            # Format messages with medical context
            formatted_messages = []
            for msg in messages:
                msg_dict = msg.dict()
                
                # Re-highlight medical terms for display
                if msg.message_type == MessageType.TEXT and not msg.is_deleted:
                    _, highlighted_terms = self._highlight_medical_terms(msg.content)
                    msg_dict["highlighted_terms"] = highlighted_terms
                
                formatted_messages.append(msg_dict)
            
            return formatted_messages
            
        except Exception as e:
            logger.error(f"Error retrieving message history: {e}", exc_info=True)
            return []
    
    # Helper methods for medical-specific features
    
    def _highlight_medical_terms(self, content: str) -> tuple[str, List[str]]:
        """
        Highlight medical terms in message content
        
        Returns:
            Tuple of (processed_content, list_of_highlighted_terms)
        """
        highlighted_terms = []
        
        # Find all medical terms
        matches = self.MEDICAL_TERMS_PATTERN.finditer(content)
        
        for match in matches:
            term = match.group()
            if term.lower() not in [t.lower() for t in highlighted_terms]:
                highlighted_terms.append(term)
        
        # In real implementation, you might wrap terms in HTML tags or special markers
        # For now, we'll just identify them
        processed_content = content
        
        return processed_content, highlighted_terms
    
    def _process_case_references(self, content: str) -> str:
        """
        Process case references like #CASE-123 or #MRN-456789
        """
        # Pattern for case references
        case_pattern = re.compile(r'#(CASE|MRN|PATIENT|REF)-(\d+)', re.IGNORECASE)
        
        def replace_case_ref(match):
            ref_type = match.group(1).upper()
            ref_id = match.group(2)
            # In real implementation, this could create clickable links
            return f'[{ref_type}-{ref_id}]'
        
        return case_pattern.sub(replace_case_ref, content)
    
    def _extract_case_references(self, content: str) -> List[Dict[str, str]]:
        """
        Extract case references from content
        """
        case_pattern = re.compile(r'#(CASE|MRN|PATIENT|REF)-(\d+)', re.IGNORECASE)
        references = []
        
        for match in case_pattern.finditer(content):
            references.append({
                "type": match.group(1).upper(),
                "id": match.group(2),
                "full_ref": match.group(0)
            })
        
        return references
    
    def _extract_mentions(self, content: str) -> List[str]:
        """
        Extract @mentions from content
        """
        mention_pattern = re.compile(r'@(\w+)')
        mentions = []
        
        for match in mention_pattern.finditer(content):
            username = match.group(1)
            mentions.append(username)
        
        return mentions
    
    async def _validate_attachments(
        self, 
        attachments: List[Dict[str, Any]], 
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Validate and process attachments
        """
        validated = []
        
        for attachment in attachments:
            # Basic validation
            if not attachment.get("id") or not attachment.get("name"):
                continue
            
            # Add validation timestamp
            attachment["validated_at"] = datetime.utcnow().isoformat()
            attachment["validated_by"] = user_id
            
            validated.append(attachment)
        
        return validated
    
    async def handle_system_message(
        self,
        room_id: str,
        message_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Send system messages for important events
        """
        try:
            system_message = {
                "content": content,
                "message_type": MessageType.SYSTEM,
                "metadata": metadata or {}
            }
            
            # Use system user ID
            message = await self.chat_service.send_message(
                room_id=room_id,
                sender_id="system",
                sender_name="System",
                request=SendMessageRequest(**system_message)
            )
            
            return message
            
        except Exception as e:
            logger.error(f"Error sending system message: {e}", exc_info=True)
            return None


# Create chat handler instance
chat_handler = ChatHandler()

# Register event handlers
def register_chat_handlers(websocket_manager):
    """Register all chat-related WebSocket event handlers"""
    websocket_manager.register_handler("send_message", chat_handler.handle_send_message)
    websocket_manager.register_handler("typing", chat_handler.handle_typing_indicator)
    websocket_manager.register_handler("message_read", chat_handler.handle_message_read)
    websocket_manager.register_handler("add_reaction", chat_handler.handle_add_reaction)
    websocket_manager.register_handler("remove_reaction", chat_handler.handle_remove_reaction)
    websocket_manager.register_handler("edit_message", chat_handler.handle_edit_message)
    websocket_manager.register_handler("delete_message", chat_handler.handle_delete_message)
    
    # Medical-specific handlers
    websocket_manager.register_handler("upload_file", lambda user_id, data, cm: 
        chat_handler.handle_file_upload(data.get("room_id"), user_id, data, cm))
    websocket_manager.register_handler("get_history", lambda user_id, data, cm:
        chat_handler.get_message_history(data.get("room_id"), data.get("limit", 50), data.get("before")))