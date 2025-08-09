"""
Temporary minimal consultation routes for voice consultations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice-consultations"])

@router.get("/health")
async def health_check():
    """Health check for voice consultation service"""
    return {"status": "healthy", "service": "voice-consultation"}

@router.post("/create")
async def create_consultation(request: Request):
    """Create a new consultation session - temporary stub"""
    return {
        "session_id": "temp-session",
        "status": "created",
        "message": "Temporary stub - please use /api/v1/voice/consultation routes"
    }