"""
User Service for managing user profiles and types in the collaboration system
Using Neo4j for storage
"""

import logging
import json
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
from pydantic import BaseModel, Field, ValidationError

from ..models import UserProfile, UserType
from ..database.neo4j_storage import get_collaboration_storage
from ..exceptions import (
    NotFoundError,
    ValidationError as AppValidationError,
    UnauthorizedError,
    ConflictError
)

logger = logging.getLogger(__name__)


class UserTypeTransition(BaseModel):
    """Model for user type transition rules"""
    from_type: UserType
    to_type: UserType
    requires_verification: bool = False
    requires_admin_approval: bool = False
    allowed: bool = True


class InstitutionVerification(BaseModel):
    """Model for institution verification data"""
    institution_name: str
    institution_email: Optional[str] = None
    institution_id: Optional[str] = None
    verification_document: Optional[str] = None
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None


class UserPreferences(BaseModel):
    """Model for user preferences"""
    language: str = Field(default="en", description="Preferred language")
    timezone: str = Field(default="UTC", description="User timezone")
    email_notifications: bool = Field(default=True)
    push_notifications: bool = Field(default=True)
    theme: str = Field(default="light", description="UI theme preference")
    accessibility_mode: bool = Field(default=False)
    teaching_availability: Optional[Dict[str, Any]] = Field(None, description="Teaching availability for teachers")
    consultation_hours: Optional[Dict[str, Any]] = Field(None, description="Consultation hours for doctors")


