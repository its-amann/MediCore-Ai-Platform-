"""
Media upload and management routes for collaboration
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Optional
import os
import io
import mimetypes

from app.core.database.models import User
from app.api.routes.auth import get_current_active_user

router = APIRouter(tags=["collaboration-media"])

# Service dependencies
async def get_file_service():
    """Get file service from collaboration integration"""
    from app.microservices.collaboration.integration import collaboration_integration
    
    if not collaboration_integration.file_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File service not available"
        )
    return collaboration_integration.file_service


async def get_room_service():
    """Get room service from collaboration integration"""
    from app.microservices.collaboration.integration import collaboration_integration
    
    if not collaboration_integration.room_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Room service not available"
        )
    return collaboration_integration.room_service


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    room_id: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    file_service = Depends(get_file_service),
    room_service = Depends(get_room_service)
):
    """Upload a file to a collaboration room"""
    # Verify user has access to room
    participant = await room_service.get_participant(room_id, current_user.user_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to room"
        )
    
    # Read file content
    content = await file.read()
    
    # Upload file
    file_info = await file_service.upload_file(
        room_id=room_id,
        user_id=current_user.user_id,
        filename=file.filename,
        content=content,
        content_type=file.content_type,
        description=description
    )
    
    return file_info


@router.get("/rooms/{room_id}/files")
async def get_room_files(
    room_id: str,
    current_user: User = Depends(get_current_active_user),
    file_service = Depends(get_file_service),
    room_service = Depends(get_room_service)
):
    """Get all files in a room"""
    # Verify user has access to room
    participant = await room_service.get_participant(room_id, current_user.user_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to room"
        )
    
    files = await file_service.get_room_files(room_id)
    return files


@router.get("/files/{file_id}")
async def get_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    file_service = Depends(get_file_service),
    room_service = Depends(get_room_service)
):
    """Get file metadata"""
    file_info = await file_service.get_file_info(file_id)
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Verify user has access to the room
    participant = await room_service.get_participant(file_info["room_id"], current_user.user_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return file_info


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    file_service = Depends(get_file_service),
    room_service = Depends(get_room_service)
):
    """Download a file"""
    file_info = await file_service.get_file_info(file_id)
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Verify user has access to the room
    participant = await room_service.get_participant(file_info["room_id"], current_user.user_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get file content
    content = await file_service.get_file_content(file_id)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File content not found"
        )
    
    # Return file
    return StreamingResponse(
        io.BytesIO(content),
        media_type=file_info.get("content_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f'attachment; filename="{file_info.get("filename", "download")}"'
        }
    )


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user),
    file_service = Depends(get_file_service),
    room_service = Depends(get_room_service)
):
    """Delete a file"""
    file_info = await file_service.get_file_info(file_id)
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Verify user is the uploader or room creator
    room = await room_service.get_room(file_info["room_id"])
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    if file_info["uploaded_by"] != current_user.user_id and room.created_by != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only file uploader or room creator can delete files"
        )
    
    success = await file_service.delete_file(file_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )
    
    return {"message": "File deleted successfully"}