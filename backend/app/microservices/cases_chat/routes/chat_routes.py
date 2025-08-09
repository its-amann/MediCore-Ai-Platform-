"""
Chat/Consultation Routes
Handles AI doctor consultations and chat interactions
"""
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from typing import List, Optional, Dict, Any
import logging
import time
from datetime import datetime

from ..models import (
    ChatRequest, ChatResponse, ChatMessage, HandoverRequest,
    CaseReportRequest, DoctorType, ChatSession
)
from ..dependencies import (
    get_current_user_id, get_storage_service, get_doctor_service,
    get_websocket_adapter, get_mcp_client
)
from ..utils.validators import validate_chat_request
from ..utils.error_handlers import handle_ai_service_error

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat", "consultation"]
)


@router.post("/consult", response_model=ChatResponse)
async def consult_doctor(
    request: ChatRequest,
    case_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    storage = Depends(get_storage_service),
    doctor_service = Depends(get_doctor_service),
    ws_adapter = Depends(get_websocket_adapter)
):
    """
    Consult with an AI doctor
    
    Args:
        request: Chat request with message and doctor type
        case_id: Case ID for the consultation
        background_tasks: FastAPI background tasks
        user_id: Current user ID
        storage: Storage service instance
        doctor_service: AI doctor service
        ws_adapter: WebSocket adapter for real-time updates
        
    Returns:
        Doctor's response
    """
    start_time = time.time()
    
    try:
        # Validate request
        validated_request = validate_chat_request(request)
        
        # Verify user owns this case
        case = await storage.get_case(case_id)
        if case.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this case"
            )
        
        # Create or get chat session
        session_id = validated_request.session_id
        if not session_id:
            # Create new session
            session = ChatSession(
                case_id=case_id,
                user_id=user_id,
                session_type="single_doctor",
                participating_doctors=[validated_request.doctor_type.value]
            )
            session_data = await storage.create_chat_session(session.dict())
            session_id = session_data["session_id"]
            
            # Notify about new session
            await ws_adapter.notify_chat_session_created(
                user_id, case_id, session_data
            )
        
        # Get chat history for context
        chat_history = []
        if validated_request.context_window > 0:
            chat_history = await storage.get_chat_history(
                session_id=session_id,
                limit=validated_request.context_window
            )
        
        # Notify that doctor is responding
        await ws_adapter.notify_doctor_response_streaming(
            user_id=user_id,
            case_id=case_id,
            doctor_type=validated_request.doctor_type,
            is_start=True
        )
        
        # Get doctor response
        try:
            response = await doctor_service.get_doctor_response(
                doctor_type=validated_request.doctor_type,
                user_message=validated_request.message,
                case_context=case,
                chat_history=chat_history,
                image_data=validated_request.image_data,
                audio_data=validated_request.audio_data
            )
        except Exception as e:
            # Notify about response failure
            await ws_adapter.notify_doctor_response_streaming(
                user_id=user_id,
                case_id=case_id,
                doctor_type=validated_request.doctor_type,
                is_end=True,
                full_response="I apologize, but I'm having trouble processing your request. Please try again."
            )
            raise handle_ai_service_error(e)
        
        # Create chat message
        message = ChatMessage(
            session_id=session_id,
            case_id=case_id,
            user_id=user_id,
            user_message=validated_request.message,
            doctor_type=validated_request.doctor_type.value,
            doctor_response=response["response"],
            metadata=response.get("metadata", {})
        )
        
        # Save message to storage
        await storage.save_chat_message(message.dict())
        
        # Update session activity
        await storage.update_chat_session(session_id, {
            "last_activity": datetime.utcnow(),
            "message_count": await storage.get_session_message_count(session_id)
        })
        
        # Notify completion
        await ws_adapter.notify_doctor_response_streaming(
            user_id=user_id,
            case_id=case_id,
            doctor_type=validated_request.doctor_type,
            is_end=True,
            full_response=response["response"]
        )
        
        # Broadcast to case room
        background_tasks.add_task(
            ws_adapter.broadcast_new_message,
            case_id,
            message.dict()
        )
        
        processing_time = time.time() - start_time
        
        return ChatResponse(
            session_id=session_id,
            message_id=message.message_id,
            doctor_response=response["response"],
            doctor_type=validated_request.doctor_type.value,
            confidence_score=response.get("confidence_score", 0.8),
            processing_time=processing_time,
            context_used=len(chat_history),
            timestamp=message.created_at,
            metadata=response.get("metadata", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in doctor consultation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing consultation request"
        )


@router.post("/handover", response_model=Dict[str, Any])
async def handover_to_specialist(
    request: HandoverRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    storage = Depends(get_storage_service),
    doctor_service = Depends(get_doctor_service),
    ws_adapter = Depends(get_websocket_adapter)
):
    """
    Handover case from one doctor to another specialist
    
    Args:
        request: Handover request details
        background_tasks: FastAPI background tasks
        user_id: Current user ID
        storage: Storage service instance
        doctor_service: AI doctor service
        ws_adapter: WebSocket adapter
        
    Returns:
        Handover summary and new doctor's initial assessment
    """
    try:
        # Get session and verify ownership
        session = await storage.get_chat_session(request.session_id)
        if session.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session"
            )
        
        case_id = session.get("case_id")
        case = await storage.get_case(case_id)
        
        # Get handover summary from current doctor
        handover_summary = await doctor_service.generate_handover_summary(
            from_doctor=request.from_doctor,
            to_doctor=request.to_doctor,
            case_context=case,
            chat_history=await storage.get_chat_history(
                session_id=request.session_id
            ) if request.include_full_history else [],
            custom_message=request.handover_message
        )
        
        # Update session with new doctor
        await storage.update_chat_session(request.session_id, {
            "participating_doctors": list(set(
                session.get("participating_doctors", []) + [request.to_doctor.value]
            )),
            "last_activity": datetime.utcnow()
        })
        
        # Notify about doctor switch
        await ws_adapter.notify_doctor_switch(
            case_id=case_id,
            from_doctor=request.from_doctor.value,
            to_doctor=request.to_doctor,
            user_id=user_id,
            handover_summary=handover_summary
        )
        
        # Get initial assessment from new doctor
        initial_assessment = await doctor_service.get_doctor_response(
            doctor_type=request.to_doctor,
            user_message=f"I've been handed over this case. {handover_summary}",
            case_context=case,
            chat_history=[],
            is_handover=True
        )
        
        # Save handover message
        handover_message = ChatMessage(
            session_id=request.session_id,
            case_id=case_id,
            user_id=user_id,
            user_message="[Handover]",
            doctor_type=request.to_doctor.value,
            doctor_response=initial_assessment["response"],
            metadata={
                "handover": True,
                "from_doctor": request.from_doctor.value,
                "handover_summary": handover_summary
            }
        )
        
        await storage.save_chat_message(handover_message.dict())
        
        # Broadcast handover completion
        background_tasks.add_task(
            ws_adapter.broadcast_new_message,
            case_id,
            handover_message.dict()
        )
        
        return {
            "success": True,
            "handover_summary": handover_summary,
            "new_doctor_assessment": initial_assessment["response"],
            "session_id": request.session_id,
            "timestamp": datetime.utcnow()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in doctor handover: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing handover request"
        )


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessage])
async def get_session_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
    storage = Depends(get_storage_service)
):
    """
    Get messages from a chat session
    
    Args:
        session_id: Chat session ID
        limit: Maximum messages to return
        offset: Number of messages to skip
        user_id: Current user ID
        storage: Storage service instance
        
    Returns:
        List of chat messages
    """
    try:
        # Verify user owns this session
        session = await storage.get_chat_session(session_id)
        if session.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session"
            )
        
        messages = await storage.get_chat_history(
            session_id=session_id,
            limit=limit,
            offset=offset
        )
        
        return [ChatMessage(**msg) for msg in messages]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session messages: {e}")
        raise handle_storage_error(e)


