"""
Cases Chat Microservice Routes - Complete rewrite with Groq AI doctors
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json
import asyncio
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# Import error logger
from app.core.error_logger import log_api_error, log_error

from app.api.dependencies.auth import get_auth_credentials
from app.api.routes.auth import get_current_user, get_current_active_user
from app.core.database.models import User
from app.microservices.cases_chat.models import (
    CaseCreate, CaseUpdate, CaseResponse, CaseStatus, CasePriority,
    ChatMessage, ChatSession, DoctorType
)
from app.microservices.cases_chat.services.groq_doctors.doctor_service import DoctorService
from app.microservices.cases_chat.services.neo4j_storage.unified_cases_chat_storage import UnifiedCasesChatStorage
from app.microservices.cases_chat.services.media_handler.media_handler import MediaHandler
from app.microservices.cases_chat.services.case_numbering import CaseNumberGenerator
from app.microservices.cases_chat.websocket_adapter import get_cases_chat_ws_adapter
from app.core.config import settings
from app.api.dependencies.database import get_sync_driver

router = APIRouter(tags=["cases"])

# Service initialization with dependency injection and connection pooling
@lru_cache()
def get_doctor_service() -> DoctorService:
    """Get doctor service instance with error handling"""
    try:
        return DoctorService()
    except Exception as e:
        logger.error(f"Failed to initialize DoctorService: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Doctor service is currently unavailable"
        )

@lru_cache()
def get_storage_service() -> UnifiedCasesChatStorage:
    """Get storage service instance using unified database manager"""
    try:
        driver = get_sync_driver()
        return UnifiedCasesChatStorage(driver)
    except Exception as e:
        logger.error(f"Failed to initialize UnifiedCasesChatStorage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage service is currently unavailable"
        )

@lru_cache()
def get_media_handler() -> MediaHandler:
    """Get media handler instance with error handling"""
    try:
        return MediaHandler()
    except Exception as e:
        logger.error(f"Failed to initialize MediaHandler: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media handler service is currently unavailable"
        )


@lru_cache()
def get_case_number_generator() -> CaseNumberGenerator:
    """Get case number generator instance with error handling"""
    try:
        driver = get_sync_driver()
        return CaseNumberGenerator(driver)
    except Exception as e:
        logger.error(f"Failed to initialize CaseNumberGenerator: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Case number generator is currently unavailable"
        )

# Test endpoint - to verify routing
@router.get("/test")
@log_api_error
async def test_cases_route():
    """Test if cases route is loaded"""
    return {"status": "Cases route is working", "endpoint": "/api/v1/cases/test"}


@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
@log_api_error
async def create_case(
    case_data: CaseCreate,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new medical case with chat capability"""
    try:
        # Get services
        storage_service = get_storage_service()
        case_number_generator = get_case_number_generator()
        
        # Create case with user ownership
        case_dict = case_data.dict()
        
        # Parse priority if it comes as a string with description
        if case_dict.get("priority") and " - " in case_dict["priority"]:
            # Extract just the priority level (e.g., "Medium" from "Medium - Moderate concern")
            case_dict["priority"] = case_dict["priority"].split(" - ")[0].lower()
        elif case_dict.get("priority"):
            case_dict["priority"] = case_dict["priority"].lower()
        else:
            case_dict["priority"] = "medium"
        
        # Generate title if not provided
        if not case_dict.get("title"):
            case_dict["title"] = f"{case_dict['chief_complaint'][:50]}..."
            
        # Generate description if not provided
        if not case_dict.get("description"):
            case_dict["description"] = case_dict["chief_complaint"]
        
        # Generate case number
        case_number = case_number_generator.generate_case_number()
        
        case_dict.update({
            "case_id": str(uuid.uuid4()),
            "case_number": case_number,
            "user_id": current_user.user_id,
            "status": CaseStatus.ACTIVE.value,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "chat_sessions": []
        })
        
        # Store in Neo4j
        created_case = storage_service.create_case(case_dict)
        
        # Initialize chat session for the case
        chat_session = storage_service.create_chat_session(
            case_id=created_case["case_id"],
            user_id=current_user.user_id,
            session_type="multi_doctor"
        )
        
        # Notify about chat session creation via WebSocket
        if chat_session:
            ws_adapter = get_cases_chat_ws_adapter()
            await ws_adapter.notify_chat_session_created(
                user_id=current_user.user_id,
                case_id=created_case["case_id"],
                session_data=chat_session
            )
        
        # Add missing fields for CaseResponse
        created_case["title"] = created_case.get("title")
        created_case["description"] = created_case.get("description")
        created_case["case_number"] = created_case.get("case_number")
        created_case["patient_age"] = created_case.get("patient_age")
        created_case["patient_gender"] = created_case.get("patient_gender")
        created_case["medical_category"] = created_case.get("medical_category")
        created_case["diagnosis"] = None
        created_case["treatment_plan"] = None
        created_case["outcome"] = None
        created_case["closed_at"] = None
        created_case["chat_sessions"] = [chat_session] if chat_session else []
        
        # Convert datetime strings to datetime objects
        if isinstance(created_case.get("created_at"), str):
            created_case["created_at"] = datetime.fromisoformat(created_case["created_at"])
        if created_case.get("updated_at") and isinstance(created_case["updated_at"], str):
            created_case["updated_at"] = datetime.fromisoformat(created_case["updated_at"])
        else:
            created_case["updated_at"] = None
        
        # Ensure priority is a valid enum value
        if created_case.get("priority"):
            priority_str = created_case["priority"].lower()
            if priority_str in ["low", "medium", "high", "critical"]:
                created_case["priority"] = CasePriority(priority_str)
            else:
                created_case["priority"] = CasePriority.MEDIUM
        else:
            created_case["priority"] = CasePriority.MEDIUM
            
        # Ensure status is a valid enum value  
        if created_case.get("status"):
            status_str = created_case["status"].lower()
            if status_str in ["active", "closed", "archived", "pending"]:
                created_case["status"] = CaseStatus(status_str)
            else:
                created_case["status"] = CaseStatus.ACTIVE
        else:
            created_case["status"] = CaseStatus.ACTIVE
        
        return CaseResponse(**created_case)
        
    except Exception as e:
        import traceback
        # Log detailed error
        error_context = {
            "case_data": case_data.dict() if case_data else None,
            "user_id": current_user.user_id if current_user else None,
            "endpoint": "create_case"
        }
        log_error(e, **error_context)
        
        logger.error(f"Failed to create case: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create case: {str(e)}"
        )


