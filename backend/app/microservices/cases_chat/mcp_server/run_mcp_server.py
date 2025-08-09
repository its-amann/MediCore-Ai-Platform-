#!/usr/bin/env python3
"""
Run the MCP server for medical history service
"""

import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging

from app.core.config import settings
from app.microservices.cases_chat.mcp_server.medical_history_service import (
    MedicalHistoryService,
    get_medical_history_service
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app for MCP server
app = FastAPI(
    title="Medical Context Protocol Server",
    description="MCP server for medical history and context retrieval",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize medical history service
medical_service = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global medical_service
    try:
        medical_service = get_medical_history_service()
        logger.info("Medical history service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize medical history service: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global medical_service
    if medical_service:
        await medical_service.close()
        logger.info("Medical history service closed")


# Request/Response models
class CaseHistoryRequest(BaseModel):
    case_id: str
    user_id: str
    include_chat: bool = True
    include_analysis: bool = True


class SimilarCasesRequest(BaseModel):
    case_id: str
    user_id: Optional[str] = None
    similarity_threshold: float = 0.5
    limit: int = 5


class SearchCasesRequest(BaseModel):
    user_id: str
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10


class PatternAnalysisRequest(BaseModel):
    user_id: str
    pattern_type: str = "symptoms"


class PatientTimelineRequest(BaseModel):
    user_id: str
    date_from: Optional[str] = None
    date_to: Optional[str] = None


# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "MCP Server"}


@app.get("/get_server_info")
async def get_server_info():
    """Get server information"""
    return {
        "server_name": "Medical Context Protocol Server",
        "version": "2.0.0",
        "capabilities": [
            "case_history",
            "similar_cases",
            "search_cases",
            "pattern_analysis",
            "patient_timeline"
        ],
        "authentication_required": False
    }


@app.get("/get_server_health")
async def get_server_health():
    """Get detailed server health status"""
    return {
        "status": "healthy",
        "components": {
            "database": {"status": "connected" if medical_service else "disconnected"},
            "medical_service": {"status": "active" if medical_service else "inactive"}
        }
    }


@app.post("/get_case_history")
async def get_case_history(request: CaseHistoryRequest):
    """Get case history"""
    if not medical_service:
        raise HTTPException(status_code=503, detail="Medical service not available")
    
    try:
        result = await medical_service.get_case_history(
            case_id=request.case_id,
            user_id=request.user_id,
            include_chat=request.include_chat,
            include_analysis=request.include_analysis
        )
        return result
    except Exception as e:
        logger.error(f"Error getting case history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/find_similar_cases")
async def find_similar_cases(request: SimilarCasesRequest):
    """Find similar cases"""
    if not medical_service:
        raise HTTPException(status_code=503, detail="Medical service not available")
    
    try:
        result = await medical_service.find_similar_cases(
            case_id=request.case_id,
            user_id=request.user_id,
            similarity_threshold=request.similarity_threshold,
            limit=request.limit
        )
        return result
    except Exception as e:
        logger.error(f"Error finding similar cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search_cases")
async def search_cases(request: SearchCasesRequest):
    """Search cases"""
    if not medical_service:
        raise HTTPException(status_code=503, detail="Medical service not available")
    
    try:
        result = await medical_service.search_cases(
            user_id=request.user_id,
            query=request.query,
            filters=request.filters,
            limit=request.limit
        )
        return result
    except Exception as e:
        logger.error(f"Error searching cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze_patterns")
async def analyze_patterns(request: PatternAnalysisRequest):
    """Analyze patterns"""
    if not medical_service:
        raise HTTPException(status_code=503, detail="Medical service not available")
    
    try:
        result = await medical_service.analyze_patterns(
            user_id=request.user_id,
            pattern_type=request.pattern_type
        )
        return result
    except Exception as e:
        logger.error(f"Error analyzing patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_patient_timeline")
async def get_patient_timeline(request: PatientTimelineRequest):
    """Get patient timeline"""
    if not medical_service:
        raise HTTPException(status_code=503, detail="Medical service not available")
    
    try:
        result = await medical_service.get_patient_timeline(
            user_id=request.user_id,
            date_from=request.date_from,
            date_to=request.date_to
        )
        return result
    except Exception as e:
        logger.error(f"Error getting patient timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_case_statistics")
async def get_case_statistics(user_id: str):
    """Get case statistics"""
    if not medical_service:
        raise HTTPException(status_code=503, detail="Medical service not available")
    
    try:
        result = await medical_service.get_case_statistics(user_id=user_id)
        return result
    except Exception as e:
        logger.error(f"Error getting case statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the MCP server"""
    host = settings.mcp_server_host
    port = settings.mcp_server_port
    
    logger.info(f"Starting MCP server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()