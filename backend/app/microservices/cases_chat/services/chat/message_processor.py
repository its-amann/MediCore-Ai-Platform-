"""
Message processing service for chat functionality
"""
from typing import List, Dict, Any, AsyncGenerator, Optional
import logging
from datetime import datetime

from ...models.chat_models import ChatMessage, MessageCreate, MessageType
from ...models.case_models import CaseData
from ..storage.neo4j_storage import UnifiedNeo4jStorage
from ..doctors.doctor_coordinator import DoctorCoordinator
from ...core.websocket_manager import WebSocketManager
from ...core.exceptions import CaseNotFoundError, DoctorServiceError

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Processes chat messages and coordinates AI responses"""
    
    def __init__(
        self,
        storage: UnifiedNeo4jStorage,
        doctor_coordinator: DoctorCoordinator,
        websocket_manager: WebSocketManager
    ):
        self.storage = storage
        self.doctor_coordinator = doctor_coordinator
        self.websocket_manager = websocket_manager
    
    async def process_message(self, message: MessageCreate) -> ChatMessage:
        """
        Process a user message and get AI response
        
        Args:
            message: User message
            
        Returns:
            AI response message
        """
        # Get case data
        case = await self.storage.get_case(message.case_id)
        if not case:
            raise CaseNotFoundError(message.case_id)
        
        # Store user message
        stored_message = await self.storage.store_message(message)
        
        # Get chat history for context
        chat_history = await self._get_context_messages(message.case_id)
        
        # Convert case to CaseData for doctor service
        case_data = self._case_to_case_data(case)
        
        # Get AI response
        try:
            response = await self.doctor_coordinator.get_response(
                case_data=case_data,
                chat_history=chat_history,
                prompt=message.content,
                stream=False
            )
            
            # Create response message
            response_message = MessageCreate(
                case_id=message.case_id,
                content=response["content"],
                message_type=MessageType.DOCTOR_RESPONSE,
                sender_id=response["service"],
                sender_type="doctor",
                metadata={
                    "model": response["model"],
                    "confidence": response["confidence"],
                    "response_time": response["response_time"],
                    **response.get("metadata", {})
                }
            )
            
            # Store AI response
            stored_response = await self.storage.store_message(response_message)
            
            logger.info(f"Processed message for case {message.case_id}")
            return stored_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise DoctorServiceError(f"Failed to get AI response: {str(e)}")
    
    async def process_message_stream(self, message: MessageCreate) -> ChatMessage:
        """
        Process a user message with streaming response
        
        Note: This returns the complete message after streaming.
        For real streaming, use stream_response method.
        
        Args:
            message: User message
            
        Returns:
            Complete AI response message
        """
        # Get case data
        case = await self.storage.get_case(message.case_id)
        if not case:
            raise CaseNotFoundError(message.case_id)
        
        # Store user message
        stored_message = await self.storage.store_message(message)
        
        # Get chat history for context
        chat_history = await self._get_context_messages(message.case_id)
        
        # Convert case to CaseData
        case_data = self._case_to_case_data(case)
        
        # Stream AI response
        full_response = ""
        metadata = {}
        
        async for chunk in self.doctor_coordinator.stream_response(
            case_data=case_data,
            chat_history=chat_history,
            prompt=message.content
        ):
            if chunk.get("done"):
                metadata = chunk.get("metadata", {})
                metadata["confidence"] = chunk.get("confidence", 0)
                metadata["response_time"] = chunk.get("response_time", 0)
                metadata["model"] = chunk.get("model", "unknown")
                metadata["service"] = chunk.get("service", "unknown")
            else:
                full_response += chunk.get("chunk", "")
        
        # Create complete response message
        response_message = MessageCreate(
            case_id=message.case_id,
            content=full_response,
            message_type=MessageType.DOCTOR_RESPONSE,
            sender_id=metadata.get("service", "ai_doctor"),
            sender_type="doctor",
            metadata=metadata
        )
        
        # Store AI response
        stored_response = await self.storage.store_message(response_message)
        
        logger.info(f"Processed streaming message for case {message.case_id}")
        return stored_response
    
    async def stream_response(
        self, 
        message: MessageCreate
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream AI response chunks
        
        Args:
            message: User message
            
        Yields:
            Response chunks with metadata
        """
        # Get case data
        case = await self.storage.get_case(message.case_id)
        if not case:
            raise CaseNotFoundError(message.case_id)
        
        # Store user message
        stored_message = await self.storage.store_message(message)
        
        # Get chat history for context
        chat_history = await self._get_context_messages(message.case_id)
        
        # Convert case to CaseData
        case_data = self._case_to_case_data(case)
        
        # Stream AI response
        full_response = ""
        
        async for chunk in self.doctor_coordinator.stream_response(
            case_data=case_data,
            chat_history=chat_history,
            prompt=message.content
        ):
            if chunk.get("done"):
                # Final chunk - store the complete message
                response_message = MessageCreate(
                    case_id=message.case_id,
                    content=full_response,
                    message_type=MessageType.DOCTOR_RESPONSE,
                    sender_id=chunk.get("service", "ai_doctor"),
                    sender_type="doctor",
                    metadata={
                        "model": chunk.get("model", "unknown"),
                        "confidence": chunk.get("confidence", 0),
                        "response_time": chunk.get("response_time", 0),
                        **chunk.get("metadata", {})
                    }
                )
                
                stored_response = await self.storage.store_message(response_message)
                
                # Yield final chunk with stored message info
                yield {
                    "type": "complete",
                    "message_id": stored_response.id,
                    "content": full_response,
                    **chunk
                }
            else:
                # Regular chunk
                chunk_content = chunk.get("chunk", "")
                full_response += chunk_content
                
                yield {
                    "type": "chunk",
                    "content": chunk_content,
                    "service": chunk.get("service", "unknown"),
                    "model": chunk.get("model", "unknown")
                }
    
    async def send_typing_indicator(
        self,
        case_id: str,
        user_id: str,
        is_typing: bool
    ) -> None:
        """
        Send typing indicator through WebSocket
        
        Args:
            case_id: Case ID
            user_id: User who is typing
            is_typing: Whether user is typing
        """
        await self.websocket_manager.broadcast_to_case(case_id, {
            "type": "typing_indicator",
            "user_id": user_id,
            "is_typing": is_typing,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _get_context_messages(
        self,
        case_id: str,
        limit: int = 50
    ) -> List[ChatMessage]:
        """
        Get recent messages for context
        
        Args:
            case_id: Case ID
            limit: Maximum messages to retrieve
            
        Returns:
            List of recent messages
        """
        messages = await self.storage.get_case_messages(
            case_id=case_id,
            limit=limit,
            include_system=False
        )
        
        # Return in chronological order
        return messages
    
    def _case_to_case_data(self, case: Any) -> CaseData:
        """
        Convert storage case to CaseData model
        
        Args:
            case: Case from storage
            
        Returns:
            CaseData object
        """
        # Handle both dict and object cases
        if hasattr(case, 'dict'):
            case_dict = case.dict()
        elif hasattr(case, '__dict__'):
            case_dict = case.__dict__
        else:
            case_dict = dict(case)
        
        # Extract relevant fields
        return CaseData(
            id=case_dict.get("id", ""),
            case_number=case_dict.get("case_number", ""),
            title=case_dict.get("title", ""),
            description=case_dict.get("description", ""),
            patient_id=case_dict.get("patient_id", ""),
            patient_age=case_dict.get("patient_age"),
            patient_gender=case_dict.get("patient_gender"),
            medical_history=case_dict.get("medical_history", ""),
            current_medications=case_dict.get("current_medications", []),
            allergies=case_dict.get("allergies", []),
            symptoms=case_dict.get("symptoms", []),
            status=case_dict.get("status", "active"),
            urgency_level=case_dict.get("urgency_level", "medium")
        )