@router.get("/search/case-number/{case_number}", response_model=CaseResponse)
@log_api_error
async def search_case_by_number(
    case_number: str,
    current_user: User = Depends(get_current_active_user)
):
    """Search for a case by its case number"""
    try:
        # Get services
        storage_service = get_storage_service()
        case_number_generator = get_case_number_generator()
        
        # Validate case number format
        if not case_number_generator.validate_case_number(case_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid case number format. Expected format: MED-YYYYMMDD-XXXX"
            )
        
        # Search for the case
        case = storage_service.get_case_by_number(case_number, current_user.user_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Get chat sessions for the case
        chat_sessions = storage_service.get_case_chat_sessions(case["case_id"])
        case["chat_sessions"] = chat_sessions
        
        # Add missing fields for CaseResponse
        case["user_id"] = current_user.user_id  # Add user_id from current user
        case["case_number"] = case.get("case_number")
        case["diagnosis"] = case.get("diagnosis")
        case["treatment_plan"] = case.get("treatment_plan")
        case["outcome"] = case.get("outcome")
        case["closed_at"] = case.get("closed_at")
        
        # Convert datetime strings to datetime objects
        if isinstance(case.get("created_at"), str):
            case["created_at"] = datetime.fromisoformat(case["created_at"])
        if isinstance(case.get("updated_at"), str):
            case["updated_at"] = datetime.fromisoformat(case["updated_at"])
        if case.get("closed_at") and isinstance(case["closed_at"], str):
            case["closed_at"] = datetime.fromisoformat(case["closed_at"])
        
        # Ensure priority and status are enums
        if case.get("priority"):
            priority_str = case["priority"].lower()
            if priority_str in ["low", "medium", "high", "critical"]:
                case["priority"] = CasePriority(priority_str)
            else:
                case["priority"] = CasePriority.MEDIUM
        else:
            case["priority"] = CasePriority.MEDIUM
            
        if case.get("status"):
            status_str = case["status"].lower()
            if status_str in ["active", "closed", "archived", "pending"]:
                case["status"] = CaseStatus(status_str)
            else:
                case["status"] = CaseStatus.ACTIVE
        else:
            case["status"] = CaseStatus.ACTIVE
        
        return CaseResponse(**case)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search case: {str(e)}"
        )


