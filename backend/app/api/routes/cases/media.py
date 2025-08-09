"""
Media handling routes for cases chat
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from typing import Optional, Dict, Any
import logging
from io import BytesIO

from app.api.routes.auth import get_current_active_user
from app.core.database.models import User
from app.microservices.cases_chat.services.media_handler.media_handler import MediaHandler
from app.microservices.cases_chat.services.neo4j_storage.unified_cases_chat_storage import UnifiedCasesChatStorage
from app.core.config import settings
from app.api.dependencies.database import get_sync_driver

logger = logging.getLogger(__name__)
router = APIRouter(tags=["cases-media"])

# Service dependencies
def get_media_handler() -> MediaHandler:
    """Get media handler instance"""
    return MediaHandler()

def get_storage_service() -> UnifiedCasesChatStorage:
    """Get storage service instance using unified database manager"""
    driver = get_sync_driver()
    return UnifiedCasesChatStorage(driver)


@router.post("/upload")
async def upload_media(
    case_id: str = Form(...),
    session_id: str = Form(...),
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    media_handler: MediaHandler = Depends(get_media_handler),
    storage: UnifiedCasesChatStorage = Depends(get_storage_service)
):
    """Upload media file for a case"""
    try:
        # Verify user owns the case
        case = storage.get_case(case_id)
        if not case or case.get("user_id") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Process the file
        content = await file.read()
        
        # Store media
        media_info = await media_handler.store_media(
            case_id=case_id,
            session_id=session_id,
            file_content=content,
            filename=file.filename,
            content_type=file.content_type,
            description=description
        )
        
        return {
            "message": "Media uploaded successfully",
            "media": media_info
        }
        
    except Exception as e:
        logger.error(f"Error uploading media: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload media: {str(e)}"
        )


@router.get("/{media_id}")
async def get_media_info(
    media_id: str,
    current_user: User = Depends(get_current_active_user),
    media_handler: MediaHandler = Depends(get_media_handler),
    storage: UnifiedCasesChatStorage = Depends(get_storage_service)
):
    """Get media file information"""
    try:
        # Get media info
        media_info = await media_handler.get_media_info(media_id)
        if not media_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found"
            )
        
        # Verify user has access to the case
        case = storage.get_case(media_info["case_id"])
        if not case or case.get("user_id") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return media_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting media info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get media info: {str(e)}"
        )


@router.get("/{media_id}/download")
async def download_media(
    media_id: str,
    current_user: User = Depends(get_current_active_user),
    media_handler: MediaHandler = Depends(get_media_handler),
    storage: UnifiedCasesChatStorage = Depends(get_storage_service)
):
    """Download media file"""
    try:
        # Get media info
        media_info = await media_handler.get_media_info(media_id)
        if not media_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found"
            )
        
        # Verify user has access to the case
        case = storage.get_case(media_info["case_id"])
        if not case or case.get("user_id") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get media content
        content = await media_handler.get_media_content(media_id)
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media content not found"
            )
        
        # Return file
        return StreamingResponse(
            BytesIO(content),
            media_type=media_info.get("content_type", "application/octet-stream"),
            headers={
                "Content-Disposition": f'attachment; filename="{media_info.get("filename", "download")}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading media: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download media: {str(e)}"
        )


@router.delete("/{media_id}")
async def delete_media(
    media_id: str,
    current_user: User = Depends(get_current_active_user),
    media_handler: MediaHandler = Depends(get_media_handler),
    storage: UnifiedCasesChatStorage = Depends(get_storage_service)
):
    """Delete media file"""
    try:
        # Get media info
        media_info = await media_handler.get_media_info(media_id)
        if not media_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found"
            )
        
        # Verify user owns the case
        case = storage.get_case(media_info["case_id"])
        if not case or case.get("user_id") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Delete media
        success = await media_handler.delete_media(media_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete media"
            )
        
        return {"message": "Media deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting media: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete media: {str(e)}"
        )