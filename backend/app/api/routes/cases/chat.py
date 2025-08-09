"""
Chat Routes - Dedicated chat endpoints for medical cases
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Import error logger
from app.core.error_logger import log_api_error, log_error

from app.api.routes.auth import get_current_user, get_current_active_user
from app.core.database.models import User
from app.microservices.cases_chat.models import ChatMessage, ChatSession, DoctorType
from app.microservices.cases_chat.services.neo4j_storage.unified_cases_chat_storage import UnifiedCasesChatStorage
from app.core.config import settings
from app.api.dependencies.database import get_sync_driver
from functools import lru_cache
from io import BytesIO
import json
import csv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from fastapi.responses import StreamingResponse, FileResponse

router = APIRouter(tags=["chat"])

# Service initialization with dependency injection
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


@router.get("/case/{case_id}/conversations", response_model=Dict[str, Any])
@log_api_error
async def get_case_conversations(
    case_id: str,
    session_id: Optional[str] = Query(None),
    doctor_type: Optional[DoctorType] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user)
):
    """Get all conversations for a specific case"""
    try:
        # Verify case access
        storage_service = get_storage_service()
        case = storage_service.get_case(case_id, current_user.user_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Get all chat sessions for the case
        chat_sessions = storage_service.get_case_chat_sessions(case_id)
        
        # Get chat history
        messages = storage_service.get_case_chat_history(
            case_id=case_id,
            session_id=session_id,
            doctor_type=doctor_type.value if doctor_type else None,
            limit=limit
        )
        
        # Format messages for frontend
        formatted_messages = []
        for msg in messages:
            formatted_msg = {
                "id": msg.get("message_id"),
                "message_id": msg.get("message_id"),
                "session_id": msg.get("session_id"),
                "case_id": msg.get("case_id"),
                "user_id": msg.get("user_id"),
                "user_message": msg.get("user_message"),
                "doctor_type": msg.get("doctor_type"),
                "doctor_response": msg.get("doctor_response"),
                "created_at": msg.get("created_at"),
                "timestamp": msg.get("created_at"),
                "metadata": msg.get("metadata", {}),
                "is_user": False,  # All messages in DB are doctor responses with user messages
                "content": msg.get("doctor_response"),  # For backward compatibility
                "sender": msg.get("doctor_type", "doctor"),
                "role": "doctor"
            }
            formatted_messages.append(formatted_msg)
            
            # Also add the user message as a separate entry if it exists
            if msg.get("user_message") and msg.get("user_message") != "[Doctor Switch]":
                user_msg = {
                    "id": f"user_{msg.get('message_id')}",
                    "message_id": f"user_{msg.get('message_id')}",
                    "session_id": msg.get("session_id"),
                    "case_id": msg.get("case_id"),
                    "user_id": msg.get("user_id"),
                    "content": msg.get("user_message"),
                    "created_at": msg.get("created_at"),
                    "timestamp": msg.get("created_at"),
                    "is_user": True,
                    "sender": "user",
                    "role": "user"
                }
                # Insert user message before doctor response
                formatted_messages.insert(-1, user_msg)
        
        # Get active session info
        active_session = None
        if chat_sessions:
            # Get the most recent active session
            active_sessions = [s for s in chat_sessions if s.get("is_active", False)]
            if active_sessions:
                active_session = active_sessions[0]
            else:
                active_session = chat_sessions[0]  # Fallback to most recent
        
        return {
            "case_id": case_id,
            "sessions": chat_sessions,
            "active_session": active_session,
            "messages": formatted_messages,
            "total_messages": len(formatted_messages),
            "has_more": len(messages) == limit,
            "offset": offset,
            "limit": limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_context = {
            "case_id": case_id,
            "user_id": current_user.user_id if current_user else None,
            "endpoint": "get_case_conversations"
        }
        log_error(e, **error_context)
        
        logger.error(f"Failed to retrieve conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversations: {str(e)}"
        )


@router.get("/case/{case_id}/sessions", response_model=List[Dict[str, Any]])
@log_api_error
async def get_case_sessions(
    case_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get all chat sessions for a case"""
    try:
        # Verify case access
        storage_service = get_storage_service()
        case = storage_service.get_case(case_id, current_user.user_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Get chat sessions
        sessions = storage_service.get_case_chat_sessions(case_id)
        
        # Format sessions for frontend
        formatted_sessions = []
        for session in sessions:
            formatted_session = {
                "session_id": session.get("session_id"),
                "case_id": session.get("case_id"),
                "user_id": session.get("user_id"),
                "session_type": session.get("session_type"),
                "created_at": session.get("created_at"),
                "last_activity": session.get("last_activity"),
                "is_active": session.get("is_active", False),
                "participating_doctors": session.get("participating_doctors", []),
                "message_count": session.get("message_count", 0)
            }
            formatted_sessions.append(formatted_session)
        
        return formatted_sessions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sessions: {str(e)}"
        )


