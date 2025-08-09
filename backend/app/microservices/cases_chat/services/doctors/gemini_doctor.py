"""
Google Gemini AI doctor service implementation
"""
import google.generativeai as genai
from typing import Dict, Any, Optional, AsyncGenerator, List
import asyncio
import logging
from ..base.doctor_service_base import BaseDoctorService
from ...models.case_models import CaseData
from ...models.chat_models import ChatMessage
from ...core.config import settings

logger = logging.getLogger(__name__)


class GeminiDoctorService(BaseDoctorService):
    """Google Gemini AI implementation for medical consultations"""
    
    def __init__(self, api_key: str, model_name: Optional[str] = None):
        super().__init__(api_key, model_name)
        self.client = None
        self.model = None
        self.generation_config = {
            "temperature": settings.default_temperature,
            "top_p": 1,
            "top_k": 1,
            "max_output_tokens": settings.default_max_tokens,
        }
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]
    
    def get_default_model(self) -> str:
        """Get default model name for Gemini"""
        return "gemini-pro"
    
    async def initialize(self) -> None:
        """Initialize Gemini client"""
        try:
            # Configure API key
            genai.configure(api_key=self.api_key)
            
            # Create model instance
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            self.initialized = True
            logger.info(f"Initialized Gemini doctor with model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini doctor: {e}")
            raise
    
    async def diagnose_case(self, case_data: CaseData, chat_history: List[ChatMessage]) -> str:
        """Generate diagnosis using Gemini"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Build prompt
            system_prompt = self.build_system_prompt(case_data)
            conversation_context = self.build_conversation_context(chat_history)
            
            full_prompt = f"{system_prompt}\n\n{conversation_context}\n\nProvide a comprehensive medical analysis."
            
            # Generate response synchronously (Gemini SDK is sync)
            response = await asyncio.to_thread(
                self.model.generate_content,
                full_prompt
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini diagnosis error: {e}")
            return await self.handle_error(e, {"case_id": case_data.id})
    
    async def stream_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """Stream response from Gemini"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Gemini streaming is synchronous, so we need to handle it carefully
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            error_msg = await self.handle_error(e)
            yield error_msg
    
    async def get_treatment_recommendations(self, diagnosis: str, case_data: CaseData) -> List[Dict[str, Any]]:
        """Get treatment recommendations from Gemini"""
        if not self.initialized:
            await self.initialize()
        
        prompt = f"""Based on the following diagnosis and case information, provide detailed treatment recommendations:

Diagnosis: {diagnosis}

Case Information:
{case_data.description}

Please provide:
1. Primary treatment options with rationale
2. Medication recommendations (if applicable)
3. Lifestyle modifications
4. Follow-up care requirements
5. Warning signs to watch for

Format the response as a structured list of recommendations."""
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            # Parse the response into structured recommendations
            recommendations = self._parse_recommendations(response.text)
            return recommendations
            
        except Exception as e:
            logger.error(f"Gemini treatment recommendations error: {e}")
            return [{
                "type": "error",
                "title": "Unable to generate recommendations",
                "description": await self.handle_error(e),
                "priority": "high"
            }]
    
    async def assess_urgency(self, case_data: CaseData) -> Dict[str, Any]:
        """Assess case urgency using Gemini"""
        if not self.initialized:
            await self.initialize()
        
        prompt = f"""Assess the medical urgency of the following case:

{case_data.description}

Provide:
1. Urgency level (critical/high/moderate/low)
2. Urgency score (0-10, where 10 is most urgent)
3. Key factors contributing to the urgency assessment
4. Recommended timeframe for medical attention
5. Any immediate actions required

Be specific and evidence-based in your assessment."""
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            
            # Parse the urgency assessment
            assessment = self._parse_urgency_assessment(response.text)
            return assessment
            
        except Exception as e:
            logger.error(f"Gemini urgency assessment error: {e}")
            return {
                "urgency_level": "unknown",
                "score": 5,
                "reasoning": "Unable to assess urgency due to technical error",
                "error": str(e)
            }
    
    async def get_confidence_score(self, response: str, case_data: CaseData) -> float:
        """Calculate confidence score for Gemini response"""
        # Base confidence on response validation
        validation = await self.validate_response(response)
        base_confidence = validation["confidence"]
        
        # Adjust based on response characteristics
        adjustments = 0.0
        
        # Check for medical terminology usage
        medical_terms = ["diagnosis", "symptoms", "treatment", "condition", "examination"]
        term_count = sum(1 for term in medical_terms if term.lower() in response.lower())
        if term_count >= 3:
            adjustments += 0.1
        
        # Check for structured response
        if any(marker in response for marker in ["1.", "•", "-", "**"]):
            adjustments += 0.05
        
        # Check response length (too short might indicate incomplete analysis)
        if len(response) < 200:
            adjustments -= 0.1
        elif len(response) > 500:
            adjustments += 0.05
        
        # Calculate final confidence
        final_confidence = base_confidence + adjustments
        return max(0.0, min(1.0, final_confidence))
    
    def _parse_recommendations(self, text: str) -> List[Dict[str, Any]]:
        """Parse treatment recommendations from text"""
        recommendations = []
        
        # Simple parsing - this could be enhanced with more sophisticated NLP
        lines = text.strip().split('\n')
        current_rec = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a new recommendation (starts with number or bullet)
            if any(line.startswith(marker) for marker in ['1', '2', '3', '4', '5', '•', '-', '*']):
                if current_rec:
                    recommendations.append(current_rec)
                
                # Clean the line
                for marker in ['1.', '2.', '3.', '4.', '5.', '•', '-', '*']:
                    if line.startswith(marker):
                        line = line[len(marker):].strip()
                        break
                
                # Determine recommendation type
                rec_type = "general"
                if any(word in line.lower() for word in ["medication", "drug", "prescription"]):
                    rec_type = "medication"
                elif any(word in line.lower() for word in ["lifestyle", "diet", "exercise"]):
                    rec_type = "lifestyle"
                elif any(word in line.lower() for word in ["follow", "appointment", "checkup"]):
                    rec_type = "follow_up"
                elif any(word in line.lower() for word in ["warning", "emergency", "immediate"]):
                    rec_type = "warning"
                
                current_rec = {
                    "type": rec_type,
                    "title": line[:100],  # First 100 chars as title
                    "description": line,
                    "priority": "high" if rec_type == "warning" else "medium"
                }
            elif current_rec:
                # Continue previous recommendation
                current_rec["description"] += " " + line
        
        if current_rec:
            recommendations.append(current_rec)
        
        return recommendations if recommendations else [{
            "type": "general",
            "title": "Medical Consultation Recommended",
            "description": text[:500],
            "priority": "medium"
        }]
    
    def _parse_urgency_assessment(self, text: str) -> Dict[str, Any]:
        """Parse urgency assessment from text"""
        assessment = {
            "urgency_level": "moderate",
            "score": 5,
            "factors": [],
            "timeframe": "within 48 hours",
            "immediate_actions": []
        }
        
        text_lower = text.lower()
        
        # Determine urgency level
        if any(word in text_lower for word in ["critical", "emergency", "immediate", "urgent"]):
            assessment["urgency_level"] = "critical"
            assessment["score"] = 9
            assessment["timeframe"] = "immediately"
        elif any(word in text_lower for word in ["high", "serious", "concerning"]):
            assessment["urgency_level"] = "high"
            assessment["score"] = 7
            assessment["timeframe"] = "within 24 hours"
        elif any(word in text_lower for word in ["moderate", "medium"]):
            assessment["urgency_level"] = "moderate"
            assessment["score"] = 5
            assessment["timeframe"] = "within 48-72 hours"
        elif any(word in text_lower for word in ["low", "minor", "routine"]):
            assessment["urgency_level"] = "low"
            assessment["score"] = 3
            assessment["timeframe"] = "within 1-2 weeks"
        
        # Extract factors (simple approach)
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 20 and len(line) < 200:
                if any(marker in line for marker in ['-', '•', '*']) or any(line.startswith(f"{i}.") for i in range(1, 10)):
                    assessment["factors"].append(line)
        
        # Add reasoning
        assessment["reasoning"] = text[:500] if len(text) > 500 else text
        
        return assessment