@router.post("/generate-report", response_model=Dict[str, Any])
async def generate_case_report(
    request: CaseReportRequest,
    user_id: str = Depends(get_current_user_id),
    storage = Depends(get_storage_service),
    doctor_service = Depends(get_doctor_service),
    ws_adapter = Depends(get_websocket_adapter)
):
    """
    Generate a comprehensive case report
    
    Args:
        request: Report generation request
        user_id: Current user ID
        storage: Storage service instance
        doctor_service: AI doctor service
        ws_adapter: WebSocket adapter
        
    Returns:
        Generated report data
    """
    try:
        # Verify access to case and session
        case = await storage.get_case(request.case_id)
        if case.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this case"
            )
        
        session = await storage.get_chat_session(request.session_id)
        if session.get("case_id") != request.case_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session does not belong to this case"
            )
        
        # Get all chat history
        chat_history = await storage.get_chat_history(
            session_id=request.session_id,
            limit=1000  # Get all messages
        )
        
        # Generate report
        report = await doctor_service.generate_case_report(
            case_data=case,
            chat_history=chat_history,
            include_sections=request.include_sections,
            format=request.format
        )
        
        # Save report to storage
        report_data = {
            "case_id": request.case_id,
            "session_id": request.session_id,
            "user_id": user_id,
            "report_content": report["content"],
            "format": request.format,
            "sections": request.include_sections,
            "generated_at": datetime.utcnow(),
            "metadata": report.get("metadata", {})
        }
        
        report_id = await storage.save_case_report(report_data)
        report_data["report_id"] = report_id
        
        # Notify about report generation
        await ws_adapter.notify_report_generated(
            user_id=user_id,
            case_id=request.case_id,
            report_data={
                "report_id": report_id,
                "format": request.format,
                "generated_at": report_data["generated_at"]
            }
        )
        
        return report_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating case report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating case report"
        )


