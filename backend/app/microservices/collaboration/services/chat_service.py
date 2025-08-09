"""
Chat service for managing messages in collaboration rooms
"""

import uuid
import re
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from ..models import Message, MessageType, SendMessageRequest
from .notification_service import NotificationService
from ..database.neo4j_storage import get_collaboration_storage

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chat messages"""
    
    def __init__(self, db_client=None):
        self.db_client = db_client
        self.notification_service = NotificationService()
        self.storage = get_collaboration_storage()
    
    async def send_message(
        self,
        room_id: str,
        sender_id: str,
        sender_name: str,
        request: SendMessageRequest
    ) -> Message:
        """Send a message to a room"""
        # Validate room exists
        room = await self.storage.get_room_by_id(room_id)
        if not room:
            raise ValueError(f"Room with ID {room_id} does not exist")
        
        # Check if user is a participant in the room
        is_participant = await self.storage.is_room_member(room_id, sender_id)
        if not is_participant:
            raise PermissionError(f"User {sender_id} is not authorized to send messages in room {room_id}")
        
        message_id = str(uuid.uuid4())
        
        # Extract mentions from content
        mentions = self._extract_mentions(request.content)
        mentions.extend(request.mentions)
        mentions = list(set(mentions))  # Remove duplicates
        
        # Prepare message data for Neo4j
        message_data = {
            "message_id": message_id,
            "room_id": room_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": request.content,
            "type": request.message_type.value if isinstance(request.message_type, MessageType) else request.message_type,
            "reply_to_id": request.reply_to_id,
            "attachments": request.attachments if request.attachments else [],
            "mentions": mentions,
            "timestamp": datetime.utcnow(),
            "is_edited": False,
            "is_deleted": False,
            "reactions": {}
        }
        
        # Store message in Neo4j
        stored_message = await self.storage.store_message(message_data)
        
        # Send notifications for mentions
        for mentioned_user_id in mentions:
            await self.notification_service.send_mention_notification(
                user_id=mentioned_user_id,
                sender_name=sender_name,
                room_id=room_id,
                message_preview=request.content[:100]
            )
        
        # Track user activity
        await self.storage.track_user_activity(
            sender_id, room_id, "sent_message",
            {"message_type": request.message_type.value if isinstance(request.message_type, MessageType) else request.message_type}
        )
        
        # Convert back to Message model
        # Handle both 'id' and 'message_id' field names from database
        message_id_value = stored_message.get("message_id") or stored_message.get("id")
        message = Message(
            message_id=message_id_value,
            room_id=stored_message["room_id"],
            sender_id=stored_message["sender_id"],
            sender_name=stored_message["sender_name"],
            content=stored_message["content"],
            message_type=MessageType(stored_message["type"]),
            timestamp=datetime.fromisoformat(stored_message["timestamp"]) if isinstance(stored_message["timestamp"], str) else stored_message["timestamp"]
        )
        
        return message
    
    async def get_messages(
        self,
        room_id: str,
        limit: int = 50,
        offset: int = 0,
        before_timestamp: Optional[datetime] = None,
        after_timestamp: Optional[datetime] = None
    ) -> List[Message]:
        """Get messages from a room"""
        # Convert datetime to string if needed
        before_timestamp_str = before_timestamp.isoformat() if before_timestamp else None
        
        # Get messages from Neo4j
        message_data_list = await self.storage.get_room_messages(
            room_id=room_id,
            limit=limit,
            offset=offset,
            before_timestamp=before_timestamp_str
        )
        
        # Convert to Message models
        messages = []
        for msg_data in message_data_list:
            # Parse reactions if stored as JSON string
            reactions = msg_data.get("reactions", {})
            if isinstance(reactions, str):
                import json
                try:
                    reactions = json.loads(reactions)
                except:
                    reactions = {}
            
            # Parse attachments if stored as JSON string
            attachments = msg_data.get("attachments", [])
            if isinstance(attachments, str):
                import json
                try:
                    attachments = json.loads(attachments)
                except:
                    attachments = []
            
            # Parse mentions if stored as JSON string
            mentions = msg_data.get("mentions", [])
            if isinstance(mentions, str):
                import json
                try:
                    mentions = json.loads(mentions)
                except:
                    mentions = []
            
            # Handle both 'id' and 'message_id' field names from database
            message_id = msg_data.get("message_id") or msg_data.get("id")
            if not message_id:
                logger.warning(f"No message_id found in message data: {msg_data}")
                continue
            
            # Parse timestamp
            timestamp = msg_data["timestamp"]
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            # Parse edited_at if present
            edited_at = msg_data.get("edited_at")
            if edited_at and isinstance(edited_at, str):
                edited_at = datetime.fromisoformat(edited_at)
            
            # Create Message directly
            message = Message(
                message_id=message_id,
                room_id=msg_data["room_id"],
                sender_id=msg_data["sender_id"],
                sender_name=msg_data.get("sender_name", f"User_{msg_data['sender_id']}"),
                content=msg_data["content"],
                message_type=MessageType(msg_data.get("type", "text")),
                timestamp=timestamp,
                edited_at=edited_at,
                is_edited=msg_data.get("is_edited", False),
                reactions=[],  # Convert dict reactions to list format
                thread_id=None
            )
            
            # Apply after_timestamp filter if needed (Neo4j query doesn't support this directly)
            if after_timestamp and message.timestamp <= after_timestamp:
                continue
                
            messages.append(message)
        
        return messages
    
    async def get_message(self, message_id: str) -> Optional[Message]:
        """Get a specific message by ID"""
        try:
            query = """
            MATCH (m:Message {message_id: $message_id})
            MATCH (u:User)-[:SENT]->(m)
            RETURN m, u.username as sender_name, u.user_id as sender_id
            """
            
            result = await self.storage.run_query(query, {"message_id": message_id})
            
            if result:
                msg_data = dict(result[0]["m"])
                msg_data["sender_name"] = result[0]["sender_name"]
                msg_data["sender_id"] = result[0]["sender_id"]
                
                # Parse timestamp
                timestamp = msg_data["timestamp"]
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                
                return Message(
                    message_id=msg_data["message_id"],
                    room_id=msg_data["room_id"],
                    sender_id=msg_data["sender_id"],
                    sender_name=msg_data["sender_name"],
                    content=msg_data["content"],
                    message_type=MessageType(msg_data.get("type", "text")),
                    timestamp=timestamp
                )
            return None
        except Exception as e:
            logger.error(f"Error getting message: {str(e)}")
            return None
    
    async def update_message(
        self,
        message_id: str,
        user_id: str,
        new_content: str
    ) -> Optional[Message]:
        """Update a message (edit)"""
        try:
            # First check if message exists and user is sender
            message = await self.get_message(message_id)
            if not message:
                return None
            
            # Check if user is the sender
            if message.sender_id != user_id:
                raise PermissionError("Only the sender can edit their message")
            
            # Update in database
            query = """
            MATCH (m:Message {message_id: $message_id})
            SET m.content = $new_content,
                m.is_edited = true,
                m.edited_at = $edited_at
            RETURN m
            """
            
            result = await self.storage.run_write_query(query, {
                "message_id": message_id,
                "new_content": new_content,
                "edited_at": datetime.utcnow().isoformat()
            })
            
            if result:
                # Return updated message
                message.content = new_content
                message.is_edited = True
                message.edited_at = datetime.utcnow()
                return message
            
            return None
        except Exception as e:
            logger.error(f"Error updating message: {str(e)}")
            raise
    
    async def delete_message(
        self,
        message_id: str,
        user_id: str
    ) -> bool:
        """Delete a message (soft delete)"""
        try:
            # First check if message exists and user is sender
            message = await self.get_message(message_id)
            if not message:
                return False
            
            # Check if user is the sender
            if message.sender_id != user_id:
                raise PermissionError("Only the sender can delete their message")
            
            # Soft delete in database
            query = """
            MATCH (m:Message {message_id: $message_id})
            SET m.is_deleted = true,
                m.deleted_at = $deleted_at,
                m.content = '[Message deleted]'
            RETURN m
            """
            
            result = await self.storage.run_write_query(query, {
                "message_id": message_id,
                "deleted_at": datetime.utcnow().isoformat()
            })
            
            return result is not None and len(result) > 0
        except Exception as e:
            logger.error(f"Error deleting message: {str(e)}")
            raise
    
    async def add_reaction(
        self,
        message_id: str,
        user_id: str,
        emoji: str
    ) -> bool:
        """Add a reaction to a message"""
        try:
            # Check if message exists
            message = await self.get_message(message_id)
            if not message:
                return False
            
            # Add reaction relationship
            query = """
            MATCH (m:Message {message_id: $message_id})
            MATCH (u:User {user_id: $user_id})
            MERGE (u)-[r:REACTED_TO {emoji: $emoji}]->(m)
            SET r.timestamp = $timestamp
            RETURN r
            """
            
            result = await self.storage.run_write_query(query, {
                "message_id": message_id,
                "user_id": user_id,
                "emoji": emoji,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return result is not None and len(result) > 0
        except Exception as e:
            logger.error(f"Error adding reaction: {str(e)}")
            return False
    
    async def remove_reaction(
        self,
        message_id: str,
        user_id: str,
        emoji: str
    ) -> bool:
        """Remove a reaction from a message"""
        try:
            # Remove reaction relationship
            query = """
            MATCH (u:User {user_id: $user_id})-[r:REACTED_TO {emoji: $emoji}]->(m:Message {message_id: $message_id})
            DELETE r
            RETURN COUNT(r) as deleted
            """
            
            result = await self.storage.run_write_query(query, {
                "message_id": message_id,
                "user_id": user_id,
                "emoji": emoji
            })
            
            if result and len(result) > 0:
                return result[0]["deleted"] > 0
            return False
        except Exception as e:
            logger.error(f"Error removing reaction: {str(e)}")
            return False
    
    async def search_messages(
        self,
        room_id: str,
        query: str,
        sender_id: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        limit: int = 50
    ) -> List[Message]:
        """Search messages in a room"""
        # Get all messages from the room
        all_messages = await self.get_messages(room_id, limit=1000)
        results = []
        
        for message in all_messages:
            # Filter by sender
            if sender_id and message.sender_id != sender_id:
                continue
            
            # Filter by type
            if message_type and message.message_type != message_type:
                continue
            
            # Search in content
            if query.lower() in message.content.lower():
                results.append(message)
                
            # Limit results
            if len(results) >= limit:
                break
        
        return results
    
    async def get_thread_messages(
        self,
        parent_message_id: str
    ) -> List[Message]:
        """Get all replies to a message (thread)"""
        try:
            # Get parent message to verify it exists
            parent = await self.get_message(parent_message_id)
            if not parent:
                return []
            
            # Query for all messages that reply to this parent
            query = """
            MATCH (m:Message {reply_to_id: $parent_message_id})
            MATCH (u:User)-[:SENT]->(m)
            RETURN m, u.username as sender_name, u.user_id as sender_id
            ORDER BY m.timestamp ASC
            """
            
            results = await self.storage.run_query(query, {"parent_message_id": parent_message_id})
            
            thread_messages = []
            for result in results:
                msg_data = dict(result["m"])
                msg_data["sender_name"] = result["sender_name"]
                msg_data["sender_id"] = result["sender_id"]
                
                # Parse timestamp
                timestamp = msg_data["timestamp"]
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                
                message = Message(
                    message_id=msg_data["message_id"],
                    room_id=msg_data["room_id"],
                    sender_id=msg_data["sender_id"],
                    sender_name=msg_data["sender_name"],
                    content=msg_data["content"],
                    message_type=MessageType(msg_data.get("type", "text")),
                    timestamp=timestamp,
                    reply_to_id=msg_data.get("reply_to_id")
                )
                thread_messages.append(message)
            
            return thread_messages
        except Exception as e:
            logger.error(f"Error getting thread messages: {str(e)}")
            return []
    
    async def mark_messages_as_read(
        self,
        room_id: str,
        user_id: str,
        up_to_timestamp: datetime
    ) -> int:
        """Mark messages as read up to a certain timestamp"""
        try:
            # Create or update read receipt relationship
            query = """
            MATCH (u:User {user_id: $user_id})
            MATCH (r:Room {room_id: $room_id})
            MERGE (u)-[read:READ_MESSAGES_IN]->(r)
            SET read.last_read_timestamp = $timestamp
            WITH u, r
            MATCH (m:Message)-[:SENT_IN]->(r)
            WHERE m.timestamp <= $timestamp AND m.sender_id <> $user_id
            RETURN COUNT(m) as count
            """
            
            result = await self.storage.run_write_query(query, {
                "user_id": user_id,
                "room_id": room_id,
                "timestamp": up_to_timestamp.isoformat()
            })
            
            if result and len(result) > 0:
                return result[0]["count"]
            return 0
        except Exception as e:
            logger.error(f"Error marking messages as read: {str(e)}")
            return 0
    
    async def get_unread_count(
        self,
        room_id: str,
        user_id: str,
        last_read_timestamp: datetime
    ) -> int:
        """Get count of unread messages"""
        try:
            # Count messages after last read timestamp
            query = """
            MATCH (m:Message)-[:SENT_IN]->(r:Room {room_id: $room_id})
            WHERE m.timestamp > $last_read_timestamp AND m.sender_id <> $user_id
            RETURN COUNT(m) as count
            """
            
            result = await self.storage.run_query(query, {
                "room_id": room_id,
                "user_id": user_id,
                "last_read_timestamp": last_read_timestamp.isoformat()
            })
            
            if result and len(result) > 0:
                return result[0]["count"]
            return 0
        except Exception as e:
            logger.error(f"Error getting unread count: {str(e)}")
            return 0
    
    def _extract_mentions(self, content: str) -> List[str]:
        """Extract @mentions from message content"""
        # Pattern to match @username or @user_id
        mention_pattern = r'@(\w+)'
        matches = re.findall(mention_pattern, content)
        return matches
    
    async def send_system_message(
        self,
        room_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Send a system message to a room"""
        # Validate room exists
        room = await self.storage.get_room_by_id(room_id)
        if not room:
            raise ValueError(f"Room with ID {room_id} does not exist")
        
        message_id = str(uuid.uuid4())
        
        # Prepare system message data
        message_data = {
            "message_id": message_id,
            "room_id": room_id,
            "sender_id": "system",
            "sender_name": "System",
            "content": content,
            "message_type": MessageType.SYSTEM.value,
            "created_at": datetime.utcnow(),
            "attachments": [],
            "mentions": [],
            "metadata": metadata or {}
        }
        
        # Create message object
        message = Message(
            message_id=message_id,
            room_id=room_id,
            sender_id="system",
            sender_name="System",
            content=content,
            message_type=MessageType.SYSTEM,
            timestamp=datetime.utcnow()
        )
        
        # Store message
        stored_message = await self.storage.store_message(message_data)
        
        return message
    
    async def send_screen_share_event_message(
        self,
        room_id: str,
        event_type: str,
        user_name: str,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Send a system message for screen share events"""
        # Generate appropriate message content
        if event_type == "start":
            content = f"{user_name} started sharing their screen"
        elif event_type == "stop":
            content = f"{user_name} stopped sharing their screen"
        elif event_type == "quality_change":
            quality = details.get("new_quality", "auto") if details else "auto"
            content = f"{user_name} changed screen share quality to {quality}"
        elif event_type == "control_granted":
            grantee_name = details.get("grantee_name", "someone") if details else "someone"
            content = f"{user_name} granted screen control to {grantee_name}"
        elif event_type == "error":
            content = f"{user_name} encountered an error while screen sharing"
        else:
            content = f"Screen share event: {event_type}"
        
        # Add metadata
        metadata = {
            "event_type": f"screen_share_{event_type}",
            "session_id": session_id,
            "user_name": user_name
        }
        if details:
            metadata["details"] = details
        
        return await self.send_system_message(room_id, content, metadata)
    
    async def export_chat_history(
        self,
        room_id: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export chat history for a room"""
        try:
            # Get all messages from the room
            messages = await self.get_messages(room_id, limit=10000)  # Large limit to get all
            
            # Filter out deleted messages
            active_messages = [m for m in messages if not getattr(m, 'is_deleted', False)]
            
            if format == "json":
                return {
                    "room_id": room_id,
                    "exported_at": datetime.utcnow().isoformat(),
                    "message_count": len(active_messages),
                    "messages": [m.dict() for m in active_messages]
                }
            else:
                # Could support other formats like CSV, TXT, etc.
                raise ValueError(f"Unsupported export format: {format}")
        except Exception as e:
            logger.error(f"Error exporting chat history: {str(e)}")
            raise