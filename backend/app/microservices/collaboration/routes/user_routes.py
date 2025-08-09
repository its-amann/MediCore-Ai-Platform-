"""
User profile management routes for the collaboration microservice
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional, Dict, Any
import logging

from ..models import (
    UserProfile,
    UserType,
    CreateUserProfileRequest,
    UpdateUserProfileRequest,
    SetUserTypeRequest,
    TeacherVerificationRequest,
    UpdatePreferencesRequest,
    UserSearchRequest
)
from ..services.user_service import UserService, InstitutionVerification
from ..exceptions import NotFoundError, ValidationError, ConflictError, UnauthorizedError
from ..utils.auth_utils import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["User Profiles"], redirect_slashes=False)


# Service dependencies - will be injected from integration
async def get_user_service():
    """Get user service from collaboration integration"""
    from ..integration import collaboration_integration
    
    # Try to initialize if not already done
    if not collaboration_integration.user_service:
        try:
            # Check if running as part of unified system
            from app.core.database.neo4j_client import neo4j_client
            if neo4j_client and hasattr(neo4j_client, 'driver') and neo4j_client.driver:
                await collaboration_integration.initialize(unified_neo4j_client=neo4j_client)
        except ImportError:
            # Running standalone, initialize without unified client
            await collaboration_integration.initialize()
    
    if not collaboration_integration.user_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User service not available. Collaboration integration may not be initialized."
        )
    return collaboration_integration.user_service


@router.post("/profile", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def create_user_profile(
    request: CreateUserProfileRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Create a new user profile
    
    Only authenticated users can create profiles.
    Admin users can create profiles for others.
    """
    try:
        # Check if user is creating their own profile or is admin
        if request.user_id != current_user.get("user_id") and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only create your own profile unless you are an admin"
            )
        
        profile = await user_service.create_user_profile(request.dict())
        return profile
        
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user profile: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user profile")


