"""
API endpoints for Medical Imaging microservice
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import uuid
import io
import json
import base64
from datetime import datetime
import asyncio
import concurrent.futures
from functools import wraps
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import Settings
from app.core.auth.shared_dependencies import get_current_user
from app.core.database.models import User
from app.microservices.medical_imaging.models import (
    ImagingReport, ImageAnalysis, ReportStatus, ImageType
)
from app.microservices.medical_imaging.services.database_services import (
    MedicalImagingStorage,
    EmbeddingService
)
from app.microservices.medical_imaging.services.image_processing import ImageProcessor
# Import from the websocket package
from app.core.websocket import websocket_manager, MessageType

from app.microservices.medical_imaging.workflows.websocket_adapter import medical_imaging_websocket, send_medical_progress

# Import new workflow manager
from app.microservices.medical_imaging.workflows.workflow_manager import WorkflowManager

logger = logging.getLogger(__name__)
# Fixed double prefix issue - removed prefix from router
router = APIRouter(tags=["medical-imaging"])


# Helper functions to handle both dict and User object formats
def get_user_id(current_user) -> str:
    """Extract user_id from current_user which can be either dict or User object"""
    return current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id


def get_user_name(current_user) -> str:
    """Extract user name from current_user which can be either dict or User object"""
    if isinstance(current_user, dict):
        return current_user.get("username", "Unknown User")
    else:
        return f"{getattr(current_user, 'first_name', '')} {getattr(current_user, 'last_name', '')}".strip() or "Unknown User"


def get_user_attr(current_user, attr: str, default=None):
    """Get attribute from current_user which can be either dict or User object"""
    if isinstance(current_user, dict):
        return current_user.get(attr, default)
    else:
        return getattr(current_user, attr, default)

# Create limiter instance
limiter = Limiter(key_func=get_remote_address)

# Global variable to track OpenRouter instance
_openrouter_instance = None

# Import new services
from app.microservices.medical_imaging.services.ai_services import AIProviderHealthMonitor
from app.microservices.medical_imaging.services.utilities_services import CircuitBreaker
from app.microservices.medical_imaging.services.database_services import get_embedding_service as db_get_embedding_service

# Initialize services
settings = Settings()
storage = MedicalImagingStorage(
    uri=settings.neo4j_uri,
    user=settings.neo4j_user,
    password=settings.neo4j_password
)
image_processor = ImageProcessor()

# Initialize health monitor
health_monitor = AIProviderHealthMonitor()

# Use managed embedding service
async def get_embedding_service():
    """Get embedding service from database services"""
    return db_get_embedding_service()

# Initialize workflow manager as module-level variable
_workflow_manager = None

async def get_workflow_manager():
    """Get or create workflow manager"""
    global _workflow_manager
    if _workflow_manager is None:
        try:
            _workflow_manager = WorkflowManager()
            await _workflow_manager.initialize()
            logger.info("Workflow manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize workflow manager: {e}")
            _workflow_manager = None
    return _workflow_manager


@router.post("/upload-images", response_model=dict)
@limiter.limit("5/minute")  # Max 5 uploads per minute per user
async def upload_medical_images(
    request: Request,
    case_id: str = Form(...),
    image_type: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload medical images for analysis
    """
    # File validation constants
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.dcm', '.dicom', '.tiff', '.tif'}
    ALLOWED_MIME_TYPES = {
        'image/jpeg', 'image/png', 'image/tiff', 
        'application/dicom', 'image/x-dcm'
    }
    
    # Validate file count
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 files allowed per upload"
        )
    
    # Validate each file
    for file in files:
        # Check file extension
        import os
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Check MIME type
        if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"MIME type {file.content_type} not allowed"
            )
        
        # Check file size
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File {file.filename} exceeds maximum size of 50MB"
            )
    
    try:
        # Get workflow manager
        workflow_manager = await get_workflow_manager()
        if not workflow_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Workflow manager not available"
            )
        
        # Create new imaging report
        # Handle both dict and User object formats
        user_id = current_user.get("user_id") if isinstance(current_user, dict) else get_user_id(current_user)
        report = ImagingReport(
            report_id=str(uuid.uuid4()),
            case_id=case_id,
            user_id=user_id,
            status=ReportStatus.PROCESSING
        )
        
        # Save initial report to database
        stored_report_id = await storage.create_imaging_report(report)
        
        # Send WebSocket notification - upload started
        await send_medical_progress(
            user_id=user_id,
            status="upload_started",
            report_id=report.report_id,
            case_id=case_id,
            total_images=len(files),
            message=f"Starting to process {len(files)} medical images"
        )
        
        # Prepare images for workflow
        images = []
        for idx, file in enumerate(files):
            file_data = await file.read()
            # Convert to base64
            base64_data = base64.b64encode(file_data).decode('utf-8')
            
            images.append({
                "id": f"{case_id}_img_{idx}",
                "data": base64_data,
                "type": image_type or "CT",
                "metadata": {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "modality": image_type or "CT"
                }
            })
        
        # Prepare patient info
        patient_info = {
            "patient_id": user_id,
            "name": get_user_name(current_user),
            "age": get_user_attr(current_user, "age", 30),
            "gender": get_user_attr(current_user, "gender", "unknown"),
            "symptoms": [],
            "clinical_history": "Not provided"
        }
        
        # Process images through new workflow
        workflow_result = await workflow_manager.process_medical_images(
            case_id=case_id,
            images=images,
            patient_info=patient_info,
            user_id=user_id
        )
        
        if not workflow_result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=workflow_result.get("error", "Workflow processing failed")
            )
        
        # Extract report data from workflow result
        workflow_state = workflow_result.get("workflow_state", {})
        report_id = workflow_result.get("report_id", workflow_result.get("workflow_id", str(uuid.uuid4())))
        
        # Send WebSocket notification - complete success
        await send_medical_progress(
            user_id=user_id,
            status="completed",
            report_id=report_id,
            case_id=case_id,
            progress_percentage=100,
            images_processed=len(images),
            severity=workflow_state.get("severity", "low"),
            findings_count=len(workflow_state.get("abnormalities_detected", [])),
            message="Medical imaging analysis completed successfully"
        )
        
        logger.info(f"Successfully processed imaging report: {report_id}")
        
        # Return response with custom headers
        response_data = {
            "report_id": report_id,
            "workflow_id": workflow_result.get("workflow_id", f"workflow_{report_id}"),
            "case_id": case_id,
            "status": "completed",
            "images_processed": len(images),
            "message": "Medical images processed successfully",
            "workflow_state": workflow_state
        }
        
        return JSONResponse(
            content=response_data,
            headers={
                "X-Report-ID": report_id,
                "X-Workflow-ID": workflow_result.get("workflow_id", f"workflow_{report_id}"),
                "X-Upload-Progress": "100"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in upload_medical_images: {e}")
        # Send WebSocket notification - unexpected error
        if 'report' in locals() and hasattr(report, 'report_id'):
            await send_medical_progress(
                user_id=get_user_id(current_user),
                status="error",
                report_id=report.report_id,
                case_id=case_id,
                error=str(e),
                message="An error occurred during medical imaging analysis"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )



# Removed duplicate route - see get_report function below which uses Neo4j


@router.get("/imaging-reports/case/{case_id}", response_model=List[dict])
async def get_case_imaging_reports(
    case_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all imaging reports for a case
    """
    try:
        reports = await storage.get_reports_by_case(case_id)
        return reports
        
    except Exception as e:
        logger.error(f"Error getting case reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/imaging-reports/{report_id}/download")
async def download_imaging_report(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Download imaging report as PDF
    """
    try:
        # Get report data
        report = await storage.get_report_by_id(report_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        # Check access
        if report["user_id"] != get_user_id(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Generate PDF content with proper markdown rendering
        import markdown
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
        import html
        import re
        
        # Convert markdown to HTML for reportlab
        def markdown_to_reportlab_paragraphs(md_text, styles):
            """Convert markdown text to reportlab paragraphs"""
            if not md_text:
                return []
            
            # Convert markdown to HTML
            html_text = markdown.markdown(md_text, extensions=['extra', 'codehilite', 'tables'])
            
            # Clean up HTML for reportlab
            # Replace code blocks with formatted text
            html_text = re.sub(r'<pre><code[^>]*>(.*?)</code></pre>', 
                             lambda m: f'<para backColor="#f0f0f0" fontName="Courier">{html.escape(m.group(1))}</para>', 
                             html_text, flags=re.DOTALL)
            
            # Convert strong tags to bold
            html_text = html_text.replace('<strong>', '<b>').replace('</strong>', '</b>')
            html_text = html_text.replace('<em>', '<i>').replace('</em>', '</i>')
            
            # Split by headings and paragraphs
            paragraphs = []
            sections = re.split(r'(<h[1-6]>.*?</h[1-6]>|<p>.*?</p>|<ul>.*?</ul>|<ol>.*?</ol>)', html_text, flags=re.DOTALL)
            
            for section in sections:
                if not section.strip():
                    continue
                    
                if section.startswith('<h1>'):
                    text = re.sub(r'<[^>]+>', '', section)
                    paragraphs.append(Paragraph(text, styles['Title']))
                    paragraphs.append(Spacer(1, 0.3*inch))
                elif section.startswith('<h2>'):
                    text = re.sub(r'<[^>]+>', '', section)
                    paragraphs.append(Paragraph(text, styles['Heading1']))
                    paragraphs.append(Spacer(1, 0.2*inch))
                elif section.startswith('<h3>'):
                    text = re.sub(r'<[^>]+>', '', section)
                    paragraphs.append(Paragraph(text, styles['Heading2']))
                    paragraphs.append(Spacer(1, 0.15*inch))
                elif section.startswith('<p>'):
                    # Keep basic HTML formatting
                    text = section.replace('<p>', '').replace('</p>', '')
                    paragraphs.append(Paragraph(text, styles['Normal']))
                    paragraphs.append(Spacer(1, 0.1*inch))
                elif section.startswith('<ul>') or section.startswith('<ol>'):
                    # Extract list items
                    items = re.findall(r'<li>(.*?)</li>', section, re.DOTALL)
                    for item in items:
                        text = re.sub(r'<[^>]+>', '', item)
                        paragraphs.append(Paragraph(f"• {text}", styles['Normal']))
                    paragraphs.append(Spacer(1, 0.1*inch))
            
            return paragraphs
        
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer, 
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Enhanced styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            alignment=TA_CENTER,
            spaceAfter=30
        ))
        styles.add(ParagraphStyle(
            name='ReportHeader',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER
        ))
        
        story = []
        
        # Header
        story.append(Paragraph("Medical Imaging Analysis Report", styles['CustomTitle']))
        story.append(Paragraph(f"Report ID: {report_id}", styles['ReportHeader']))
        story.append(Paragraph(f"Generated: {report.get('created_at', 'N/A')}", styles['ReportHeader']))
        story.append(Spacer(1, 0.5*inch))
        
        # Patient Information
        if report.get("patient_name") or report.get("patient_id"):
            story.append(Paragraph("Patient Information", styles['Heading1']))
            patient_data = []
            if report.get("patient_name"):
                patient_data.append(["Patient Name:", report["patient_name"]])
            if report.get("patient_id"):
                patient_data.append(["Patient ID:", report["patient_id"]])
            if report.get("study_type"):
                patient_data.append(["Study Type:", report["study_type"]])
            
            if patient_data:
                t = Table(patient_data, colWidths=[2*inch, 4*inch])
                t.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(t)
                story.append(Spacer(1, 0.3*inch))
        
        # Process markdown content if available
        if report.get("markdown_content"):
            story.extend(markdown_to_reportlab_paragraphs(report["markdown_content"], styles))
        else:
            # Fallback to structured content
            if report.get("overall_analysis"):
                story.append(Paragraph("Analysis", styles['Heading1']))
                story.extend(markdown_to_reportlab_paragraphs(report["overall_analysis"], styles))
                story.append(Spacer(1, 0.25*inch))
            
            if report.get("clinical_impression"):
                story.append(Paragraph("Clinical Impression", styles['Heading1']))
                story.extend(markdown_to_reportlab_paragraphs(report["clinical_impression"], styles))
                story.append(Spacer(1, 0.25*inch))
            
            if report.get("recommendations"):
                story.append(Paragraph("Recommendations", styles['Heading1']))
                for rec in report["recommendations"]:
                    story.append(Paragraph(f"• {rec}", styles['Normal']))
                story.append(Spacer(1, 0.25*inch))
            
            # Add findings if available
            if report.get("findings"):
                story.append(Paragraph("Findings", styles['Heading1']))
                for i, finding in enumerate(report["findings"], 1):
                    story.append(Paragraph(f"Finding {i}:", styles['Heading3']))
                    if isinstance(finding, dict):
                        if finding.get("description"):
                            story.append(Paragraph(finding["description"], styles['Normal']))
                        if finding.get("severity"):
                            story.append(Paragraph(f"Severity: {finding['severity']}", styles['Normal']))
                    else:
                        story.append(Paragraph(str(finding), styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
        
        # Footer
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph("This report was generated by AI and should be reviewed by a qualified medical professional.", 
                              styles['ReportHeader']))
        
        doc.build(story)
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(pdf_buffer.getvalue()),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=imaging_report_{report_id}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/imaging-reports/{report_id}/similar", response_model=List[dict])
async def find_similar_reports(
    report_id: str,
    limit: int = 5,
    current_user: User = Depends(get_current_user)
):
    """
    Find similar imaging reports based on embeddings
    """
    try:
        # Get the original report
        report = await storage.get_report_by_id(report_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        # Generate embedding for the report if not already stored
        if "embedding" not in report or not report["embedding"]:
            try:
                embedding_text = f"{report.get('overall_analysis', '')} {report.get('clinical_impression', '')}"
                embedding = await (await get_embedding_service()).generate_text_embedding(embedding_text)
                
                if not embedding:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to generate embedding"
                    )
            except Exception as e:
                logger.warning(f"Failed to generate embedding for similarity search: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Similarity search temporarily unavailable due to embedding service issues"
                )
        else:
            embedding = report["embedding"]
        
        # Find similar reports
        similar_reports = await storage.find_similar_reports(embedding, limit)
        
        return similar_reports
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/image-types", response_model=List[str])
async def get_supported_image_types(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of supported medical image types
    """
    # Require authentication
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    return [img_type.value for img_type in ImageType]


# Removed duplicate route - see get_patient_reports function below which returns a more structured response


@router.get("/imaging-reports/recent", response_model=List[dict])
async def get_recent_reports(
    limit: int = 10,
    study_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get recent reports across all patients (for medical professionals)
    """
    try:
        # Log the request
        logger.info(f"Getting recent reports - limit: {limit}, study_type: {study_type}")
        
        # Get recent reports from storage
        reports = await storage.get_recent_reports(limit, study_type)
        
        logger.info(f"Retrieved {len(reports)} reports from storage")
        
        # Filter based on user permissions
        if not getattr(current_user, "is_medical_professional", False):
            # Only show user's own reports
            user_id = get_user_id(current_user)
            logger.info(f"Filtering reports for user: {user_id}")
            
            # Debug: Log the first report's patientId to see the format
            if reports and len(reports) > 0:
                logger.info(f"Sample report - patientId: {reports[0].get('patientId')}, userId: {reports[0].get('userId')}, comparing with user_id: {user_id}")
            
            # Simple filtering - only show reports for this user
            filtered_reports = []
            for r in reports:
                report_user_id = r.get("userId", "")
                
                # Only check userId field
                if report_user_id == user_id:
                    filtered_reports.append(r)
                    
            reports = filtered_reports
            logger.info(f"After filtering: {len(reports)} reports")
        
        return reports
        
    except Exception as e:
        logger.error(f"Error retrieving recent reports: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/imaging-reports/debug/all")
async def debug_get_all_reports(
    current_user: User = Depends(get_current_user)
):
    """Debug endpoint to see all reports in database"""
    try:
        from app.core.database.unified_db_manager import unified_db_manager
        driver = unified_db_manager.connect_sync()
        
        with driver.session() as session:
            result = session.run("""
                MATCH (r:MedicalReport)
                RETURN r, labels(r) as node_labels
                ORDER BY r.createdAt DESC
                LIMIT 20
            """)
            
            reports = []
            for record in result:
                report = dict(record["r"])
                report["_labels"] = record["node_labels"]
                reports.append(report)
            
            return {
                "total_count": len(reports),
                "reports": reports,
                "current_user_id": get_user_id(current_user)
            }
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/imaging-reports/search", response_model=List[dict])
async def search_reports(
    query: str,
    patient_id: Optional[str] = None,
    study_type: Optional[str] = None,
    severity: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    """
    Search reports by text query and filters
    """
    try:
        filters = {}
        
        # Add patient filter based on permissions
        if not getattr(current_user, "is_medical_professional", False):
            filters["patientId"] = get_user_id(current_user)
        elif patient_id:
            filters["patientId"] = patient_id
        
        if study_type:
            filters["studyType"] = study_type
        
        if severity:
            filters["severity"] = severity
        
        if start_date or end_date:
            filters["dateRange"] = {}
            if start_date:
                filters["dateRange"]["start"] = start_date
            if end_date:
                filters["dateRange"]["end"] = end_date
        
        # Search reports in storage
        reports = await storage.search_reports(query, filters, limit)
        
        return reports
        
    except Exception as e:
        logger.error(f"Error searching reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Removed duplicate route - see get_report_detail function below which has more complete response structure


@router.post("/workflow/analyze", response_model=dict)
@limiter.limit("10/hour")  # Max 10 workflow analyses per hour per user
async def analyze_with_workflow(
    request: Request,
    case_id: str = Form(...),
    image_type: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze medical images using the integrated workflow system
    """
    try:
        # Get workflow manager
        workflow_manager = await get_workflow_manager()
        if not workflow_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Workflow manager not available"
            )
        
        logger.info(f"Processing medical images for case {case_id} using workflow")
        
        # Prepare images for workflow
        images = []
        for idx, file in enumerate(files):
            file_data = await file.read()
            # Convert to base64
            base64_data = base64.b64encode(file_data).decode('utf-8')
            
            images.append({
                "id": f"{case_id}_img_{idx}_{datetime.now().timestamp()}",
                "data": base64_data,
                "type": image_type or "CT",
                "metadata": {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "modality": image_type or "CT"
                }
            })
        
        # Prepare patient info
        patient_info = {
            "patient_id": get_user_id(current_user),
            "name": get_user_name(current_user),
            "age": get_user_attr(current_user, "age", 30),
            "gender": get_user_attr(current_user, "gender", "unknown"),
            "symptoms": [],
            "clinical_history": "Not provided"
        }
        
        # Process through workflow
        workflow_result = await workflow_manager.process_medical_images(
            case_id=case_id,
            images=images,
            patient_info=patient_info,
            user_id=get_user_id(current_user)
        )
        
        if workflow_result.get("success"):
            workflow_state = workflow_result.get("workflow_state", {})
            return {
                "success": True,
                "case_id": case_id,
                "workflow_id": workflow_result.get("workflow_id", f"workflow_{case_id}"),
                "report_id": workflow_result.get("report_id", case_id),
                "status": "completed",
                "images_processed": len(images),
                "findings_detected": len(workflow_state.get("abnormalities_detected", [])),
                "urgency_level": workflow_state.get("severity", "routine"),
                "quality_score": workflow_state.get("quality_score", 0.95),
                "workflow_type": "improved",
                "message": "Medical images analyzed successfully",
                "workflow_state": workflow_state
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=workflow_result.get("error", "Workflow processing failed")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in workflow analysis: {e}")
        # Send WebSocket notification - workflow error
        if 'report_id' in locals():
            await send_medical_progress(
                user_id=get_user_id(current_user),
                status="workflow_error",
                report_id=report_id,
                case_id=case_id,
                error=str(e),
                message="An error occurred during workflow analysis"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/workflow/status/{workflow_id}", response_model=dict)
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get status of a workflow execution
    """
    try:
        # Extract report_id from workflow_id
        report_id = workflow_id
        if workflow_id.startswith("workflow_"):
            report_id = workflow_id.replace("workflow_", "")
        
        # Try to get report status from storage
        try:
            report = await storage.get_report_by_id(report_id)
            if report:
                return {
                    "workflow_id": workflow_id,
                    "status": "completed",
                    "details": {
                        "report_id": report.get('id', report_id),
                        "case_id": report.get('caseId'),
                        "created_at": report.get('createdAt'),
                        "completed_at": report.get('updatedAt'),
                        "severity": report.get('severity'),
                        "findings_count": len(report.get('findings', []))
                    }
                }
        except Exception as e:
            logger.warning(f"Could not get report from storage: {e}")
        
        # Default response
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "workflow_type": "improved",
            "details": {
                "message": "Workflow completed"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/workflow/recover", response_model=dict)
async def recover_workflow(
    case_id: str = Form(...),
    action: str = Form("check_or_restart"),
    current_user: User = Depends(get_current_user)
):
    """
    Recover or restart a stuck workflow
    
    Args:
        case_id: The case ID to recover
        action: Recovery action - "check_or_restart", "force_restart", "cancel"
    """
    try:
        logger.info(f"Workflow recovery requested for case {case_id} with action {action}")
        
        # Extract workflow ID
        workflow_id = case_id if case_id.startswith("workflow_") else f"workflow_{case_id}"
        
        # Get workflow manager for direct processing
        workflow_manager = await get_workflow_manager()
        
        # For direct processing, workflows complete immediately
        logger.info(f"Direct processing workflow recovery for {workflow_id}")
        
        # Get workflow status (will always be completed for direct processing)
        workflow_status = await workflow_manager.get_workflow_status(workflow_id)
        current_status = workflow_status.get("status", "completed")
        
        if current_status == "completed":
            return {
                "status": "completed",
                "workflow_id": workflow_id,
                "workflow_type": "direct",
                "message": "Direct processing workflow completed successfully"
            }
        else:
            # For any other status, indicate completion since direct processing is immediate
            return {
                "status": "recovered",
                "workflow_id": workflow_id,
                "workflow_type": "direct",
                "message": "Direct processing workflow - no recovery needed",
                "current_status": "completed"
            }
        
        return {
            "status": "no_action",
            "message": "No recovery action taken"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recovering workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recover workflow: {str(e)}"
        )


@router.get("/imaging-reports/{report_id}", response_model=dict)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get a medical imaging report from Neo4j by ID
    """
    try:
        # Get report from storage
        report = await storage.get_report_by_id(report_id)
        
        if report:
            # Create a dummy image analysis for frontend compatibility
            # The frontend expects an images array with at least one item
            dummy_image = {
                "id": f"{report_id}_img",
                "analysis_text": report.get("radiologicalAnalysis", ""),
                "findings": report.get("key_findings", []),
                "processing_time": 1.0
            }
            
            # Add heatmap data if available
            if report.get("heatmap_data"):
                dummy_image["heatmap_data"] = {
                    "heatmap_overlay": report["heatmap_data"].get("overlay", ""),
                    "attention_regions": []
                }
            
            # Format the response to match frontend expectations
            return {
                "report_id": report.get("id", report_id),
                "case_id": report.get("caseId"),
                "user_id": report.get("userId"),  # Changed from patient_id
                "study_type": report.get("studyType", "Medical Imaging"),
                "status": "completed",  # Always completed for retrieved reports
                "overall_analysis": report.get("radiologicalAnalysis", ""),
                "recommendations": report.get("recommendations", []),
                "key_findings": report.get("key_findings", []),
                "created_at": report.get("createdAt"),
                "updated_at": report.get("updatedAt"),
                "images": [dummy_image],  # Frontend expects this
                "heatmap_data": report.get("heatmap_data")  # Include heatmap data if available
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/imaging-reports/{report_id}/detail", response_model=dict)
async def get_report_detail(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed medical imaging report including all workflow data
    """
    try:
        # Get report from storage
        report = await storage.get_report_by_id(report_id)
        
        if report:
            # Include complete workflow data
            final_report = report.get("final_report", {})
            return {
                "report_id": report.get("id", report_id),
                "case_id": report.get("caseId"),
                "patient_info": {
                    "patient_id": report.get("patientId"),
                    "name": report.get("patientName"),
                    "age": report.get("patientAge"),
                    "gender": report.get("patientGender")
                },
                "study_info": {
                    "type": report.get("studyType"),
                    "date": report.get("studyDate")
                },
                "status": report.get("status"),
                "overall_analysis": report.get("overall_analysis", report.get("radiologicalAnalysis", "")),
                "radiological_analysis": report.get("radiologicalAnalysis"),
                "clinical_impression": report.get("clinicalImpression"),
                "recommendations": report.get("recommendations", []),
                "findings": report.get("findings", []),
                "key_findings": report.get("key_findings", []),
                "citations": report.get("citations", []),
                "image_analyses": report.get("imageAnalyses", []),
                "severity": report.get("severity", "low"),
                "created_at": report.get("createdAt"),
                "updated_at": report.get("updatedAt"),
                "final_report": {
                    "content": final_report.get("content", ""),
                    "sections": final_report.get("sections", []),
                    "generated_at": final_report.get("generated_at"),
                    "literature_included": final_report.get("literature_included", False)
                },
                "literature_references": report.get("literature_references", []),
                "quality_score": report.get("quality_score", 0),
                "abnormalities_detected": report.get("abnormalities_detected", []),
                "heatmap_data": report.get("heatmap_data"),
                "embedding_info": {
                    "has_summary_embedding": "summaryEmbedding" in report,
                    "has_findings_embedding": "findingsEmbedding" in report,
                    "has_full_report_embedding": "fullReportEmbedding" in report
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving detailed report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/imaging-reports/{report_id}/chat", response_model=dict)
async def chat_about_report(
    report_id: str,
    request: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Chat with AI about a specific medical report
    """
    try:
        from app.microservices.medical_imaging.services.workflow_services.report_chat_service import ReportChatService
        
        chat_service = ReportChatService()
        
        # Extract message and conversation history from request
        message = request.get("message", "")
        conversation_history = request.get("conversation_history", [])
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message is required"
            )
        
        # Generate AI response
        result = await chat_service.chat_about_report(
            report_id=report_id,
            message=message,
            conversation_history=conversation_history
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND if result["error"] == "Report not found" else status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in report chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/imaging-reports/{report_id}/chat/history", response_model=dict)
async def get_chat_history(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get chat history for a specific report
    """
    try:
        from app.microservices.medical_imaging.services.workflow_services.report_chat_service import ReportChatService
        
        chat_service = ReportChatService()
        history = await chat_service.get_conversation_history(report_id)
        
        return {
            "report_id": report_id,
            "history": history,
            "count": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/imaging-reports/patient/{patient_id}", response_model=dict)
async def get_patient_reports(
    patient_id: str,
    limit: int = Query(default=10, le=100),
    skip: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user)
):
    """
    Get all reports for a specific user (using patient_id for backward compatibility)
    """
    try:
        # In new schema, patient_id is actually user_id
        # Get user reports from storage
        reports = await storage.get_patient_reports(patient_id, limit, skip)
        
        return {
            "patient_id": patient_id,
            "total_reports": len(reports),
            "limit": limit,
            "skip": skip,
            "reports": reports
        }
        
    except Exception as e:
        logger.error(f"Error retrieving patient reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )




# JSON-based workflow endpoint for testing
class WorkflowRequest(BaseModel):
    """Request model for workflow analysis"""
    images: List[Dict[str, Any]]
    patient_info: Dict[str, Any]
    case_id: str
    use_langgraph: bool = True


@router.post("/workflow/analyze-json", response_model=dict)
@limiter.limit("10/hour")
async def analyze_workflow_json(
    request: Request,
    workflow_data: WorkflowRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Analyze medical images using JSON payload (for API testing)
    Accepts base64 encoded images in JSON format
    """
    try:
        # Get workflow manager
        workflow_manager = await get_workflow_manager()
        
        if not workflow_manager:
            raise HTTPException(
                status_code=503,
                detail="Workflow manager not available"
            )
        
        logger.info(f"Starting JSON workflow for case {workflow_data.case_id}")
        
        # Add user info to patient info if not present
        if "user_id" not in workflow_data.patient_info:
            workflow_data.patient_info["user_id"] = get_user_id(current_user)
        
        # Process images through workflow
        result = await workflow_manager.process_medical_images(
            images=workflow_data.images,
            patient_info=workflow_data.patient_info,
            case_id=workflow_data.case_id,
            user_id=get_user_id(current_user)
        )
        
        if result.get("success"):
            return {
                "success": True,
                "workflow_id": result.get("workflow_id"),
                "case_id": workflow_data.case_id,
                "report": result.get("report"),
                "workflow_type": result.get("workflow_type", "langgraph"),
                "message": "Workflow started successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Workflow processing failed")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workflow JSON error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process workflow: {str(e)}"
        )