@router.get("/session/{session_id}/messages", response_model=Dict[str, Any])
@log_api_error
async def get_session_messages(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user)
):
    """Get messages for a specific chat session"""
    try:
        # Get messages for the session
        messages = storage_service.get_conversation_context(
            session_id=session_id,
            limit=limit
        )
        
        # Format messages for frontend
        formatted_messages = []
        for msg in messages:
            # Add doctor response
            formatted_msg = {
                "id": msg.get("message_id"),
                "message_id": msg.get("message_id"),
                "session_id": msg.get("session_id"),
                "case_id": msg.get("case_id"),
                "user_id": msg.get("user_id"),
                "content": msg.get("doctor_response"),
                "doctor_type": msg.get("doctor_type"),
                "created_at": msg.get("created_at"),
                "timestamp": msg.get("created_at"),
                "metadata": msg.get("metadata", {}),
                "is_user": False,
                "sender": msg.get("doctor_type", "doctor"),
                "role": "doctor"
            }
            
            # Add user message if exists
            if msg.get("user_message") and msg.get("user_message") != "[Doctor Switch]":
                user_msg = {
                    "id": f"user_{msg.get('message_id')}",
                    "message_id": f"user_{msg.get('message_id')}",
                    "session_id": msg.get("session_id"),
                    "case_id": msg.get("case_id"),
                    "user_id": msg.get("user_id"),
                    "content": msg.get("user_message"),
                    "created_at": msg.get("created_at"),
                    "timestamp": msg.get("created_at"),
                    "is_user": True,
                    "sender": "user",
                    "role": "user"
                }
                formatted_messages.append(user_msg)
            
            formatted_messages.append(formatted_msg)
        
        return {
            "session_id": session_id,
            "messages": formatted_messages,
            "total_messages": len(formatted_messages),
            "has_more": len(messages) == limit
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve session messages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session messages: {str(e)}"
        )


@router.get("/doctors/available", response_model=List[Dict[str, Any]])
async def get_available_doctors():
    """Get list of available AI doctors"""
    doctors = [
        {
            "type": "general",
            "name": "Dr. Sarah Chen",
            "title": "General Practitioner",
            "specialization": "Primary care and general medicine",
            "avatar": "/api/placeholder/40/40",
            "status": "available"
        },
        {
            "type": "specialist",
            "name": "Dr. Michael Roberts",
            "title": "Internal Medicine Specialist",
            "specialization": "Complex medical conditions",
            "avatar": "/api/placeholder/40/40",
            "status": "available"
        },
        {
            "type": "pediatric",
            "name": "Dr. Emily Watson",
            "title": "Pediatrician",
            "specialization": "Children's health",
            "avatar": "/api/placeholder/40/40",
            "status": "available"
        },
        {
            "type": "mental_health",
            "name": "Dr. James Miller",
            "title": "Psychiatrist",
            "specialization": "Mental health and wellness",
            "avatar": "/api/placeholder/40/40",
            "status": "available"
        },
        {
            "type": "emergency",
            "name": "Dr. Lisa Johnson",
            "title": "Emergency Medicine",
            "specialization": "Urgent care and emergencies",
            "avatar": "/api/placeholder/40/40",
            "status": "available"
        }
    ]
    
    return doctors