@router.get("/user/cases", response_model=List[CaseResponse])
@log_api_error
async def get_user_cases(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user)
):
    """Get all cases for the current user"""
    try:
        # Get services
        storage_service = get_storage_service()
        
        cases = storage_service.get_user_cases(
            user_id=current_user.user_id,
            skip=offset,  # The method uses 'skip' parameter, not 'offset'
            limit=limit
        )
        
        formatted_cases = []
        for case in cases:
            # Get chat sessions for each case
            chat_sessions = storage_service.get_case_chat_sessions(case["case_id"])
            case["chat_sessions"] = chat_sessions
            
            # Add missing fields for CaseResponse
            case["user_id"] = current_user.user_id  # Add user_id from current user
            case["case_number"] = case.get("case_number")
            case["diagnosis"] = case.get("diagnosis")
            case["treatment_plan"] = case.get("treatment_plan")
            case["outcome"] = case.get("outcome")
            case["closed_at"] = case.get("closed_at")
            
            # Convert datetime strings to datetime objects
            if isinstance(case.get("created_at"), str):
                case["created_at"] = datetime.fromisoformat(case["created_at"])
            if isinstance(case.get("updated_at"), str):
                case["updated_at"] = datetime.fromisoformat(case["updated_at"])
            if case.get("closed_at") and isinstance(case["closed_at"], str):
                case["closed_at"] = datetime.fromisoformat(case["closed_at"])
            
            # Ensure priority and status are enums
            if case.get("priority"):
                priority_str = case["priority"].lower()
                if priority_str in ["low", "medium", "high", "critical"]:
                    case["priority"] = CasePriority(priority_str)
                else:
                    case["priority"] = CasePriority.MEDIUM
            else:
                case["priority"] = CasePriority.MEDIUM
                
            if case.get("status"):
                status_str = case["status"].lower()
                if status_str in ["active", "closed", "archived", "pending"]:
                    case["status"] = CaseStatus(status_str)
                else:
                    case["status"] = CaseStatus.ACTIVE
            else:
                case["status"] = CaseStatus.ACTIVE
            
            formatted_cases.append(CaseResponse(**case))
        
        return formatted_cases
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cases: {str(e)}"
        )