@router.get("/profile/{user_id}", response_model=UserProfile)
async def get_user_profile(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get a user profile by ID
    
    Returns the user profile if it exists and is accessible.
    """
    try:
        profile = await user_service.get_user_profile(user_id)
        
        # Check if profile is private and user is not the owner or admin
        if not profile.is_profile_public:
            if user_id != current_user.get("user_id") and current_user.get("role") != "admin":
                # Return limited information for private profiles
                profile.email = None if not profile.show_email else profile.email
                profile.institution = None if not profile.show_institution else profile.institution
                profile.preferences = {}
        
        return profile
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get user profile")


@router.get("/profile", response_model=UserProfile)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get the current user's profile
    """
    try:
        profile = await user_service.get_user_profile(current_user["user_id"])
        return profile
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting current user profile: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get user profile")


@router.put("/profile/{user_id}", response_model=UserProfile)
async def update_user_profile(
    user_id: str,
    request: UpdateUserProfileRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update a user profile
    
    Users can only update their own profile unless they are admins.
    """
    try:
        # Check authorization
        if user_id != current_user.get("user_id") and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own profile"
            )
        
        # Filter out None values
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        profile = await user_service.update_user_profile(user_id, update_data)
        return profile
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user profile")


@router.post("/profile/{user_id}/set-type", response_model=UserProfile)
async def set_user_type(
    user_id: str,
    request: SetUserTypeRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Change a user's type
    
    Some transitions may require verification or admin approval.
    """
    try:
        # Check authorization
        if user_id != current_user.get("user_id") and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only change your own user type"
            )
        
        profile = await user_service.set_user_type(user_id, request.user_type)
        return profile
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting user type: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set user type")


@router.get("/by-type/{user_type}", response_model=List[UserProfile])
async def get_users_by_type(
    user_type: UserType,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get all users of a specific type
    
    Returns a paginated list of users.
    """
    try:
        users = await user_service.get_users_by_type(user_type, limit, offset)
        
        # Filter private information based on privacy settings
        filtered_users = []
        for user in users:
            if not user.is_profile_public and user.user_id != current_user.get("user_id"):
                user.email = None if not user.show_email else user.email
                user.institution = None if not user.show_institution else user.institution
                user.preferences = {}
            filtered_users.append(user)
        
        return filtered_users
        
    except Exception as e:
        logger.error(f"Error getting users by type: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get users")


@router.post("/profile/{user_id}/verify-teacher", response_model=UserProfile)
async def verify_teacher(
    user_id: str,
    request: TeacherVerificationRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Verify a teacher with institution data
    
    Teachers can verify themselves, or admins can verify teachers.
    """
    try:
        # Check authorization
        if user_id != current_user.get("user_id") and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only verify your own teacher profile"
            )
        
        # Create InstitutionVerification instance
        verification_data = InstitutionVerification(
            institution_name=request.institution_name,
            institution_email=request.institution_email,
            institution_id=request.institution_id,
            verification_document=request.verification_document
        )
        
        profile = await user_service.verify_teacher(user_id, verification_data)
        return profile
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error verifying teacher: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to verify teacher")


@router.get("/profile/{user_id}/teacher-info", response_model=Dict[str, Any])
async def get_teacher_info(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get teacher-specific information
    
    Returns detailed teacher information if the user is a teacher.
    """
    try:
        info = await user_service.get_teacher_info(user_id)
        
        # Check privacy settings
        profile = await user_service.get_user_profile(user_id)
        if not profile.is_profile_public and user_id != current_user.get("user_id"):
            # Return limited information
            info = {
                "user_id": info["user_id"],
                "full_name": info["full_name"],
                "is_verified": info["is_verified"]
            }
        
        return info
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting teacher info: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get teacher info")


@router.get("/profile/{user_id}/patient-info", response_model=Dict[str, Any])
async def get_patient_info(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get patient-specific information
    
    Returns patient information with privacy controls.
    Only the patient themselves or medical professionals can access full info.
    """
    try:
        # Check if current user is the patient, a doctor, or admin
        current_profile = await user_service.get_user_profile(current_user["user_id"])
        is_medical_professional = current_profile.user_type in [UserType.DOCTOR, UserType.ADMIN]
        
        if user_id != current_user.get("user_id") and not is_medical_professional:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the patient or medical professionals can access patient information"
            )
        
        info = await user_service.get_patient_info(user_id)
        return info
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting patient info: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get patient info")


@router.put("/profile/{user_id}/preferences", response_model=UserProfile)
async def update_preferences(
    user_id: str,
    request: UpdatePreferencesRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update user preferences
    
    Users can only update their own preferences.
    """
    try:
        # Check authorization
        if user_id != current_user.get("user_id") and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own preferences"
            )
        
        # Combine regular preferences with additional ones
        preferences = {k: v for k, v in request.dict().items() if v is not None and k != "additional_preferences"}
        if request.additional_preferences:
            preferences.update(request.additional_preferences)
        
        profile = await user_service.update_preferences(user_id, preferences)
        return profile
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update preferences")


@router.post("/search", response_model=List[UserProfile])
async def search_users(
    request: UserSearchRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Search users by name, email, or institution
    
    Returns matching users with privacy filters applied.
    """
    try:
        users = await user_service.search_users(
            query=request.query,
            user_types=request.user_types,
            limit=request.limit
        )
        
        # Apply privacy filters
        filtered_users = []
        for user in users:
            if not user.is_profile_public and user.user_id != current_user.get("user_id"):
                user.email = None if not user.show_email else user.email
                user.institution = None if not user.show_institution else user.institution
                user.preferences = {}
            filtered_users.append(user)
        
        return filtered_users
        
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to search users")


@router.get("/profile/{user_id}/completeness", response_model=Dict[str, Any])
async def get_profile_completeness(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get profile completeness information
    
    Returns completeness percentage and missing fields.
    """
    try:
        # Check authorization
        if user_id != current_user.get("user_id") and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only check your own profile completeness"
            )
        
        profile = await user_service.get_user_profile(user_id)
        
        # Calculate missing fields
        missing_fields = []
        if not profile.bio:
            missing_fields.append("bio")
        if not profile.profile_picture:
            missing_fields.append("profile_picture")
        
        # Type-specific fields
        if profile.user_type == UserType.TEACHER:
            if not profile.institution:
                missing_fields.append("institution")
            if not profile.department:
                missing_fields.append("department")
        elif profile.user_type == UserType.DOCTOR:
            if not profile.specialization:
                missing_fields.append("specialization")
            if not profile.license_number:
                missing_fields.append("license_number")
        elif profile.user_type == UserType.STUDENT:
            if not profile.student_id:
                missing_fields.append("student_id")
        
        return {
            "user_id": user_id,
            "completeness_percentage": profile.profile_completeness,
            "missing_fields": missing_fields,
            "is_verified": profile.is_verified
        }
        
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting profile completeness: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get profile completeness")