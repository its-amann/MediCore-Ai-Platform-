"""
Abstract base class for all doctor services
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime
import uuid
from ...models.case_models import CaseData
from ...models.chat_models import ChatMessage, MessageType


class BaseDoctorService(ABC):
    """Abstract base class for all doctor services"""
    
    def __init__(self, api_key: str, model_name: Optional[str] = None):
        self.api_key = api_key
        self.model_name = model_name or self.get_default_model()
        self.service_name = self.__class__.__name__
        self.initialized = False
    
    @abstractmethod
    def get_default_model(self) -> str:
        """Get default model name for this service"""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the service (connect to API, etc.)"""
        pass
    
    @abstractmethod
    async def diagnose_case(self, case_data: CaseData, chat_history: List[ChatMessage]) -> str:
        """
        Generate diagnosis based on case data and chat history
        
        Args:
            case_data: The medical case information
            chat_history: Previous conversation messages
            
        Returns:
            Diagnosis text
        """
        pass
    
    @abstractmethod
    async def stream_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """
        Stream response tokens in real-time
        
        Args:
            prompt: The user's prompt
            context: Additional context for the response
            
        Yields:
            Response tokens as they are generated
        """
        pass
    
    @abstractmethod
    async def get_treatment_recommendations(self, diagnosis: str, case_data: CaseData) -> List[Dict[str, Any]]:
        """
        Get treatment recommendations based on diagnosis
        
        Args:
            diagnosis: The diagnosis text
            case_data: The medical case information
            
        Returns:
            List of treatment recommendations with details
        """
        pass
    
    @abstractmethod
    async def assess_urgency(self, case_data: CaseData) -> Dict[str, Any]:
        """
        Assess case urgency and priority level
        
        Args:
            case_data: The medical case information
            
        Returns:
            Dictionary containing urgency level, score, and reasoning
        """
        pass
    
    @abstractmethod
    async def get_confidence_score(self, response: str, case_data: CaseData) -> float:
        """
        Get confidence score for generated response
        
        Args:
            response: The generated response
            case_data: The medical case information
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        pass
    
    async def validate_response(self, response: str) -> Dict[str, Any]:
        """
        Validate medical response for safety and accuracy
        
        Args:
            response: The response to validate
            
        Returns:
            Validation result with warnings and confidence
        """
        # Base validation logic
        warnings = []
        
        # Check for common medical safety issues
        dangerous_terms = [
            "definitely", "certainly", "guaranteed", "100%",
            "cure", "never", "always", "impossible"
        ]
        
        response_lower = response.lower()
        for term in dangerous_terms:
            if term in response_lower:
                warnings.append(f"Response contains absolute term: '{term}'")
        
        # Check for disclaimer
        disclaimer_terms = ["consult", "professional", "doctor", "physician", "medical advice"]
        has_disclaimer = any(term in response_lower for term in disclaimer_terms)
        
        if not has_disclaimer:
            warnings.append("Response lacks professional consultation disclaimer")
        
        # Calculate base confidence
        confidence = 0.8
        if warnings:
            confidence -= 0.1 * len(warnings)
        
        return {
            "is_valid": len(warnings) < 3,
            "warnings": warnings,
            "confidence": max(0.3, confidence),
            "has_disclaimer": has_disclaimer
        }
    
    async def format_response(self, response: str, metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        """
        Format response as a ChatMessage
        
        Args:
            response: The response text
            metadata: Additional metadata
            
        Returns:
            Formatted ChatMessage
        """
        validation = await self.validate_response(response)
        
        return ChatMessage(
            id=str(uuid.uuid4()),
            case_id=metadata.get("case_id", "") if metadata else "",
            content=response,
            message_type=MessageType.DOCTOR_RESPONSE,
            sender_id=self.service_name.lower(),
            sender_type="doctor",
            timestamp=datetime.utcnow(),
            metadata={
                "model": self.model_name,
                "service": self.service_name,
                "confidence": validation["confidence"],
                "warnings": validation["warnings"],
                **(metadata or {})
            }
        )
    
    async def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Handle service errors gracefully
        
        Args:
            error: The exception that occurred
            context: Error context
            
        Returns:
            User-friendly error message
        """
        error_message = f"I apologize, but I encountered an issue while processing your request. "
        
        if isinstance(error, TimeoutError):
            error_message += "The response took too long. Please try again."
        elif isinstance(error, ConnectionError):
            error_message += "I'm having trouble connecting to the medical knowledge base. Please try again in a moment."
        else:
            error_message += "Please try rephrasing your question or contact support if the issue persists."
        
        # Log the actual error for debugging
        import logging
        logger = logging.getLogger(self.service_name)
        logger.error(f"Service error: {error}", exc_info=True, extra={"context": context})
        
        return error_message
    
    def build_system_prompt(self, case_data: CaseData) -> str:
        """
        Build system prompt for the AI model
        
        Args:
            case_data: The medical case information
            
        Returns:
            System prompt string
        """
        return f"""You are an experienced medical consultant providing advice for the following case:

Patient Information:
- Age: {case_data.patient_age if hasattr(case_data, 'patient_age') else 'Not specified'}
- Gender: {case_data.patient_gender if hasattr(case_data, 'patient_gender') else 'Not specified'}
- Medical History: {case_data.medical_history if hasattr(case_data, 'medical_history') else 'Not provided'}

Current Symptoms:
{case_data.description}

Please provide:
1. A thorough analysis of the symptoms
2. Possible diagnoses with reasoning
3. Recommended next steps or treatments
4. Any red flags that require immediate attention

Always include appropriate medical disclaimers and recommend consulting with healthcare professionals for definitive diagnosis and treatment.
"""
    
    def build_conversation_context(self, chat_history: List[ChatMessage], max_messages: int = 10) -> str:
        """
        Build conversation context from chat history
        
        Args:
            chat_history: List of previous messages
            max_messages: Maximum number of messages to include
            
        Returns:
            Formatted conversation context
        """
        if not chat_history:
            return ""
        
        # Take the most recent messages
        recent_messages = chat_history[-max_messages:]
        
        context = "Previous conversation:\n"
        for msg in recent_messages:
            sender = "Patient" if msg.sender_type == "user" else "Doctor"
            context += f"{sender}: {msg.content}\n"
        
        return context
    
    async def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the service
        
        Returns:
            Service information dictionary
        """
        return {
            "name": self.service_name,
            "model": self.model_name,
            "initialized": self.initialized,
            "capabilities": {
                "streaming": True,
                "diagnosis": True,
                "treatment_recommendations": True,
                "urgency_assessment": True,
                "confidence_scoring": True
            }
        }