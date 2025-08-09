"""
Doctor Service - Main orchestrator for AI doctor consultations
Uses Groq API for all three doctors with specific prompts
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import base64
from PIL import Image
import io
from datetime import datetime

from ...config import settings
from ...models import DoctorType
from ...prompts import (
    get_general_consultant_prompt,
    get_cardiologist_prompt,
    get_bp_specialist_prompt,
    get_handover_prompt,
    get_case_summary_prompt,
    get_report_generation_prompt,
    get_image_analysis_prompt,
    get_audio_context_prompt,
    get_mcp_context_prompt
)
from .doctor_profiles import get_doctor_profile, DOCTOR_PROFILES
from ...mcp_server.mcp_client import MCPClient

logger = logging.getLogger(__name__)


class DoctorService:
    """
    Service for managing AI doctor consultations using Google Gemini API
    """
    
    def __init__(self):
        """Initialize the doctor service with Gemini client"""
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not configured, using fallback Groq service")
            self.use_gemini = False
        else:
            self.use_gemini = True
        
        # Configure Gemini API if available
        if self.use_gemini:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # Initialize models
        self.text_model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.vision_model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Map doctor types to prompt functions
        self.prompt_functions = {
            DoctorType.GENERAL: get_general_consultant_prompt,
            DoctorType.CARDIOLOGIST: get_cardiologist_prompt,
            DoctorType.BP_SPECIALIST: get_bp_specialist_prompt
        }
        
        # Initialize MCP client (optional - will work without MCP server)
        self.mcp_client = None
        if settings.mcp_server_enabled:
            try:
                self.mcp_client = MCPClient(
                    host=settings.mcp_server_host,
                    port=settings.mcp_server_port
                )
                logger.info(f"MCP client initialized for {settings.mcp_server_host}:{settings.mcp_server_port}")
            except Exception as e:
                logger.warning(f"MCP client initialization failed: {e}. Continuing without MCP.")
    
    def _prepare_image_for_gemini(self, base64_data: str) -> Dict:
        """
        Prepare image data for Gemini API
        
        Args:
            base64_data: Base64 encoded image data
            
        Returns:
            Image data formatted for Gemini
        """
        # Decode base64 to bytes
        image_bytes = base64.b64decode(base64_data)
        
        # Open image with PIL to determine format
        image = Image.open(io.BytesIO(image_bytes))
        
        # Determine MIME type
        mime_type = f"image/{image.format.lower()}" if image.format else "image/jpeg"
        
        return {
            'inline_data': {
                'mime_type': mime_type,
                'data': base64_data
            }
        }
    
    async def get_doctor_response(
        self,
        doctor_type: DoctorType,
        message: str,
        case_info: dict,
        context: List[Dict] = None,
        image_data: Optional[str] = None,
        is_handover: bool = False
    ) -> Dict[str, Any]:
        """
        Get response from a specific doctor
        
        Args:
            doctor_type: Type of doctor to consult
            message: User's message
            case_info: Case information
            context: Conversation context
            image_data: Base64 encoded image data
            is_handover: Whether this is a doctor handover
            
        Returns:
            Dictionary with doctor response and metadata
        """
        start_time = time.time()
        
        try:
            # Get doctor profile
            profile = get_doctor_profile(doctor_type)
            if not profile:
                raise ValueError(f"Unknown doctor type: {doctor_type}")
            
            # Get appropriate prompt
            prompt_func = self.prompt_functions.get(doctor_type)
            if not prompt_func:
                raise ValueError(f"No prompt function for doctor type: {doctor_type}")
            
            # Generate system prompt
            system_prompt = prompt_func(case_info=case_info, context=context)
            
            # Try to get related cases from MCP if available
            related_cases_context = ""
            if self.mcp_client and case_info.get("case_id") and settings.mcp_server_enabled:
                try:
                    # Notify that MCP analysis is starting
                    case_id = case_info.get("case_id")
                    user_id = case_info.get("user_id")
                    
                    # Send WebSocket notification for MCP analysis start
                    if case_id and user_id:
                        from app.microservices.cases_chat.websocket_adapter import get_cases_chat_ws_adapter
                        ws_adapter = get_cases_chat_ws_adapter()
                        await ws_adapter.notify_mcp_analysis(
                            user_id=user_id,
                            case_id=case_id,
                            doctor_type=doctor_type,
                            status="started",
                            data={"message": "Analyzing past medical cases..."}
                        )
                    
                    # Connect to MCP if not connected
                    if not self.mcp_client.connected:
                        await self.mcp_client.connect()
                    
                    # Find similar cases
                    similar_cases = await self.mcp_client.find_similar_cases(
                        case_id=case_info["case_id"],
                        similarity_threshold=0.6,
                        limit=3
                    )
                    
                    if similar_cases:
                        related_cases_context = get_mcp_context_prompt(similar_cases)
                        system_prompt += related_cases_context
                        logger.info(f"Added {len(similar_cases)} related cases to context")
                        
                        # Send WebSocket notification for MCP analysis complete
                        if case_id and user_id:
                            from app.microservices.cases_chat.websocket_adapter import get_cases_chat_ws_adapter
                            ws_adapter = get_cases_chat_ws_adapter()
                            await ws_adapter.notify_mcp_analysis(
                                user_id=user_id,
                                case_id=case_id,
                                doctor_type=doctor_type,
                                status="completed",
                                data={
                                    "similar_cases_found": len(similar_cases),
                                    "message": f"Found {len(similar_cases)} similar cases"
                                }
                            )
                    else:
                        # Send notification that no similar cases were found
                        if case_id and user_id:
                            from app.microservices.cases_chat.websocket_adapter import get_cases_chat_ws_adapter
                            ws_adapter = get_cases_chat_ws_adapter()
                            await ws_adapter.notify_mcp_analysis(
                                user_id=user_id,
                                case_id=case_id,
                                doctor_type=doctor_type,
                                status="completed",
                                data={
                                    "similar_cases_found": 0,
                                    "message": "No similar cases found"
                                }
                            )
                        
                except Exception as e:
                    logger.warning(f"Failed to get MCP context: {e}")
                    # Send error notification
                    if case_id and user_id:
                        from app.microservices.cases_chat.websocket_adapter import get_cases_chat_ws_adapter
                        ws_adapter = get_cases_chat_ws_adapter()
                        await ws_adapter.notify_mcp_analysis(
                            user_id=user_id,
                            case_id=case_id,
                            doctor_type=doctor_type,
                            status="failed",
                            data={
                                "error": str(e),
                                "message": "Failed to analyze past cases"
                            }
                        )
            
            # Add image analysis enhancement if image provided
            if image_data:
                system_prompt = get_image_analysis_prompt(doctor_type.value, system_prompt)
            
            # Prepare content for Gemini
            content_parts = []
            
            # Add system prompt as the first part of the conversation
            full_message = f"{system_prompt}\n\n"
            
            # Add context from previous conversations
            if context:
                full_message += "Previous conversation context:\n"
                for ctx_msg in context[-5:]:  # Last 5 messages
                    if ctx_msg.get('user_message'):
                        full_message += f"Patient: {ctx_msg['user_message']}\n"
                    if ctx_msg.get('doctor_response'):
                        full_message += f"Doctor: {ctx_msg['doctor_response']}\n"
                full_message += "\n"
            
            # Add current message
            full_message += f"Current patient message: {message}"
            content_parts.append(full_message)
            
            # Add image if provided
            if image_data:
                content_parts.append(self._prepare_image_for_gemini(image_data))
            
            # Configure generation settings
            generation_config = genai.types.GenerationConfig(
                temperature=profile.temperature,
                max_output_tokens=profile.max_tokens,
            )
            
            # Get response from Gemini
            logger.info(f"Requesting response from {doctor_type.value} using Gemini")
            
            # Select appropriate model
            model = self.vision_model if image_data else self.text_model
            
            # Generate response
            response = await asyncio.to_thread(
                model.generate_content,
                content_parts,
                generation_config=generation_config
            )
            
            response_text = response.text
            processing_time = time.time() - start_time
            
            # Log successful response
            logger.info(f"Doctor {doctor_type.value} responded in {processing_time:.2f}s")
            
            return {
                "response": response_text,
                "doctor_type": doctor_type.value,
                "doctor_name": profile.name,
                "processing_time": processing_time,
                "confidence_score": 0.85,  # Can be calculated based on response
                "model_used": "gemini-2.0-flash-exp",
                "has_image": bool(image_data),
                "is_handover": is_handover
            }
            
        except Exception as e:
            logger.error(f"Error getting doctor response: {str(e)}")
            # Log the full traceback for debugging
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            processing_time = time.time() - start_time
            
            # Return a fallback response
            return {
                "response": "I apologize, but I'm experiencing technical difficulties. Please try again or consult another doctor.",
                "doctor_type": doctor_type.value,
                "doctor_name": profile.name if 'profile' in locals() else "Unknown",
                "processing_time": processing_time,
                "confidence_score": 0.0,
                "error": str(e)
            }
    
    async def create_handover_summary(
        self,
        from_doctor: str,
        to_doctor: DoctorType,
        conversation_history: List[Dict],
        handover_message: Optional[str] = None
    ) -> str:
        """
        Create a handover summary when switching doctors
        
        Args:
            from_doctor: Doctor handing over
            to_doctor: Doctor receiving
            conversation_history: Full conversation history
            handover_message: Optional message from user
            
        Returns:
            Handover summary text
        """
        try:
            # Create a summary of key points from conversation
            summary_prompt = get_case_summary_prompt(
                conversations=conversation_history,
                case_info={}  # Extract from conversation if needed
            )
            
            # Prepare prompt for Gemini
            full_prompt = f"You are a medical assistant creating a concise handover summary.\n\n{summary_prompt}"
            
            generation_config = genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=300,
            )
            
            response = await asyncio.to_thread(
                self.text_model.generate_content,
                full_prompt,
                generation_config=generation_config
            )
            
            summary = response.text
            
            # Add handover message if provided
            if handover_message:
                summary += f"\n\nPatient's handover request: {handover_message}"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creating handover summary: {str(e)}")
            return f"Handover from {from_doctor} to {to_doctor.value}. Previous conversation available for review."
    
    async def generate_case_report(
        self,
        case_info: dict,
        conversations: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive case report from all consultations
        
        Args:
            case_info: Case information
            conversations: All conversation history
            
        Returns:
            Dictionary with report sections
        """
        try:
            # Default report sections
            report_sections = [
                "chief_complaint",
                "history_of_present_illness",
                "physical_examination",
                "assessment_by_specialty",
                "diagnostic_recommendations",
                "treatment_plan",
                "follow_up_recommendations"
            ]
            
            # Generate report using Gemini
            report_prompt = get_report_generation_prompt(
                conversations=conversations,
                case_info=case_info,
                report_sections=report_sections
            )
            
            # Prepare prompt for Gemini
            full_prompt = f"You are a medical professional creating a comprehensive case report.\n\n{report_prompt}"
            
            generation_config = genai.types.GenerationConfig(
                temperature=0.1,  # Low temperature for factual report
                max_output_tokens=2000,
            )
            
            response = await asyncio.to_thread(
                self.text_model.generate_content,
                full_prompt,
                generation_config=generation_config
            )
            
            full_report = response.text
            
            # Extract contributing doctors
            contributing_doctors = []
            for conv in conversations:
                doctor = conv.get('doctor_type')
                if doctor and doctor not in contributing_doctors:
                    contributing_doctors.append(doctor)
            
            return {
                "full_report": full_report,
                "sections": self._parse_report_sections(full_report),
                "contributing_doctors": contributing_doctors,
                "total_consultations": len(conversations),
                "case_id": case_info.get('case_id'),
                "generated_by": "AI Medical Report Generator v1.0"
            }
            
        except Exception as e:
            logger.error(f"Error generating case report: {str(e)}")
            return {
                "full_report": "Report generation failed. Please try again.",
                "sections": {},
                "contributing_doctors": [],
                "error": str(e)
            }
    
    def _parse_report_sections(self, report_text: str) -> Dict[str, str]:
        """
        Parse report text into sections
        
        Args:
            report_text: Full report text
            
        Returns:
            Dictionary of report sections
        """
        sections = {}
        current_section = None
        current_content = []
        
        for line in report_text.split('\n'):
            # Check if line is a section header (starts with ##)
            if line.strip().startswith('##'):
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = line.strip('#').strip().lower().replace(' ', '_')
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    async def get_all_doctors_consultation(
        self,
        message: str,
        case_info: dict,
        context: List[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Get opinions from all three doctors simultaneously
        
        Args:
            message: User's message
            case_info: Case information
            context: Conversation context
            
        Returns:
            List of responses from all doctors
        """
        # Create tasks for all doctors
        tasks = []
        for doctor_type in [DoctorType.GENERAL, DoctorType.CARDIOLOGIST, DoctorType.BP_SPECIALIST]:
            task = self.get_doctor_response(
                doctor_type=doctor_type,
                message=message,
                case_info=case_info,
                context=context
            )
            tasks.append(task)
        
        # Execute all consultations in parallel
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process responses
        results = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(f"Error in parallel consultation: {str(response)}")
                results.append({
                    "error": str(response),
                    "doctor_type": list(DoctorType)[i].value
                })
            else:
                results.append(response)
        
        return results
    
    async def cleanup(self):
        """Cleanup resources including MCP client connection"""
        if self.mcp_client and self.mcp_client.connected:
            try:
                await self.mcp_client.disconnect()
                logger.info("MCP client disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting MCP client: {e}")
    
    async def validate_diagnosis_consensus(
        self,
        conversations: List[Dict]
    ) -> Dict[str, Any]:
        """
        Analyze conversations to find diagnostic consensus among doctors
        
        Args:
            conversations: Conversation history from multiple doctors
            
        Returns:
            Consensus analysis
        """
        try:
            # Group conversations by doctor
            doctor_opinions = {}
            for conv in conversations:
                doctor = conv.get('doctor_type', 'unknown')
                if doctor not in doctor_opinions:
                    doctor_opinions[doctor] = []
                doctor_opinions[doctor].append(conv.get('doctor_response', ''))
            
            # Create consensus analysis prompt
            consensus_prompt = f"""Analyze the following medical opinions from different specialists and identify:
1. Areas of agreement
2. Divergent opinions
3. Overall diagnostic consensus
4. Recommended unified treatment approach

Doctor Opinions:
{self._format_doctor_opinions(doctor_opinions)}

Provide a structured consensus analysis."""
            
            # Prepare prompt for Gemini
            full_prompt = f"You are a medical coordinator analyzing multiple specialist opinions.\n\n{consensus_prompt}"
            
            generation_config = genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=500,
            )
            
            response = await asyncio.to_thread(
                self.text_model.generate_content,
                full_prompt,
                generation_config=generation_config
            )
            
            return {
                "consensus_analysis": response.text,
                "doctors_consulted": list(doctor_opinions.keys()),
                "total_opinions": sum(len(ops) for ops in doctor_opinions.values())
            }
            
        except Exception as e:
            logger.error(f"Error in consensus analysis: {str(e)}")
            return {
                "consensus_analysis": "Unable to analyze consensus at this time.",
                "error": str(e)
            }
    
    def _format_doctor_opinions(self, doctor_opinions: Dict[str, List[str]]) -> str:
        """Format doctor opinions for consensus analysis"""
        formatted = []
        for doctor, opinions in doctor_opinions.items():
            formatted.append(f"\n{doctor.upper()}:")
            for i, opinion in enumerate(opinions[-3:], 1):  # Last 3 opinions
                formatted.append(f"Opinion {i}: {opinion[:200]}...")
        return '\n'.join(formatted)