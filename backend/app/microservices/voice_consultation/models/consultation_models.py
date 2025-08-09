"""
Data models for voice and video consultations
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class ConsultationStatus(str, Enum):
    """Consultation session status"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(str, Enum):
    """Message types in consultation"""
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"
    SYSTEM = "system"
    ANALYSIS = "analysis"
    TRANSCRIPTION_STARTED = "transcription_started"
    TRANSCRIPTION_COMPLETED = "transcription_completed"
    AI_RESPONSE_STARTED = "ai_response_started"
    AI_RESPONSE_COMPLETED = "ai_response_completed"


class ProviderType(str, Enum):
    """AI Provider types"""
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    GROQ = "groq"
    TOGETHER = "together"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class TranscriptEntry(BaseModel):
    """Single entry in consultation transcript"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    speaker: str  # 'user', 'ai', 'system'
    message_type: MessageType
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = None
    duration_ms: Optional[int] = None
    provider_used: Optional[ProviderType] = None


class VoiceSession(BaseModel):
    """Voice consultation session model"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    case_id: Optional[str] = None
    doctor_type: str = "general_consultant"
    status: ConsultationStatus = ConsultationStatus.INITIALIZING
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    duration_seconds: int = 0
    transcript: List[TranscriptEntry] = Field(default_factory=list)
    ai_provider: ProviderType = ProviderType.GEMINI
    language: str = "en-US"
    audio_format: str = "webm"
    sample_rate: int = 16000
    metadata: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    recommendations: List[str] = Field(default_factory=list)
    follow_up_required: bool = False


class VideoSession(BaseModel):
    """Video consultation session model"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    case_id: Optional[str] = None
    doctor_type: str = "general_consultant"
    status: ConsultationStatus = ConsultationStatus.INITIALIZING
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    duration_seconds: int = 0
    transcript: List[TranscriptEntry] = Field(default_factory=list)
    ai_provider: ProviderType = ProviderType.GEMINI
    video_enabled: bool = True
    screen_sharing_enabled: bool = False
    recording_enabled: bool = False
    recording_url: Optional[str] = None
    peer_connection_id: Optional[str] = None
    ice_servers: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    visual_analysis: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Optional[str] = None


class ConsultationTranscript(BaseModel):
    """Complete consultation transcript"""
    consultation_id: str
    consultation_type: str  # 'voice' or 'video'
    user_id: str
    case_id: Optional[str] = None
    doctor_type: str
    started_at: datetime
    ended_at: datetime
    duration_seconds: int
    entries: List[TranscriptEntry]
    summary: Optional[str] = None
    key_findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    follow_up_required: bool = False
    providers_used: List[ProviderType] = Field(default_factory=list)
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AIProviderConfig(BaseModel):
    """Configuration for AI providers"""
    provider: ProviderType
    api_key: str
    model_name: str
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    rate_limit_rpm: int = 60  # requests per minute
    rate_limit_tpm: int = 1000000  # tokens per minute
    cost_per_1k_tokens: float = 0.0
    supports_streaming: bool = True
    supports_voice: bool = False
    supports_vision: bool = False
    supports_function_calling: bool = False
    priority: int = 1  # Lower number = higher priority
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConsultationRequest(BaseModel):
    """Request to start a consultation"""
    case_id: Optional[str] = None
    doctor_type: str = "general"
    consultation_type: str = "voice"  # 'voice' or 'video'
    language: str = "en"
    ai_provider: Optional[ProviderType] = ProviderType.GEMINI
    enable_recording: bool = False
    initial_context: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    duration_minutes: int = 30
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConsultationResponse(BaseModel):
    """Response from consultation operations"""
    session_id: str
    status: str
    created_at: datetime
    ai_provider: Optional[ProviderType] = ProviderType.GEMINI
    websocket_url: Optional[str] = None
    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AudioChunk(BaseModel):
    """Audio chunk for streaming"""
    session_id: str
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data: bytes
    format: str = "pcm16"
    sample_rate: int = 16000
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_final: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VideoFrame(BaseModel):
    """Video frame for streaming"""
    session_id: str
    frame_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data: str  # Base64 encoded image
    format: str = "jpeg"
    width: int
    height: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VoiceWebSocketMessage(BaseModel):
    """WebSocket message for voice consultation"""
    type: MessageType
    session_id: str
    data: Optional[Dict[str, Any]] = None
    text: Optional[str] = None
    audio_data: Optional[str] = None  # Base64 encoded
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class VoiceWebSocketSession(BaseModel):
    """WebSocket session for voice consultation"""
    session_id: str
    user_id: str
    connection_id: str
    consultation_session_id: str
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)