@router.post("/analyze-with-mcp/{case_id}", response_model=Dict[str, Any])
async def analyze_case_with_mcp(
    case_id: str,
    analysis_type: str = "comprehensive",
    user_id: str = Depends(get_current_user_id),
    storage = Depends(get_storage_service),
    mcp_client = Depends(get_mcp_client),
    ws_adapter = Depends(get_websocket_adapter)
):
    """
    Analyze case using MCP server for medical history context
    
    Args:
        case_id: Case ID to analyze
        analysis_type: Type of analysis to perform
        user_id: Current user ID
        storage: Storage service instance
        mcp_client: MCP client instance
        ws_adapter: WebSocket adapter
        
    Returns:
        Analysis results from MCP
    """
    try:
        # Verify user owns this case
        case = await storage.get_case(case_id)
        if case.get("user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this case"
            )
        
        # Notify analysis started
        await ws_adapter.notify_mcp_analysis(
            user_id=user_id,
            case_id=case_id,
            doctor_type=DoctorType.GENERAL,
            status="started",
            data={"analysis_type": analysis_type}
        )
        
        try:
            # Perform MCP analysis
            if not mcp_client or not mcp_client.is_available():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="MCP service is not available"
                )
            
            analysis_result = await mcp_client.analyze_case(
                case_data=case,
                analysis_type=analysis_type
            )
            
            # Store analysis result
            await storage.save_case_analysis(
                case_id=case_id,
                analysis_type=analysis_type,
                analysis_data=analysis_result
            )
            
            # Notify analysis completed
            await ws_adapter.notify_mcp_analysis(
                user_id=user_id,
                case_id=case_id,
                doctor_type=DoctorType.GENERAL,
                status="completed",
                data={"summary": analysis_result.get("summary", "")}
            )
            
            return {
                "success": True,
                "case_id": case_id,
                "analysis_type": analysis_type,
                "results": analysis_result,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            # Notify analysis failed
            await ws_adapter.notify_mcp_analysis(
                user_id=user_id,
                case_id=case_id,
                doctor_type=DoctorType.GENERAL,
                status="failed",
                data={"error": str(e)}
            )
            raise
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing case with MCP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error performing MCP analysis"
        )