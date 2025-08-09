"""
AI integration service for intelligent assistance in collaboration
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import asyncio
import json
import logging
from contextlib import asynccontextmanager
import base64
import os

# Import Google Generative AI
try:
    import google.generativeai as genai
except ImportError:
    genai = None
    logging.warning("google-generativeai not installed. AI features will be limited.")

from ..models import Message, AIAssistantContext, MessageType
from ..prompts.ai_assistant_prompt import (
    get_ai_assistant_prompt,
    get_diagnostic_suggestion_prompt,
    get_treatment_suggestion_prompt,
    get_summary_generation_prompt,
    get_action_item_extraction_prompt,
    get_medical_context_prompt
)
from ..config import settings

logger = logging.getLogger(__name__)


class AIIntegrationService:
    """Service for AI-powered assistance in collaboration rooms with Gemini integration"""
    
    def __init__(self, ai_client=None, db_client=None):
        # Initialize Gemini if API key is available
        if genai and settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-pro')
            self.vision_model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini AI initialized successfully")
        else:
            self.gemini_model = None
            self.vision_model = None
            logger.warning("Gemini AI not initialized. Check API key configuration.")
        
        self.ai_client = ai_client or self.gemini_model
        self.db_client = db_client
        
        # Store AI contexts for active rooms
        self._ai_contexts: Dict[str, AIAssistantContext] = {}
        
        # Rate limiting
        self._rate_limits: Dict[str, Dict[str, Any]] = {}
        self._rate_limit_window = 60  # seconds
        self._rate_limit_max_requests = 10  # per window
        
        # Session summaries cache
        self._session_summaries: Dict[str, Dict[str, Any]] = {}
    
    async def initialize_session(
        self,
        room_id: str,
        subject: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Initialize AI session for a teaching room with medical education context"""
        medical_context = {
            "session_type": "medical_education",
            "subject": subject,
            "timestamp": datetime.utcnow().isoformat(),
            "language": context.get("language", "en") if context else "en",
            "education_level": context.get("education_level", "medical_student") if context else "medical_student",
            "specialization": context.get("specialization", "general") if context else "general"
        }
        
        if context:
            medical_context.update(context)
        
        ai_context = AIAssistantContext(
            room_id=room_id,
            medical_context=medical_context,
            ai_enabled=True
        )
        
        self._ai_contexts[room_id] = ai_context
        
        # Initialize session summary
        self._session_summaries[room_id] = {
            "subject": subject,
            "started_at": datetime.utcnow().isoformat(),
            "qa_pairs": [],
            "key_concepts": [],
            "references": []
        }
        
        logger.info(f"Initialized AI session for room {room_id} with subject: {subject}")
        
        return {
            "status": "initialized",
            "room_id": room_id,
            "subject": subject,
            "context": medical_context
        }
    
    async def initialize_ai_context(
        self,
        room_id: str,
        active_case_id: Optional[str] = None,
        medical_context: Optional[Dict[str, Any]] = None
    ) -> AIAssistantContext:
        """Initialize AI context for a room (backward compatibility)"""
        context = AIAssistantContext(
            room_id=room_id,
            active_case_id=active_case_id,
            medical_context=medical_context or {},
            ai_enabled=True
        )
        
        self._ai_contexts[room_id] = context
        return context
    
    async def get_ai_context(self, room_id: str) -> Optional[AIAssistantContext]:
        """Get AI context for a room"""
        return self._ai_contexts.get(room_id)
    
    async def update_conversation_history(
        self,
        room_id: str,
        message: Message
    ):
        """Update conversation history in AI context"""
        context = self._ai_contexts.get(room_id)
        if not context:
            context = await self.initialize_ai_context(room_id)
        
        # Keep last 50 messages for context
        context.conversation_history.append(message)
        if len(context.conversation_history) > 50:
            context.conversation_history = context.conversation_history[-50:]
    
    async def get_ai_suggestions(
        self,
        room_id: str,
        query: str,
        suggestion_type: str = "general"
    ) -> Dict[str, Any]:
        """Get AI suggestions based on conversation context"""
        context = self._ai_contexts.get(room_id)
        if not context or not context.ai_enabled:
            return {"suggestions": [], "error": "AI not enabled for this room"}
        
        # Prepare prompt based on context
        prompt = await self._prepare_ai_prompt(
            context=context,
            query=query,
            suggestion_type=suggestion_type
        )
        
        # Call AI service (placeholder for actual AI integration)
        if self.ai_client:
            try:
                response = await self.ai_client.generate(prompt)
                suggestions = await self._parse_ai_response(response)
            except Exception as e:
                return {"suggestions": [], "error": str(e)}
        else:
            # Mock response for demonstration
            suggestions = await self._generate_mock_suggestions(suggestion_type)
        
        # Store suggestions in context
        suggestion_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": suggestion_type,
            "query": query,
            "suggestions": suggestions
        }
        context.ai_suggestions.append(suggestion_entry)
        
        return {
            "suggestions": suggestions,
            "timestamp": suggestion_entry["timestamp"]
        }
    
    async def analyze_conversation(
        self,
        room_id: str
    ) -> Dict[str, Any]:
        """Analyze conversation for key insights"""
        context = self._ai_contexts.get(room_id)
        if not context or not context.conversation_history:
            return {"analysis": {}, "error": "No conversation history"}
        
        # Analyze conversation patterns
        analysis = {
            "message_count": len(context.conversation_history),
            "participants": list(set(m.sender_id for m in context.conversation_history)),
            "topics": await self._extract_topics(context.conversation_history),
            "sentiment": await self._analyze_sentiment(context.conversation_history),
            "key_decisions": await self._extract_decisions(context.conversation_history),
            "action_items": await self._extract_action_items(context.conversation_history)
        }
        
        return {"analysis": analysis}
    
    async def generate_summary(
        self,
        room_id: str
    ) -> Dict[str, Any]:
        """Generate conversation summary"""
        context = self._ai_contexts.get(room_id)
        if not context or not context.conversation_history:
            return {"summary": "", "error": "No conversation history"}
        
        # Generate summary using AI
        if self.ai_client:
            prompt = await self._prepare_summary_prompt(context)
            try:
                summary = await self.ai_client.generate(prompt)
            except Exception as e:
                return {"summary": "", "error": str(e)}
        else:
            # Mock summary
            summary = await self._generate_mock_summary(context)
        
        return {
            "summary": summary,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def suggest_next_steps(
        self,
        room_id: str,
        case_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Suggest next steps based on conversation"""
        context = self._ai_contexts.get(room_id)
        if not context:
            return []
        
        # Update medical context if provided
        if case_context:
            context.medical_context.update(case_context)
        
        # Generate next steps suggestions
        next_steps = []
        
        # Analyze conversation for medical decisions
        if "diagnosis" in str(context.conversation_history):
            next_steps.append({
                "type": "diagnostic",
                "action": "Order recommended tests",
                "priority": "high",
                "details": "Based on discussed symptoms, consider ordering CBC, metabolic panel"
            })
        
        if "treatment" in str(context.conversation_history):
            next_steps.append({
                "type": "treatment",
                "action": "Initiate treatment plan",
                "priority": "medium",
                "details": "Document treatment decisions and create care plan"
            })
        
        if "follow-up" in str(context.conversation_history):
            next_steps.append({
                "type": "follow-up",
                "action": "Schedule follow-up consultation",
                "priority": "medium",
                "details": "Recommend follow-up in 2-4 weeks to assess treatment response"
            })
        
        return next_steps
    
    async def toggle_ai_assistance(
        self,
        room_id: str,
        enabled: bool
    ) -> bool:
        """Toggle AI assistance for a room"""
        context = self._ai_contexts.get(room_id)
        if not context:
            return False
        
        context.ai_enabled = enabled
        return True
    
    async def process_question(
        self,
        room_id: str,
        user_id: str,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a student question with context-aware AI response"""
        # Check rate limiting
        if not await self._check_rate_limit(room_id, user_id):
            return {
                "error": "Rate limit exceeded. Please wait before asking another question.",
                "retry_after": self._rate_limit_window
            }
        
        ai_context = self._ai_contexts.get(room_id)
        if not ai_context or not ai_context.ai_enabled:
            return {"error": "AI not enabled for this room"}
        
        try:
            # Get conversation history for context
            history = [f"{m.sender_name}: {m.content}" for m in ai_context.conversation_history[-20:]]
            
            # Get AI response
            response = await self.get_ai_response(
                question=question,
                context={
                    **ai_context.medical_context,
                    **(context or {}),
                    "user_id": user_id,
                    "room_id": room_id
                },
                history=history
            )
            
            # Save Q&A to session
            await self.save_qa_history(room_id, question, response["answer"])
            
            # Create AI message
            ai_message = Message(
                message_id=f"ai_{datetime.utcnow().timestamp()}",
                room_id=room_id,
                sender_id="ai_assistant",
                sender_name="AI Medical Assistant",
                content=response["answer"],
                message_type=MessageType.AI_RESPONSE,
                metadata={
                    "question": question,
                    "user_id": user_id,
                    "references": response.get("references", [])
                }
            )
            
            # Update conversation history
            await self.update_conversation_history(room_id, ai_message)
            
            return {
                "success": True,
                "response": response,
                "message": ai_message.dict()
            }
            
        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            return {
                "error": "Failed to process question",
                "details": str(e)
            }
    
    async def get_ai_response(
        self,
        question: str,
        context: Dict[str, Any],
        history: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get AI response from Gemini with medical education context"""
        if not self.gemini_model:
            return await self._get_fallback_response(question, context)
        
        try:
            # Prepare the prompt
            prompt = self._prepare_education_prompt(question, context, history)
            
            # Generate response
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.gemini_model.generate_content(prompt)
            )
            
            # Extract and structure the response
            answer = response.text
            
            # Extract references if present
            references = self._extract_references(answer)
            
            # Extract key concepts
            concepts = self._extract_concepts(answer)
            
            return {
                "answer": answer,
                "references": references,
                "concepts": concepts,
                "model": "gemini-1.5-pro",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return await self._get_fallback_response(question, context)
    
    async def stream_response(
        self,
        room_id: str,
        user_id: str,
        question: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream AI responses for real-time interaction"""
        # Check rate limiting
        if not await self._check_rate_limit(room_id, user_id):
            yield {
                "type": "error",
                "content": "Rate limit exceeded. Please wait before asking another question."
            }
            return
        
        ai_context = self._ai_contexts.get(room_id)
        if not ai_context or not ai_context.ai_enabled:
            yield {"type": "error", "content": "AI not enabled for this room"}
            return
        
        if not self.gemini_model:
            yield {"type": "error", "content": "AI model not available"}
            return
        
        try:
            # Prepare prompt
            history = [f"{m.sender_name}: {m.content}" for m in ai_context.conversation_history[-20:]]
            prompt = self._prepare_education_prompt(question, ai_context.medical_context, history)
            
            # Stream response
            response_stream = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.gemini_model.generate_content(prompt, stream=True)
            )
            
            full_response = ""
            
            # Yield start event
            yield {
                "type": "start",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Stream chunks
            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    yield {
                        "type": "chunk",
                        "content": chunk.text
                    }
            
            # Save Q&A history
            await self.save_qa_history(room_id, question, full_response)
            
            # Yield completion event
            yield {
                "type": "complete",
                "full_response": full_response,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            yield {
                "type": "error",
                "content": f"Failed to stream response: {str(e)}"
            }
    
    async def save_qa_history(
        self,
        room_id: str,
        question: str,
        answer: str
    ) -> None:
        """Save Q&A pair for later reference"""
        if room_id not in self._session_summaries:
            self._session_summaries[room_id] = {
                "qa_pairs": [],
                "key_concepts": [],
                "references": []
            }
        
        qa_pair = {
            "question": question,
            "answer": answer,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self._session_summaries[room_id]["qa_pairs"].append(qa_pair)
        
        # Extract and save concepts and references
        concepts = self._extract_concepts(answer)
        references = self._extract_references(answer)
        
        self._session_summaries[room_id]["key_concepts"].extend(concepts)
        self._session_summaries[room_id]["references"].extend(references)
        
        # Keep unique concepts and references
        self._session_summaries[room_id]["key_concepts"] = list(
            set(self._session_summaries[room_id]["key_concepts"])
        )
        self._session_summaries[room_id]["references"] = list(
            set(tuple(ref.items()) for ref in references) if isinstance(ref, dict) else ref
            for ref in self._session_summaries[room_id]["references"]
        )
    
    async def get_session_summary(
        self,
        room_id: str
    ) -> Dict[str, Any]:
        """Generate comprehensive summary of Q&A session"""
        summary_data = self._session_summaries.get(room_id, {})
        
        if not summary_data or not summary_data.get("qa_pairs"):
            return {
                "error": "No session data available",
                "room_id": room_id
            }
        
        try:
            # Use AI to generate a comprehensive summary
            if self.gemini_model:
                prompt = f"""
                Generate a comprehensive summary of this medical education session:
                
                Subject: {summary_data.get('subject', 'Unknown')}
                Number of Q&A pairs: {len(summary_data.get('qa_pairs', []))}
                
                Q&A History:
                {self._format_qa_pairs(summary_data.get('qa_pairs', []))}
                
                Please provide:
                1. Session Overview
                2. Key Topics Discussed
                3. Important Medical Concepts Covered
                4. Common Questions and Themes
                5. Recommended Follow-up Topics
                6. Additional Resources for Students
                
                Format the summary in a clear, educational manner suitable for medical students.
                """
                
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.gemini_model.generate_content(prompt)
                )
                
                ai_summary = response.text
            else:
                ai_summary = "AI summary not available"
            
            return {
                "room_id": room_id,
                "subject": summary_data.get("subject", "Unknown"),
                "started_at": summary_data.get("started_at"),
                "ended_at": datetime.utcnow().isoformat(),
                "total_questions": len(summary_data.get("qa_pairs", [])),
                "key_concepts": summary_data.get("key_concepts", []),
                "references": summary_data.get("references", []),
                "ai_summary": ai_summary,
                "qa_pairs": summary_data.get("qa_pairs", [])
            }
            
        except Exception as e:
            logger.error(f"Error generating session summary: {str(e)}")
            return {
                "error": "Failed to generate summary",
                "details": str(e),
                "basic_summary": summary_data
            }
    
    async def analyze_medical_image(
        self,
        room_id: str,
        image_data: str,  # base64 encoded image
        question: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze medical images using Gemini Vision model"""
        if not self.vision_model:
            return {"error": "Vision model not available"}
        
        ai_context = self._ai_contexts.get(room_id)
        if not ai_context or not ai_context.ai_enabled:
            return {"error": "AI not enabled for this room"}
        
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            
            # Prepare prompt
            prompt = f"""
            You are a medical AI assistant helping with medical education.
            Analyze this medical image and provide educational insights.
            
            Context: {ai_context.medical_context.get('subject', 'Medical Education')}
            
            {f"Specific question: {question}" if question else "Please describe what you see in this medical image and explain its clinical significance."}
            
            Provide:
            1. Description of what is visible in the image
            2. Clinical significance
            3. Key features to note for students
            4. Potential differential diagnoses (if applicable)
            5. Educational points
            
            Remember to maintain a teaching perspective suitable for medical students.
            """
            
            # Generate response
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.vision_model.generate_content([prompt, image_bytes])
            )
            
            return {
                "success": True,
                "analysis": response.text,
                "model": "gemini-1.5-flash",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Image analysis error: {str(e)}")
            return {
                "error": "Failed to analyze image",
                "details": str(e)
            }
    
    # Private helper methods
    
    async def _prepare_ai_prompt(
        self,
        context: AIAssistantContext,
        query: str,
        suggestion_type: str
    ) -> str:
        """Prepare AI prompt based on context"""
        return get_ai_assistant_prompt(
            conversation_history=[m.content for m in context.conversation_history[-10:]],
            medical_context=context.medical_context,
            query=query,
            suggestion_type=suggestion_type
        )
    
    async def _prepare_summary_prompt(
        self,
        context: AIAssistantContext
    ) -> str:
        """Prepare prompt for generating summary"""
        messages = [f"{m.sender_name}: {m.content}" for m in context.conversation_history]
        return f"Summarize this medical consultation:\n\n" + "\n".join(messages)
    
    async def _parse_ai_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse AI response into structured suggestions"""
        # Implementation would depend on AI response format
        return []
    
    async def _generate_mock_suggestions(
        self,
        suggestion_type: str
    ) -> List[Dict[str, Any]]:
        """Generate mock suggestions for demonstration"""
        if suggestion_type == "diagnostic":
            return [
                {
                    "type": "test",
                    "name": "Complete Blood Count (CBC)",
                    "rationale": "To assess overall health and detect various disorders"
                },
                {
                    "type": "test",
                    "name": "Basic Metabolic Panel",
                    "rationale": "To evaluate kidney function and electrolyte balance"
                }
            ]
        elif suggestion_type == "treatment":
            return [
                {
                    "type": "medication",
                    "name": "Consider appropriate medication",
                    "rationale": "Based on symptoms and medical history"
                }
            ]
        else:
            return [
                {
                    "type": "general",
                    "suggestion": "Consider patient's medical history",
                    "rationale": "Important for comprehensive assessment"
                }
            ]
    
    async def _generate_mock_summary(
        self,
        context: AIAssistantContext
    ) -> str:
        """Generate mock summary for demonstration"""
        participant_count = len(context.participant_roles)
        message_count = len(context.conversation_history)
        
        return f"""Medical Consultation Summary:
        
Participants: {participant_count} healthcare professionals
Messages exchanged: {message_count}

Key Discussion Points:
- Patient symptoms and history reviewed
- Diagnostic options discussed
- Treatment plan considerations
- Follow-up recommendations made

This is a mock summary. In production, AI would analyze actual conversation content."""
    
    async def _extract_topics(
        self,
        messages: List[Message]
    ) -> List[str]:
        """Extract main topics from conversation"""
        # Simple keyword extraction for demonstration
        topics = set()
        keywords = ["diagnosis", "treatment", "symptoms", "medication", "test", "procedure"]
        
        for message in messages:
            content_lower = message.content.lower()
            for keyword in keywords:
                if keyword in content_lower:
                    topics.add(keyword)
        
        return list(topics)
    
    async def _analyze_sentiment(
        self,
        messages: List[Message]
    ) -> Dict[str, float]:
        """Analyze conversation sentiment"""
        # Mock sentiment analysis
        return {
            "positive": 0.7,
            "neutral": 0.2,
            "negative": 0.1
        }
    
    async def _extract_decisions(
        self,
        messages: List[Message]
    ) -> List[str]:
        """Extract key decisions from conversation"""
        decisions = []
        decision_keywords = ["decided", "will", "plan to", "agreed", "recommend"]
        
        for message in messages:
            content_lower = message.content.lower()
            for keyword in decision_keywords:
                if keyword in content_lower:
                    decisions.append(message.content[:100] + "...")
                    break
        
        return decisions[:5]  # Return top 5 decisions
    
    async def _extract_action_items(
        self,
        messages: List[Message]
    ) -> List[str]:
        """Extract action items from conversation"""
        action_items = []
        action_keywords = ["todo", "action", "follow up", "schedule", "order", "prescribe"]
        
        for message in messages:
            content_lower = message.content.lower()
            for keyword in action_keywords:
                if keyword in content_lower:
                    action_items.append(message.content[:100] + "...")
                    break
        
        return action_items[:5]  # Return top 5 action items
    
    async def handle_voice_query(
        self,
        room_id: str,
        user_id: str,
        audio_data: str  # base64 encoded audio
    ) -> Dict[str, Any]:
        """Process voice questions by transcribing and then processing as text"""
        # Check rate limiting
        if not await self._check_rate_limit(room_id, user_id):
            return {
                "error": "Rate limit exceeded. Please wait before asking another question.",
                "retry_after": self._rate_limit_window
            }
        
        ai_context = self._ai_contexts.get(room_id)
        if not ai_context or not ai_context.ai_enabled:
            return {"error": "AI not enabled for this room"}
        
        try:
            # Transcribe audio using Gemini or fallback service
            transcription = await self._transcribe_audio(audio_data)
            
            if not transcription.get("success"):
                return {
                    "error": "Failed to transcribe audio",
                    "details": transcription.get("error")
                }
            
            # Process the transcribed text as a regular question
            result = await self.process_question(
                room_id=room_id,
                user_id=user_id,
                question=transcription["text"],
                context={"source": "voice", "original_audio": True}
            )
            
            # Add transcription info to result
            if result.get("success"):
                result["transcription"] = {
                    "text": transcription["text"],
                    "confidence": transcription.get("confidence", 1.0),
                    "language": transcription.get("language", "en")
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing voice query: {str(e)}")
            return {
                "error": "Failed to process voice query",
                "details": str(e)
            }
    
    async def get_subject_specific_prompt(
        self,
        subject: str,
        education_level: str = "medical_student"
    ) -> str:
        """Get subject-specific AI prompts for different medical topics"""
        prompts = {
            "anatomy": f"""
            You are an expert anatomy professor teaching {education_level}s.
            Focus on:
            - Clear anatomical descriptions with spatial relationships
            - Clinical correlations and relevance
            - Common anatomical variations
            - High-yield exam topics
            - Visual descriptions when helpful
            Use standard anatomical terminology and reference common mnemonics.
            """,
            
            "physiology": f"""
            You are an expert physiology professor teaching {education_level}s.
            Focus on:
            - Mechanisms and processes
            - Cause-and-effect relationships
            - Integration between systems
            - Clinical applications
            - Common pathophysiological states
            Explain complex concepts step-by-step.
            """,
            
            "pathology": f"""
            You are an expert pathology professor teaching {education_level}s.
            Focus on:
            - Disease mechanisms and progression
            - Gross and microscopic features
            - Differential diagnoses
            - Clinical-pathological correlations
            - Key diagnostic features
            Include relevant staging and grading systems.
            """,
            
            "pharmacology": f"""
            You are an expert pharmacology professor teaching {education_level}s.
            Focus on:
            - Drug mechanisms of action
            - Indications and contraindications
            - Side effects and interactions
            - Dosing principles
            - Clinical pearls
            Emphasize high-yield drugs and common clinical scenarios.
            """,
            
            "clinical_medicine": f"""
            You are an experienced clinician educator teaching {education_level}s.
            Focus on:
            - Clinical reasoning and approach
            - History taking and physical examination
            - Diagnostic workup
            - Evidence-based management
            - Patient safety considerations
            Use case-based examples when appropriate.
            """,
            
            "medical_ethics": f"""
            You are a medical ethics expert teaching {education_level}s.
            Focus on:
            - Ethical principles (autonomy, beneficence, non-maleficence, justice)
            - Informed consent
            - Confidentiality and privacy
            - End-of-life issues
            - Professional boundaries
            Use real-world scenarios to illustrate concepts.
            """,
            
            "research_methods": f"""
            You are a medical research expert teaching {education_level}s.
            Focus on:
            - Study design and methodology
            - Statistical concepts and interpretation
            - Evidence-based medicine principles
            - Critical appraisal skills
            - Research ethics
            Explain concepts with practical examples.
            """,
            
            "general_medical": f"""
            You are a comprehensive medical educator teaching {education_level}s.
            Provide clear, accurate, and educational responses about medical topics.
            Adapt your explanation level to the audience and encourage learning.
            Use evidence-based information and cite sources when relevant.
            """
        }
        
        # Get the specific prompt or fall back to general
        base_prompt = prompts.get(subject.lower(), prompts["general_medical"])
        
        # Add general teaching guidelines
        teaching_guidelines = """
        
        Teaching Guidelines:
        1. Start with the basics and build complexity
        2. Use analogies and examples to clarify concepts
        3. Highlight clinically relevant points
        4. Encourage critical thinking
        5. Address common misconceptions
        6. Provide memory aids when helpful
        7. Be encouraging and supportive
        
        Remember: You're here to facilitate learning, not just provide information.
        """
        
        return base_prompt + teaching_guidelines
    
    async def process_ai_query(
        self,
        room_id: str,
        user_id: str,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process student questions with contextual AI responses"""
        # This is an alias for process_question for backward compatibility
        return await self.process_question(room_id, user_id, query, context)
    
    async def get_session_context(
        self,
        room_id: str
    ) -> Dict[str, Any]:
        """Get teaching session context including subject and participant info"""
        ai_context = self._ai_contexts.get(room_id)
        if not ai_context:
            return {
                "error": "No active session found",
                "room_id": room_id
            }
        
        session_summary = self._session_summaries.get(room_id, {})
        
        return {
            "room_id": room_id,
            "subject": ai_context.medical_context.get("subject", "Unknown"),
            "session_type": ai_context.medical_context.get("session_type", "medical_education"),
            "language": ai_context.medical_context.get("language", "en"),
            "education_level": ai_context.medical_context.get("education_level", "medical_student"),
            "specialization": ai_context.medical_context.get("specialization", "general"),
            "started_at": session_summary.get("started_at"),
            "total_questions": len(session_summary.get("qa_pairs", [])),
            "key_concepts_discussed": session_summary.get("key_concepts", [])[:10],
            "ai_enabled": ai_context.ai_enabled,
            "participants": len(ai_context.participant_roles)
        }
    
    async def generate_ai_response(
        self,
        query: str,
        context: Dict[str, Any],
        subject: str
    ) -> Dict[str, Any]:
        """Generate AI response with subject-specific context"""
        # Get subject-specific prompt
        education_level = context.get("education_level", "medical_student")
        subject_prompt = await self.get_subject_specific_prompt(subject, education_level)
        
        # Add the subject prompt to context
        enhanced_context = {
            **context,
            "subject": subject,
            "subject_prompt": subject_prompt
        }
        
        # Get conversation history if available
        room_id = context.get("room_id")
        history = []
        if room_id:
            ai_context = self._ai_contexts.get(room_id)
            if ai_context:
                history = [f"{m.sender_name}: {m.content}" for m in ai_context.conversation_history[-20:]]
        
        # Generate response using the main method
        return await self.get_ai_response(query, enhanced_context, history)
    
    async def initialize_gemini_client(self) -> bool:
        """Initialize or reinitialize Gemini API client"""
        try:
            if genai and settings.gemini_api_key:
                genai.configure(api_key=settings.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-1.5-pro')
                self.vision_model = genai.GenerativeModel('gemini-1.5-flash')
                self.ai_client = self.gemini_model
                logger.info("Gemini AI client initialized successfully")
                return True
            else:
                logger.warning("Cannot initialize Gemini: Missing API key or library")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            return False
    
    def _prepare_education_prompt(
        self,
        question: str,
        context: Dict[str, Any],
        history: Optional[List[str]] = None
    ) -> str:
        """Prepare prompt for educational context"""
        subject = context.get("subject", "general medical topics")
        education_level = context.get("education_level", "medical student")
        language = context.get("language", "en")
        
        # Check if we have a subject-specific prompt in context
        if "subject_prompt" in context:
            base_prompt = context["subject_prompt"]
        else:
            base_prompt = f"""You are an AI Medical Education Assistant helping with teaching about {subject}.
        
Education Level: {education_level}"""
        
        prompt = base_prompt + f"\n\nLanguage: Please respond in {language}\n"
        
        if history:
            prompt += "\nRecent Discussion:\n"
            prompt += "\n".join(history[-10:])
            prompt += "\n\n"
        
        prompt += f"""Student Question: {question}

Please provide a comprehensive educational response that:
1. Directly answers the question
2. Provides relevant medical context
3. Includes clinical correlations when appropriate
4. Uses appropriate terminology for the education level
5. Cites key references or guidelines when relevant
6. Encourages further learning

Important: Maintain an educational tone and encourage critical thinking."""
        
        # Add language-specific instructions for non-English responses
        if language != "en":
            language_names = {
                "es": "Spanish",
                "fr": "French",
                "de": "German",
                "ja": "Japanese",
                "zh": "Chinese",
                "pt": "Portuguese",
                "it": "Italian",
                "ru": "Russian",
                "ko": "Korean",
                "ar": "Arabic",
                "hi": "Hindi"
            }
            lang_name = language_names.get(language, language)
            prompt += f"\n\nIMPORTANT: Provide your entire response in {lang_name}. Use medical terminology appropriate for that language."
        
        return prompt
    
    async def _check_rate_limit(
        self,
        room_id: str,
        user_id: str
    ) -> bool:
        """Check if user has exceeded rate limit"""
        current_time = datetime.utcnow()
        user_key = f"{room_id}:{user_id}"
        
        if user_key not in self._rate_limits:
            self._rate_limits[user_key] = {
                "requests": [],
                "last_reset": current_time
            }
        
        user_limits = self._rate_limits[user_key]
        
        # Clean old requests
        cutoff_time = current_time.timestamp() - self._rate_limit_window
        user_limits["requests"] = [
            req_time for req_time in user_limits["requests"]
            if req_time > cutoff_time
        ]
        
        # Check if limit exceeded
        if len(user_limits["requests"]) >= self._rate_limit_max_requests:
            return False
        
        # Add current request
        user_limits["requests"].append(current_time.timestamp())
        return True
    
    async def _transcribe_audio(
        self,
        audio_data: str
    ) -> Dict[str, Any]:
        """Transcribe audio data to text"""
        try:
            # For now, return a mock transcription
            # In production, this would use a speech-to-text service
            # Options: Google Speech-to-Text, OpenAI Whisper, etc.
            
            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_data)
            
            # Mock transcription result
            return {
                "success": True,
                "text": "What are the main differences between systolic and diastolic heart failure?",
                "confidence": 0.95,
                "language": "en",
                "duration": 3.5
            }
            
            # Production implementation would be:
            # if self.gemini_model:
            #     # Use Gemini's audio capabilities if available
            #     response = await self._transcribe_with_gemini(audio_bytes)
            # else:
            #     # Fallback to other service
            #     response = await self._transcribe_with_fallback(audio_bytes)
            # return response
            
        except Exception as e:
            logger.error(f"Audio transcription error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_qa_pairs(
        self,
        qa_pairs: List[Dict[str, Any]]
    ) -> str:
        """Format Q&A pairs for prompt"""
        formatted = []
        for i, qa in enumerate(qa_pairs, 1):
            formatted.append(f"\nQ{i}: {qa['question']}\nA{i}: {qa['answer'][:200]}...")
        return "\n".join(formatted)
    
    def _extract_concepts(
        self,
        text: str
    ) -> List[str]:
        """Extract key medical concepts from text"""
        # Simple keyword extraction - in production would use NLP
        medical_terms = [
            "diagnosis", "treatment", "symptoms", "pathophysiology",
            "medication", "procedure", "anatomy", "physiology",
            "etiology", "prognosis", "differential", "complication",
            "indication", "contraindication", "side effect", "mechanism"
        ]
        
        concepts = []
        text_lower = text.lower()
        
        for term in medical_terms:
            if term in text_lower:
                concepts.append(term)
        
        # Extract specific medical terms mentioned
        # This is a simplified version - production would use medical NER
        if "heart failure" in text_lower:
            concepts.append("heart failure")
        if "diabetes" in text_lower:
            concepts.append("diabetes")
        if "hypertension" in text_lower:
            concepts.append("hypertension")
        
        return list(set(concepts))[:10]
    
    def _extract_references(
        self,
        text: str
    ) -> List[Dict[str, str]]:
        """Extract references from AI response"""
        references = []
        
        # Look for common reference patterns
        # This is simplified - production would use regex or NLP
        if "according to" in text.lower():
            references.append({
                "type": "guideline",
                "source": "Clinical guidelines mentioned in response"
            })
        
        if "study" in text.lower() or "research" in text.lower():
            references.append({
                "type": "research",
                "source": "Research studies referenced"
            })
        
        if "recommend" in text.lower():
            references.append({
                "type": "recommendation",
                "source": "Clinical recommendations"
            })
        
        return references
    
    async def _get_fallback_response(
        self,
        question: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Provide fallback response when AI is not available"""
        subject = context.get("subject", "medical topic")
        
        return {
            "answer": f"""I understand you're asking about: {question}

While I cannot provide a detailed AI-generated response at this moment, here are some general points about {subject}:

1. This is an important topic in medical education
2. Consider reviewing your course materials and textbooks
3. Discuss with your instructor for detailed clarification
4. Look for peer-reviewed resources and clinical guidelines

For the best learning experience, I recommend:
- Breaking down complex concepts into smaller parts
- Using visual aids and diagrams when possible
- Practicing with clinical cases
- Collaborating with peers for discussion

Please try again later for AI-powered assistance.""",
            "references": [],
            "concepts": [subject],
            "model": "fallback",
            "timestamp": datetime.utcnow().isoformat()
        }