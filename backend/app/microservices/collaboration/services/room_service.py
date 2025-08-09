"""
Room management service for collaboration
Fixed: Room model field mapping to use alias 'type' instead of field name 'room_type'
"""

import uuid
import logging
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from collections import defaultdict
from ..models import (
    Room, RoomParticipant, RoomType, RoomStatus, UserRole,
    CreateRoomRequest, UpdateRoomRequest, JoinRoomRequest
)
from ..utils.auth_utils import hash_password, verify_password
from ..database.neo4j_storage import get_collaboration_storage

logger = logging.getLogger(__name__)


class RoomService:
    """Service for managing collaboration rooms"""
    
    def __init__(self, db_client=None):
        self.db_client = db_client
        self.storage = get_collaboration_storage()
        # Cache for active users and search results
        self._active_users_cache: Dict[str, Tuple[List[str], datetime]] = {}  # room_id -> (active_users, cache_time)
        self._cache_ttl = timedelta(seconds=30)  # Cache TTL
        # Search cache
        self._search_cache: Dict[str, Tuple[List[Room], datetime]] = {}
        self._search_cache_ttl = timedelta(seconds=60)  # Search cache TTL
        
        # Initialize missing in-memory dictionaries
        self._rooms: Dict[str, Room] = {}  # room_id -> Room object
        self._participants: Dict[str, List[RoomParticipant]] = {}  # room_id -> List of participants
        self._user_activity: Dict[str, Dict[str, Any]] = {}  # "{room_id}:{user_id}" -> activity data
        self._user_logins: Dict[str, datetime] = {}  # user_id -> last login time
        self._room_activity: Dict[str, Dict[str, Any]] = {}  # room_id -> room activity data
        self._message_index: Dict[str, Any] = {}  # message_id -> message data (for future use)
    
    async def create_room(
        self,
        creator_id: str,
        request: CreateRoomRequest
    ) -> Room:
        """Create a new collaboration room"""
        logger.info(f"Creating room with name: {request.name}")
        logger.info(f"Request type: {request.type}, type of type: {type(request.type)}")
        room_id = str(uuid.uuid4())
        
        # Hash password if private room
        hashed_password = None
        if not request.is_public and request.room_password:
            hashed_password = hash_password(request.room_password)
        
        # Prepare room data for Neo4j
        room_data = {
            "room_id": room_id,
            "name": request.name,
            "description": request.description,
            "room_type": request.type.value if isinstance(request.type, RoomType) else request.type,
            "created_by": {"user_id": creator_id},
            "max_participants": request.max_participants,
            "is_private": not request.is_public,
            "is_public": request.is_public,
            "password": hashed_password,
            "scheduled_start": request.scheduled_start,
            "scheduled_end": request.scheduled_end,
            "status": (RoomStatus.SCHEDULED if request.scheduled_start else RoomStatus.ACTIVE).value,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "current_participants": 1,  # Creator is automatically added
            "last_activity": datetime.utcnow(),
            # Teaching-specific fields
            "subject": request.subject if hasattr(request, 'subject') else None,
            "institution": request.institution if hasattr(request, 'institution') else None,
            "tags": request.tags if hasattr(request, 'tags') else [],
            "settings": {
                "require_approval": request.require_approval if hasattr(request, 'require_approval') else False,
                "voice_enabled": request.voice_enabled,
                "screen_sharing": request.screen_sharing,
                "recording_enabled": request.recording_enabled
            }
        }
        
        # Create room in Neo4j
        try:
            created_room_data = await self.storage.create_room(room_data)
        except Exception as e:
            logger.error(f"Error in storage.create_room: {e}")
            logger.error(f"Room data passed: {room_data}")
            logger.error(f"Room data type: {type(room_data)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        
        # Track user activity
        await self.storage.track_user_activity(
            creator_id, room_id, "room_created",
            {"room_name": request.name}
        )
        
        # Convert Neo4j data back to Room model
        # Data should already be parsed by neo4j_storage._parse_neo4j_data
        
        # Get parsed data
        settings = created_room_data.get("settings", {})
        tags = created_room_data.get("tags", [])
        created_by = created_room_data.get("created_by", {"user_id": creator_id})
        
        logger.info(f"Tags from created_room_data: {tags}, type: {type(tags)}")
        logger.info(f"Settings from created_room_data: {settings}, type: {type(settings)}")
        logger.info(f"Created_by from created_room_data: {created_by}, type: {type(created_by)}")
        
        room_data_for_model = {
            "room_id": created_room_data["room_id"],
            "name": created_room_data["name"],
            "description": created_room_data.get("description"),
            "room_type": created_room_data["room_type"],
            "status": created_room_data["status"],
            "max_participants": created_room_data["max_participants"],
            "current_participants": 0,
            "is_public": not created_room_data["is_private"],
            "password_protected": bool(created_room_data.get("password")),
            "room_password": created_room_data.get("password"),
            "created_by": created_by,
            "created_at": created_room_data["created_at"],
            "updated_at": created_room_data["updated_at"],
            "settings": settings,
            "voice_enabled": settings.get("voice_enabled", False),
            "screen_sharing": settings.get("screen_sharing", False),
            "recording_enabled": settings.get("recording_enabled", False),
            "active_users": [],
            # Teaching-specific fields
            "subject": created_room_data.get("subject"),
            "institution": created_room_data.get("institution"),
            "tags": tags,
            "scheduled_start": created_room_data.get("scheduled_start"),
            "scheduled_end": created_room_data.get("scheduled_end")
        }
        
        # Final validation to ensure tags is a list
        if isinstance(room_data_for_model.get("tags"), str):
            logger.warning(f"Tags is still a string after parsing: {room_data_for_model['tags']}")
            try:
                room_data_for_model["tags"] = json.loads(room_data_for_model["tags"])
            except:
                room_data_for_model["tags"] = []
        
        # Create Room instance from dictionary (allows alias to work)
        logger.info(f"Creating Room with data: {room_data_for_model}")
        logger.info(f"room_type field value: {room_data_for_model.get('room_type')}")
        logger.info(f"type field value: {room_data_for_model.get('type')}")
        logger.info(f"tags field value: {room_data_for_model.get('tags')}, type: {type(room_data_for_model.get('tags'))}")
        
        try:
            room = Room(**room_data_for_model)
        except Exception as e:
            logger.error(f"Error creating Room model: {e}")
            logger.error(f"Room data keys: {list(room_data_for_model.keys())}")
            raise
        
        # Automatically add creator as participant with HOST role
        try:
            logger.info(f"Attempting to add creator {creator_id} to room {room_id}")
            # Get creator's user info
            creator_info = await self.storage.get_user_by_id(creator_id)
            logger.info(f"Creator info fetched: {creator_info}")
            
            if creator_info:
                username = creator_info.get("username", creator_info.get("full_name", f"User-{creator_id[:8]}"))
                participant_added = await self.storage.add_participant(
                    room_id,
                    creator_id,
                    username,
                    UserRole.HOST
                )
                logger.info(f"Add participant result: {participant_added}")
                # Update participant count
                room.current_participants = 1
                logger.info(f"Automatically added creator {creator_id} ({username}) as HOST to room {room_id}")
            else:
                logger.warning(f"Creator user info not found for {creator_id}, adding with default username")
                participant_added = await self.storage.add_participant(
                    room_id,
                    creator_id,
                    f"User-{creator_id[:8]}",
                    UserRole.HOST
                )
                logger.info(f"Add participant result (default username): {participant_added}")
                room.current_participants = 1
        except Exception as e:
            logger.error(f"Failed to automatically add creator as participant: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Don't fail room creation if adding participant fails
        
        return room
    
    async def get_all_rooms(
        self,
        room_type: Optional[RoomType] = None,
        status: Optional[RoomStatus] = None,
        is_private: Optional[bool] = None
    ) -> List[Room]:
        """Get all rooms with optional filters"""
        try:
            # Get rooms from Neo4j storage
            rooms_data = await self.storage.get_rooms(
                room_type=room_type.value if room_type else None,
                status=status.value if status else None,
                is_private=is_private
            )
            
            # Convert to Room models
            rooms = []
            for room_data in rooms_data:
                room = Room(
                    room_id=room_data["room_id"],
                    name=room_data["name"],
                    description=room_data.get("description"),
                    room_type=room_data["room_type"],
                    status=RoomStatus(room_data.get("status", "active")),
                    max_participants=room_data.get("max_participants"),
                    current_participants=room_data.get("current_participants", 0),
                    is_public=not room_data.get("is_private", False),
                    password_protected=bool(room_data.get("password")),
                    created_by=room_data.get("created_by", {}),
                    created_at=datetime.fromisoformat(room_data["created_at"]) if isinstance(room_data["created_at"], str) else room_data["created_at"],
                    updated_at=datetime.fromisoformat(room_data["updated_at"]) if isinstance(room_data["updated_at"], str) else room_data["updated_at"],
                    settings=room_data.get("settings", {}),
                    voice_enabled=room_data.get("voice_enabled", False),
                    screen_sharing=room_data.get("screen_sharing", False),
                    recording_enabled=room_data.get("recording_enabled", False),
                    active_users=[]  # Don't populate from storage, use empty list  # Don't populate from storage, use empty list
                )
                rooms.append(room)
            
            return rooms
        except Exception as e:
            logger.error(f"Failed to get all rooms: {e}")
            return []
    
    async def get_room(self, room_id: str) -> Optional[Room]:
        """Get room by ID"""
        # Force reload - v3 - critical fix
        logger.info(f"[RELOAD CHECK] Getting room {room_id}")
        room_data = await self.storage.get_room_by_id(room_id)
        if not room_data:
            return None
        
        # Log the data received from storage
        logger.info(f"Room data from storage: {room_data}")
        logger.info(f"room_type field value: {room_data.get('room_type')}")
        
        # Convert Neo4j data to Room model
        room = Room(
            room_id=room_data["room_id"],
            name=room_data["name"],
            description=room_data.get("description"),
            room_type=room_data["room_type"],
            status=RoomStatus(room_data.get("status", RoomStatus.ACTIVE)),
            max_participants=room_data.get("max_participants", 50),
            current_participants=room_data.get("current_participants", 0),
            is_public=not room_data.get("is_private", False),
            password_protected=bool(room_data.get("password")),
            room_password=room_data.get("password"),
            created_by={"user_id": room_data.get("creator_id", "")},
            settings=room_data.get("settings", {}),
            created_at=datetime.fromisoformat(room_data["created_at"]) if isinstance(room_data.get("created_at"), str) else room_data.get("created_at", datetime.utcnow()),
            updated_at=datetime.fromisoformat(room_data["updated_at"]) if isinstance(room_data.get("updated_at"), str) else room_data.get("updated_at", datetime.utcnow()),
            last_activity=room_data.get("last_activity"),
            closed_at=room_data.get("closed_at"),
            voice_enabled=room_data.get("settings", {}).get("voice_enabled", False),
            screen_sharing=room_data.get("settings", {}).get("screen_sharing", False),
            recording_enabled=room_data.get("settings", {}).get("recording_enabled", False),
            active_users=[],  # Don't populate from storage, use empty list
            # Teaching room specific fields
            subject=room_data.get("subject"),
            scheduled_start=room_data.get("scheduled_start"),
            scheduled_end=room_data.get("scheduled_end"),
            institution=room_data.get("institution"),
            tags=room_data.get("tags", []),
            recording_url=room_data.get("recording_url"),
            class_materials=room_data.get("class_materials", []),
            is_class_active=room_data.get("is_class_active", False)
        )
        
        return room
    
    async def update_room(
        self,
        room_id: str,
        user_id: str,
        request: UpdateRoomRequest
    ) -> Optional[Room]:
        """Update room settings"""
        # Get room to verify it exists
        room = await self.get_room(room_id)
        if not room:
            return None
        
        # Check if user is host or co-host
        participants = await self.storage.get_room_participants(room_id)
        user_participant = next((p for p in participants if p["user_id"] == user_id), None)
        
        if not user_participant or user_participant["role"] not in ["host", "co_host"]:
            raise PermissionError("Only hosts can update room settings")
        
        # Prepare update data
        update_data = request.dict(exclude_unset=True)
        
        # Hash password if provided
        if "password" in update_data and update_data["password"]:
            update_data["password"] = hash_password(update_data["password"])
        
        # Convert enum values
        if "room_type" in update_data and isinstance(update_data["room_type"], RoomType):
            update_data["type"] = update_data["room_type"].value
            del update_data["room_type"]
        
        if "status" in update_data and isinstance(update_data["status"], RoomStatus):
            update_data["status"] = update_data["status"].value
        
        # Update room in Neo4j
        updated_room_data = await self.storage.update_room(room_id, update_data)
        
        if not updated_room_data:
            return None
        
        # Track activity
        await self.storage.track_user_activity(
            user_id, room_id, "room_updated",
            {"updated_fields": list(update_data.keys())}
        )
        
        # Convert back to Room model
        return await self.get_room(room_id)
    
    async def delete_room(self, room_id: str, user_id: str) -> bool:
        """Delete a room"""
        # Verify room exists
        room = await self.get_room(room_id)
        if not room:
            return False
        
        # Check if user is host
        participants = await self.storage.get_room_participants(room_id)
        user_participant = next((p for p in participants if p["user_id"] == user_id), None)
        
        if not user_participant or user_participant["role"] != "host":
            raise PermissionError("Only hosts can delete rooms")
        
        # Instead of hard delete, archive the room
        update_data = {
            "status": RoomStatus.ARCHIVED.value,
            "actual_end": datetime.utcnow()
        }
        
        # Update room status to archived
        result = await self.storage.update_room(room_id, update_data)
        
        if result:
            # Track activity
            await self.storage.track_user_activity(
                user_id, room_id, "room_deleted",
                {"room_name": room.name}
            )
            
            # Clear caches
            if room_id in self._active_users_cache:
                del self._active_users_cache[room_id]
            
            return True
        
        return False
    
    async def join_room(
        self,
        room_id: str,
        user_id: str,
        user_name: str,
        request: JoinRoomRequest
    ) -> RoomParticipant:
        """Join a room"""
        # Get room details
        room = await self.get_room(room_id)
        if not room:
            raise ValueError("Room not found")
        
        # Get current participants
        participants = await self.storage.get_room_participants(room_id)
        active_participants = [p for p in participants if p.get("is_active", True)]
        
        # Check if room is full
        if len(active_participants) >= room.max_participants:
            raise ValueError("Room is full")
        
        # Check password for private rooms
        if not room.is_public and room.password_protected:
            # Check both password fields (for compatibility)
            password = request.password or request.room_password
            if not password:
                raise ValueError("Password required")
            if not verify_password(password, room.room_password):
                raise ValueError("Invalid password")
        
        # Check if user already in room
        existing = next((p for p in participants if p["user_id"] == user_id), None)
        if existing:
            # User is already a participant
            participant = RoomParticipant(
                room_id=room_id,
                user_id=user_id,
                user_name=existing.get("username", user_name),
                user_role=UserRole(existing["role"]),
                joined_at=datetime.fromisoformat(existing["joined_at"]) if isinstance(existing.get("joined_at"), str) else existing.get("joined_at"),
                is_active=True
            )
            
            # Update activity
            await self.storage.track_user_activity(
                user_id, room_id, "rejoined_room", {}
            )
            
            return participant
        
        # Add new participant
        role = request.role.value if isinstance(request.role, UserRole) else request.role
        success = await self.storage.add_participant(room_id, user_id, user_name, role)
        
        if not success:
            raise ValueError("Failed to join room")
        
        # Track activity
        await self.storage.track_user_activity(
            user_id, room_id, "joined_room",
            {"room_name": room.name}
        )
        
        # Update room status if needed
        if len(active_participants) == 0 and room.status == RoomStatus.SCHEDULED:
            await self.storage.update_room(room_id, {
                "status": RoomStatus.ACTIVE.value,
                "actual_start": datetime.utcnow()
            })
        
        # Clear cache
        if room_id in self._active_users_cache:
            del self._active_users_cache[room_id]
        
        # Create participant object
        participant = RoomParticipant(
            room_id=room_id,
            user_id=user_id,
            user_name=user_name,
            user_role=request.role,
            joined_at=datetime.utcnow(),
            is_active=True
        )
        
        return participant
    
    async def leave_room(self, room_id: str, user_id: str) -> bool:
        """Leave a room"""
        # Remove participant from room
        success = await self.storage.remove_participant(room_id, user_id)
        
        if not success:
            return False
        
        # Track activity
        await self.storage.track_user_activity(
            user_id, room_id, "left_room", {}
        )
        
        # Check if room is now empty
        participants = await self.storage.get_room_participants(room_id)
        active_participants = [p for p in participants if p.get("is_active", True)]
        
        if len(active_participants) == 0:
            # Update room status to completed
            await self.storage.update_room(room_id, {
                "status": RoomStatus.COMPLETED.value,
                "actual_end": datetime.utcnow()
            })
        
        # Clear cache
        if room_id in self._active_users_cache:
            del self._active_users_cache[room_id]
        
        return True
    
    async def get_participant(
        self,
        room_id: str,
        user_id: str
    ) -> Optional[RoomParticipant]:
        """Get participant by user ID"""
        participants = await self.storage.get_room_participants(room_id)
        
        for p in participants:
            if p["user_id"] == user_id:
                return RoomParticipant(
                    room_id=room_id,
                    user_id=p["user_id"],
                    user_name=p.get("username", f"User_{p['user_id']}"),
                    user_role=UserRole(p["role"]),
                    joined_at=datetime.fromisoformat(p["joined_at"]) if isinstance(p.get("joined_at"), str) else p.get("joined_at"),
                    is_active=p.get("is_active", True),
                    last_seen=datetime.fromisoformat(p["last_seen"]) if isinstance(p.get("last_seen"), str) else p.get("last_seen")
                )
        
        return None
    
    async def get_active_participants(
        self,
        room_id: str
    ) -> List[RoomParticipant]:
        """Get all active participants in a room"""
        participants = await self.storage.get_room_participants(room_id)
        
        active_participants = []
        for p in participants:
            if p.get("is_active", True):  # Default to active if not specified
                participant = RoomParticipant(
                    room_id=room_id,
                    user_id=p["user_id"],
                    user_name=p.get("username", f"User_{p['user_id']}"),
                    user_role=UserRole(p["role"]),
                    joined_at=datetime.fromisoformat(p["joined_at"]) if isinstance(p.get("joined_at"), str) else p.get("joined_at"),
                    is_active=True,
                    last_seen=datetime.fromisoformat(p["last_seen"]) if isinstance(p.get("last_seen"), str) else p.get("last_seen")
                )
                active_participants.append(participant)
        
        return active_participants
    
    async def update_participant_status(
        self,
        room_id: str,
        user_id: str,
        video_enabled: Optional[bool] = None,
        audio_enabled: Optional[bool] = None,
        screen_sharing: Optional[bool] = None,
        hand_raised: Optional[bool] = None
    ) -> Optional[RoomParticipant]:
        """Update participant status"""
        participant = await self.get_participant(room_id, user_id)
        if not participant:
            return None
        
        if video_enabled is not None:
            participant.video_enabled = video_enabled
        if audio_enabled is not None:
            participant.audio_enabled = audio_enabled
        if screen_sharing is not None:
            participant.screen_sharing = screen_sharing
        if hand_raised is not None:
            participant.hand_raised = hand_raised
        
        return participant
    
    async def promote_to_cohost(
        self,
        room_id: str,
        host_id: str,
        target_user_id: str
    ) -> bool:
        """Promote a participant to co-host"""
        # Update role using Neo4j storage
        success = await self.storage.update_user_role_in_room(
            room_id=room_id,
            user_id=target_user_id,
            new_role="co_host",
            updated_by=host_id
        )
        
        if success:
            # Track activity
            await self.storage.track_user_activity(
                host_id, room_id, "promoted_user",
                {"target_user": target_user_id, "new_role": "co_host"}
            )
            
            # Clear cache
            if room_id in self._active_users_cache:
                del self._active_users_cache[room_id]
        
        return success
    
    async def get_user_rooms(
        self,
        user_id: str,
        include_archived: bool = False
    ) -> List[Room]:
        """Get all rooms for a user"""
        # Prepare status filter
        status_filter = None if include_archived else ["active", "scheduled", "completed", "disabled"]
        
        # Get rooms from Neo4j
        room_data_list = await self.storage.get_user_rooms(
            user_id=user_id,
            status_filter=status_filter,
            limit=100,
            offset=0
        )
        
        # Convert to Room models
        user_rooms = []
        for room_data in room_data_list:
            room = Room(
                room_id=room_data["room_id"],
                name=room_data["name"],
                description=room_data.get("description"),
                room_type=room_data["room_type"],
                status=RoomStatus(room_data.get("status", RoomStatus.ACTIVE)),
                max_participants=room_data.get("max_participants", 50),
                current_participants=room_data.get("current_participants", 0),
                is_public=not room_data.get("is_private", False),
                password_protected=bool(room_data.get("password")),
                room_password=room_data.get("password"),
                created_by={"user_id": room_data.get("creator_id", "")},
                created_at=datetime.fromisoformat(room_data["created_at"]) if isinstance(room_data.get("created_at"), str) else room_data.get("created_at", datetime.utcnow()),
                updated_at=datetime.fromisoformat(room_data["updated_at"]) if isinstance(room_data.get("updated_at"), str) else room_data.get("updated_at", datetime.utcnow()),
                settings={},
                voice_enabled=room_data.get("voice_enabled", False),
                screen_sharing=room_data.get("screen_sharing", False),
                recording_enabled=room_data.get("recording_enabled", False),
                active_users=[]  # Don't populate from storage, use empty list
            )
            user_rooms.append(room)
        
        return user_rooms
    
    async def search_rooms(
        self,
        query: str = "",
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Room]:
        """Main search method with comprehensive filters"""
        if filters is None:
            filters = {}
        
        # Check cache first
        cache_key = self._get_cache_key(query, filters)
        cached_results = await self._get_cached_results(cache_key)
        if cached_results is not None:
            return cached_results
        
        # Extract filters
        room_type = filters.get('room_type')
        status = filters.get('status')
        is_public = filters.get('is_public')
        limit = filters.get('limit', 50)
        offset = filters.get('offset', 0)
        
        # Use database search
        if is_public is True or is_public is None:
            # Search public rooms or all rooms
            room_data_list = await self.storage.search_public_rooms(
                search_query=query,
                room_type=room_type.value if room_type and isinstance(room_type, RoomType) else room_type,
                limit=limit,
                offset=offset
            )
        else:
            # Get all rooms with filters
            room_data_list = await self.storage.get_rooms(
                room_type=room_type.value if room_type and isinstance(room_type, RoomType) else room_type,
                status=status.value if status and isinstance(status, RoomStatus) else status,
                is_private=not is_public if is_public is not None else None
            )
            
            # Apply text search manually if query provided
            if query:
                query_lower = query.lower()
                filtered_data = []
                for room_data in room_data_list:
                    if (query_lower in room_data.get('name', '').lower() or 
                        query_lower in room_data.get('description', '').lower()):
                        filtered_data.append(room_data)
                room_data_list = filtered_data
            
            # Apply pagination
            room_data_list = room_data_list[offset:offset + limit]
        
        # Convert to Room models
        results = []
        for room_data in room_data_list:
            room = Room(
                room_id=room_data["room_id"],
                name=room_data["name"],
                description=room_data.get("description"),
                room_type=room_data["room_type"],
                status=RoomStatus(room_data.get("status", RoomStatus.ACTIVE)),
                max_participants=room_data.get("max_participants", 50),
                current_participants=room_data.get("current_participants", 0),
                is_public=not room_data.get("is_private", False),
                password_protected=bool(room_data.get("password")),
                created_by={"user_id": room_data.get("creator_id", "")},
                created_at=datetime.fromisoformat(room_data["created_at"]) if isinstance(room_data.get("created_at"), str) else room_data.get("created_at", datetime.utcnow()),
                updated_at=datetime.fromisoformat(room_data["updated_at"]) if isinstance(room_data.get("updated_at"), str) else room_data.get("updated_at", datetime.utcnow()),
                settings={},
                voice_enabled=room_data.get("voice_enabled", False),
                screen_sharing=room_data.get("screen_sharing", False),
                recording_enabled=room_data.get("recording_enabled", False),
                active_users=[]
            )
            results.append(room)
        
        # Cache the results
        self._cache_results(cache_key, results)
        
        return results
    
    async def search_by_name(self, query: str, fuzzy: bool = True) -> List[Room]:
        """Search rooms by name with fuzzy matching"""
        # Use the main search method with name filtering
        filters = {
            'status': None,  # Include all statuses except archived
            'limit': 100
        }
        
        all_rooms = await self.search_rooms(query, filters)
        
        # Filter out archived rooms
        results = []
        query_lower = query.lower()
        
        for room in all_rooms:
            if room.status == RoomStatus.ARCHIVED:
                continue
                
            room_name_lower = room.name.lower()
            
            if fuzzy:
                # Fuzzy matching
                score = self._fuzzy_match_score(query_lower, room_name_lower)
                if score > 0.6:  # Threshold for fuzzy matching
                    results.append((score, room))
            else:
                # Exact substring match
                if query_lower in room_name_lower:
                    results.append((1.0, room))
        
        # Sort by score
        results.sort(key=lambda x: x[0], reverse=True)
        return [room for _, room in results]
    
    async def search_by_type(self, room_type: RoomType) -> List[Room]:
        """Search by room type"""
        filters = {
            'room_type': room_type,
            'limit': 100
        }
        rooms = await self.search_rooms("", filters)
        # Filter out archived rooms
        return [room for room in rooms if room.status != RoomStatus.ARCHIVED]
    
    async def search_by_status(self, status: RoomStatus) -> List[Room]:
        """Search by room status"""
        filters = {
            'status': status,
            'limit': 100
        }
        return await self.search_rooms("", filters)
    
    async def search_by_creator(self, creator_id: str) -> List[Room]:
        """Search rooms created by specific user"""
        # Get all rooms and filter by creator
        all_rooms = await self.get_all_rooms()
        return [
            room for room in all_rooms
            if room.created_by.get('user_id') == creator_id
        ]
    
    async def search_by_participant(self, user_id: str) -> List[Room]:
        """Search rooms where user is participant"""
        # Use get_user_rooms method which queries the database
        return await self.get_user_rooms(user_id, include_archived=False)
    
    async def search_public_rooms(self, filters: Optional[Dict[str, Any]] = None) -> List[Room]:
        """Search only public rooms"""
        if filters is None:
            filters = {}
        
        # Extract search parameters
        search_query = filters.get('query', '')
        room_type = filters.get('room_type')
        limit = filters.get('limit', 20)
        offset = filters.get('offset', 0)
        
        # Convert enum to string if needed
        if room_type and isinstance(room_type, RoomType):
            room_type = room_type.value
        
        # Search using Neo4j
        room_data_list = await self.storage.search_public_rooms(
            search_query=search_query,
            room_type=room_type,
            limit=limit,
            offset=offset
        )
        
        # Convert to Room models
        rooms = []
        for room_data in room_data_list:
            room = Room(
                room_id=room_data["room_id"],
                name=room_data["name"],
                description=room_data.get("description"),
                room_type=room_data["room_type"],
                status=RoomStatus(room_data.get("status", RoomStatus.ACTIVE)),
                max_participants=room_data.get("max_participants", 50),
                current_participants=room_data.get("participant_count", 0),
                is_public=not room_data.get("is_private", False),
                password_protected=bool(room_data.get("password")),
                room_password=room_data.get("password"),
                created_by={"user_id": room_data.get("creator_id", "")},
                created_at=datetime.fromisoformat(room_data["created_at"]) if isinstance(room_data.get("created_at"), str) else room_data.get("created_at", datetime.utcnow()),
                updated_at=datetime.fromisoformat(room_data["updated_at"]) if isinstance(room_data.get("updated_at"), str) else room_data.get("updated_at", datetime.utcnow()),
                settings={},
                voice_enabled=room_data.get("voice_enabled", False),
                screen_sharing=room_data.get("screen_sharing", False),
                recording_enabled=room_data.get("recording_enabled", False),
                active_users=[]  # Don't populate from storage, use empty list
            )
            rooms.append(room)
        
        return rooms
    
    async def advanced_search(self, criteria: Dict[str, Any]) -> List[Room]:
        """Advanced search with multiple criteria"""
        # Build filters from criteria
        filters = {}
        
        # Extract search query
        query = criteria.get('query', '')
        
        # Map criteria to filters
        if 'room_type' in criteria:
            filters['room_type'] = criteria['room_type']
        if 'status' in criteria:
            filters['status'] = criteria['status']
        if 'is_public' in criteria:
            filters['is_public'] = criteria['is_public']
        if 'max_participants' in criteria:
            filters['max_participants'] = criteria['max_participants']
        if 'created_after' in criteria:
            filters['created_after'] = criteria['created_after']
        if 'created_before' in criteria:
            filters['created_before'] = criteria['created_before']
        if 'has_recording' in criteria:
            filters['has_recording'] = criteria['has_recording']
        if 'institution' in criteria:
            filters['institution'] = criteria['institution']
        if 'tags' in criteria:
            filters['tags'] = criteria['tags']
        if 'creator_id' in criteria:
            filters['creator_id'] = criteria['creator_id']
        if 'participant_id' in criteria:
            filters['participant_id'] = criteria['participant_id']
        
        # Pagination and sorting
        if 'offset' in criteria:
            filters['offset'] = criteria['offset']
        if 'limit' in criteria:
            filters['limit'] = criteria['limit']
        if 'sort_by' in criteria:
            filters['sort_by'] = criteria['sort_by']
        if 'sort_order' in criteria:
            filters['sort_order'] = criteria['sort_order']
        
        return await self.search_rooms(query, filters)
    
    # ============= Search Helper Methods =============
    
    def _apply_filters(self, room: Room, filters: Dict[str, Any]) -> bool:
        """Apply all filters to a room"""
        # Room type filter
        if 'room_type' in filters and room.room_type != filters['room_type']:
            return False
        
        # Status filter
        if 'status' in filters and room.status != filters['status']:
            return False
        
        # Public/private filter
        if 'is_public' in filters:
            if filters['is_public'] and not room.is_public:
                return False
            if not filters['is_public'] and not not room.is_public:
                return False
        
        # Max participants filter
        if 'max_participants' in filters:
            if room.max_participants < filters['max_participants']:
                return False
        
        # Date range filters
        if 'created_after' in filters:
            if room.created_at < filters['created_after']:
                return False
        
        if 'created_before' in filters:
            if room.created_at > filters['created_before']:
                return False
        
        # Creator filter
        if 'creator_id' in filters:
            if room.creator_id != filters['creator_id']:
                return False
        
        # Participant filter - skip for now as it requires async database lookup
        # This should be handled at the database query level
        if 'participant_id' in filters:
            # TODO: This filter needs to be applied differently
            pass
        
        # Teaching room specific filters
        if room.room_type == RoomType.TEACHING:
            # Has recording filter
            if 'has_recording' in filters:
                has_recording = hasattr(room, 'recording_url') and room.recording_url
                if filters['has_recording'] and not has_recording:
                    return False
                if not filters['has_recording'] and has_recording:
                    return False
            
            # Institution filter
            if 'institution' in filters:
                if not hasattr(room, 'institution') or room.institution != filters['institution']:
                    return False
        
        # Tags filter
        if 'tags' in filters and filters['tags']:
            if not hasattr(room, 'tags') or not room.tags:
                return False
            room_tags = set(room.tags) if isinstance(room.tags, list) else set()
            filter_tags = set(filters['tags']) if isinstance(filters['tags'], list) else {filters['tags']}
            if not room_tags.intersection(filter_tags):
                return False
        
        return True
    
    def _calculate_relevance_score(self, room: Room, query: str) -> float:
        """Calculate relevance score for search query"""
        score = 0.0
        
        # Name match (highest weight)
        if query in room.name.lower():
            score += 10.0
        else:
            # Fuzzy match on name
            name_score = self._fuzzy_match_score(query, room.name.lower())
            score += name_score * 8.0
        
        # Description match (medium weight)
        if room.description:
            if query in room.description.lower():
                score += 5.0
            else:
                desc_score = self._fuzzy_match_score(query, room.description.lower())
                score += desc_score * 3.0
        
        # Tags match (low weight)
        if hasattr(room, 'tags') and room.tags:
            for tag in room.tags:
                if query in tag.lower():
                    score += 2.0
                    break
        
        # Boost active rooms
        if room.status == RoomStatus.ACTIVE:
            score *= 1.2
        
        # Boost public rooms
        if not not room.is_public:
            score *= 1.1
        
        return score
    
    def _fuzzy_match_score(self, query: str, text: str) -> float:
        """Calculate fuzzy match score between query and text"""
        # Simple fuzzy matching based on character overlap
        if not query or not text:
            return 0.0
        
        # Check for exact substring
        if query in text:
            return 1.0
        
        # Calculate character overlap
        query_chars = set(query)
        text_chars = set(text)
        overlap = len(query_chars.intersection(text_chars))
        
        # Calculate position-based similarity
        min_len = min(len(query), len(text))
        position_matches = sum(1 for i in range(min_len) if query[i] == text[i])
        
        # Combined score
        char_score = overlap / len(query_chars) if query_chars else 0
        position_score = position_matches / min_len if min_len > 0 else 0
        
        # Check for word boundaries
        words_in_text = text.split()
        word_match_score = 0
        for word in words_in_text:
            if query in word or word in query:
                word_match_score = 0.5
                break
        
        return (char_score * 0.3 + position_score * 0.4 + word_match_score * 0.3)
    
    def _sort_results(self, rooms: List[Room], sort_by: str, reverse: bool) -> List[Room]:
        """Sort search results"""
        if not rooms:
            return rooms
        
        # Define sort key functions
        sort_keys = {
            'created_at': lambda r: r.created_at,
            'updated_at': lambda r: r.updated_at,
            'name': lambda r: r.name.lower(),
            'participant_count': lambda r: r.current_participants,
            'active_participant_count': lambda r: r.current_participants
        }
        
        # Get sort key function
        key_func = sort_keys.get(sort_by, lambda r: r.created_at)
        
        try:
            return sorted(rooms, key=key_func, reverse=reverse)
        except Exception as e:
            logger.error(f"Error sorting results: {e}")
            return rooms
    
    # ============= Search Caching =============
    
    def _get_cache_key(self, query: str, filters: Dict[str, Any]) -> str:
        """Generate cache key for search"""
        import json
        filter_str = json.dumps(filters, sort_keys=True, default=str)
        return f"{query}:{filter_str}"
    
    async def _get_cached_results(self, cache_key: str) -> Optional[List[Room]]:
        """Get cached search results"""
        if cache_key in self._search_cache:
            results, cache_time = self._search_cache[cache_key]
            if datetime.utcnow() - cache_time < self._search_cache_ttl:
                return results
            else:
                del self._search_cache[cache_key]
        return None
    
    def _cache_results(self, cache_key: str, results: List[Room]) -> None:
        """Cache search results"""
        self._search_cache[cache_key] = (results, datetime.utcnow())
        
        # Limit cache size
        if len(self._search_cache) > 100:
            # Remove oldest entries
            sorted_cache = sorted(
                self._search_cache.items(),
                key=lambda x: x[1][1]
            )
            for key, _ in sorted_cache[:20]:
                del self._search_cache[key]
    
    # ============= Search Suggestions =============
    
    async def get_search_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """Get search suggestions based on partial query"""
        suggestions = []
        query_lower = query.lower()
        
        # Get all active rooms from database
        all_rooms = await self.get_all_rooms()
        
        # Collect all searchable terms
        terms = set()
        
        for room in all_rooms:
            if room.status == RoomStatus.ARCHIVED:
                continue
                
            # Add room names
            if query_lower in room.name.lower():
                terms.add(room.name)
            
            # Add words from room names
            for word in room.name.split():
                if query_lower in word.lower():
                    terms.add(word)
            
            # Add tags
            if hasattr(room, 'tags') and room.tags:
                for tag in room.tags:
                    if query_lower in tag.lower():
                        terms.add(tag)
        
        # Sort by relevance and limit
        suggestions = sorted(
            terms,
            key=lambda t: (
                t.lower().startswith(query_lower),  # Prefix matches first
                query_lower in t.lower(),  # Then substring matches
                len(t)  # Shorter terms preferred
            ),
            reverse=True
        )[:limit]
        
        return suggestions
    
    # ============= User Activity Tracking Methods =============
    
    async def update_user_last_seen(self, room_id: str, user_id: str) -> None:
        """Update user's last activity timestamp"""
        try:
            # Update participant last seen
            participant = await self.get_participant(room_id, user_id)
            if participant:
                participant.last_seen = datetime.utcnow()
                participant.is_currently_active = True
                
                # Update activity tracking
                activity_key = f"{room_id}:{user_id}"
                if activity_key not in self._user_activity:
                    self._user_activity[activity_key] = {
                        'room_id': room_id,
                        'user_id': user_id,
                        'first_seen': datetime.utcnow(),
                        'message_count': 0,
                        'total_time_seconds': 0,
                        'last_activity_start': datetime.utcnow()
                    }
                
                self._user_activity[activity_key]['last_seen'] = datetime.utcnow()
                
                # Invalidate cache
                if room_id in self._active_users_cache:
                    del self._active_users_cache[room_id]
                    
                logger.info(f"Updated last seen for user {user_id} in room {room_id}")
        except Exception as e:
            logger.error(f"Error updating user last seen: {e}")
    
    async def get_active_users(self, room_id: str, threshold_minutes: int = 5) -> List[Dict[str, Any]]:
        """Get users active within threshold"""
        try:
            # Check cache first
            if room_id in self._active_users_cache:
                cached_users, cache_time = self._active_users_cache[room_id]
                if datetime.utcnow() - cache_time < self._cache_ttl:
                    return cached_users
            
            active_users = []
            threshold = datetime.utcnow() - timedelta(minutes=threshold_minutes)
            
            # Get participants from database
            participants = await self.storage.get_room_participants(room_id)
            for participant_data in participants:
                if participant_data.get('is_active', True):
                    # Check activity tracking for last seen info
                    activity_key = f"{room_id}:{participant_data['user_id']}"
                    activity_info = self._user_activity.get(activity_key)
                    
                    last_seen = None
                    if activity_info and 'last_seen' in activity_info:
                        last_seen = activity_info['last_seen']
                    
                    if last_seen and last_seen > threshold:
                        user_info = {
                            'user_id': participant_data['user_id'],
                            'user_name': participant_data.get('username', f"User_{participant_data['user_id']}"),
                            'user_role': participant_data['role'],
                            'last_seen': last_seen,
                            'is_currently_active': activity_info.get('is_currently_active', False) if activity_info else False,
                            'video_enabled': False,
                            'audio_enabled': False,
                            'screen_sharing': False
                        }
                        active_users.append(user_info)
            
            # Update cache
            self._active_users_cache[room_id] = (active_users, datetime.utcnow())
            
            return active_users
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    async def update_user_status(self, room_id: str, user_id: str, is_active: bool) -> bool:
        """Update user active/inactive status"""
        try:
            participant = await self.get_participant(room_id, user_id)
            if not participant:
                return False
            
            participant.is_currently_active = is_active
            
            # Update activity tracking
            activity_key = f"{room_id}:{user_id}"
            if activity_key in self._user_activity:
                if is_active:
                    self._user_activity[activity_key]['last_activity_start'] = datetime.utcnow()
                else:
                    # Calculate time spent
                    if 'last_activity_start' in self._user_activity[activity_key]:
                        start_time = self._user_activity[activity_key]['last_activity_start']
                        time_spent = (datetime.utcnow() - start_time).total_seconds()
                        self._user_activity[activity_key]['total_time_seconds'] += time_spent
            
            # Invalidate cache
            if room_id in self._active_users_cache:
                del self._active_users_cache[room_id]
                
            logger.info(f"Updated user {user_id} status to {'active' if is_active else 'inactive'} in room {room_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating user status: {e}")
            return False
    
    async def get_user_activity_info(self, room_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed activity info for a user"""
        try:
            activity_key = f"{room_id}:{user_id}"
            activity_data = self._user_activity.get(activity_key)
            
            if not activity_data:
                return None
            
            participant = await self.get_participant(room_id, user_id)
            if not participant:
                return None
            
            # Calculate current session time if active
            current_session_time = 0
            if participant.is_currently_active and 'last_activity_start' in activity_data:
                current_session_time = (datetime.utcnow() - activity_data['last_activity_start']).total_seconds()
            
            return {
                'user_id': user_id,
                'room_id': room_id,
                'first_seen': activity_data.get('first_seen'),
                'last_seen': activity_data.get('last_seen'),
                'is_currently_active': participant.is_currently_active,
                'message_count': activity_data.get('message_count', 0),
                'total_time_seconds': activity_data.get('total_time_seconds', 0) + current_session_time,
                'last_login': self._user_logins.get(user_id),
                'current_session_duration': current_session_time if participant.is_currently_active else 0
            }
        except Exception as e:
            logger.error(f"Error getting user activity info: {e}")
            return None
    
    async def track_user_login(self, user_id: str) -> None:
        """Track user login time globally"""
        try:
            self._user_logins[user_id] = datetime.utcnow()
            logger.info(f"Tracked login for user {user_id}")
        except Exception as e:
            logger.error(f"Error tracking user login: {e}")
    
    async def get_user_last_login(self, user_id: str) -> Optional[datetime]:
        """Get user's last login timestamp"""
        return self._user_logins.get(user_id)
    
    # ============= Enhanced Participant Tracking =============
    
    def _enhance_participant(self, participant: RoomParticipant) -> None:
        """Add enhanced tracking fields to participant"""
        if not hasattr(participant, 'last_seen'):
            participant.last_seen = datetime.utcnow()
        if not hasattr(participant, 'is_currently_active'):
            participant.is_currently_active = True
        if not hasattr(participant, 'last_login'):
            participant.last_login = self._user_logins.get(participant.user_id)
    
    async def track_message_activity(self, room_id: str, user_id: str) -> None:
        """Track message activity for a user"""
        try:
            activity_key = f"{room_id}:{user_id}"
            if activity_key in self._user_activity:
                self._user_activity[activity_key]['message_count'] += 1
                await self.update_user_last_seen(room_id, user_id)
        except Exception as e:
            logger.error(f"Error tracking message activity: {e}")
    
    # ============= Room Status Management =============
    
    async def enable_room(self, room_id: str) -> bool:
        """Enable a disabled room"""
        try:
            room = await self.get_room(room_id)
            if not room:
                return False
            
            if room.status in [RoomStatus.DISABLED, RoomStatus.SCHEDULED]:
                update_data = {
                    "status": RoomStatus.ACTIVE.value,
                    "updated_at": datetime.utcnow()
                }
                result = await self.storage.update_room(room_id, update_data)
                if result:
                    logger.info(f"Enabled room {room_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error enabling room: {e}")
            return False
    
    async def disable_room(self, room_id: str) -> bool:
        """Disable a room temporarily"""
        try:
            room = await self.get_room(room_id)
            if not room:
                return False
            
            if room.status in [RoomStatus.ACTIVE, RoomStatus.SCHEDULED]:
                update_data = {
                    "status": RoomStatus.DISABLED.value,
                    "updated_at": datetime.utcnow()
                }
                result = await self.storage.update_room(room_id, update_data)
                
                if result:
                    # Mark all participants as inactive
                    participants = await self.storage.get_room_participants(room_id)
                    for participant_data in participants:
                        await self.update_user_status(room_id, participant_data['user_id'], False)
                    
                    logger.info(f"Disabled room {room_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error disabling room: {e}")
            return False
    
    async def close_room(self, room_id: str) -> bool:
        """Close a room permanently"""
        try:
            room = await self.get_room(room_id)
            if not room:
                return False
            
            update_data = {
                "status": RoomStatus.COMPLETED.value,
                "actual_end": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            result = await self.storage.update_room(room_id, update_data)
            
            if result:
                # Mark all participants as left
                participants = await self.storage.get_room_participants(room_id)
                for participant_data in participants:
                    if participant_data.get('is_active', True):
                        await self.leave_room(room_id, participant_data['user_id'])
                
                logger.info(f"Closed room {room_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error closing room: {e}")
            return False
    
    async def get_room_status(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed room status"""
        try:
            room = await self.get_room(room_id)
            if not room:
                return None
            
            active_users = await self.get_active_users(room_id)
            all_participants = await self.storage.get_room_participants(room_id)
            
            # Calculate room statistics
            total_participants = len(all_participants)
            active_participants = len([p for p in all_participants if p.get('is_active', True)])
            peak_concurrent = self._room_activity.get(room_id, {}).get('peak_concurrent_users', active_participants)
            
            return {
                'room_id': room_id,
                'name': room.name,
                'status': room.status,
                'created_at': room.created_at,
                'updated_at': room.updated_at,
                'actual_start': room.actual_start,
                'actual_end': room.actual_end,
                'total_participants': total_participants,
                'active_participants': active_participants,
                'currently_active_users': len(active_users),
                'peak_concurrent_users': peak_concurrent,
                'is_private': not room.is_public,
                'room_type': room.room_type,
                'max_participants': room.max_participants
            }
        except Exception as e:
            logger.error(f"Error getting room status: {e}")
            return None
    
    async def update_room_status(self, room_id: str, status: RoomStatus) -> bool:
        """Update room status"""
        try:
            room = await self.get_room(room_id)
            if not room:
                return False
            
            old_status = room.status
            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow()
            }
            
            # Handle status-specific actions
            if status == RoomStatus.ACTIVE and old_status != RoomStatus.ACTIVE:
                update_data["actual_start"] = datetime.utcnow()
            elif status in [RoomStatus.COMPLETED, RoomStatus.ARCHIVED]:
                update_data["actual_end"] = datetime.utcnow()
            
            result = await self.storage.update_room(room_id, update_data)
            if result:
                logger.info(f"Updated room {room_id} status from {old_status} to {status}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating room status: {e}")
            return False
    
    # ============= Activity-Based Features =============
    
    async def update_participant_count(self, room_id: str) -> None:
        """Auto-update participant count based on active users"""
        try:
            active_users = await self.get_active_users(room_id, threshold_minutes=5)
            current_count = len(active_users)
            
            if room_id not in self._room_activity:
                self._room_activity[room_id] = {
                    'peak_concurrent_users': 0,
                    'total_unique_users': set(),
                    'activity_log': []
                }
            
            # Update peak concurrent users
            if current_count > self._room_activity[room_id]['peak_concurrent_users']:
                self._room_activity[room_id]['peak_concurrent_users'] = current_count
            
            # Track unique users
            for user in active_users:
                self._room_activity[room_id]['total_unique_users'].add(user['user_id'])
            
            # Log activity
            self._room_activity[room_id]['activity_log'].append({
                'timestamp': datetime.utcnow(),
                'active_count': current_count
            })
        except Exception as e:
            logger.error(f"Error updating participant count: {e}")
    
    async def generate_activity_report(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Generate activity report for a room"""
        try:
            room = self._rooms.get(room_id)
            if not room:
                return None
            
            room_activity = self._room_activity.get(room_id, {})
            participants = await self.storage.get_room_participants(room_id)
            
            # Calculate metrics
            total_unique_users = len(room_activity.get('total_unique_users', set()))
            peak_concurrent = room_activity.get('peak_concurrent_users', 0)
            
            # User activity breakdown
            user_activities = []
            for participant_data in participants:
                activity_info = await self.get_user_activity_info(room_id, participant_data['user_id'])
                if activity_info:
                    user_activities.append({
                        'user_id': participant_data['user_id'],
                        'user_name': participant_data.get('username', f"User_{participant_data['user_id']}"),
                        'total_time_seconds': activity_info['total_time_seconds'],
                        'message_count': activity_info['message_count'],
                        'last_seen': activity_info['last_seen']
                    })
            
            # Sort by total time
            user_activities.sort(key=lambda x: x['total_time_seconds'], reverse=True)
            
            duration = None
            if room.actual_start:
                end_time = room.actual_end or datetime.utcnow()
                duration = (end_time - room.actual_start).total_seconds()
            
            return {
                'room_id': room_id,
                'room_name': room.name,
                'status': room.status,
                'duration_seconds': duration,
                'total_unique_users': total_unique_users,
                'peak_concurrent_users': peak_concurrent,
                'user_activities': user_activities[:10],  # Top 10 users
                'created_at': room.created_at,
                'actual_start': room.actual_start,
                'actual_end': room.actual_end
            }
        except Exception as e:
            logger.error(f"Error generating activity report: {e}")
            return None
    
    async def identify_inactive_users(self, room_id: str, inactive_threshold_minutes: int = 30) -> List[str]:
        """Identify inactive users for cleanup"""
        try:
            inactive_users = []
            threshold = datetime.utcnow() - timedelta(minutes=inactive_threshold_minutes)
            
            participants = await self.storage.get_room_participants(room_id)
            for participant_data in participants:
                if participant_data.get('is_active', True):
                    # Check activity tracking for last seen info
                    activity_key = f"{room_id}:{participant_data['user_id']}"
                    activity_info = self._user_activity.get(activity_key)
                    
                    if activity_info and 'last_seen' in activity_info:
                        if activity_info['last_seen'] < threshold:
                            inactive_users.append(participant_data['user_id'])
                    else:
                        # No last_seen data, consider inactive
                        inactive_users.append(participant_data['user_id'])
            
            return inactive_users
        except Exception as e:
            logger.error(f"Error identifying inactive users: {e}")
            return []
    
    async def cleanup_inactive_users(self, room_id: str, inactive_threshold_minutes: int = 30) -> int:
        """Cleanup inactive users from a room"""
        try:
            inactive_users = await self.identify_inactive_users(room_id, inactive_threshold_minutes)
            cleanup_count = 0
            
            for user_id in inactive_users:
                if await self.leave_room(room_id, user_id):
                    cleanup_count += 1
                    logger.info(f"Cleaned up inactive user {user_id} from room {room_id}")
            
            return cleanup_count
        except Exception as e:
            logger.error(f"Error cleaning up inactive users: {e}")
            return 0
    
    async def cleanup_old_activity_data(self, days_to_keep: int = 7) -> int:
        """Cleanup old activity data"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            cleanup_count = 0
            
            # Cleanup room activity logs
            for room_id, activity in list(self._room_activity.items()):
                if 'activity_log' in activity:
                    old_logs = [log for log in activity['activity_log'] if log['timestamp'] < cutoff_date]
                    cleanup_count += len(old_logs)
                    activity['activity_log'] = [log for log in activity['activity_log'] if log['timestamp'] >= cutoff_date]
            
            # Cleanup completed/archived rooms from in-memory activity data
            # Note: We don't delete rooms from the database, only clean up in-memory tracking
            for room_id in list(self._room_activity.keys()):
                if room_id in self._room_activity:
                    # Check if this room should be cleaned up
                    room = await self.get_room(room_id)
                    if room and room.status in [RoomStatus.COMPLETED, RoomStatus.ARCHIVED]:
                        if room.updated_at < cutoff_date:
                            del self._room_activity[room_id]
                            # Clean up related in-memory data
                            keys_to_remove = [k for k in self._user_activity.keys() if k.startswith(f"{room_id}:")]
                            for key in keys_to_remove:
                                del self._user_activity[key]
                            cleanup_count += 1
            
            logger.info(f"Cleaned up {cleanup_count} old activity records")
            return cleanup_count
        except Exception as e:
            logger.error(f"Error cleaning up old activity data: {e}")
            return 0
    
    # ============= Join Request Methods =============
    
    async def create_join_request(
        self,
        room_id: str,
        user_id: str,
        user_name: str,
        message: Optional[str] = None
    ) -> "RoomJoinRequest":
        """Create a new join request"""
        from ..models import RoomJoinRequest, RequestStatus
        
        request_id = str(uuid.uuid4())
        join_request_data = {
            "request_id": request_id,
            "room_id": room_id,
            "user_id": user_id,
            "user_name": user_name,
            "status": RequestStatus.PENDING.value,
            "message": message,
            "requested_at": datetime.utcnow()
        }
        
        # Store in Neo4j
        await self.storage.create_join_request(join_request_data)
        
        return RoomJoinRequest(**join_request_data)
    
    async def get_pending_join_request(
        self,
        room_id: str,
        user_id: str
    ) -> Optional["RoomJoinRequest"]:
        """Get pending join request for a user in a room"""
        from ..models import RoomJoinRequest, RequestStatus
        
        requests = await self.storage.get_join_requests(
            room_id=room_id,
            user_id=user_id,
            status=RequestStatus.PENDING.value
        )
        
        if requests:
            return RoomJoinRequest(**requests[0])
        return None
    
    async def get_room_join_requests(
        self,
        room_id: str,
        status: Optional["RequestStatus"] = None
    ) -> List["RoomJoinRequest"]:
        """Get all join requests for a room"""
        from ..models import RoomJoinRequest
        
        requests_data = await self.storage.get_join_requests(
            room_id=room_id,
            status=status.value if status else None
        )
        
        return [RoomJoinRequest(**req) for req in requests_data]
    
    async def process_join_request(
        self,
        request_id: str,
        processed_by: str,
        approve: bool,
        reason: Optional[str] = None
    ) -> Optional["RoomJoinRequest"]:
        """Process a join request (approve/reject)"""
        from ..models import RoomJoinRequest, RequestStatus
        
        # Get the request
        request_data = await self.storage.get_join_request_by_id(request_id)
        if not request_data:
            return None
        
        # Update request status
        update_data = {
            "status": RequestStatus.APPROVED.value if approve else RequestStatus.REJECTED.value,
            "processed_at": datetime.utcnow(),
            "processed_by": processed_by
        }
        
        if not approve and reason:
            update_data["rejection_reason"] = reason
        
        updated_request = await self.storage.update_join_request(request_id, update_data)
        
        if updated_request:
            return RoomJoinRequest(**updated_request)
        return None
    
    async def add_user_from_request(self, join_request: "RoomJoinRequest") -> bool:
        """Add user to room from approved join request"""
        from ..models import JoinRoomRequest, UserRole
        
        # Create a join room request
        join_room_req = JoinRoomRequest(role=UserRole.PARTICIPANT)
        
        # Add user to room
        try:
            await self.join_room(
                room_id=join_request.room_id,
                user_id=join_request.user_id,
                user_name=join_request.user_name,
                request=join_room_req
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add user from join request: {e}")
            return False
    
    async def update_room_settings(self, room_id: str, settings_update: Dict[str, Any]) -> bool:
        """Update room settings"""
        room = await self.get_room(room_id)
        if not room:
            return False
        
        # Merge settings
        current_settings = room.settings or {}
        current_settings.update(settings_update)
        
        # Update in storage
        update_data = {"settings": current_settings}
        result = await self.storage.update_room(room_id, update_data)
        
        return result is not None