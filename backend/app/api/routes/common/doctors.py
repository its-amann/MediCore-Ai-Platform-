"""
AI Doctor consultation routes for the Unified Medical AI Platform
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from starlette.requests import Request
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json
import asyncio
import logging

from app.core.database.neo4j_client import Neo4jClient
from app.core.database.models import (
    User, Analysis, AnalysisCreate, AnalysisType, ChatHistory, ChatType,
    Doctor, DoctorSpecialty, DoctorConsultationRequest, DoctorConsultationResponse
)
from app.api.routes.auth import get_current_active_user
# Session manager removed - now integrated into cases microservice

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependency to get database client
async def get_database():
    """Get database client dependency"""
    from app.main import get_neo4j_client
    return get_neo4j_client()

@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify routing"""
    return {"message": "Doctors endpoint is working"}

@router.get("/test-ai")
async def test_ai_service():
    """Test if AI service is configured"""
    return {
        "groq_configured": True,
        "primary_client": "cases_microservice",
        "message": "AI service now handled by cases microservice"
    }

@router.post("/test-chat-history")
async def test_chat_history_creation(
    current_user: User = Depends(get_current_active_user),
    db: Neo4jClient = Depends(get_database)
):
    """Test chat history creation directly"""
    try:
        # Create simple chat history data with only primitives
        chat_id = str(uuid.uuid4())
        chat_history_data = {
            "chat_id": chat_id,
            "chat_type": "doctor_consultation",
            "doctor_specialty": "general_consultant",
            "user_message": "Test user message",
            "doctor_response": "Test doctor response",
            "conversation_data": json.dumps({
                "user_message": "Test user message",
                "doctor_response": "Test doctor response",
                "doctor_specialty": "general_consultant"
            }),
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.utcnow().isoformat(),
            "metadata": json.dumps({
                "test": "true",
                "consultation_id": str(uuid.uuid4())
            })
        }
        
        # Create chat history in database
        created_chat = await db.create_chat_history(chat_history_data)
        
        return {
            "success": True,
            "chat_id": chat_id,
            "message": "Chat history created successfully",
            "created_chat": created_chat
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to create chat history"
        }

@router.post("/test-neo4j-serialization")
async def test_neo4j_serialization_issue(
    db: Neo4jClient = Depends(get_database)
):
    """Test Neo4j serialization specifically for chat history"""
    try:
        # Create minimal chat history data that matches what we send in consultation
        chat_history_data = {
            "chat_id": str(uuid.uuid4()),
            "chat_type": "doctor_consultation",
            "doctor_specialty": "general_consultant",
            "user_message": "Test user message for serialization",
            "doctor_response": "Test doctor response for serialization",
            "conversation_data": json.dumps({
                "user_message": "Test user message for serialization",
                "doctor_response": "Test doctor response for serialization",
                "doctor_specialty": "general_consultant",
                "consultation_id": str(uuid.uuid4()),
                "has_image": False,
                "has_audio": False
            }),
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.utcnow().isoformat(),
            "metadata": json.dumps({
                "consultation_id": str(uuid.uuid4()),
                "doctor_id": "test_doctor_id",
                "confidence_score": 0.8
            })
        }
        
        # Log data types before Neo4j
        logger.info("=== NEO4J SERIALIZATION TEST ===")
        logger.info("Raw chat history data:")
        for key, value in chat_history_data.items():
            logger.info(f"  {key}: {type(value)} = {repr(value)}")
        
        # Test data preparation
        prepared_data = db._prepare_data_for_neo4j(chat_history_data)
        logger.info("Prepared data:")
        for key, value in prepared_data.items():
            logger.info(f"  {key}: {type(value)} = {repr(value)}")
        
        # Try to create chat history
        created_chat = await db.create_chat_history(chat_history_data)
        
        return {
            "success": True,
            "message": "Chat history created successfully",
            "chat_id": chat_history_data["chat_id"],
            "created_chat": created_chat
        }
        
    except Exception as e:
        logger.error(f"=== NEO4J SERIALIZATION TEST FAILED ===")
        logger.error(f"Error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

@router.post("/test-consult")
@router.post("/test-consult-auth")
async def test_consult_no_auth(
    consultation_request: DoctorConsultationRequest,
    db: Neo4jClient = Depends(get_database)
):
    """Test consultation endpoint without authentication"""
    
    # Create a simple test response
    consultation_id = str(uuid.uuid4())
    
    # Prepare response with test AI message
    response_message = f"""Thank you for consulting with me about your case. 

Based on your message: "{consultation_request.message}"

As a {consultation_request.specialty or 'General Consultant'}, I understand your concerns. Here's my initial assessment:

1. Your symptoms require careful evaluation
2. Please monitor your condition closely
3. If symptoms worsen, seek immediate medical attention

This is a test response from the AI medical consultation system."""
    
    return {
        "consultation_id": consultation_id,
        "doctor_specialty": consultation_request.specialty or "general_consultant",
        "response": response_message,
        "analysis": None,
        "recommendations": [
            "Monitor your symptoms daily",
            "Stay well hydrated",
            "Get adequate rest",
            "Follow up if symptoms persist or worsen"
        ],
        "follow_up_questions": [
            "How long have you been experiencing these symptoms?",
            "Are you currently taking any medications?",
            "Do you have any known allergies?",
            "Have you had similar symptoms before?"
        ],
        "confidence_score": 0.85,
        "processing_time": 0.5,
        "session_id": consultation_id
    }

@router.get("/", response_model=List[Doctor])
async def get_available_doctors(
    current_user: User = Depends(get_current_active_user),
    db: Neo4jClient = Depends(get_database),
    specialty: Optional[DoctorSpecialty] = Query(None, description="Filter by specialty"),
    is_active: bool = Query(True, description="Filter by active status")
):
    """Get all available AI doctors"""
    try:
        # Build query with filters
        base_query = "MATCH (d:Doctor)"
        conditions = ["d.is_active = $is_active"]
        params = {"is_active": is_active}
        
        if specialty:
            conditions.append("d.specialty = $specialty")
            params["specialty"] = specialty.value
        
        query = base_query + " WHERE " + " AND ".join(conditions) + """
        RETURN d
        ORDER BY d.specialty, d.name
        """
        
        result = await db.run_query(query, params)
        doctors = [Doctor(**record["d"]) for record in result]
        
        return doctors
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve doctors: {str(e)}"
        )