class UserService:
    """Service for managing user profiles and types"""
    
    def __init__(self):
        self.storage = get_collaboration_storage()
        
        # Define allowed user type transitions
        self.type_transitions = [
            # Students can become teachers or doctors with verification
            UserTypeTransition(from_type=UserType.STUDENT, to_type=UserType.TEACHER, requires_verification=True),
            UserTypeTransition(from_type=UserType.STUDENT, to_type=UserType.DOCTOR, requires_verification=True),
            
            # Patients can become students
            UserTypeTransition(from_type=UserType.PATIENT, to_type=UserType.STUDENT),
            
            # Teachers and doctors can switch between each other with verification
            UserTypeTransition(from_type=UserType.TEACHER, to_type=UserType.DOCTOR, requires_verification=True),
            UserTypeTransition(from_type=UserType.DOCTOR, to_type=UserType.TEACHER, requires_verification=True),
            
            # Admin transitions require admin approval
            UserTypeTransition(from_type=UserType.TEACHER, to_type=UserType.ADMIN, requires_admin_approval=True),
            UserTypeTransition(from_type=UserType.DOCTOR, to_type=UserType.ADMIN, requires_admin_approval=True),
            
            # Admins can become any type
            UserTypeTransition(from_type=UserType.ADMIN, to_type=UserType.TEACHER),
            UserTypeTransition(from_type=UserType.ADMIN, to_type=UserType.DOCTOR),
            UserTypeTransition(from_type=UserType.ADMIN, to_type=UserType.STUDENT),
            UserTypeTransition(from_type=UserType.ADMIN, to_type=UserType.PATIENT),
        ]
    
    async def get_user_profile(self, user_id: str) -> UserProfile:
        """
        Get user profile by user ID from Neo4j database
        
        Args:
            user_id: User ID
            
        Returns:
            UserProfile object
            
        Raises:
            NotFoundError: If user profile not found
        """
        try:
            query = """
            MATCH (u:User {user_id: $user_id})
            RETURN u
            """
            
            result = await self.storage.run_query(query, {"user_id": user_id})
            
            if not result:
                raise NotFoundError(f"User profile not found for user_id: {user_id}")
            
            user_data = dict(result[0]["u"])
            
            # Parse preferences if stored as JSON string
            if "preferences" in user_data and isinstance(user_data["preferences"], str):
                try:
                    user_data["preferences"] = json.loads(user_data["preferences"])
                except json.JSONDecodeError:
                    user_data["preferences"] = {}
            
            # Ensure all required fields are present with defaults
            user_data.setdefault("preferences", {})
            user_data.setdefault("profile_completeness", 0.0)
            user_data.setdefault("is_active", True)
            user_data.setdefault("is_verified", False)
            user_data.setdefault("show_email", False)
            user_data.setdefault("show_real_name", True)
            user_data.setdefault("show_institution", True)
            user_data.setdefault("is_profile_public", True)
            
            # Convert string dates to datetime objects if needed
            for date_field in ["created_at", "updated_at", "last_login"]:
                if date_field in user_data and isinstance(user_data[date_field], str):
                    user_data[date_field] = datetime.fromisoformat(user_data[date_field])
            
            # Convert user_type string to enum if needed
            if "user_type" in user_data and isinstance(user_data["user_type"], str):
                user_data["user_type"] = UserType(user_data["user_type"])
            
            # Update last login
            await self.storage.run_write_query(
                """
                MATCH (u:User {user_id: $user_id})
                SET u.last_login = $last_login
                RETURN u
                """,
                {
                    "user_id": user_id,
                    "last_login": datetime.utcnow().isoformat()
                }
            )
            
            return UserProfile(**user_data)
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            raise
    
    async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> UserProfile:
        """
        Update user profile in Neo4j database
        
        Args:
            user_id: User ID
            profile_data: Profile data to update
            
        Returns:
            Updated UserProfile object
            
        Raises:
            NotFoundError: If user profile not found
            ValidationError: If profile data is invalid
        """
        try:
            # Get current profile to validate it exists
            current_profile = await self.get_user_profile(user_id)
            
            # Check if user type is being changed
            if "user_type" in profile_data and profile_data["user_type"] != current_profile.user_type.value:
                # Validate type transition
                new_type = UserType(profile_data["user_type"]) if isinstance(profile_data["user_type"], str) else profile_data["user_type"]
                await self._validate_type_transition(
                    current_profile.user_type,
                    new_type,
                    user_id
                )
            
            # Prepare update data
            update_data = profile_data.copy()
            update_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Convert enums to strings
            if "user_type" in update_data and isinstance(update_data["user_type"], UserType):
                update_data["user_type"] = update_data["user_type"].value
            
            # Convert preferences dict to JSON string for storage
            if "preferences" in update_data and isinstance(update_data["preferences"], dict):
                update_data["preferences"] = json.dumps(update_data["preferences"])
            
            # Calculate profile completeness
            merged_data = {**current_profile.dict(), **profile_data}
            update_data["profile_completeness"] = self._calculate_profile_completeness(merged_data)
            
            # Build SET clause dynamically
            set_clauses = [f"u.{key} = ${key}" for key in update_data.keys()]
            set_clause = "SET " + ", ".join(set_clauses)
            
            query = f"""
            MATCH (u:User {{user_id: $user_id}})
            {set_clause}
            RETURN u
            """
            
            params = {"user_id": user_id}
            params.update(update_data)
            
            result = await self.storage.run_write_query(query, params)
            
            if not result:
                raise NotFoundError(f"User profile not found for user_id: {user_id}")
            
            # Return updated profile
            return await self.get_user_profile(user_id)
            
        except ValidationError as e:
            raise AppValidationError(f"Invalid profile data: {str(e)}")
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            raise
    
    async def set_user_type(self, user_id: str, user_type: UserType) -> UserProfile:
        """
        Change user type with validation
        """
        # Get current profile
        current_profile = await self.get_user_profile(user_id)
        
        # Validate transition
        await self._validate_type_transition(
            current_profile.user_type,
            user_type,
            user_id
        )
        
        # Update user type
        return await self.update_user_profile(user_id, {"user_type": user_type.value})
    
    async def get_users_by_type(self, user_type: UserType, limit: int = 100, offset: int = 0) -> List[UserProfile]:
        """
        Get all users of a specific type from Neo4j
        
        Args:
            user_type: User type to filter by
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of UserProfile objects
        """
        try:
            query = """
            MATCH (u:User {user_type: $user_type})
            WHERE u.is_active = true
            RETURN u
            ORDER BY u.created_at DESC
            SKIP $offset
            LIMIT $limit
            """
            
            result = await self.storage.run_query(query, {
                "user_type": user_type.value,
                "limit": limit,
                "offset": offset
            })
            
            profiles = []
            for record in result:
                user_data = dict(record["u"])
                
                # Parse preferences if stored as JSON string
                if "preferences" in user_data and isinstance(user_data["preferences"], str):
                    try:
                        user_data["preferences"] = json.loads(user_data["preferences"])
                    except json.JSONDecodeError:
                        user_data["preferences"] = {}
                
                # Ensure defaults
                user_data.setdefault("preferences", {})
                user_data.setdefault("profile_completeness", 0.0)
                user_data.setdefault("is_active", True)
                user_data.setdefault("is_verified", False)
                user_data.setdefault("show_email", False)
                user_data.setdefault("show_real_name", True)
                user_data.setdefault("show_institution", True)
                user_data.setdefault("is_profile_public", True)
                
                # Convert string dates to datetime
                for date_field in ["created_at", "updated_at", "last_login"]:
                    if date_field in user_data and isinstance(user_data[date_field], str):
                        user_data[date_field] = datetime.fromisoformat(user_data[date_field])
                
                # Convert user_type to enum
                if "user_type" in user_data and isinstance(user_data["user_type"], str):
                    user_data["user_type"] = UserType(user_data["user_type"])
                
                profiles.append(UserProfile(**user_data))
            
            return profiles
            
        except Exception as e:
            logger.error(f"Error getting users by type: {str(e)}")
            return []
    
    async def verify_teacher(self, user_id: str, institution_data: InstitutionVerification) -> UserProfile:
        """
        Verify teacher with institution data
        
        Args:
            user_id: User ID
            institution_data: Institution verification data
            
        Returns:
            Updated UserProfile object
            
        Raises:
            NotFoundError: If user profile not found
            ValidationError: If verification fails
        """
        try:
            # Get current profile
            profile = await self.get_user_profile(user_id)
            
            # Check if user is a teacher
            if profile.user_type != UserType.TEACHER:
                raise AppValidationError("Only teachers can be verified with institution data")
            
            # Store verification data in Neo4j
            verification_data = {
                "verification_id": str(uuid.uuid4()),
                "user_id": user_id,
                "institution_name": institution_data.institution_name,
                "institution_email": institution_data.institution_email,
                "institution_id": institution_data.institution_id,
                "verification_document": institution_data.verification_document,
                "verified_at": datetime.utcnow().isoformat(),
                "verified_by": institution_data.verified_by,
                "status": "verified"
            }
            
            # Create verification node and relationship
            query = """
            MATCH (u:User {user_id: $user_id})
            CREATE (v:TeacherVerification)
            SET v += $verification_data
            CREATE (u)-[:HAS_VERIFICATION]->(v)
            RETURN v
            """
            
            await self.storage.run_write_query(query, {
                "user_id": user_id,
                "verification_data": verification_data
            })
            
            # Update profile
            update_data = {
                "institution": institution_data.institution_name,
                "is_verified": True
            }
            
            return await self.update_user_profile(user_id, update_data)
            
        except Exception as e:
            logger.error(f"Error verifying teacher: {str(e)}")
            raise
    
    async def get_teacher_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get teacher-specific information including verification details
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with teacher information
            
        Raises:
            NotFoundError: If user not found
            ValidationError: If user is not a teacher
        """
        try:
            # Get user profile
            profile = await self.get_user_profile(user_id)
            
            if profile.user_type != UserType.TEACHER:
                raise AppValidationError(f"User {user_id} is not a teacher")
            
            # Get verification info if exists
            verification_query = """
            MATCH (u:User {user_id: $user_id})-[:HAS_VERIFICATION]->(v:TeacherVerification)
            WHERE v.status = 'verified'
            RETURN v
            ORDER BY v.verified_at DESC
            LIMIT 1
            """
            
            verification_result = await self.storage.run_query(
                verification_query, 
                {"user_id": user_id}
            )
            
            verification_info = None
            if verification_result:
                verification_info = dict(verification_result[0]["v"])
            
            teacher_info = {
                "user_id": user_id,
                "full_name": profile.full_name,
                "institution": profile.institution,
                "department": profile.department,
                "years_of_experience": profile.years_of_experience,
                "is_verified": profile.is_verified,
                "bio": profile.bio,
                "teaching_availability": profile.preferences.get("teaching_availability", {}),
                "verification_info": verification_info,
                "specialization": profile.specialization,
                "profile_picture": profile.profile_picture
            }
            
            return teacher_info
            
        except Exception as e:
            logger.error(f"Error getting teacher info: {str(e)}")
            raise
    
    async def get_patient_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get patient-specific information
        """
        # Get user profile
        profile = await self.get_user_profile(user_id)
        
        if profile.user_type != UserType.PATIENT:
            raise AppValidationError(f"User {user_id} is not a patient")
        
        patient_info = {
            "user_id": user_id,
            "full_name": profile.full_name,
            "email": profile.email if profile.show_email else None,
            "bio": profile.bio,
            "preferences": {
                "language": profile.preferences.get("language", "en"),
                "timezone": profile.preferences.get("timezone", "UTC"),
                "accessibility_mode": profile.preferences.get("accessibility_mode", False)
            },
            "is_active": profile.is_active,
            "last_login": profile.last_login
        }
        
        return patient_info
    
    async def update_preferences(self, user_id: str, preferences: Dict[str, Any]) -> UserProfile:
        """
        Update user preferences
        """
        # Get current profile
        profile = await self.get_user_profile(user_id)
        
        # Merge preferences
        current_preferences = profile.preferences or {}
        updated_preferences = {**current_preferences, **preferences}
        
        # Validate preferences based on user type
        validated_preferences = self._validate_preferences(profile.user_type, updated_preferences)
        
        # Update profile
        return await self.update_user_profile(user_id, {"preferences": validated_preferences})
    
    async def search_users(
        self,
        query: str,
        user_types: Optional[List[UserType]] = None,
        limit: int = 50
    ) -> List[UserProfile]:
        """
        Search users by name, email, or institution
        
        Args:
            query: Search query
            user_types: Optional list of user types to filter
            limit: Maximum number of results
            
        Returns:
            List of matching UserProfile objects
        """
        try:
            # Build the WHERE clause
            where_clauses = [
                "u.is_active = true",
                "(toLower(u.username) CONTAINS toLower($query) OR "
                "toLower(u.full_name) CONTAINS toLower($query) OR "
                "toLower(u.email) CONTAINS toLower($query) OR "
                "toLower(u.institution) CONTAINS toLower($query))"
            ]
            
            params = {
                "query": query,
                "limit": limit
            }
            
            if user_types:
                where_clauses.append("u.user_type IN $user_types")
                params["user_types"] = [ut.value for ut in user_types]
            
            where_clause = " AND ".join(where_clauses)
            
            query_str = f"""
            MATCH (u:User)
            WHERE {where_clause}
            RETURN u
            ORDER BY u.username
            LIMIT $limit
            """
            
            result = await self.storage.run_query(query_str, params)
            
            profiles = []
            for record in result:
                user_data = dict(record["u"])
                
                # Parse preferences if stored as JSON string
                if "preferences" in user_data and isinstance(user_data["preferences"], str):
                    try:
                        user_data["preferences"] = json.loads(user_data["preferences"])
                    except json.JSONDecodeError:
                        user_data["preferences"] = {}
                
                # Ensure defaults
                user_data.setdefault("preferences", {})
                user_data.setdefault("profile_completeness", 0.0)
                user_data.setdefault("is_active", True)
                user_data.setdefault("is_verified", False)
                user_data.setdefault("show_email", False)
                user_data.setdefault("show_real_name", True)
                user_data.setdefault("show_institution", True)
                user_data.setdefault("is_profile_public", True)
                
                # Convert string dates to datetime
                for date_field in ["created_at", "updated_at", "last_login"]:
                    if date_field in user_data and isinstance(user_data[date_field], str):
                        user_data[date_field] = datetime.fromisoformat(user_data[date_field])
                
                # Convert user_type to enum
                if "user_type" in user_data and isinstance(user_data["user_type"], str):
                    user_data["user_type"] = UserType(user_data["user_type"])
                
                # Filter based on privacy settings
                if not user_data.get("is_profile_public", True):
                    # Hide private information
                    if not user_data.get("show_email", False):
                        user_data["email"] = "***@***.***"
                    if not user_data.get("show_real_name", True):
                        user_data["full_name"] = "Anonymous"
                    if not user_data.get("show_institution", True):
                        user_data["institution"] = None
                
                profiles.append(UserProfile(**user_data))
            
            return profiles
            
        except Exception as e:
            logger.error(f"Error searching users: {str(e)}")
            return []
    
    async def create_user_profile(self, user_data: Dict[str, Any]) -> UserProfile:
        """
        Create a new user profile in Neo4j
        
        Args:
            user_data: User data for creating profile
            
        Returns:
            Created UserProfile object
            
        Raises:
            ConflictError: If user already exists
            ValidationError: If user data is invalid
        """
        try:
            # Check if user already exists
            existing_query = """
            MATCH (u:User {user_id: $user_id})
            RETURN u
            """
            
            existing = await self.storage.run_query(
                existing_query, 
                {"user_id": user_data["user_id"]}
            )
            
            if existing:
                raise ConflictError(f"User profile already exists for user_id: {user_data['user_id']}")
            
            # Create UserProfile instance for validation
            profile = UserProfile(**user_data)
            
            # Calculate initial profile completeness
            profile_dict = profile.dict()
            profile_dict["profile_completeness"] = self._calculate_profile_completeness(profile_dict)
            
            # Prepare data for Neo4j
            neo4j_data = profile_dict.copy()
            
            # Convert datetime objects to ISO strings
            for key, value in neo4j_data.items():
                if isinstance(value, datetime):
                    neo4j_data[key] = value.isoformat()
                elif isinstance(value, UserType):
                    neo4j_data[key] = value.value
                elif isinstance(value, dict):
                    neo4j_data[key] = json.dumps(value)
            
            # Create user node
            create_query = """
            CREATE (u:User)
            SET u += $user_data
            RETURN u
            """
            
            result = await self.storage.run_write_query(
                create_query,
                {"user_data": neo4j_data}
            )
            
            if not result:
                raise Exception("Failed to create user profile")
            
            logger.info(f"Created user profile for {user_data['user_id']}")
            return await self.get_user_profile(user_data["user_id"])
            
        except ValidationError as e:
            raise AppValidationError(f"Invalid user data: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating user profile: {str(e)}")
            raise
    
    def _calculate_profile_completeness(self, profile_data: Dict[str, Any]) -> float:
        """
        Calculate profile completeness percentage
        """
        required_fields = ["username", "full_name", "email", "user_type"]
        optional_fields = ["bio", "profile_picture", "institution", "specialization", "department"]
        
        # Count completed required fields (weight: 60%)
        required_complete = sum(1 for field in required_fields if profile_data.get(field))
        required_score = (required_complete / len(required_fields)) * 60
        
        # Count completed optional fields (weight: 40%)
        optional_complete = sum(1 for field in optional_fields if profile_data.get(field))
        optional_score = (optional_complete / len(optional_fields)) * 40 if optional_fields else 0
        
        return round(required_score + optional_score, 2)
    
    async def _validate_type_transition(
        self,
        from_type: UserType,
        to_type: UserType,
        user_id: str
    ) -> bool:
        """
        Validate if user type transition is allowed
        
        Args:
            from_type: Current user type
            to_type: Target user type
            user_id: User ID for additional checks
            
        Returns:
            True if transition is allowed
            
        Raises:
            ValidationError: If transition is not allowed
        """
        # Check if transition is defined
        transition = next(
            (t for t in self.type_transitions 
             if t.from_type == from_type and t.to_type == to_type),
            None
        )
        
        if not transition or not transition.allowed:
            raise AppValidationError(
                f"Transition from {from_type.value} to {to_type.value} is not allowed"
            )
        
        # Check verification requirements
        if transition.requires_verification:
            # Check if user has verification
            verification_query = """
            MATCH (u:User {user_id: $user_id})-[:HAS_VERIFICATION]->(v:TeacherVerification)
            WHERE v.status = 'verified'
            RETURN v
            """
            
            verification_result = await self.storage.run_query(
                verification_query,
                {"user_id": user_id}
            )
            
            if not verification_result:
                raise AppValidationError(
                    f"Transition to {to_type.value} requires verification"
                )
        
        # Check admin approval requirements
        if transition.requires_admin_approval:
            # Check for admin approval
            approval_query = """
            MATCH (u:User {user_id: $user_id})-[:HAS_APPROVAL]->(a:AdminApproval)
            WHERE a.approval_type = $approval_type 
            AND a.status = 'approved'
            AND a.target_user_type = $target_type
            RETURN a
            """
            
            approval_result = await self.storage.run_query(
                approval_query,
                {
                    "user_id": user_id,
                    "approval_type": "user_type_transition",
                    "target_type": to_type.value
                }
            )
            
            if not approval_result:
                raise AppValidationError(
                    f"Transition to {to_type.value} requires admin approval"
                )
        
        return True
    
    def _validate_preferences(self, user_type: UserType, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate preferences based on user type
        """
        # Common preferences for all users
        validated = {
            "language": preferences.get("language", "en"),
            "timezone": preferences.get("timezone", "UTC"),
            "email_notifications": preferences.get("email_notifications", True),
            "push_notifications": preferences.get("push_notifications", True),
            "theme": preferences.get("theme", "light"),
            "accessibility_mode": preferences.get("accessibility_mode", False)
        }
        
        # Type-specific preferences
        if user_type == UserType.TEACHER:
            validated["teaching_availability"] = preferences.get("teaching_availability", {})
            validated["preferred_subjects"] = preferences.get("preferred_subjects", [])
            validated["max_students_per_session"] = preferences.get("max_students_per_session", 30)
        
        elif user_type == UserType.DOCTOR:
            validated["consultation_hours"] = preferences.get("consultation_hours", {})
            validated["emergency_contact"] = preferences.get("emergency_contact", False)
            validated["telemedicine_enabled"] = preferences.get("telemedicine_enabled", True)
        
        elif user_type == UserType.STUDENT:
            validated["learning_goals"] = preferences.get("learning_goals", [])
            validated["preferred_learning_style"] = preferences.get("preferred_learning_style", "visual")
            validated["study_reminders"] = preferences.get("study_reminders", True)
        
        elif user_type == UserType.PATIENT:
            validated["appointment_reminders"] = preferences.get("appointment_reminders", True)
            validated["medication_reminders"] = preferences.get("medication_reminders", True)
            validated["health_data_sharing"] = preferences.get("health_data_sharing", False)
        
        return validated


# Global instance
user_service = UserService()
