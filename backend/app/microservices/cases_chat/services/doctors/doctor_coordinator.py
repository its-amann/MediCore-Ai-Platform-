"""
Doctor service coordinator for managing multiple AI doctor services
"""
from typing import Dict, Any, Optional, List, AsyncGenerator
import asyncio
import logging
from datetime import datetime
from .doctor_factory import DoctorServiceFactory
from ..base.doctor_service_base import BaseDoctorService
from ...models.case_models import CaseData
from ...models.chat_models import ChatMessage
from ...core.config import settings
from ...core.exceptions import DoctorServiceError

logger = logging.getLogger(__name__)


class DoctorCoordinator:
    """Coordinates multiple doctor services with fallback and load balancing"""
    
    def __init__(self):
        self.factory = DoctorServiceFactory
        self.active_sessions: Dict[str, str] = {}  # case_id -> service_type mapping
        self.service_stats: Dict[str, Dict[str, Any]] = {}  # Track service performance
        self.initialized = False
    
    async def initialize(self) -> None:
        """Initialize the coordinator and all doctor services"""
        if self.initialized:
            return
        
        logger.info("Initializing doctor coordinator...")
        
        # Initialize factory and all services
        await self.factory.initialize()
        
        # Initialize stats for each service
        for service_type in self.factory.get_available_doctors():
            self.service_stats[service_type] = {
                "requests": 0,
                "successes": 0,
                "failures": 0,
                "total_response_time": 0,
                "average_response_time": 0,
                "last_error": None,
                "last_success": None
            }
        
        self.initialized = True
        logger.info("Doctor coordinator initialized")
    
    async def get_response(
        self,
        case_data: CaseData,
        chat_history: List[ChatMessage],
        prompt: str,
        preferred_service: Optional[str] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Get response from doctor service with automatic fallback
        
        Args:
            case_data: The medical case data
            chat_history: Previous conversation messages
            prompt: User's prompt
            preferred_service: Preferred service type
            stream: Whether to stream the response
            
        Returns:
            Response dictionary with content and metadata
        """
        if not self.initialized:
            await self.initialize()
        
        # Determine which service to use
        service_type = preferred_service or self.active_sessions.get(case_data.id)
        if not service_type:
            service_type = settings.default_ai_provider
        
        # Try to get response with fallback
        attempted_services = []
        last_error = None
        
        while service_type:
            try:
                doctor = await self.factory.create_doctor(service_type)
                if not doctor:
                    raise DoctorServiceError(f"Failed to create {service_type} doctor")
                
                # Record start time
                start_time = datetime.utcnow()
                
                # Get response based on whether streaming is requested
                if stream:
                    # For streaming, we'll collect the full response
                    response_content = ""
                    async for chunk in self._stream_response(doctor, case_data, chat_history, prompt):
                        response_content += chunk
                else:
                    # Build full prompt with context
                    full_prompt = self._build_full_prompt(doctor, case_data, chat_history, prompt)
                    response_content = await doctor.diagnose_case(case_data, chat_history)
                
                # Record success
                response_time = (datetime.utcnow() - start_time).total_seconds()
                self._record_success(service_type, response_time)
                
                # Update active session
                self.active_sessions[case_data.id] = service_type
                
                # Get confidence score
                confidence = await doctor.get_confidence_score(response_content, case_data)
                
                # Format response
                return {
                    "content": response_content,
                    "service": service_type,
                    "model": doctor.model_name,
                    "confidence": confidence,
                    "response_time": response_time,
                    "metadata": {
                        "attempted_services": attempted_services,
                        "fallback_used": len(attempted_services) > 1
                    }
                }
                
            except Exception as e:
                logger.error(f"Error with {service_type} doctor: {e}")
                last_error = e
                attempted_services.append(service_type)
                self._record_failure(service_type, str(e))
                
                # Try fallback if enabled
                if settings.enable_doctor_fallback:
                    service_type = await self._get_next_service(attempted_services)
                else:
                    break
        
        # All services failed
        error_msg = f"All doctor services failed. Last error: {last_error}"
        logger.error(error_msg)
        raise DoctorServiceError(
            error_msg,
            {
                "attempted_services": attempted_services,
                "last_error": str(last_error)
            }
        )
    
    async def stream_response(
        self,
        case_data: CaseData,
        chat_history: List[ChatMessage],
        prompt: str,
        preferred_service: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream response from doctor service
        
        Args:
            case_data: The medical case data
            chat_history: Previous conversation messages
            prompt: User's prompt
            preferred_service: Preferred service type
            
        Yields:
            Response chunks with metadata
        """
        if not self.initialized:
            await self.initialize()
        
        # Determine which service to use
        service_type = preferred_service or self.active_sessions.get(case_data.id)
        if not service_type:
            service_type = settings.default_ai_provider
        
        # Try to stream with fallback
        attempted_services = []
        
        while service_type:
            try:
                doctor = await self.factory.create_doctor(service_type)
                if not doctor:
                    raise DoctorServiceError(f"Failed to create {service_type} doctor")
                
                # Start streaming
                start_time = datetime.utcnow()
                full_response = ""
                
                async for chunk in self._stream_response(doctor, case_data, chat_history, prompt):
                    full_response += chunk
                    yield {
                        "chunk": chunk,
                        "service": service_type,
                        "model": doctor.model_name
                    }
                
                # Record success after streaming completes
                response_time = (datetime.utcnow() - start_time).total_seconds()
                self._record_success(service_type, response_time)
                self.active_sessions[case_data.id] = service_type
                
                # Send final metadata
                confidence = await doctor.get_confidence_score(full_response, case_data)
                yield {
                    "chunk": "",
                    "done": True,
                    "service": service_type,
                    "model": doctor.model_name,
                    "confidence": confidence,
                    "response_time": response_time,
                    "metadata": {
                        "attempted_services": attempted_services,
                        "fallback_used": len(attempted_services) > 1
                    }
                }
                
                return
                
            except Exception as e:
                logger.error(f"Error streaming with {service_type} doctor: {e}")
                attempted_services.append(service_type)
                self._record_failure(service_type, str(e))
                
                # Try fallback if enabled
                if settings.enable_doctor_fallback:
                    service_type = await self._get_next_service(attempted_services)
                    if service_type:
                        # Send error notification
                        yield {
                            "chunk": "",
                            "error": f"Switching to {service_type} due to error",
                            "service": service_type
                        }
                else:
                    break
        
        # All services failed
        yield {
            "chunk": "",
            "error": "All doctor services failed",
            "done": True,
            "metadata": {
                "attempted_services": attempted_services
            }
        }
    
    async def get_treatment_recommendations(
        self,
        diagnosis: str,
        case_data: CaseData,
        service_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get treatment recommendations from doctor service"""
        if not service_type:
            service_type = self.active_sessions.get(case_data.id, settings.default_ai_provider)
        
        doctor = await self.factory.create_doctor(service_type)
        if not doctor:
            raise DoctorServiceError(f"Failed to create {service_type} doctor")
        
        return await doctor.get_treatment_recommendations(diagnosis, case_data)
    
    async def assess_urgency(
        self,
        case_data: CaseData,
        service_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Assess case urgency"""
        if not service_type:
            service_type = settings.default_ai_provider
        
        doctor = await self.factory.create_doctor(service_type)
        if not doctor:
            raise DoctorServiceError(f"Failed to create {service_type} doctor")
        
        return await doctor.assess_urgency(case_data)
    
    async def get_consensus_diagnosis(
        self,
        case_data: CaseData,
        chat_history: List[ChatMessage],
        services: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get consensus diagnosis from multiple doctor services
        
        Args:
            case_data: The medical case data
            chat_history: Previous conversation messages
            services: List of services to use (or all available)
            
        Returns:
            Consensus diagnosis with individual responses
        """
        if not services:
            services = self.factory.get_available_doctors()
        
        # Get diagnoses from all services in parallel
        tasks = []
        for service_type in services:
            task = self._get_diagnosis_from_service(service_type, case_data, chat_history)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_diagnoses = []
        failed_services = []
        
        for service_type, result in zip(services, results):
            if isinstance(result, Exception):
                failed_services.append({
                    "service": service_type,
                    "error": str(result)
                })
            else:
                successful_diagnoses.append({
                    "service": service_type,
                    "diagnosis": result["content"],
                    "confidence": result.get("confidence", 0.5)
                })
        
        if not successful_diagnoses:
            raise DoctorServiceError("All services failed to provide diagnosis")
        
        # Generate consensus (simple approach - could be enhanced)
        consensus = self._generate_consensus(successful_diagnoses)
        
        return {
            "consensus": consensus,
            "individual_diagnoses": successful_diagnoses,
            "failed_services": failed_services,
            "confidence": sum(d["confidence"] for d in successful_diagnoses) / len(successful_diagnoses)
        }
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """Get performance statistics for all services"""
        return {
            "services": self.service_stats,
            "active_sessions": len(self.active_sessions),
            "available_services": self.factory.get_available_doctors()
        }
    
    def clear_session(self, case_id: str) -> None:
        """Clear active session for a case"""
        if case_id in self.active_sessions:
            del self.active_sessions[case_id]
    
    async def _stream_response(
        self,
        doctor: BaseDoctorService,
        case_data: CaseData,
        chat_history: List[ChatMessage],
        prompt: str
    ) -> AsyncGenerator[str, None]:
        """Internal method to stream response from a doctor"""
        full_prompt = self._build_full_prompt(doctor, case_data, chat_history, prompt)
        
        async for chunk in doctor.stream_response(full_prompt):
            yield chunk
    
    def _build_full_prompt(
        self,
        doctor: BaseDoctorService,
        case_data: CaseData,
        chat_history: List[ChatMessage],
        prompt: str
    ) -> str:
        """Build full prompt with system prompt and context"""
        system_prompt = doctor.build_system_prompt(case_data)
        conversation_context = doctor.build_conversation_context(chat_history)
        
        return f"{system_prompt}\n\n{conversation_context}\n\nPatient: {prompt}"
    
    async def _get_diagnosis_from_service(
        self,
        service_type: str,
        case_data: CaseData,
        chat_history: List[ChatMessage]
    ) -> Dict[str, Any]:
        """Get diagnosis from a specific service"""
        try:
            response = await self.get_response(
                case_data,
                chat_history,
                "Please provide a diagnosis based on the case information.",
                preferred_service=service_type,
                stream=False
            )
            return response
        except Exception as e:
            logger.error(f"Failed to get diagnosis from {service_type}: {e}")
            raise
    
    def _generate_consensus(self, diagnoses: List[Dict[str, Any]]) -> str:
        """Generate consensus from multiple diagnoses"""
        # Simple approach - find common themes
        # This could be enhanced with more sophisticated NLP techniques
        
        if len(diagnoses) == 1:
            return diagnoses[0]["diagnosis"]
        
        # For now, return the diagnosis with highest confidence
        best = max(diagnoses, key=lambda d: d["confidence"])
        
        consensus = f"Based on analysis from {len(diagnoses)} medical AI systems:\n\n"
        consensus += f"Primary Assessment ({best['service']}, confidence: {best['confidence']:.2f}):\n"
        consensus += best["diagnosis"]
        
        if len(diagnoses) > 1:
            consensus += "\n\nAdditional Perspectives:\n"
            for diag in diagnoses:
                if diag["service"] != best["service"]:
                    consensus += f"\n- {diag['service']}: Key points from analysis"
        
        return consensus
    
    async def _get_next_service(self, attempted: List[str]) -> Optional[str]:
        """Get next service to try based on fallback order"""
        for service_type in settings.doctor_fallback_order:
            if service_type not in attempted and service_type in self.factory.get_available_doctors():
                return service_type
        
        # Try any available service not attempted
        for service_type in self.factory.get_available_doctors():
            if service_type not in attempted:
                return service_type
        
        return None
    
    def _record_success(self, service_type: str, response_time: float) -> None:
        """Record successful service call"""
        stats = self.service_stats.get(service_type, {})
        stats["requests"] += 1
        stats["successes"] += 1
        stats["total_response_time"] += response_time
        stats["average_response_time"] = stats["total_response_time"] / stats["successes"]
        stats["last_success"] = datetime.utcnow().isoformat()
    
    def _record_failure(self, service_type: str, error: str) -> None:
        """Record failed service call"""
        stats = self.service_stats.get(service_type, {})
        stats["requests"] += 1
        stats["failures"] += 1
        stats["last_error"] = {
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }