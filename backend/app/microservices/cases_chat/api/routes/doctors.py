"""
Doctor service management routes
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any, List
import logging

from ...core.dependencies import get_doctor_coordinator
from ...services.doctors.doctor_coordinator import DoctorCoordinator

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=Dict[str, Any])
async def get_available_doctors(
    coordinator: DoctorCoordinator = Depends(get_doctor_coordinator)
) -> Dict[str, Any]:
    """
    Get information about available doctor services
    
    Returns:
        Dictionary with available services and their status
    """
    try:
        info = await coordinator.factory.get_service_info()
        stats = coordinator.get_service_statistics()
        
        return {
            "available_services": info["configured_services"],
            "primary_service": info["primary_service"],
            "fallback_enabled": info.get("fallback_enabled", True),
            "services": info["services"],
            "statistics": stats["services"]
        }
        
    except Exception as e:
        logger.error(f"Error getting doctor info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get doctor information"
        )


@router.get("/{service_type}", response_model=Dict[str, Any])
async def get_doctor_service_info(
    service_type: str,
    coordinator: DoctorCoordinator = Depends(get_doctor_coordinator)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific doctor service
    
    Args:
        service_type: Service type (gemini, groq, etc.)
        
    Returns:
        Service information and capabilities
    """
    try:
        available = coordinator.factory.get_available_doctors()
        if service_type not in available:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Doctor service '{service_type}' not available"
            )
        
        doctor = await coordinator.factory.create_doctor(service_type)
        service_info = await doctor.get_service_info()
        
        # Add statistics
        stats = coordinator.get_service_statistics()
        if service_type in stats["services"]:
            service_info["statistics"] = stats["services"][service_type]
        
        return service_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting doctor service info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get service information"
        )


@router.get("/{service_type}/models", response_model=List[str])
async def get_available_models(
    service_type: str,
    coordinator: DoctorCoordinator = Depends(get_doctor_coordinator)
) -> List[str]:
    """
    Get available models for a doctor service
    
    Args:
        service_type: Service type (gemini, groq, etc.)
        
    Returns:
        List of available model names
    """
    try:
        models = coordinator.factory.get_available_models(service_type)
        if not models:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No models found for service '{service_type}'"
            )
        
        return models
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting models for {service_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get available models"
        )


@router.post("/test/{service_type}", response_model=Dict[str, Any])
async def test_doctor_service(
    service_type: str,
    test_prompt: str = "Hello, can you assist with medical questions?",
    coordinator: DoctorCoordinator = Depends(get_doctor_coordinator)
) -> Dict[str, Any]:
    """
    Test a doctor service
    
    Args:
        service_type: Service type to test
        test_prompt: Test prompt to send
        
    Returns:
        Test results including response and timing
    """
    try:
        available = coordinator.factory.get_available_doctors()
        if service_type not in available:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Doctor service '{service_type}' not available"
            )
        
        # Create a minimal case data for testing
        from ...models.case_models import CaseData
        test_case = CaseData(
            id="test-case",
            case_number="TEST000001",
            title="Test Case",
            description="Test case for service validation",
            patient_id="test-patient",
            status="active"
        )
        
        # Test the service
        import time
        start_time = time.time()
        
        try:
            response = await coordinator.get_response(
                case_data=test_case,
                chat_history=[],
                prompt=test_prompt,
                preferred_service=service_type,
                stream=False
            )
            
            end_time = time.time()
            
            return {
                "service": service_type,
                "status": "success",
                "response_time": end_time - start_time,
                "response": response["content"][:200] + "..." if len(response["content"]) > 200 else response["content"],
                "confidence": response.get("confidence", 0),
                "model": response.get("model", "unknown")
            }
            
        except Exception as e:
            end_time = time.time()
            return {
                "service": service_type,
                "status": "failed",
                "response_time": end_time - start_time,
                "error": str(e)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing doctor service {service_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test doctor service"
        )