@router.get("/{case_id}", response_model=CaseResponse)
@log_api_error
async def get_case(
    case_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific case with chat history"""
    try:
        # Get services
        storage_service = get_storage_service()
        
        case = storage_service.get_case(case_id, current_user.user_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Get chat sessions for the case
        chat_sessions = storage_service.get_case_chat_sessions(case_id)
        case["chat_sessions"] = chat_sessions
        
        # Add missing fields for CaseResponse
        case["user_id"] = current_user.user_id  # Add user_id from current user
        case["case_number"] = case.get("case_number")
        case["diagnosis"] = case.get("diagnosis")
        case["treatment_plan"] = case.get("treatment_plan")
        case["outcome"] = case.get("outcome")
        case["closed_at"] = case.get("closed_at")
        
        # Convert datetime strings to datetime objects
        if isinstance(case.get("created_at"), str):
            case["created_at"] = datetime.fromisoformat(case["created_at"])
        if isinstance(case.get("updated_at"), str):
            case["updated_at"] = datetime.fromisoformat(case["updated_at"])
        if case.get("closed_at") and isinstance(case["closed_at"], str):
            case["closed_at"] = datetime.fromisoformat(case["closed_at"])
        
        # Ensure priority and status are enums  
        if case.get("priority"):
            priority_str = case["priority"].lower()
            if priority_str in ["low", "medium", "high", "critical"]:
                case["priority"] = CasePriority(priority_str)
            else:
                case["priority"] = CasePriority.MEDIUM
        else:
            case["priority"] = CasePriority.MEDIUM
            
        if case.get("status"):
            status_str = case["status"].lower()
            if status_str in ["active", "closed", "archived", "pending"]:
                case["status"] = CaseStatus(status_str)
            else:
                case["status"] = CaseStatus.ACTIVE
        else:
            case["status"] = CaseStatus.ACTIVE
        
        return CaseResponse(**case)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve case: {str(e)}"
        )


@router.put("/{case_id}", response_model=CaseResponse)
@log_api_error
async def update_case(
    case_id: str,
    case_update: CaseUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update a medical case"""
    try:
        # Get services
        storage_service = get_storage_service()
        
        # Verify case access
        existing_case = storage_service.get_case(case_id, current_user.user_id)
        if not existing_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Prepare update data
        update_data = case_update.dict(exclude_unset=True)
        
        # Convert enums to strings for storage
        if "status" in update_data and update_data["status"]:
            update_data["status"] = update_data["status"].value
        if "priority" in update_data and update_data["priority"]:
            update_data["priority"] = update_data["priority"].value
            
        # Update timestamp
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        # If closing the case, set closed_at timestamp
        if update_data.get("status") == CaseStatus.CLOSED.value:
            update_data["closed_at"] = datetime.utcnow().isoformat()
        
        # Update case in storage
        updated_case = storage_service.update_case(case_id, current_user.user_id, update_data)
        
        if not updated_case:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update case"
            )
        
        # Get chat sessions for the case
        chat_sessions = storage_service.get_case_chat_sessions(case_id)
        updated_case["chat_sessions"] = chat_sessions
        
        # Format response
        updated_case["user_id"] = current_user.user_id  # Add user_id from current user
        updated_case["case_number"] = updated_case.get("case_number")
        updated_case["diagnosis"] = updated_case.get("diagnosis")
        updated_case["treatment_plan"] = updated_case.get("treatment_plan")
        updated_case["outcome"] = updated_case.get("outcome")
        updated_case["closed_at"] = updated_case.get("closed_at")
        
        # Convert datetime strings to datetime objects
        if isinstance(updated_case.get("created_at"), str):
            updated_case["created_at"] = datetime.fromisoformat(updated_case["created_at"])
        if isinstance(updated_case.get("updated_at"), str):
            updated_case["updated_at"] = datetime.fromisoformat(updated_case["updated_at"])
        if updated_case.get("closed_at") and isinstance(updated_case["closed_at"], str):
            updated_case["closed_at"] = datetime.fromisoformat(updated_case["closed_at"])
        
        # Ensure priority and status are enums
        if updated_case.get("priority"):
            priority_str = updated_case["priority"].lower()
            if priority_str in ["low", "medium", "high", "critical"]:
                updated_case["priority"] = CasePriority(priority_str)
            else:
                updated_case["priority"] = CasePriority.MEDIUM
        else:
            updated_case["priority"] = CasePriority.MEDIUM
            
        if updated_case.get("status"):
            status_str = updated_case["status"].lower()
            if status_str in ["active", "closed", "archived", "pending"]:
                updated_case["status"] = CaseStatus(status_str)
            else:
                updated_case["status"] = CaseStatus.ACTIVE
        else:
            updated_case["status"] = CaseStatus.ACTIVE
        
        # Notify about case update via WebSocket
        ws_adapter = get_cases_chat_ws_adapter()
        await ws_adapter.notify_case_update(
            case_id=case_id,
            update_data=update_data
        )
        
        return CaseResponse(**updated_case)
        
    except HTTPException:
        raise
    except Exception as e:
        error_context = {
            "case_id": case_id,
            "update_data": case_update.dict() if case_update else None,
            "user_id": current_user.user_id if current_user else None,
            "endpoint": "update_case"
        }
        log_error(e, **error_context)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update case: {str(e)}"
        )


