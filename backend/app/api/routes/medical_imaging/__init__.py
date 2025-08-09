"""
Medical Imaging microservice routes
"""

from .medical_imaging import router as medical_imaging_router
from .debug import router as debug_router

# Create a combined router for medical imaging microservice
from fastapi import APIRouter

router = APIRouter()
router.include_router(medical_imaging_router, tags=["medical-imaging"])
router.include_router(debug_router, prefix="/debug", tags=["medical-imaging-debug"])

__all__ = ["router", "medical_imaging_router", "debug_router"]