@router.get("/{doctor_id}", response_model=Doctor)
async def get_doctor(
    doctor_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Neo4jClient = Depends(get_database)
):
    """Get specific doctor information"""
    try:
        query = """
        MATCH (d:Doctor {doctor_id: $doctor_id})
        RETURN d
        """
        
        result = await db.run_query(query, {"doctor_id": doctor_id})
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found"
            )
        
        return Doctor(**result[0]["d"])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve doctor: {str(e)}"
        )

@router.post("/consult/cardiologist", response_model=DoctorConsultationResponse)
async def consult_cardiologist(
    consultation_request: DoctorConsultationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Neo4jClient = Depends(get_database)
):
    """Consult with AI Cardiologist"""
    return await _process_consultation(
        consultation_request, 
        DoctorSpecialty.CARDIOLOGIST, 
        current_user, 
        db
    )

@router.post("/consult/bp-specialist", response_model=DoctorConsultationResponse)
async def consult_bp_specialist(
    consultation_request: DoctorConsultationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Neo4jClient = Depends(get_database)
):
    """Consult with AI Blood Pressure Specialist"""
    return await _process_consultation(
        consultation_request, 
        DoctorSpecialty.BP_SPECIALIST, 
        current_user, 
        db
    )

@router.post("/consult/general-consultant", response_model=DoctorConsultationResponse)
async def consult_general_consultant(
    consultation_request: DoctorConsultationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Neo4jClient = Depends(get_database)
):
    """Consult with AI General Consultant"""
    return await _process_consultation(
        consultation_request, 
        DoctorSpecialty.GENERAL_CONSULTANT, 
        current_user, 
        db
    )

@router.post("/consult")
async def consult_doctor(
    consultation_request: DoctorConsultationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Neo4jClient = Depends(get_database)
):
    """General consultation endpoint that routes to appropriate specialist"""
    
    try:
        logger.info(f"Parsed consultation request: {consultation_request}")
        
        # Map specialty string to enum
        specialty_map = {
            "cardiologist": DoctorSpecialty.CARDIOLOGIST,
            "bp_specialist": DoctorSpecialty.BP_SPECIALIST,
            "general_consultant": DoctorSpecialty.GENERAL_CONSULTANT
        }
        
        # Get specialty from the request model
        specialty_value = getattr(consultation_request, 'specialty', 'general_consultant')
        logger.info(f"Specialty value: {specialty_value}")
        
        specialty = specialty_map.get(
            specialty_value.lower() if specialty_value else "general_consultant",
            DoctorSpecialty.GENERAL_CONSULTANT
        )
        
        # Process the consultation using the appropriate doctor service
        consultation_response = await _process_consultation(
            consultation_request,
            specialty,
            current_user,
            db
        )
        
        return consultation_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Consultation error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Consultation failed: {str(e)}"
        )

async def _process_consultation(
    consultation_request: DoctorConsultationRequest,
    doctor_specialty: DoctorSpecialty,
    current_user: User,
    db: Neo4jClient
) -> DoctorConsultationResponse:
    """Process consultation with specified doctor specialty"""
    try:
        start_time = datetime.utcnow()
        logger.info(f"Starting consultation for user {current_user.user_id}, case {consultation_request.case_id}")
        
        # Verify case exists and user owns it
        case_query = """
        MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case {case_id: $case_id})
        RETURN c
        """
        
        case_result = await db.run_query(case_query, {
            "user_id": current_user.user_id,
            "case_id": consultation_request.case_id
        })
        
        logger.info(f"Case query result: {case_result}")
        
        if not case_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        case_data = case_result[0]["c"]
        logger.info(f"Case data retrieved: {case_data.get('case_id')}")
        
        # Get doctor information
        doctor_query = """
        MATCH (d:Doctor {specialty: $specialty, is_active: true})
        RETURN d
        LIMIT 1
        """
        
        doctor_result = await db.run_query(doctor_query, {
            "specialty": doctor_specialty.value
        })
        
        if not doctor_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active {doctor_specialty.value} found"
            )
        
        doctor_data = doctor_result[0]["d"]
        
        # Process consultation based on doctor specialty
        # Call the actual AI consultation function
        consultation_response = await _generate_consultation_response(
            consultation_request,
            doctor_specialty,
            case_data,
            doctor_data,
            current_user,
            db
        )
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Create analysis record if significant findings
        analysis = None
        # Skip analysis creation for now to get consultation working
        if False:  # Disable analysis creation temporarily
            analysis_data = AnalysisCreate(
                case_id=consultation_request.case_id,
                analysis_type=_determine_analysis_type(consultation_request),
                content={
                    "doctor_id": doctor_data["doctor_id"],
                    "analysis_result": consultation_response["analysis_result"],
                    "findings": consultation_response.get("findings", []),
                    "recommendations": consultation_response.get("recommendations", []),
                    "input_data": {
                        "message": consultation_request.get_message(),
                        "has_image": bool(consultation_request.image_data) if consultation_request.image_data else False,
                        "has_audio": bool(consultation_request.audio_data) if consultation_request.audio_data else False,
                        "additional_context": consultation_request.additional_context or ""
                    },
                    "doctor_name": doctor_data.get("name", "AI Doctor"),
                    "doctor_specialty": doctor_data.get("specialty", "unknown"),
                    "confidence_score": consultation_response.get("confidence_score", 0.8),
                    "processing_time": (datetime.utcnow() - start_time).total_seconds(),
                    "model_used": consultation_response.get("model_used", "gemini-2.0-flash-exp")
                }
            )
            
            # Create analysis in database
            analysis_dict = analysis_data.dict()
            
            # Convert content to JSON string for Neo4j compatibility
            if "content" in analysis_dict and isinstance(analysis_dict["content"], dict):
                analysis_dict["content"] = json.dumps(analysis_dict["content"])
            
            # Add additional fields required for database
            analysis_dict.update({
                "analysis_id": str(uuid.uuid4()),
                "user_id": current_user.user_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "result": json.dumps({
                    "status": "completed",
                    "confidence_score": consultation_response.get("confidence_score", 0.8),
                    "processing_time": processing_time,
                    "model_used": f"AI_{doctor_specialty.value}",
                    "model_version": doctor_data.get("version", "1.0.0"),
                    "is_reviewed": False,
                    "metadata": {
                        "doctor_specialty": doctor_specialty.value,
                        "consultation_id": consultation_response["consultation_id"]
                    }
                })
            })
            
            # Create analysis
            create_analysis_query = """
            CREATE (a:Analysis)
            SET a += $props
            RETURN a
            """
            
            analysis_result = await db.run_write_query(create_analysis_query, {
                "props": analysis_dict
            })
            
            if analysis_result:
                # Link analysis to case
                link_query = """
                MATCH (c:Case {case_id: $case_id}), (a:Analysis {analysis_id: $analysis_id})
                CREATE (c)-[:HAS_ANALYSIS]->(a)
                """
                
                await db.run_write_query(link_query, {
                    "case_id": consultation_request.case_id,
                    "analysis_id": analysis_dict["analysis_id"]
                })
                
                analysis = Analysis(**analysis_result[0]["a"])
        
        # Create or use existing chat session using the cases chat storage
        from app.microservices.cases_chat.services.neo4j_storage.unified_cases_chat_storage import UnifiedCasesChatStorage
        from app.api.dependencies.database import get_sync_driver
        
        chat_storage = UnifiedCasesChatStorage(get_sync_driver())
        
        # Use the session_id from the consultation response (already created in _generate_consultation_response)
        session_id = consultation_response.get("session_id")
        
        if not session_id:
            # This shouldn't happen since session is created in _generate_consultation_response
            logger.error("No session_id found in consultation response!")
            session_id = str(uuid.uuid4())
            logger.info(f"Generated fallback session ID: {session_id}")
        
        # Store the consultation as a chat message in the new system
        try:
            stored_message = chat_storage.store_chat_message(
                session_id=session_id,
                case_id=consultation_request.case_id,
                user_id=current_user.user_id,
                user_message=consultation_request.get_message(),
                doctor_type=doctor_specialty.value,
                doctor_response=consultation_response["response"],
                metadata={
                    "consultation_id": consultation_response["consultation_id"],
                    "doctor_id": doctor_data["doctor_id"],
                    "confidence_score": consultation_response.get("confidence_score", 0.8),
                    "has_image": bool(consultation_request.image_data),
                    "has_audio": bool(consultation_request.audio_data)
                }
            )
            logger.info(f"Stored consultation message: {stored_message.get('message_id')}")
        except Exception as e:
            logger.error(f"Failed to store consultation message: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Don't fail the consultation if message storage fails
            pass
        
        # Also create the old ChatHistory for backward compatibility
        chat_history_data = {
            "chat_id": str(uuid.uuid4()),
            "chat_type": ChatType.DOCTOR_CONSULTATION.value,
            "doctor_specialty": doctor_specialty.value,
            "user_message": consultation_request.get_message(),
            "doctor_response": consultation_response["response"],
            "conversation_data": json.dumps({
                "user_message": consultation_request.get_message(),
                "doctor_response": consultation_response["response"],
                "doctor_specialty": doctor_specialty.value,
                "consultation_id": consultation_response["consultation_id"],
                "has_image": bool(consultation_request.image_data),
                "has_audio": bool(consultation_request.audio_data)
            }),
            "session_id": session_id,  # Use the same session_id
            "created_at": datetime.utcnow().isoformat(),
            "metadata": json.dumps({
                "consultation_id": consultation_response["consultation_id"],
                "doctor_id": doctor_data["doctor_id"],
                "confidence_score": consultation_response.get("confidence_score", 0.8)
            })
        }
        
        # Create chat history for backward compatibility
        try:
            created_chat = await db.create_chat_history(chat_history_data)
            if created_chat:
                # Link chat history to case
                link_chat_query = """
                MATCH (c:Case {case_id: $case_id}), (ch:ChatHistory {chat_id: $chat_id})
                CREATE (c)-[:HAS_CHAT_HISTORY]->(ch)
                """
                
                await db.run_write_query(link_chat_query, {
                    "case_id": consultation_request.case_id,
                    "chat_id": chat_history_data["chat_id"]
                })
                
                # Link chat history to user
                link_user_query = """
                MATCH (u:User {user_id: $user_id}), (ch:ChatHistory {chat_id: $chat_id})
                CREATE (u)-[:HAS_CHAT_HISTORY]->(ch)
                """
                
                await db.run_write_query(link_user_query, {
                    "user_id": current_user.user_id,
                    "chat_id": chat_history_data["chat_id"]
                })
        except Exception as e:
            logger.error(f"Failed to create backward-compatible chat history: {e}")
            # Don't fail the consultation if backward compatibility fails
            pass
        
        # Update doctor consultation count
        update_doctor_query = """
        MATCH (d:Doctor {doctor_id: $doctor_id})
        SET d.consultation_count = COALESCE(d.consultation_count, 0) + 1,
            d.updated_at = $updated_at
        """
        
        await db.run_write_query(update_doctor_query, {
            "doctor_id": doctor_data["doctor_id"],
            "updated_at": datetime.utcnow().isoformat()
        })
        
        # Create and return consultation response
        return DoctorConsultationResponse(
            consultation_id=consultation_response["consultation_id"],
            doctor_specialty=doctor_specialty,
            response=consultation_response["response"],
            analysis=analysis,
            recommendations=consultation_response.get("recommendations", []),
            follow_up_questions=consultation_response.get("follow_up_questions", []),
            confidence_score=consultation_response.get("confidence_score", 0.8),
            processing_time=processing_time,
            session_id=session_id  # Use the session_id we created/used
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Consultation failed: {str(e)}"
        )

async def _generate_consultation_response(
    consultation_request: DoctorConsultationRequest,
    doctor_specialty: DoctorSpecialty,
    case_data: Dict[str, Any],
    doctor_data: Dict[str, Any],
    current_user: User,
    db: Neo4jClient
) -> Dict[str, Any]:
    """Generate consultation response using AI service with session-based chat"""
    
    consultation_id = str(uuid.uuid4())
    
    # Create or get session
    session_id = consultation_request.session_id
    if not session_id:
        # Generate new session ID
        session_id = str(uuid.uuid4())
        logger.info(f"Generated new session ID: {session_id}")
        
        # CREATE THE CHAT SESSION IN NEO4J - THIS IS THE FIX!
        try:
            from app.microservices.cases_chat.services.neo4j_storage.unified_cases_chat_storage import UnifiedCasesChatStorage
            from app.api.dependencies.database import get_sync_driver
            
            chat_storage = UnifiedCasesChatStorage(get_sync_driver())
            
            # Create the chat session with the generated session_id
            chat_session = chat_storage.create_chat_session(
                case_id=case_data.get("case_id"),
                user_id=current_user.user_id,
                session_type="doctor_consultation",
                session_id=session_id  # Pass the session_id we generated
            )
            logger.info(f"Created chat session in Neo4j: {session_id}")
        except Exception as e:
            logger.error(f"Failed to create chat session: {e}")
            # Continue anyway - don't break the consultation
    
    # Session management now handled by cases microservice
    
    try:
        logger.info(f"=== STARTING AI CONSULTATION ===")
        logger.info(f"Doctor specialty: {doctor_specialty}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"User message: {consultation_request.get_message()}")
        
        # Use proxy service for compatibility
        try:
            from app.core.ai.doctor_proxy import DoctorProxyService
            ai_service = DoctorProxyService()
            logger.info(f"Using doctor proxy service. Primary client: {ai_service.primary_client}")
        except Exception as e:
            logger.error(f"Failed to initialize DoctorProxyService: {e}")
            raise
        
        # ALWAYS provide comprehensive medical history - let AI use full context intelligently
        
        # Initialize chat storage
        if 'chat_storage' not in locals():
            from app.microservices.cases_chat.services.neo4j_storage.unified_cases_chat_storage import UnifiedCasesChatStorage
            from app.api.dependencies.database import get_sync_driver
            
            chat_storage = UnifiedCasesChatStorage(get_sync_driver())
        
        # Always load comprehensive history - let AI use full context intelligently
        user_message = consultation_request.get_message()
        is_cross_case_request = True  # Always use comprehensive history
        
        # Debug logging
        logger.info(f"📝 Message: '{user_message[:100]}...' | Loading comprehensive history for all messages")
        
        chat_history = []
        formatted_history = ""
        
        try:
            # ALWAYS LOAD COMPREHENSIVE HISTORY: Get ALL medical history across ALL cases
            logger.info(f"📝 Loading comprehensive medical history for user {current_user.user_id}")
            
            comprehensive_history = chat_storage.get_user_comprehensive_medical_history(
                user_id=current_user.user_id,
                limit=100,  # Increased limit for full context
                include_cases=True,
                include_chat=True
            )
            
            logger.info(f"✅ Retrieved comprehensive history: {comprehensive_history['total_cases']} cases, {comprehensive_history['total_messages']} messages")
            
            # Format comprehensive medical history for AI context
            formatted_sections = []
            
            # Add case summary (all cases)
            if comprehensive_history['summary']['case_timeline']:
                formatted_sections.append("**MEDICAL CASE TIMELINE:**")
                for case in comprehensive_history['summary']['case_timeline']:
                    formatted_sections.append(f"- Case: {case['title']} | Chief Complaint: {case['chief_complaint']} | Symptoms: {', '.join(case.get('symptoms', []))}")
            
            # Add common symptoms (all patterns)
            if comprehensive_history['summary']['most_common_symptoms']:
                formatted_sections.append("\n**RECURRING SYMPTOMS PATTERN:**")
                for symptom_info in comprehensive_history['summary']['most_common_symptoms']:
                    formatted_sections.append(f"- {symptom_info['symptom']}: occurred {symptom_info['frequency']} times")
            
            # Add ALL conversations from across ALL cases
            if comprehensive_history['messages']:
                formatted_sections.append("\n**COMPLETE CONSULTATION HISTORY (All Cases):**")
                for msg in comprehensive_history['messages']:
                    role = "user" if msg.get("sender_type") == "user" else "doctor"
                    content = msg.get("content", "")
                    case_title = msg.get("case_title", "Unknown Case")
                    if content:
                        formatted_sections.append(f"[{case_title}] {role}: {content}")
            
            formatted_history = "\n".join(formatted_sections)
            chat_history = comprehensive_history['messages']
            
            logger.info(f"✅ Formatted comprehensive medical history: {len(formatted_history)} characters, {len(chat_history)} total messages")
                
        except Exception as e:
            logger.error(f"Failed to load comprehensive medical history: {e}")
            # Fallback to session-based as last resort
            try:
                logger.info(f"🔄 Falling back to session-based history for session {session_id}")
                chat_history = chat_storage.get_conversation_context(session_id, limit=20)
                
                if chat_history:
                    formatted_messages = []
                    for msg in reversed(chat_history):
                        role = "user" if msg.get("sender_type") == "user" else "assistant"
                        content = msg.get("content", "")
                        if content:
                            formatted_messages.append(f"{role}: {content}")
                    formatted_history = "\n".join(formatted_messages)
                    logger.info(f"Session fallback successful: {len(chat_history)} messages")
                else:
                    logger.info("No session history available either")
                    chat_history = []
                    formatted_history = ""
            except Exception as e2:
                logger.error(f"Session fallback also failed: {e2}")
                chat_history = []
                formatted_history = ""
        
        # Build enhanced context with session history
        enhanced_context = {
            "session_id": session_id,
            "message_count": len(chat_history),
            "conversation_history": formatted_history,
            "current_session": True
        }
        
        # Session context now handled by cases microservice
        
        # Fetch medical context from MCP service
        medical_context = None
        try:
            logger.info(f"Fetching medical context for case {case_data.get('case_id')}")
            from app.microservices.cases_chat.mcp_server.medical_history_service import get_medical_history_service
            
            service = get_medical_history_service()
            
            # Get similar cases for context
            similar_cases = await service.find_similar_cases(
                case_id=case_data.get("case_id"),
                user_id=current_user.user_id,
                similarity_threshold=0.5,
                limit=3
            )
            
            # Get patient timeline (last 30 days)
            from datetime import datetime, timedelta
            date_to = datetime.utcnow().isoformat()
            date_from = (datetime.utcnow() - timedelta(days=30)).isoformat()
            
            timeline = await service.get_patient_timeline(
                user_id=current_user.user_id,
                date_from=date_from,
                date_to=date_to
            )
            
            # Get symptom patterns
            patterns = await service.analyze_patterns(
                user_id=current_user.user_id,
                pattern_type="symptoms"
            )
            
            medical_context = {
                "similar_cases": similar_cases,
                "patient_timeline": timeline,
                "symptom_patterns": patterns,
                "case_count": len(timeline)
            }
            
            logger.info(f"Found {len(similar_cases)} similar cases and {len(timeline)} timeline events")
            
        except Exception as e:
            logger.error(f"Failed to fetch medical context: {str(e)}")
            # Continue without medical context
            medical_context = None
        
        # Prepare patient context with MCP data
        patient_context = {
            "case_id": case_data.get("case_id"),
            "user_id": current_user.user_id,  # Add user_id for MCP WebSocket notifications
            "chief_complaint": case_data.get("chief_complaint"),
            "medical_history": case_data.get("medical_history", []),
            "current_medications": case_data.get("current_medications", []),
            "allergies": case_data.get("allergies", []),
            "vital_signs": case_data.get("vital_signs", {}),
            "conversation_history": enhanced_context,
            "medical_context": medical_context  # Add the fetched medical context
        }
        
        # Enhanced system prompt based on context type
        if is_cross_case_request:
            system_prompt = f"""You are a {doctor_specialty.value.replace('_', ' ')} providing comprehensive medical analysis. 
You have access to the patient's COMPLETE medical history across ALL their previous cases. 
Focus on identifying patterns, recurring symptoms, and providing a holistic health assessment."""
        else:
            system_prompt = f"You are a {doctor_specialty.value.replace('_', ' ')} providing medical consultation."
        
        consultation_prompt = consultation_request.get_message() or f"{doctor_specialty.value.replace('_', ' ')} consultation"
        
        # Include context based on type detected
        if formatted_history:
            if is_cross_case_request:
                consultation_prompt = f"**COMPREHENSIVE MEDICAL HISTORY:**\n{formatted_history}\n\n**PATIENT REQUEST:**\n{consultation_prompt}\n\nPlease analyze the patient's complete medical history and provide insights into their overall health patterns, recurring symptoms, and potential underlying conditions."
            else:
                consultation_prompt = f"**Previous Conversation History:**\n{formatted_history}\n\n**Current Message:**\n{consultation_prompt}"
        
        # Add medical context to prompt if available
        if medical_context and medical_context.get("similar_cases"):
            consultation_prompt += "\n\n**Similar Past Cases:**\n"
            for i, similar_case in enumerate(medical_context["similar_cases"][:3], 1):
                consultation_prompt += f"\n{i}. Chief Complaint: {similar_case.get('chief_complaint', 'N/A')}"
                consultation_prompt += f"\n   Symptoms: {', '.join(similar_case.get('symptoms', []))}"
                consultation_prompt += f"\n   Similarity Score: {similar_case.get('similarity_score', 0):.2f}\n"
        
        if medical_context and medical_context.get("symptom_patterns"):
            common_symptoms = medical_context["symptom_patterns"].get("common_symptoms", [])
            if common_symptoms:
                consultation_prompt += "\n**Patient's Common Symptoms History:**\n"
                for symptom_info in common_symptoms[:5]:
                    consultation_prompt += f"- {symptom_info['symptom']} (occurred {symptom_info['frequency']} times)\n"
        
        # If image data is provided, analyze it
        if consultation_request.image_data:
            image_analysis = await ai_service.analyze_medical_image(
                image_data=consultation_request.image_data,
                image_type="medical_image",
                specialty=doctor_specialty.value,
                patient_context=patient_context,
                enable_heatmap=False
            )
            
            if image_analysis.get("success"):
                # Add image analysis to context
                consultation_prompt += f"\n\nImage Analysis Results:\n{image_analysis.get('analysis', 'No analysis available')}"
        
        # Get AI response
        logger.info(f"=== CALLING AI SERVICE ===")
        logger.info(f"Context Type: {'CROSS-CASE ANALYSIS' if is_cross_case_request else 'SESSION-BASED CONVERSATION'}")
        logger.info(f"Consultation prompt length: {len(consultation_prompt)}")
        logger.info(f"System prompt length: {len(system_prompt)}")
        logger.info(f"Chat history length: {len(chat_history)} messages")
        logger.info(f"Formatted history length: {len(formatted_history)} characters")
        
        # Log context-specific information for debugging
        if is_cross_case_request:
            logger.info(f"🔍 CROSS-CASE ANALYSIS: Processing comprehensive medical history")
            if chat_history:
                logger.info(f"Historical cases data: {len(set(msg.get('case_id', 'unknown') for msg in chat_history))} unique cases")
        else:
            logger.info(f"💬 SESSION CONVERSATION: Processing current session history")
            if chat_history:
                logger.info(f"Sample session history (first 2 messages): {chat_history[:2]}")
            else:
                logger.info("No session history found - this is either the first message or a loading issue")
        
        result = await ai_service.get_medical_consultation(
            message=consultation_prompt,
            specialty=doctor_specialty.value,
            chat_history=chat_history,
            patient_context=patient_context,
            system_prompt=system_prompt
        )
        
        logger.info(f"=== AI SERVICE RESPONSE ===")
        logger.info(f"Success: {result.get('success', 'Not specified')}")
        logger.info(f"Response length: {len(result.get('response', ''))}")
        logger.info(f"Model used: {result.get('model_used', 'Unknown')}")
        
        # Extract recommendations and follow-up questions from response
        response_text = result.get("response", "I apologize, but I'm having trouble processing your request.")
        logger.info(f"First 200 chars of response: {response_text[:200]}")
        
        # Session messages now handled by cases microservice
        
        # Parse response to extract structured data
        findings = []
        recommendations = []
        follow_up_questions = []
        
        # Simple extraction logic (in production, this would be more sophisticated)
        lines = response_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if 'finding' in line.lower() or 'assessment' in line.lower():
                current_section = 'findings'
            elif 'recommend' in line.lower():
                current_section = 'recommendations'
            elif 'follow' in line.lower() and 'question' in line.lower():
                current_section = 'questions'
            elif line and current_section:
                if line.startswith(('-', '*', '•', '1', '2', '3', '4', '5')):
                    cleaned_line = line.lstrip('-*•123456789. ')
                    if current_section == 'findings' and cleaned_line:
                        findings.append(cleaned_line)
                    elif current_section == 'recommendations' and cleaned_line:
                        recommendations.append(cleaned_line)
                    elif current_section == 'questions' and cleaned_line:
                        follow_up_questions.append(cleaned_line)
        
        # Default recommendations if none extracted
        if not recommendations:
            recommendations = [
                "Monitor your symptoms carefully",
                "Maintain a healthy lifestyle",
                "Follow up if symptoms worsen",
                "Keep a symptom diary"
            ]
        
        # Default follow-up questions if none extracted
        if not follow_up_questions:
            follow_up_questions = [
                "How long have you been experiencing these symptoms?",
                "Are you currently taking any medications?",
                "Do you have any known allergies?",
                "Have you had similar symptoms before?"
            ]
        
        response_data = {
            "consultation_id": consultation_id,
            "session_id": session_id,
            "response": response_text,
            "analysis_result": f"{doctor_specialty.value} consultation completed",
            "findings": findings[:5],  # Limit to 5 findings
            "recommendations": recommendations[:5],  # Limit to 5 recommendations
            "follow_up_questions": follow_up_questions[:4],  # Limit to 4 questions
            "confidence_score": 0.85,
            "model_used": result.get("model_used", "groq-llama"),
            "chat_history": chat_history[-5:]  # Include last 5 messages for frontend
        }
        
        logger.info(f"=== RETURNING CONSULTATION RESPONSE ===")
        logger.info(f"Response text preview: {response_data['response'][:200]}")
        
        return response_data
        
    except Exception as e:
        logger.error(f"AI consultation error: {str(e)}")
        # Fallback to basic response
        return {
            "consultation_id": consultation_id,
            "session_id": session_id,
            "response": f"I apologize, but I'm experiencing technical difficulties. As a {doctor_specialty.value.replace('_', ' ')}, I recommend scheduling an in-person consultation for your concerns.",
            "analysis_result": "Technical error occurred",
            "findings": [],
            "recommendations": ["Please try again or contact support"],
            "follow_up_questions": [],
            "confidence_score": 0.0
        }

def _determine_analysis_type(consultation_request: DoctorConsultationRequest) -> AnalysisType:
    """Determine analysis type based on consultation request"""
    if consultation_request.image_data and consultation_request.audio_data:
        return AnalysisType.MULTIMODAL
    elif consultation_request.image_data:
        return AnalysisType.IMAGE
    elif consultation_request.audio_data:
        return AnalysisType.AUDIO
    else:
        return AnalysisType.TEXT

@router.get("/consultations/history", response_model=List[Dict[str, Any]])
async def get_consultation_history(
    current_user: User = Depends(get_current_active_user),
    db: Neo4jClient = Depends(get_database),
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    doctor_specialty: Optional[DoctorSpecialty] = Query(None, description="Filter by doctor specialty"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of consultations to return")
):
    """Get user's consultation history"""
    try:
        # Build query to get analyses (consultations) for user's cases
        base_query = """
        MATCH (u:User {user_id: $user_id})-[:OWNS]->(c:Case)-[:HAS_ANALYSIS]->(a:Analysis)
        """
        
        conditions = []
        params = {"user_id": current_user.user_id, "limit": limit}
        
        if case_id:
            conditions.append("c.case_id = $case_id")
            params["case_id"] = case_id
        
        if doctor_specialty:
            conditions.append("a.metadata.doctor_specialty = $doctor_specialty")
            params["doctor_specialty"] = doctor_specialty.value
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        
        query = base_query + """
        RETURN a, c.title as case_title, c.case_id as case_id
        ORDER BY a.created_at DESC
        LIMIT $limit
        """
        
        result = await db.run_query(query, params)
        
        consultations = []
        for record in result:
            analysis_data = record["a"]
            consultation = {
                "consultation_id": analysis_data.get("metadata", {}).get("consultation_id"),
                "analysis_id": analysis_data["analysis_id"],
                "case_id": record["case_id"],
                "case_title": record["case_title"],
                "doctor_specialty": analysis_data.get("metadata", {}).get("doctor_specialty"),
                "analysis_result": analysis_data["analysis_result"],
                "findings": analysis_data.get("findings", []),
                "recommendations": analysis_data.get("recommendations", []),
                "confidence_score": analysis_data.get("confidence_score", 0.0),
                "created_at": analysis_data["created_at"],
                "processing_time": analysis_data.get("processing_time", 0.0)
            }
            consultations.append(consultation)
        
        return consultations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve consultation history: {str(e)}"
        )

@router.get("/statistics", response_model=Dict[str, Any])
async def get_doctor_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Neo4jClient = Depends(get_database)
):
    """Get statistics about AI doctors"""
    try:
        # Get general doctor statistics
        stats_query = """
        MATCH (d:Doctor)
        RETURN 
            count(d) as total_doctors,
            count(CASE WHEN d.is_active THEN 1 END) as active_doctors,
            collect(DISTINCT d.specialty) as specialties,
            avg(d.consultation_count) as avg_consultations,
            sum(d.consultation_count) as total_consultations
        """
        
        stats_result = await db.run_query(stats_query)
        stats = stats_result[0] if stats_result else {}
        
        # Get specialty-specific statistics
        specialty_query = """
        MATCH (d:Doctor)
        RETURN 
            d.specialty as specialty,
            count(d) as count,
            avg(d.consultation_count) as avg_consultations,
            avg(d.average_rating) as avg_rating
        """
        
        specialty_result = await db.run_query(specialty_query)
        specialty_stats = {record["specialty"]: {
            "count": record["count"],
            "avg_consultations": record["avg_consultations"] or 0,
            "avg_rating": record["avg_rating"] or 0.0
        } for record in specialty_result}
        
        return {
            "total_doctors": stats.get("total_doctors", 0),
            "active_doctors": stats.get("active_doctors", 0),
            "available_specialties": stats.get("specialties", []),
            "total_consultations": stats.get("total_consultations", 0),
            "average_consultations_per_doctor": stats.get("avg_consultations", 0),
            "specialty_breakdown": specialty_stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve doctor statistics: {str(e)}"
        )