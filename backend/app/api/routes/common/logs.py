"""
Log viewing and management routes
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Optional, Any
from pathlib import Path
import os
from datetime import datetime

from app.api.routes.auth import get_current_active_user
from app.core.database.models import User
# from app.core.logging_config import LOGS_DIR, get_log_stats  # TODO: These don't exist yet

# Temporary constants
LOGS_DIR = Path("./logs")
def get_log_stats():
    return {"logs_enabled": True, "log_directory": str(LOGS_DIR)}

router = APIRouter()

# Define allowed log files
ALLOWED_LOG_FILES = {
    "app": "app.log",
    "errors": "errors.log",
    "access": "access.log",
    "security": "security.log",
    "database": "database.log",
    "api": "api.log"
}

def is_admin_user(user: User) -> bool:
    """Check if user has admin privileges"""
    # In a real app, you'd check user roles/permissions
    # For now, we'll check if user is in admin list or has specific role
    return user.role == "admin" or user.username in ["admin", "superuser"]

@router.get("/", response_model=Dict[str, Any])
async def get_log_stats_endpoint(
    current_user: User = Depends(get_current_active_user)
):
    """Get statistics about available log files"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        stats = get_log_stats()
        return {
            "logs_directory": str(LOGS_DIR),
            "files": stats,
            "total_size_mb": sum(f["size_mb"] for f in stats.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get log stats: {str(e)}")

@router.get("/{log_type}", response_model=Dict[str, Any])
async def view_log_file(
    log_type: str,
    lines: int = Query(100, ge=1, le=1000, description="Number of lines to return"),
    offset: int = Query(0, ge=0, description="Line offset from end of file"),
    search: Optional[str] = Query(None, description="Search term to filter logs"),
    current_user: User = Depends(get_current_active_user)
):
    """View contents of a specific log file"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if log_type not in ALLOWED_LOG_FILES:
        raise HTTPException(
            status_code=404, 
            detail=f"Log type '{log_type}' not found. Available types: {list(ALLOWED_LOG_FILES.keys())}"
        )
    
    log_file = LOGS_DIR / ALLOWED_LOG_FILES[log_type]
    
    if not log_file.exists():
        return {
            "log_type": log_type,
            "file_path": str(log_file),
            "exists": False,
            "lines": [],
            "total_lines": 0,
            "message": "Log file does not exist yet"
        }
    
    try:
        # Read the file
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # Apply search filter if provided
        if search:
            filtered_lines = [line for line in all_lines if search.lower() in line.lower()]
        else:
            filtered_lines = all_lines
        
        total_lines = len(filtered_lines)
        
        # Get requested lines (from end of file)
        start_idx = max(0, total_lines - offset - lines)
        end_idx = total_lines - offset
        requested_lines = filtered_lines[start_idx:end_idx]
        
        # Parse log lines for better structure
        parsed_lines = []
        for i, line in enumerate(requested_lines):
            line = line.strip()
            if line:
                # Try to parse standard log format
                parts = line.split(' - ', 4)
                if len(parts) >= 4:
                    parsed_lines.append({
                        "line_number": start_idx + i + 1,
                        "timestamp": parts[0],
                        "logger": parts[1],
                        "level": parts[2],
                        "message": parts[3] if len(parts) > 3 else "",
                        "raw": line
                    })
                else:
                    parsed_lines.append({
                        "line_number": start_idx + i + 1,
                        "raw": line
                    })
        
        return {
            "log_type": log_type,
            "file_path": str(log_file),
            "exists": True,
            "lines": parsed_lines,
            "total_lines": total_lines,
            "showing_lines": f"{start_idx + 1}-{end_idx}",
            "file_size_mb": round(log_file.stat().st_size / (1024 * 1024), 2),
            "last_modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat(),
            "search_term": search
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read log file: {str(e)}")

@router.get("/tail/{log_type}", response_model=List[str])
async def tail_log_file(
    log_type: str,
    lines: int = Query(50, ge=1, le=500, description="Number of lines to tail"),
    current_user: User = Depends(get_current_active_user)
):
    """Get the last N lines from a log file (like tail command)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if log_type not in ALLOWED_LOG_FILES:
        raise HTTPException(
            status_code=404,
            detail=f"Log type '{log_type}' not found"
        )
    
    log_file = LOGS_DIR / ALLOWED_LOG_FILES[log_type]
    
    if not log_file.exists():
        return []
    
    try:
        # Efficient tail implementation
        with open(log_file, 'rb') as f:
            # Go to end of file
            f.seek(0, 2)
            file_size = f.tell()
            
            # Read chunks from end
            chunk_size = 1024
            chunks = []
            
            while file_size > 0 and len(chunks) < lines * 2:  # Read extra to ensure we get enough lines
                read_size = min(chunk_size, file_size)
                file_size -= read_size
                f.seek(file_size)
                chunks.append(f.read(read_size))
            
            # Combine chunks and decode
            content = b''.join(reversed(chunks)).decode('utf-8', errors='ignore')
            lines_list = content.splitlines()
            
            # Return last N lines
            return lines_list[-lines:]
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to tail log file: {str(e)}")

@router.delete("/{log_type}")
async def clear_log_file(
    log_type: str,
    current_user: User = Depends(get_current_active_user)
):
    """Clear a specific log file (admin only)"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if log_type not in ALLOWED_LOG_FILES:
        raise HTTPException(status_code=404, detail=f"Log type '{log_type}' not found")
    
    log_file = LOGS_DIR / ALLOWED_LOG_FILES[log_type]
    
    try:
        if log_file.exists():
            # Backup old log
            backup_name = f"{log_file.stem}_cleared_{datetime.now().strftime('%Y%m%d_%H%M%S')}{log_file.suffix}"
            backup_path = LOGS_DIR / backup_name
            log_file.rename(backup_path)
            
            # Create new empty file
            log_file.touch()
            
            return {
                "message": f"Log file '{log_type}' cleared successfully",
                "backup_created": str(backup_path)
            }
        else:
            return {"message": f"Log file '{log_type}' does not exist"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear log file: {str(e)}")