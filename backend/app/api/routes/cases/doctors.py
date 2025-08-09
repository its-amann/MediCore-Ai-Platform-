"""
AI Doctors routes for cases chat
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
import logging

from app.api.routes.auth import get_current_active_user
from app.core.database.models import User
from app.microservices.cases_chat.models import DoctorType
from app.microservices.cases_chat.services.groq_doctors.doctor_service import DoctorService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["cases-doctors"])

# Service dependencies
def get_doctor_service() -> DoctorService:
    """Get doctor service instance"""
    try:
        return DoctorService()
    except Exception as e:
        logger.error(f"Failed to initialize DoctorService: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Doctor service is currently unavailable"
        )


@router.get("/available", response_model=List[Dict[str, Any]])
async def get_available_doctors(
    current_user: User = Depends(get_current_active_user),
    doctor_service: DoctorService = Depends(get_doctor_service)
):
    """Get list of available AI doctors"""
    try:
        doctors = []
        for doctor_type in DoctorType:
            doctor_info = doctor_service.get_doctor_info(doctor_type)
            doctors.append({
                "type": doctor_type.value,
                "name": doctor_info["name"],
                "specialty": doctor_info["specialty"],
                "description": doctor_info["description"],
                "languages": doctor_info.get("languages", ["English"]),
                "available": True
            })
        
        return doctors
        
    except Exception as e:
        logger.error(f"Error getting available doctors: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available doctors"
        )


@router.get("/{doctor_type}", response_model=Dict[str, Any])
async def get_doctor_info(
    doctor_type: DoctorType,
    current_user: User = Depends(get_current_active_user),
    doctor_service: DoctorService = Depends(get_doctor_service)
):
    """Get detailed information about a specific doctor"""
    try:
        doctor_info = doctor_service.get_doctor_info(doctor_type)
        
        return {
            "type": doctor_type.value,
            "name": doctor_info["name"],
            "specialty": doctor_info["specialty"],
            "description": doctor_info["description"],
            "qualifications": doctor_info.get("qualifications", []),
            "experience": doctor_info.get("experience", ""),
            "languages": doctor_info.get("languages", ["English"]),
            "consultation_style": doctor_info.get("consultation_style", ""),
            "available": True
        }
        
    except Exception as e:
        logger.error(f"Error getting doctor info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve doctor information: {str(e)}"
        )


@router.get("/{doctor_type}/capabilities", response_model=Dict[str, Any])
async def get_doctor_capabilities(
    doctor_type: DoctorType,
    current_user: User = Depends(get_current_active_user),
    doctor_service: DoctorService = Depends(get_doctor_service)
):
    """Get capabilities and features of a specific doctor"""
    try:
        capabilities = doctor_service.get_doctor_capabilities(doctor_type)
        
        return {
            "doctor_type": doctor_type.value,
            "capabilities": capabilities,
            "supported_languages": doctor_service.get_supported_languages(doctor_type),
            "response_time": "Real-time",
            "features": [
                "Medical consultation",
                "Symptom analysis",
                "Treatment recommendations",
                "Follow-up care",
                "Health education"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting doctor capabilities: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve doctor capabilities: {str(e)}"
        )