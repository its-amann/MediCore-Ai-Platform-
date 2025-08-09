"""
Groq AI doctor service implementation
"""
from groq import AsyncGroq
from typing import Dict, Any, Optional, AsyncGenerator, List
import json
import logging
from ..base.doctor_service_base import BaseDoctorService
from ...models.case_models import CaseData
from ...models.chat_models import ChatMessage
from ...core.config import settings

logger = logging.getLogger(__name__)


class GroqDoctorService(BaseDoctorService):
    """Groq AI implementation for medical consultations"""
    
    def __init__(self, api_key: str, model_name: Optional[str] = None):
        super().__init__(api_key, model_name)
        self.client = None
    
    def get_default_model(self) -> str:
        """Get default model name for Groq"""
        return "mixtral-8x7b-32768"
    
    async def initialize(self) -> None:
        """Initialize Groq client"""
        try:
            self.client = AsyncGroq(api_key=self.api_key)
            self.initialized = True
            logger.info(f"Initialized Groq doctor with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Groq doctor: {e}")
            raise
    
    async def diagnose_case(self, case_data: CaseData, chat_history: List[ChatMessage]) -> str:
        """Generate diagnosis using Groq"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Build messages for chat completion
            messages = self._build_messages(case_data, chat_history)
            messages.append({
                "role": "user",
                "content": "Based on the case information provided, please provide a comprehensive medical analysis including possible diagnoses, recommended tests, and treatment options."
            })
            
            # Create completion
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=settings.default_temperature,
                max_tokens=settings.default_max_tokens,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Groq diagnosis error: {e}")
            return await self.handle_error(e, {"case_id": case_data.id})
    
    async def stream_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """Stream response from Groq"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Build messages
            messages = []
            if context and "case_data" in context:
                system_prompt = self.build_system_prompt(context["case_data"])
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            # Create streaming completion
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=settings.default_temperature,
                max_tokens=settings.default_max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Groq streaming error: {e}")
            error_msg = await self.handle_error(e)
            yield error_msg
    
    async def get_treatment_recommendations(self, diagnosis: str, case_data: CaseData) -> List[Dict[str, Any]]:
        """Get treatment recommendations from Groq"""
        if not self.initialized:
            await self.initialize()
        
        messages = [
            {
                "role": "system",
                "content": "You are an experienced medical consultant providing evidence-based treatment recommendations."
            },
            {
                "role": "user",
                "content": f"""Based on the following diagnosis and case information, provide detailed treatment recommendations:

Diagnosis: {diagnosis}

Case Information:
{case_data.description}

Please provide a JSON response with the following structure:
{{
    "recommendations": [
        {{
            "type": "medication|procedure|lifestyle|follow_up|warning",
            "title": "Brief title",
            "description": "Detailed description",
            "priority": "high|medium|low",
            "rationale": "Medical reasoning"
        }}
    ]
}}"""
            }
        ]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.3,  # Lower temperature for structured output
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            content = response.choices[0].message.content
            try:
                data = json.loads(content)
                return data.get("recommendations", [])
            except json.JSONDecodeError:
                # Fallback to text parsing if JSON fails
                return self._parse_recommendations_fallback(content)
                
        except Exception as e:
            logger.error(f"Groq treatment recommendations error: {e}")
            return [{
                "type": "error",
                "title": "Unable to generate recommendations",
                "description": await self.handle_error(e),
                "priority": "high"
            }]
    
    async def assess_urgency(self, case_data: CaseData) -> Dict[str, Any]:
        """Assess case urgency using Groq"""
        if not self.initialized:
            await self.initialize()
        
        messages = [
            {
                "role": "system",
                "content": "You are an experienced emergency medicine physician assessing patient urgency."
            },
            {
                "role": "user",
                "content": f"""Assess the medical urgency of the following case:

{case_data.description}

Provide a JSON response with:
{{
    "urgency_level": "critical|high|moderate|low",
    "score": <0-10>,
    "timeframe": "immediately|within 24 hours|within 48-72 hours|within 1-2 weeks",
    "factors": ["list of key factors"],
    "immediate_actions": ["list of immediate actions if any"],
    "reasoning": "detailed explanation"
}}"""
            }
        ]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            content = response.choices[0].message.content
            try:
                assessment = json.loads(content)
                return assessment
            except json.JSONDecodeError:
                # Fallback parsing
                return self._parse_urgency_fallback(content)
                
        except Exception as e:
            logger.error(f"Groq urgency assessment error: {e}")
            return {
                "urgency_level": "unknown",
                "score": 5,
                "reasoning": "Unable to assess urgency due to technical error",
                "error": str(e)
            }
    
    async def get_confidence_score(self, response: str, case_data: CaseData) -> float:
        """Calculate confidence score for Groq response"""
        # Base confidence on response validation
        validation = await self.validate_response(response)
        base_confidence = validation["confidence"]
        
        # Groq-specific adjustments
        adjustments = 0.0
        
        # Check for structured medical language
        medical_indicators = [
            "differential diagnosis", "clinical presentation", "pathophysiology",
            "etiology", "prognosis", "contraindications", "indication"
        ]
        
        indicator_count = sum(1 for indicator in medical_indicators if indicator.lower() in response.lower())
        if indicator_count >= 2:
            adjustments += 0.15
        elif indicator_count >= 1:
            adjustments += 0.1
        
        # Check for evidence-based language
        evidence_terms = ["studies show", "research indicates", "clinical trials", "evidence suggests"]
        if any(term in response.lower() for term in evidence_terms):
            adjustments += 0.1
        
        # Length and detail assessment
        word_count = len(response.split())
        if word_count < 100:
            adjustments -= 0.15
        elif word_count > 300:
            adjustments += 0.1
        
        # Calculate final confidence
        final_confidence = base_confidence + adjustments
        return max(0.0, min(1.0, final_confidence))
    
    def _build_messages(self, case_data: CaseData, chat_history: List[ChatMessage]) -> List[Dict[str, str]]:
        """Build message list for Groq chat completion"""
        messages = []
        
        # Add system prompt
        system_prompt = self.build_system_prompt(case_data)
        messages.append({"role": "system", "content": system_prompt})
        
        # Add chat history
        for msg in chat_history[-10:]:  # Last 10 messages to stay within context
            role = "user" if msg.sender_type == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})
        
        return messages
    
    def _parse_recommendations_fallback(self, text: str) -> List[Dict[str, Any]]:
        """Fallback parsing for recommendations when JSON parsing fails"""
        recommendations = []
        
        # Split by common separators
        sections = text.split('\n\n')
        
        for i, section in enumerate(sections):
            if section.strip():
                # Determine type based on content
                section_lower = section.lower()
                rec_type = "general"
                
                if any(word in section_lower for word in ["medication", "prescription", "dosage"]):
                    rec_type = "medication"
                elif any(word in section_lower for word in ["lifestyle", "diet", "exercise"]):
                    rec_type = "lifestyle"
                elif any(word in section_lower for word in ["follow", "appointment", "monitoring"]):
                    rec_type = "follow_up"
                elif any(word in section_lower for word in ["warning", "red flag", "emergency"]):
                    rec_type = "warning"
                elif any(word in section_lower for word in ["procedure", "surgery", "intervention"]):
                    rec_type = "procedure"
                
                # Extract title (first line or first sentence)
                lines = section.strip().split('\n')
                title = lines[0][:100] if lines else f"Recommendation {i+1}"
                
                recommendations.append({
                    "type": rec_type,
                    "title": title,
                    "description": section.strip(),
                    "priority": "high" if rec_type == "warning" else "medium",
                    "rationale": "Based on clinical assessment"
                })
        
        return recommendations if recommendations else [{
            "type": "general",
            "title": "Medical Consultation Recommended",
            "description": text[:500],
            "priority": "medium"
        }]
    
    def _parse_urgency_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback parsing for urgency assessment when JSON parsing fails"""
        assessment = {
            "urgency_level": "moderate",
            "score": 5,
            "factors": [],
            "timeframe": "within 48 hours",
            "immediate_actions": [],
            "reasoning": text[:500]
        }
        
        text_lower = text.lower()
        
        # Determine urgency level based on keywords
        if any(word in text_lower for word in ["critical", "emergency", "life-threatening", "immediate"]):
            assessment["urgency_level"] = "critical"
            assessment["score"] = 9
            assessment["timeframe"] = "immediately"
        elif any(word in text_lower for word in ["urgent", "serious", "concerning", "high priority"]):
            assessment["urgency_level"] = "high"
            assessment["score"] = 7
            assessment["timeframe"] = "within 24 hours"
        elif any(word in text_lower for word in ["moderate", "medium", "routine follow-up"]):
            assessment["urgency_level"] = "moderate"
            assessment["score"] = 5
            assessment["timeframe"] = "within 48-72 hours"
        elif any(word in text_lower for word in ["low", "minor", "non-urgent", "elective"]):
            assessment["urgency_level"] = "low"
            assessment["score"] = 3
            assessment["timeframe"] = "within 1-2 weeks"
        
        return assessment