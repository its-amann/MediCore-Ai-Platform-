"""
User Service for managing user profiles and types in the collaboration system
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
from pydantic import BaseModel, Field, ValidationError

from ..models import UserProfile, UserType
from ..exceptions import (
    NotFoundError,
    ValidationError as AppValidationError,
    UnauthorizedError,
    ConflictError
)

# Note: This is a MongoDB backup version. 
# For production, use the Neo4j-based user_service.py
# get_db_connection would need to be implemented for MongoDB support
async def get_db_connection():
    """
    Placeholder for MongoDB connection.
    This backup file is for reference only.
    Use the Neo4j-based user_service.py for actual implementation.
    """
    raise NotImplementedError("MongoDB connection not implemented. Use Neo4j-based user_service.py")

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
        self.collection_name = "user_profiles"
        self.verification_collection = "user_verifications"
        # Note: This is a MongoDB backup version
        # MongoDB storage would need to be initialized here
        
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
        Get user profile by user ID
        
        Args:
            user_id: User ID
            
        Returns:
            UserProfile object
            
        Raises:
            NotFoundError: If user profile not found
        """
        try:
            db = await get_db_connection()
            
            # Find user profile
            profile_data = await db[self.collection_name].find_one({"user_id": user_id})
            
            if not profile_data:
                raise NotFoundError(f"User profile not found for user_id: {user_id}")
            
            # Remove MongoDB _id field
            profile_data.pop("_id", None)
            
            # Update last login
            await db[self.collection_name].update_one(
                {"user_id": user_id},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            
            return UserProfile(**profile_data)
            
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            raise
    
    async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> UserProfile:
        """
        Update user profile including user type
        
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
            db = await get_db_connection()
            
            # Get current profile
            current_profile = await self.get_user_profile(user_id)
            
            # Check if user type is being changed
            if "user_type" in profile_data and profile_data["user_type"] != current_profile.user_type:
                # Validate type transition
                await self._validate_type_transition(
                    current_profile.user_type,
                    UserType(profile_data["user_type"]),
                    user_id
                )
            
            # Update profile data
            profile_data["updated_at"] = datetime.utcnow()
            
            # Calculate profile completeness
            profile_data["profile_completeness"] = self._calculate_profile_completeness(
                {**current_profile.dict(), **profile_data}
            )
            
            # Update in database
            result = await db[self.collection_name].update_one(
                {"user_id": user_id},
                {"$set": profile_data}
            )
            
            if result.matched_count == 0:
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
        
        Args:
            user_id: User ID
            user_type: New user type
            
        Returns:
            Updated UserProfile object
            
        Raises:
            NotFoundError: If user profile not found
            ValidationError: If type transition is not allowed
        """
        try:
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
            
        except Exception as e:
            logger.error(f"Error setting user type: {str(e)}")
            raise
    
    async def get_users_by_type(self, user_type: UserType, limit: int = 100, offset: int = 0) -> List[UserProfile]:
        """
        Get all users of a specific type
        
        Args:
            user_type: User type to filter by
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of UserProfile objects
        """
        try:
            db = await get_db_connection()
            
            # Find users by type
            cursor = db[self.collection_name].find(
                {"user_type": user_type.value, "is_active": True}
            ).skip(offset).limit(limit)
            
            profiles = []
            async for profile_data in cursor:
                profile_data.pop("_id", None)
                profiles.append(UserProfile(**profile_data))
            
            return profiles
            
        except Exception as e:
            logger.error(f"Error getting users by type: {str(e)}")
            raise
    
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
            db = await get_db_connection()
            
            # Get current profile
            profile = await self.get_user_profile(user_id)
            
            # Check if user is a teacher
            if profile.user_type != UserType.TEACHER:
                raise AppValidationError("Only teachers can be verified with institution data")
            
            # Store verification data
            verification_doc = {
                "user_id": user_id,
                "institution_name": institution_data.institution_name,
                "institution_email": institution_data.institution_email,
                "institution_id": institution_data.institution_id,
                "verification_document": institution_data.verification_document,
                "verified_at": datetime.utcnow(),
                "status": "verified"
            }
            
            await db[self.verification_collection].insert_one(verification_doc)
            
            # Update profile
            update_data = {
                "institution": institution_data.institution_name,
                "is_verified": True,
                "updated_at": datetime.utcnow()
            }
            
            return await self.update_user_profile(user_id, update_data)
            
        except Exception as e:
            logger.error(f"Error verifying teacher: {str(e)}")
            raise
    
    async def get_teacher_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get teacher-specific information
        
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
            
            # Get verification info
            db = await get_db_connection()
            verification = await db[self.verification_collection].find_one(
                {"user_id": user_id, "status": "verified"}
            )
            
            teacher_info = {
                "user_id": user_id,
                "full_name": profile.full_name,
                "institution": profile.institution,
                "department": profile.department,
                "years_of_experience": profile.years_of_experience,
                "is_verified": profile.is_verified,
                "bio": profile.bio,
                "teaching_availability": profile.preferences.get("teaching_availability", {}),
                "verification_info": verification if verification else None
            }
            
            return teacher_info
            
        except Exception as e:
            logger.error(f"Error getting teacher info: {str(e)}")
            raise
    
    async def get_patient_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get patient-specific information
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with patient information
            
        Raises:
            NotFoundError: If user not found
            ValidationError: If user is not a patient
        """
        try:
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
            
        except Exception as e:
            logger.error(f"Error getting patient info: {str(e)}")
            raise
    
    async def update_preferences(self, user_id: str, preferences: Dict[str, Any]) -> UserProfile:
        """
        Update user preferences
        
        Args:
            user_id: User ID
            preferences: Preferences to update
            
        Returns:
            Updated UserProfile object
        """
        try:
            # Get current profile
            profile = await self.get_user_profile(user_id)
            
            # Merge preferences
            current_preferences = profile.preferences or {}
            updated_preferences = {**current_preferences, **preferences}
            
            # Validate preferences based on user type
            validated_preferences = self._validate_preferences(profile.user_type, updated_preferences)
            
            # Update profile
            return await self.update_user_profile(user_id, {"preferences": validated_preferences})
            
        except Exception as e:
            logger.error(f"Error updating preferences: {str(e)}")
            raise
    
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
            db = await get_db_connection()
            
            # Build search filter
            search_filter = {
                "$or": [
                    {"username": {"$regex": query, "$options": "i"}},
                    {"full_name": {"$regex": query, "$options": "i"}},
                    {"email": {"$regex": query, "$options": "i"}},
                    {"institution": {"$regex": query, "$options": "i"}}
                ],
                "is_active": True
            }
            
            if user_types:
                search_filter["user_type"] = {"$in": [ut.value for ut in user_types]}
            
            # Search users
            cursor = db[self.collection_name].find(search_filter).limit(limit)
            
            profiles = []
            async for profile_data in cursor:
                profile_data.pop("_id", None)
                profiles.append(UserProfile(**profile_data))
            
            return profiles
            
        except Exception as e:
            logger.error(f"Error searching users: {str(e)}")
            raise
    
    async def create_user_profile(self, user_data: Dict[str, Any]) -> UserProfile:
        """
        Create a new user profile
        
        Args:
            user_data: User data for creating profile
            
        Returns:
            Created UserProfile object
            
        Raises:
            ConflictError: If user already exists
            ValidationError: If user data is invalid
        """
        try:
            db = await get_db_connection()
            
            # Check if user already exists
            existing = await db[self.collection_name].find_one({"user_id": user_data["user_id"]})
            if existing:
                raise ConflictError(f"User profile already exists for user_id: {user_data['user_id']}")
            
            # Create UserProfile instance for validation
            profile = UserProfile(**user_data)
            
            # Calculate initial profile completeness
            profile_dict = profile.dict()
            profile_dict["profile_completeness"] = self._calculate_profile_completeness(profile_dict)
            
            # Insert into database
            await db[self.collection_name].insert_one(profile_dict)
            
            return profile
            
        except ValidationError as e:
            raise AppValidationError(f"Invalid user data: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating user profile: {str(e)}")
            raise
    
    def _calculate_profile_completeness(self, profile_data: Dict[str, Any]) -> float:
        """
        Calculate profile completeness percentage
        
        Args:
            profile_data: Profile data dictionary
            
        Returns:
            Completeness percentage (0-100)
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
            db = await get_db_connection()
            verification = await db[self.verification_collection].find_one(
                {"user_id": user_id, "status": "verified"}
            )
            if not verification:
                raise AppValidationError(
                    f"Transition to {to_type.value} requires verification"
                )
        
        # Check admin approval requirements
        if transition.requires_admin_approval:
            # TODO: Implement admin approval check
            raise AppValidationError(
                f"Transition to {to_type.value} requires admin approval"
            )
        
        return True
    
    def _validate_preferences(self, user_type: UserType, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate preferences based on user type
        
        Args:
            user_type: User type
            preferences: Preferences to validate
            
        Returns:
            Validated preferences
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