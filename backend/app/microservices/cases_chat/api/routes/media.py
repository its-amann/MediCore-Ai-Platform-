"""
Media handling routes for file uploads
"""
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Dict, Any, Optional
import logging

from ...core.dependencies import get_media_handler
from ...core.exceptions import MediaError, CaseNotFoundError
from ...services.media.media_handler import MediaHandler

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=Dict[str, Any])
async def upload_media(
    case_id: str = Form(...),
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    media_handler: MediaHandler = Depends(get_media_handler)
) -> Dict[str, Any]:
    """
    Upload a media file for a case
    
    Args:
        case_id: Case ID to attach media to
        file: File to upload
        description: Optional file description
        
    Returns:
        Upload details including file ID and URL
    """
    try:
        result = await media_handler.upload_file(
            case_id=case_id,
            file=file,
            description=description
        )
        
        logger.info(f"Uploaded media {result['attachment_id']} for case {case_id}")
        return result
        
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found"
        )
    except MediaError as e:
        logger.error(f"Media upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error uploading media: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload media"
        )


@router.get("/{attachment_id}")
async def download_media(
    attachment_id: str,
    media_handler: MediaHandler = Depends(get_media_handler)
) -> FileResponse:
    """
    Download a media file
    
    Args:
        attachment_id: Attachment ID
        
    Returns:
        File response
    """
    try:
        file_path, filename, content_type = await media_handler.get_file(attachment_id)
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=content_type
        )
        
    except MediaError as e:
        logger.error(f"Media download error: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found"
        )
    except Exception as e:
        logger.error(f"Error downloading media: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download media"
        )


@router.post("/{attachment_id}/analyze", response_model=Dict[str, Any])
async def analyze_media(
    attachment_id: str,
    media_handler: MediaHandler = Depends(get_media_handler)
) -> Dict[str, Any]:
    """
    Analyze a medical image or document
    
    Args:
        attachment_id: Attachment ID to analyze
        
    Returns:
        Analysis results
    """
    try:
        results = await media_handler.analyze_media(attachment_id)
        return results
        
    except MediaError as e:
        logger.error(f"Media analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error analyzing media: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze media"
        )