@router.post("/{case_id}/chat")
@log_api_error
async def chat_with_doctors(
    case_id: str,
    message: str = Form(...),
    doctor_type: DoctorType = Form(...),
    session_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_active_user)
):
    """Chat with AI doctors about a case"""
    try:
        # Get services
        storage_service = get_storage_service()
        doctor_service = get_doctor_service()
        media_handler = get_media_handler()
        
        # Verify case access
        case = storage_service.get_case(case_id, current_user.user_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Create or get chat session
        if not session_id:
            chat_session = storage_service.create_chat_session(
                case_id=case_id,
                user_id=current_user.user_id,
                session_type="multi_doctor"
            )
            session_id = chat_session["session_id"]
        
        # Process media if provided
        image_data = None
        audio_text = None
        
        if image:
            image_data = await media_handler.process_image(image)
            
        if audio:
            audio_text = await media_handler.transcribe_audio(audio)
            message = f"{message}\n[Audio transcript]: {audio_text}" if message else audio_text
        
        # Get previous conversation context
        context = storage_service.get_conversation_context(
            session_id=session_id,
            limit=10
        )
        
        # Get doctor response
        doctor_response = await doctor_service.get_doctor_response(
            doctor_type=doctor_type,
            message=message,
            case_info=case,
            context=context,
            image_data=image_data
        )
        
        # Store chat message
        chat_message = storage_service.store_chat_message(
            session_id=session_id,
            case_id=case_id,
            user_id=current_user.user_id,
            user_message=message,
            doctor_type=doctor_type.value,
            doctor_response=doctor_response["response"],
            metadata={}  # Temporarily remove metadata to test basic functionality
        )
        
        # Broadcast to WebSocket using cases/chat adapter
        ws_adapter = get_cases_chat_ws_adapter()
        await ws_adapter.broadcast_new_message(
            case_id,
            {
                "message": chat_message,
                "doctor_type": doctor_type.value,
                "session_id": session_id,
                "user_message": message,
                "doctor_response": doctor_response["response"]
            }
        )
        
        return {
            "session_id": session_id,
            "message_id": chat_message["message_id"],
            "doctor_response": doctor_response["response"],
            "doctor_type": doctor_type.value,
            "timestamp": chat_message["created_at"],
            "context_used": len(context),
            "metadata": chat_message["metadata"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


@router.post("/{case_id}/chat/switch-doctor")
@log_api_error
async def switch_doctor(
    case_id: str,
    session_id: str,
    new_doctor_type: DoctorType,
    handover_message: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Switch to a different doctor while maintaining conversation context"""
    try:
        # Get services
        storage_service = get_storage_service()
        doctor_service = get_doctor_service()
        
        # Verify access
        case = storage_service.get_case(case_id, current_user.user_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Get full conversation history
        full_context = storage_service.get_conversation_context(
            session_id=session_id,
            limit=50  # Get more context for doctor handover
        )
        
        # Create handover summary
        handover_summary = await doctor_service.create_handover_summary(
            from_doctor=full_context[-1]["doctor_type"] if full_context else "general",
            to_doctor=new_doctor_type,
            conversation_history=full_context,
            handover_message=handover_message
        )
        
        # Get new doctor's introduction
        intro_response = await doctor_service.get_doctor_response(
            doctor_type=new_doctor_type,
            message=f"I'm taking over this case. {handover_summary}",
            case_info=case,
            context=full_context,
            is_handover=True
        )
        
        # Store the handover message
        handover_chat_message = storage_service.store_chat_message(
            session_id=session_id,
            case_id=case_id,
            user_id=current_user.user_id,
            user_message=f"[Doctor Switch] {handover_message or 'Switching doctors'}",
            doctor_type=new_doctor_type.value,
            doctor_response=intro_response["response"],
            metadata={
                "is_handover": True,
                "previous_doctor": full_context[-1]["doctor_type"] if full_context else None,
                "handover_summary": handover_summary
            }
        )
        
        # Notify about doctor switch via WebSocket
        ws_adapter = get_cases_chat_ws_adapter()
        await ws_adapter.notify_doctor_switch(
            case_id=case_id,
            from_doctor=full_context[-1]["doctor_type"] if full_context else None,
            to_doctor=new_doctor_type,
            user_id=current_user.user_id,
            handover_summary=handover_summary
        )
        
        return {
            "session_id": session_id,
            "new_doctor": new_doctor_type.value,
            "introduction": intro_response["response"],
            "handover_summary": handover_summary
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Doctor switch failed: {str(e)}"
        )


@router.get("/{case_id}/chat/history")
@log_api_error
async def get_chat_history(
    case_id: str,
    session_id: Optional[str] = Query(None),
    doctor_type: Optional[DoctorType] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user)
):
    """Get chat history for a case"""
    try:
        # Get services
        storage_service = get_storage_service()
        
        # Verify access
        case = storage_service.get_case(case_id, current_user.user_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Get chat history
        history = storage_service.get_case_chat_history(
            case_id=case_id,
            session_id=session_id,
            doctor_type=doctor_type.value if doctor_type else None,
            limit=limit
        )
        
        return {
            "case_id": case_id,
            "total_messages": len(history),
            "messages": history
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat history: {str(e)}"
        )


@router.get("/{case_id}/related-cases")
@log_api_error
async def get_related_cases(
    case_id: str,
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_active_user)
):
    """Get related cases using MCP server for context"""
    try:
        # Get services
        storage_service = get_storage_service()
        
        # Verify access
        case = storage_service.get_case(case_id, current_user.user_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Get related cases through similarity search
        related_cases = storage_service.find_similar_cases(
            user_id=current_user.user_id,
            symptoms=case.get("symptoms", []),
            chief_complaint=case.get("chief_complaint", ""),
            limit=limit
        )
        
        return {
            "current_case_id": case_id,
            "related_cases": related_cases,
            "total_found": len(related_cases)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find related cases: {str(e)}"
        )


@router.post("/{case_id}/chat/generate-report")
@log_api_error
async def generate_case_report(
    case_id: str,
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Generate a comprehensive report from all doctor consultations"""
    try:
        # Get services
        storage_service = get_storage_service()
        doctor_service = get_doctor_service()
        
        # Verify access
        case = storage_service.get_case(case_id, current_user.user_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Get all conversations
        all_conversations = storage_service.get_conversation_context(
            session_id=session_id,
            limit=200
        )
        
        # Generate comprehensive report
        report = await doctor_service.generate_case_report(
            case_info=case,
            conversations=all_conversations
        )
        
        # Store report as a special message
        report_message = storage_service.store_chat_message(
            session_id=session_id,
            case_id=case_id,
            user_id=current_user.user_id,
            user_message="[Report Request]",
            doctor_type="system",
            doctor_response=report["full_report"],
            metadata={
                "is_report": True,
                "report_sections": report["sections"],
                "contributing_doctors": report["contributing_doctors"]
            }
        )
        
        # Notify about report generation via WebSocket
        ws_adapter = get_cases_chat_ws_adapter()
        await ws_adapter.notify_report_generated(
            user_id=current_user.user_id,
            case_id=case_id,
            report_data={
                "report": report["full_report"],
                "sections": report["sections"],
                "contributing_doctors": report["contributing_doctors"],
                "message_id": report_message["message_id"] if report_message else None
            }
        )
        
        return {
            "case_id": case_id,
            "session_id": session_id,
            "report": report["full_report"],
            "sections": report["sections"],
            "contributing_doctors": report["contributing_doctors"],
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )


@router.get("/case-numbers/statistics")
@log_api_error
async def get_case_number_statistics(
    current_user: User = Depends(get_current_active_user)
):
    """Get statistics about case number usage"""
    try:
        # Get services
        case_number_generator = get_case_number_generator()
        
        stats = case_number_generator.get_sequence_statistics()
        
        # Add current sequence number for today
        today_sequence = case_number_generator.get_current_sequence_number()
        stats['today_sequence_number'] = today_sequence
        stats['today_date'] = datetime.utcnow().strftime("%Y-%m-%d")
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get case number statistics: {str(e)}"
        )


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
@log_api_error
async def delete_case(
    case_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Archive a case (soft delete)"""
    try:
        # Get services
        storage_service = get_storage_service()
        
        success = storage_service.archive_case(case_id, current_user.user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive case: {str(e)}"
        )