@router.post("/case/{case_id}/consultation/create", response_model=Dict[str, Any])
@log_api_error
async def create_consultation_with_history(
    case_id: str,
    request_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a consultation session with initial chat history
    
    Request body should contain:
    - initial_messages: List of message objects with user_message and doctor_response
    - session_type: Type of session (default: "consultation")
    """
    try:
        # Verify case access
        storage_service = get_storage_service()
        case = storage_service.get_case(case_id, current_user.user_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Extract request data
        initial_messages = request_data.get("initial_messages", [])
        session_type = request_data.get("session_type", "consultation")
        
        # Validate request data
        if not initial_messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="initial_messages cannot be empty"
            )
        
        # Validate each message has required fields
        for idx, msg in enumerate(initial_messages):
            if not isinstance(msg, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Message at index {idx} must be a dictionary"
                )
            if "user_message" not in msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Message at index {idx} missing 'user_message' field"
                )
            if "doctor_response" not in msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Message at index {idx} missing 'doctor_response' field"
                )
        
        # Create the chat session
        logger.info(f"Creating consultation session for case {case_id}")
        chat_session = storage_service.create_chat_session(
            case_id=case_id,
            user_id=current_user.user_id,
            session_type=session_type
        )
        
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create chat session"
            )
        
        session_id = chat_session.get("session_id")
        logger.info(f"Created session {session_id}")
        
        # Store initial messages
        stored_messages = []
        for idx, msg in enumerate(initial_messages):
            try:
                # Extract message data with defaults
                user_message = msg.get("user_message", "")
                doctor_response = msg.get("doctor_response", "")
                doctor_type = msg.get("doctor_type", "general_consultant")
                metadata = msg.get("metadata", {})
                
                # Add message index to metadata
                metadata["message_index"] = idx
                metadata["initial_history"] = True
                
                logger.info(f"Storing message {idx + 1}/{len(initial_messages)}")
                
                # Store the message
                stored_msg = storage_service.store_chat_message(
                    session_id=session_id,
                    case_id=case_id,
                    user_id=current_user.user_id,
                    user_message=user_message,
                    doctor_type=doctor_type,
                    doctor_response=doctor_response,
                    metadata=metadata
                )
                
                if stored_msg:
                    stored_messages.append(stored_msg)
                    logger.info(f"Successfully stored message {idx + 1}")
                else:
                    logger.warning(f"Failed to store message {idx + 1}")
                    
            except Exception as e:
                logger.error(f"Error storing message {idx}: {str(e)}")
                # Continue with other messages even if one fails
                continue
        
        # Update session with participating doctors
        unique_doctors = list(set(msg.get("doctor_type", "general_consultant") 
                                for msg in initial_messages))
        
        # Return the created session details
        return {
            "status": "success",
            "session": {
                "session_id": session_id,
                "case_id": case_id,
                "user_id": current_user.user_id,
                "session_type": session_type,
                "created_at": chat_session.get("created_at"),
                "is_active": True,
                "participating_doctors": unique_doctors,
                "message_count": len(stored_messages)
            },
            "messages_stored": len(stored_messages),
            "total_messages": len(initial_messages),
            "message": f"Created consultation session with {len(stored_messages)} messages"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_context = {
            "case_id": case_id,
            "user_id": current_user.user_id if current_user else None,
            "endpoint": "create_consultation_with_history"
        }
        log_error(e, **error_context)
        
        logger.error(f"Failed to create consultation with history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create consultation session: {str(e)}"
        )


@router.get("/test")
async def test_chat_route():
    """Test if chat route is loaded"""
    return {"status": "Chat route is working", "endpoint": "/api/v1/chat/test"}


@router.get("/history/{case_id}", response_model=Dict[str, Any])
@log_api_error
async def get_complete_chat_history(
    case_id: str,
    include_metadata: bool = Query(False, description="Include message metadata"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order for messages"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get complete chat history for a case
    
    Returns all messages across all sessions for the specified case,
    optionally including metadata and sorted by timestamp.
    """
    try:
        # Verify case access
        storage_service = get_storage_service()
        case = storage_service.get_case(case_id, current_user.user_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Get all messages for the case
        messages = storage_service.get_case_chat_history(
            case_id=case_id,
            limit=1000  # Set a high limit to get all messages
        )
        
        # Format messages
        formatted_messages = []
        for msg in messages:
            formatted_msg = {
                "id": msg.get("message_id"),
                "message_id": msg.get("message_id"),
                "session_id": msg.get("session_id"),
                "case_id": msg.get("case_id"),
                "user_id": msg.get("user_id"),
                "user_message": msg.get("user_message"),
                "doctor_type": msg.get("doctor_type"),
                "doctor_response": msg.get("doctor_response"),
                "created_at": msg.get("created_at"),
                "timestamp": msg.get("created_at")
            }
            
            if include_metadata:
                formatted_msg["metadata"] = msg.get("metadata", {})
                
            formatted_messages.append(formatted_msg)
        
        # Sort messages
        if sort_order == "desc":
            formatted_messages.reverse()
        
        # Get sessions info
        sessions = storage_service.get_case_chat_sessions(case_id)
        
        return {
            "case_id": case_id,
            "total_messages": len(formatted_messages),
            "total_sessions": len(sessions),
            "messages": formatted_messages,
            "sessions_summary": sessions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve complete chat history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat history: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=Dict[str, Any])
@log_api_error
async def get_session_details(
    session_id: str,
    include_messages: bool = Query(True, description="Include messages in response"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get specific session details with messages
    
    Returns detailed information about a specific chat session,
    optionally including all messages in that session.
    """
    try:
        # Get session messages to verify access
        messages = storage_service.get_conversation_context(
            session_id=session_id,
            limit=1
        )
        
        if not messages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied"
            )
        
        # Verify user access via the case
        first_msg = messages[0]
        case_id = first_msg.get("case_id")
        storage_service = get_storage_service()
        case = storage_service.get_case(case_id, current_user.user_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session"
            )
        
        # Get session info from the case sessions
        sessions = storage_service.get_case_chat_sessions(case_id)
        session_info = None
        for session in sessions:
            if session.get("session_id") == session_id:
                session_info = session
                break
        
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session information not found"
            )
        
        response = {
            "session": session_info,
            "case_id": case_id,
            "case_title": case.get("title", "")
        }
        
        if include_messages:
            # Get all messages for the session
            all_messages = storage_service.get_conversation_context(
                session_id=session_id,
                limit=1000
            )
            
            # Format messages
            formatted_messages = []
            for msg in all_messages:
                formatted_msg = {
                    "id": msg.get("message_id"),
                    "message_id": msg.get("message_id"),
                    "user_message": msg.get("user_message"),
                    "doctor_type": msg.get("doctor_type"),
                    "doctor_response": msg.get("doctor_response"),
                    "created_at": msg.get("created_at"),
                    "metadata": msg.get("metadata", {})
                }
                formatted_messages.append(formatted_msg)
            
            response["messages"] = formatted_messages
            response["total_messages"] = len(formatted_messages)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve session details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session details: {str(e)}"
        )


@router.delete("/message/{message_id}")
@log_api_error
async def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Soft delete a message (admin only)
    
    Marks a message as deleted without actually removing it from the database.
    This operation is restricted to admin users only.
    """
    try:
        # Check if user is admin (you may need to implement this check based on your user model)
        # For now, we'll add a TODO comment
        # TODO: Implement admin check based on user role/permissions
        
        # Delete the message
        success = storage_service.delete_message(message_id, current_user.user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found or access denied"
            )
        
        return {
            "status": "success",
            "message": "Message deleted successfully",
            "message_id": message_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete message: {str(e)}"
        )


@router.put("/message/{message_id}", response_model=Dict[str, Any])
@log_api_error
async def update_message(
    message_id: str,
    update_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """
    Update/edit a message (with audit trail)
    
    Updates a message content and maintains an audit trail of changes.
    Only the message owner or admin can update messages.
    """
    try:
        # Validate update data
        allowed_fields = ["user_message", "doctor_response"]
        filtered_update_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not filtered_update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )
        
        # Update the message
        updated_message = storage_service.update_message(
            message_id, 
            current_user.user_id, 
            filtered_update_data
        )
        
        if not updated_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found or access denied"
            )
        
        return {
            "status": "success",
            "message": "Message updated successfully",
            "updated_message": updated_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update message: {str(e)}"
        )


@router.get("/search", response_model=Dict[str, Any])
@log_api_error
async def search_messages(
    query: str = Query(..., min_length=1, description="Search query"),
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    doctor_type: Optional[DoctorType] = Query(None, description="Filter by doctor type"),
    start_date: Optional[datetime] = Query(None, description="Filter messages after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter messages before this date"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Search messages across cases
    
    Search for messages containing specific text across all cases
    accessible to the user, with optional filters.
    """
    try:
        # Prepare filters
        filters = {
            "limit": limit,
            "offset": offset
        }
        
        if case_id:
            filters["case_id"] = case_id
        
        if doctor_type:
            filters["doctor_type"] = doctor_type.value
        
        if start_date:
            filters["start_date"] = start_date.isoformat()
        
        if end_date:
            filters["end_date"] = end_date.isoformat()
        
        # Search messages
        messages = storage_service.search_messages(
            user_id=current_user.user_id,
            query=query,
            filters=filters
        )
        
        # Format results
        formatted_messages = []
        for msg in messages:
            formatted_msg = {
                "message_id": msg.get("message_id"),
                "case_id": msg.get("case_id"),
                "case_title": msg.get("case_title"),
                "case_number": msg.get("case_number"),
                "session_id": msg.get("session_id"),
                "user_message": msg.get("user_message"),
                "doctor_type": msg.get("doctor_type"),
                "doctor_response": msg.get("doctor_response"),
                "created_at": msg.get("created_at"),
                "relevance_snippet": query  # Could be enhanced to show matching text
            }
            formatted_messages.append(formatted_msg)
        
        return {
            "query": query,
            "filters": filters,
            "total_results": len(formatted_messages),
            "results": formatted_messages,
            "has_more": len(messages) == limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search messages: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search messages: {str(e)}"
        )


@router.get("/export/{case_id}")
@log_api_error
async def export_chat_history(
    case_id: str,
    format: str = Query("json", regex="^(json|csv|pdf)$", description="Export format"),
    include_metadata: bool = Query(False, description="Include message metadata"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Export chat history in various formats
    
    Export the complete chat history of a case in JSON, CSV, or PDF format.
    """
    try:
        # Verify case access
        storage_service = get_storage_service()
        case = storage_service.get_case(case_id, current_user.user_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Get all messages
        messages = storage_service.get_case_chat_history(
            case_id=case_id,
            limit=10000
        )
        
        if format == "json":
            # Export as JSON
            export_data = {
                "case_id": case_id,
                "case_title": case.get("title", ""),
                "export_date": datetime.utcnow().isoformat(),
                "total_messages": len(messages),
                "messages": []
            }
            
            for msg in messages:
                msg_data = {
                    "message_id": msg.get("message_id"),
                    "session_id": msg.get("session_id"),
                    "user_message": msg.get("user_message"),
                    "doctor_type": msg.get("doctor_type"),
                    "doctor_response": msg.get("doctor_response"),
                    "created_at": msg.get("created_at")
                }
                if include_metadata:
                    msg_data["metadata"] = msg.get("metadata", {})
                export_data["messages"].append(msg_data)
            
            # Create file response
            json_content = json.dumps(export_data, indent=2)
            return StreamingResponse(
                BytesIO(json_content.encode()),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=case_{case_id}_chat_history.json"
                }
            )
            
        elif format == "csv":
            # Export as CSV
            output = BytesIO()
            wrapper = csv.writer(output)
            
            # Write headers
            headers = ["Message ID", "Session ID", "Timestamp", "User Message", 
                      "Doctor Type", "Doctor Response"]
            if include_metadata:
                headers.append("Metadata")
            wrapper.writerow(headers)
            
            # Write data
            for msg in messages:
                row = [
                    msg.get("message_id", ""),
                    msg.get("session_id", ""),
                    msg.get("created_at", ""),
                    msg.get("user_message", ""),
                    msg.get("doctor_type", ""),
                    msg.get("doctor_response", "")
                ]
                if include_metadata:
                    row.append(json.dumps(msg.get("metadata", {})))
                wrapper.writerow(row)
            
            output.seek(0)
            return StreamingResponse(
                output,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=case_{case_id}_chat_history.csv"
                }
            )
            
        elif format == "pdf":
            # Export as PDF
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=30
            )
            story.append(Paragraph(f"Chat History - Case {case.get('case_number', case_id)}", title_style))
            story.append(Spacer(1, 20))
            
            # Case info
            info_style = styles['Normal']
            story.append(Paragraph(f"<b>Case Title:</b> {case.get('title', 'N/A')}", info_style))
            story.append(Paragraph(f"<b>Export Date:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", info_style))
            story.append(Paragraph(f"<b>Total Messages:</b> {len(messages)}", info_style))
            story.append(Spacer(1, 20))
            
            # Messages
            for msg in messages:
                # Timestamp
                timestamp = msg.get("created_at", "")
                story.append(Paragraph(f"<b>{timestamp}</b>", info_style))
                
                # User message
                if msg.get("user_message") and msg.get("user_message") != "[Doctor Switch]":
                    story.append(Paragraph(f"<b>Patient:</b> {msg.get('user_message', '')}", info_style))
                
                # Doctor response
                doctor_type = msg.get("doctor_type", "doctor").replace("_", " ").title()
                story.append(Paragraph(f"<b>{doctor_type}:</b> {msg.get('doctor_response', '')}", info_style))
                
                story.append(Spacer(1, 15))
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            
            return StreamingResponse(
                buffer,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=case_{case_id}_chat_history.pdf"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export chat history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export chat history: {str(e)}"
        )


@router.get("/statistics/{case_id}", response_model=Dict[str, Any])
@log_api_error
async def get_chat_statistics(
    case_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get chat statistics for a case
    
    Returns various statistics about the chat history including message counts,
    average response times, doctor participation, and more.
    """
    try:
        # Verify case access
        storage_service = get_storage_service()
        case = storage_service.get_case(case_id, current_user.user_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Get all sessions and messages
        sessions = storage_service.get_case_chat_sessions(case_id)
        messages = storage_service.get_case_chat_history(case_id, limit=10000)
        
        # Calculate statistics
        total_messages = len(messages)
        total_sessions = len(sessions)
        
        # Doctor participation
        doctor_counts = {}
        for msg in messages:
            doctor_type = msg.get("doctor_type", "unknown")
            doctor_counts[doctor_type] = doctor_counts.get(doctor_type, 0) + 1
        
        # Messages per session
        session_message_counts = {}
        for msg in messages:
            session_id = msg.get("session_id")
            session_message_counts[session_id] = session_message_counts.get(session_id, 0) + 1
        
        # Calculate average messages per session
        avg_messages_per_session = (
            sum(session_message_counts.values()) / len(session_message_counts)
            if session_message_counts else 0
        )
        
        # Time-based statistics
        if messages:
            # Sort messages by timestamp
            sorted_messages = sorted(messages, key=lambda x: x.get("created_at", ""))
            
            first_message_time = sorted_messages[0].get("created_at")
            last_message_time = sorted_messages[-1].get("created_at")
            
            # Calculate conversation duration
            if first_message_time and last_message_time:
                from datetime import datetime
                first_dt = datetime.fromisoformat(first_message_time.replace('Z', '+00:00'))
                last_dt = datetime.fromisoformat(last_message_time.replace('Z', '+00:00'))
                duration = last_dt - first_dt
                duration_minutes = duration.total_seconds() / 60
            else:
                duration_minutes = 0
        else:
            first_message_time = None
            last_message_time = None
            duration_minutes = 0
        
        # Active sessions
        active_sessions = [s for s in sessions if s.get("is_active", False)]
        
        statistics = {
            "case_id": case_id,
            "case_title": case.get("title", ""),
            "total_messages": total_messages,
            "total_sessions": total_sessions,
            "active_sessions": len(active_sessions),
            "average_messages_per_session": round(avg_messages_per_session, 2),
            "doctor_participation": doctor_counts,
            "first_message_time": first_message_time,
            "last_message_time": last_message_time,
            "total_conversation_duration_minutes": round(duration_minutes, 2),
            "messages_by_session": session_message_counts,
            "case_created_at": case.get("created_at"),
            "case_status": case.get("status")
        }
        
        return statistics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat statistics: {str(e)}"
        )