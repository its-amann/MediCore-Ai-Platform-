"""
Cases Chat Microservice
- Groq-powered AI doctors (General, Cardiologist, BP Specialist)
- Neo4j chat history storage
- MCP server integration for case history retrieval
- Image and audio support
"""

from .service import app, create_app
from .config import settings
from .models import (
    CaseStatus, CasePriority, CaseCreate, CaseUpdate, CaseResponse,
    ChatRequest, ChatResponse, ChatMessage, DoctorType
)

__all__ = [
    # Application
    "app",
    "create_app",
    "settings",
    
    # Models
    "CaseStatus",
    "CasePriority",
    "CaseCreate",
    "CaseUpdate",
    "CaseResponse",
    "ChatRequest",
    "ChatResponse",
    "ChatMessage",
    "DoctorType"
]