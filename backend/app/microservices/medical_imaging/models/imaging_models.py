"""
Data models for medical imaging microservice
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ReportStatus(str, Enum):
    """Report generation status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ImageType(str, Enum):
    """Supported medical image types"""
    CT = "ct_scan"
    MRI = "mri"
    XRAY = "xray"
    ULTRASOUND = "ultrasound"
    PET = "pet_scan"
    OTHER = "other"


class HeatmapData(BaseModel):
    """Heatmap visualization data"""
    original_image: str  # Base64 encoded
    heatmap_overlay: str  # Base64 encoded
    heatmap_only: str  # Base64 encoded
    attention_regions: List[Dict[str, Any]] = Field(default_factory=list)


class ImageAnalysis(BaseModel):
    """Individual image analysis result"""
    image_id: str = Field(..., description="Unique image identifier")
    filename: str
    image_type: ImageType
    analysis_text: str
    findings: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    heatmap_data: Optional[HeatmapData] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ImagingReport(BaseModel):
    """Complete imaging report"""
    report_id: str = Field(..., description="Unique report identifier")
    case_id: str = Field(..., description="Associated case ID")
    user_id: str = Field(..., description="User who requested the report")
    patient_id: Optional[str] = Field(default="", description="Patient identifier")
    image_paths: List[str] = Field(default_factory=list, description="Paths to image files")
    images: List[ImageAnalysis] = Field(default_factory=list)
    overall_analysis: str = Field(default="", description="Combined analysis of all images")
    clinical_impression: str = Field(default="", description="Clinical impression")
    recommendations: List[str] = Field(default_factory=list)
    citations: Optional[List[Dict[str, str]]] = Field(default=None, description="Medical literature citations")
    complete_report: Optional[str] = Field(default=None, description="Full formatted report with citations")
    report_embedding: Optional[List[float]] = None
    embedding_model: str = Field(default="gemini-embedding-001")
    heatmap_data: Optional[Dict[str, Any]] = Field(default=None, description="Heatmap visualization data")
    status: ReportStatus = Field(default=ReportStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }