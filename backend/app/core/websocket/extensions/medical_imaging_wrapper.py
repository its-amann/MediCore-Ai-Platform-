"""
Medical Imaging WebSocket Wrapper

Wraps medical imaging workflow functionality for integration with the
unified WebSocket architecture.
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import json

from .base_wrapper import AsyncEventWrapper

logger = logging.getLogger(__name__)


class MedicalImagingWrapper(AsyncEventWrapper):
    """
    WebSocket wrapper for medical imaging workflows
    
    This wrapper provides WebSocket support for medical imaging operations:
    - Workflow progress updates
    - Image processing status
    - GPU resource management notifications
    - Analysis result streaming
    - Report generation updates
    """
    
    def __init__(self, priority: int = 75):
        """Initialize the medical imaging wrapper"""
        super().__init__(
            name="medical_imaging",
            max_queue_size=500,  # Smaller queue for medical imaging events
            priority=priority
        )
        
        # Supported message types
        self._supported_types = [
            "imaging_workflow_start", "imaging_workflow_status", "imaging_workflow_complete",
            "image_upload_progress", "image_processing_status", "image_analysis_result",
            "report_generation_start", "report_generation_progress", "report_generation_complete",
            "gpu_status", "gpu_cleanup", "resource_allocation"
        ]
        
        # Active workflows tracking
        self._active_workflows: Dict[str, Dict[str, Any]] = {}
        self._user_workflows: Dict[str, set] = {}
        
        # GPU resource tracking
        self._gpu_allocations: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self, config: Dict[str, Any]):
        """Initialize the medical imaging wrapper"""
        await super().initialize(config)
        
        # Set up integration with medical imaging services
        self._setup_imaging_integration()
        
        self.logger.info("Medical imaging wrapper initialized")
    
    def _setup_imaging_integration(self):
        """Set up integration with medical imaging services"""
        try:
            # Import medical imaging services if available
            from ...microservices.medical_imaging.services.medical_analysis_workflow import (
                MedicalAnalysisWorkflow
            )
            
            # Store reference for potential integration
            self._workflow_service = MedicalAnalysisWorkflow
            self.logger.info("Medical imaging services integration established")
            
        except ImportError:
            self.logger.warning("Medical imaging services not available for integration")
            self._workflow_service = None
    
    async def shutdown(self):
        """Shutdown the medical imaging wrapper"""
        # Clean up active workflows
        self._active_workflows.clear()
        self._user_workflows.clear()
        self._gpu_allocations.clear()
        
        await super().shutdown()
        self.logger.info("Medical imaging wrapper shutdown")
    
    def can_handle_message(self, message_type: str) -> bool:
        """Check if this wrapper can handle a message type"""
        return message_type in self._supported_types
    
    def get_supported_message_types(self) -> List[str]:
        """Get list of supported message types"""
        return self._supported_types.copy()
    
    async def handle_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Handle a WebSocket message"""
        message_type = message.get("type", "")
        
        if not self.can_handle_message(message_type):
            return False
        
        try:
            # Get user info from connection
            connection_info = self.get_connection_info(connection_id)
            if not connection_info:
                self.logger.warning(f"No connection info for {connection_id}")
                return False
            
            user_id = connection_info.user_id
            
            # Handle workflow operations
            if message_type.startswith("imaging_workflow"):
                return await self._handle_workflow_operation(connection_id, user_id, message)
            
            # Handle image processing operations
            elif message_type.startswith("image_"):
                return await self._handle_image_operation(connection_id, user_id, message)
            
            # Handle report generation operations
            elif message_type.startswith("report_generation"):
                return await self._handle_report_operation(connection_id, user_id, message)
            
            # Handle GPU and resource operations
            elif message_type.startswith("gpu_") or message_type == "resource_allocation":
                return await self._handle_resource_operation(connection_id, user_id, message)
            
            else:
                self.logger.warning(f"Unhandled medical imaging message type: {message_type}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error handling medical imaging message {message_type}: {e}")
            return False
    
    async def _handle_workflow_operation(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle workflow-related operations"""
        message_type = message.get("type")
        workflow_id = message.get("workflow_id")
        
        if not workflow_id:
            await self.send_message(connection_id, {
                "type": "error",
                "message": "workflow_id is required"
            })
            return False
        
        try:
            if message_type == "imaging_workflow_start":
                return await self._start_workflow(connection_id, user_id, message)
            
            elif message_type == "imaging_workflow_status":
                return await self._get_workflow_status(connection_id, user_id, message)
            
            elif message_type == "imaging_workflow_complete":
                return await self._complete_workflow(connection_id, user_id, message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling workflow operation: {e}")
            await self.send_message(connection_id, {
                "type": "error",
                "message": f"Workflow operation failed: {str(e)}"
            })
            return False
    
    async def _start_workflow(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Start a new medical imaging workflow"""
        workflow_id = message.get("workflow_id")
        workflow_type = message.get("workflow_type", "standard")
        images = message.get("images", [])
        
        # Track workflow
        self._active_workflows[workflow_id] = {
            "id": workflow_id,
            "type": workflow_type,
            "user_id": user_id,
            "connection_id": connection_id,
            "status": "starting",
            "images": images,
            "started_at": datetime.utcnow().isoformat(),
            "progress": 0
        }
        
        # Track user workflows
        if user_id not in self._user_workflows:
            self._user_workflows[user_id] = set()
        self._user_workflows[user_id].add(workflow_id)
        
        # Queue workflow start event for async processing
        await self.queue_event("workflow_start", {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "user_id": user_id,
            "connection_id": connection_id,
            "images": images
        })
        
        # Send immediate acknowledgment
        await self.send_message(connection_id, {
            "type": "imaging_workflow_started",
            "workflow_id": workflow_id,
            "status": "starting",
            "message": "Workflow started successfully"
        })
        
        return True
    
    async def _get_workflow_status(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Get status of a workflow"""
        workflow_id = message.get("workflow_id")
        
        if workflow_id in self._active_workflows:
            workflow = self._active_workflows[workflow_id]
            
            await self.send_message(connection_id, {
                "type": "imaging_workflow_status_response",
                "workflow_id": workflow_id,
                "status": workflow["status"],
                "progress": workflow["progress"],
                "started_at": workflow["started_at"],
                "current_step": workflow.get("current_step", "initialization")
            })
        else:
            await self.send_message(connection_id, {
                "type": "error",
                "message": f"Workflow {workflow_id} not found"
            })
        
        return True
    
    async def _complete_workflow(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Complete a workflow"""
        workflow_id = message.get("workflow_id")
        
        if workflow_id in self._active_workflows:
            workflow = self._active_workflows[workflow_id]
            workflow["status"] = "completed"
            workflow["completed_at"] = datetime.utcnow().isoformat()
            workflow["progress"] = 100
            
            # Notify completion
            await self.send_message(connection_id, {
                "type": "imaging_workflow_completed",
                "workflow_id": workflow_id,
                "results": message.get("results", {}),
                "completed_at": workflow["completed_at"]
            })
            
            # Clean up
            del self._active_workflows[workflow_id]
            if user_id in self._user_workflows:
                self._user_workflows[user_id].discard(workflow_id)
        
        return True
    
    async def _handle_image_operation(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle image processing operations"""
        message_type = message.get("type")
        
        try:
            if message_type == "image_upload_progress":
                # Handle image upload progress
                await self._handle_upload_progress(connection_id, user_id, message)
            
            elif message_type == "image_processing_status":
                # Handle image processing status
                await self._handle_processing_status(connection_id, user_id, message)
            
            elif message_type == "image_analysis_result":
                # Handle analysis results
                await self._handle_analysis_result(connection_id, user_id, message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling image operation: {e}")
            return False
    
    async def _handle_upload_progress(self, connection_id: str, user_id: str, message: Dict[str, Any]):
        """Handle image upload progress updates"""
        image_id = message.get("image_id")
        progress = message.get("progress", 0)
        
        # Update workflow progress if applicable
        workflow_id = message.get("workflow_id")
        if workflow_id and workflow_id in self._active_workflows:
            workflow = self._active_workflows[workflow_id]
            workflow["current_step"] = "image_upload"
            workflow["progress"] = max(workflow["progress"], progress * 0.2)  # Upload is 20% of total
        
        # Broadcast progress to user
        await self.send_message(connection_id, {
            "type": "image_upload_progress_update",
            "image_id": image_id,
            "progress": progress,
            "workflow_id": workflow_id
        })
    
    async def _handle_processing_status(self, connection_id: str, user_id: str, message: Dict[str, Any]):
        """Handle image processing status updates"""
        image_id = message.get("image_id")
        status = message.get("status")
        progress = message.get("progress", 0)
        
        # Update workflow progress if applicable
        workflow_id = message.get("workflow_id")
        if workflow_id and workflow_id in self._active_workflows:
            workflow = self._active_workflows[workflow_id]
            workflow["current_step"] = "image_processing"
            workflow["progress"] = max(workflow["progress"], 20 + (progress * 0.3))  # Processing is 30% of total
        
        # Send status update
        await self.send_message(connection_id, {
            "type": "image_processing_status_update",
            "image_id": image_id,
            "status": status,
            "progress": progress,
            "workflow_id": workflow_id
        })
    
    async def _handle_analysis_result(self, connection_id: str, user_id: str, message: Dict[str, Any]):
        """Handle image analysis results"""
        image_id = message.get("image_id")
        results = message.get("results", {})
        
        # Update workflow progress if applicable
        workflow_id = message.get("workflow_id")
        if workflow_id and workflow_id in self._active_workflows:
            workflow = self._active_workflows[workflow_id]
            workflow["current_step"] = "analysis_complete"
            workflow["progress"] = max(workflow["progress"], 50)  # Analysis is 50% of total
        
        # Send analysis results
        await self.send_message(connection_id, {
            "type": "image_analysis_complete",
            "image_id": image_id,
            "results": results,
            "workflow_id": workflow_id
        })
    
    async def _handle_report_operation(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle report generation operations"""
        message_type = message.get("type")
        
        try:
            if message_type == "report_generation_start":
                await self._start_report_generation(connection_id, user_id, message)
            
            elif message_type == "report_generation_progress":
                await self._update_report_progress(connection_id, user_id, message)
            
            elif message_type == "report_generation_complete":
                await self._complete_report_generation(connection_id, user_id, message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling report operation: {e}")
            return False
    
    async def _start_report_generation(self, connection_id: str, user_id: str, message: Dict[str, Any]):
        """Start report generation"""
        workflow_id = message.get("workflow_id")
        report_type = message.get("report_type", "standard")
        
        if workflow_id and workflow_id in self._active_workflows:
            workflow = self._active_workflows[workflow_id]
            workflow["current_step"] = "report_generation"
            workflow["progress"] = max(workflow["progress"], 60)
        
        await self.send_message(connection_id, {
            "type": "report_generation_started",
            "workflow_id": workflow_id,
            "report_type": report_type
        })
    
    async def _update_report_progress(self, connection_id: str, user_id: str, message: Dict[str, Any]):
        """Update report generation progress"""
        workflow_id = message.get("workflow_id")
        progress = message.get("progress", 0)
        
        if workflow_id and workflow_id in self._active_workflows:
            workflow = self._active_workflows[workflow_id]
            workflow["progress"] = max(workflow["progress"], 60 + (progress * 0.3))  # Report is 30% of total
        
        await self.send_message(connection_id, {
            "type": "report_generation_progress_update",
            "workflow_id": workflow_id,
            "progress": progress
        })
    
    async def _complete_report_generation(self, connection_id: str, user_id: str, message: Dict[str, Any]):
        """Complete report generation"""
        workflow_id = message.get("workflow_id")
        report_url = message.get("report_url")
        
        if workflow_id and workflow_id in self._active_workflows:
            workflow = self._active_workflows[workflow_id]
            workflow["current_step"] = "report_complete"
            workflow["progress"] = 90  # Almost complete
        
        await self.send_message(connection_id, {
            "type": "report_generation_completed",
            "workflow_id": workflow_id,
            "report_url": report_url
        })
    
    async def _handle_resource_operation(self, connection_id: str, user_id: str, message: Dict[str, Any]) -> bool:
        """Handle GPU and resource operations"""
        message_type = message.get("type")
        
        try:
            if message_type == "gpu_status":
                await self._handle_gpu_status(connection_id, user_id, message)
            
            elif message_type == "gpu_cleanup":
                await self._handle_gpu_cleanup(connection_id, user_id, message)
            
            elif message_type == "resource_allocation":
                await self._handle_resource_allocation(connection_id, user_id, message)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling resource operation: {e}")
            return False
    
    async def _handle_gpu_status(self, connection_id: str, user_id: str, message: Dict[str, Any]):
        """Handle GPU status requests"""
        # This would integrate with actual GPU monitoring
        gpu_status = {
            "gpu_count": 1,  # Placeholder
            "gpu_usage": [{"id": 0, "utilization": 0, "memory_used": 0, "memory_total": 8192}],
            "available": True
        }
        
        await self.send_message(connection_id, {
            "type": "gpu_status_response",
            "status": gpu_status
        })
    
    async def _handle_gpu_cleanup(self, connection_id: str, user_id: str, message: Dict[str, Any]):
        """Handle GPU cleanup requests"""
        workflow_id = message.get("workflow_id")
        
        # Queue cleanup event
        await self.queue_event("gpu_cleanup", {
            "workflow_id": workflow_id,
            "user_id": user_id,
            "connection_id": connection_id
        })
        
        await self.send_message(connection_id, {
            "type": "gpu_cleanup_initiated",
            "workflow_id": workflow_id
        })
    
    async def _handle_resource_allocation(self, connection_id: str, user_id: str, message: Dict[str, Any]):
        """Handle resource allocation requests"""
        requested_resources = message.get("resources", {})
        
        # Simple resource allocation logic
        allocation_id = f"alloc_{datetime.utcnow().timestamp()}"
        
        self._gpu_allocations[allocation_id] = {
            "user_id": user_id,
            "resources": requested_resources,
            "allocated_at": datetime.utcnow().isoformat()
        }
        
        await self.send_message(connection_id, {
            "type": "resource_allocation_response",
            "allocation_id": allocation_id,
            "allocated_resources": requested_resources
        })
    
    async def process_event(self, event: Dict[str, Any]):
        """Process queued events"""
        event_type = event.get("type")
        event_data = event.get("data", {})
        
        try:
            if event_type == "workflow_start":
                await self._process_workflow_start(event_data)
            
            elif event_type == "gpu_cleanup":
                await self._process_gpu_cleanup(event_data)
            
            else:
                self.logger.warning(f"Unknown event type: {event_type}")
        
        except Exception as e:
            self.logger.error(f"Error processing event {event_type}: {e}")
    
    async def _process_workflow_start(self, event_data: Dict[str, Any]):
        """Process workflow start event"""
        workflow_id = event_data.get("workflow_id")
        connection_id = event_data.get("connection_id")
        
        # Simulate workflow initialization
        if workflow_id in self._active_workflows:
            workflow = self._active_workflows[workflow_id]
            workflow["status"] = "initialized"
            workflow["progress"] = 10
            
            # Send progress update
            await self.send_message(connection_id, {
                "type": "imaging_workflow_progress",
                "workflow_id": workflow_id,
                "status": "initialized",
                "progress": 10,
                "current_step": "workflow_initialized"
            })
    
    async def _process_gpu_cleanup(self, event_data: Dict[str, Any]):
        """Process GPU cleanup event"""
        workflow_id = event_data.get("workflow_id")
        connection_id = event_data.get("connection_id")
        
        # Simulate GPU cleanup
        await self.send_message(connection_id, {
            "type": "gpu_cleanup_complete",
            "workflow_id": workflow_id,
            "message": "GPU resources cleaned up successfully"
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get medical imaging wrapper statistics"""
        stats = super().get_stats()
        
        stats.update({
            'active_workflows': len(self._active_workflows),
            'users_with_workflows': len(self._user_workflows),
            'gpu_allocations': len(self._gpu_allocations),
            'workflow_status_distribution': self._get_workflow_status_distribution()
        })
        
        return stats
    
    def _get_workflow_status_distribution(self) -> Dict[str, int]:
        """Get distribution of workflow statuses"""
        distribution = {}
        for workflow in self._active_workflows.values():
            status = workflow.get("status", "unknown")
            distribution[status] = distribution.get(status, 0) + 1
        return distribution
    
    def get_user_workflows(self, user_id: str) -> List[Dict[str, Any]]:
        """Get workflows for a specific user"""
        if user_id not in self._user_workflows:
            return []
        
        user_workflow_ids = self._user_workflows[user_id]
        return [
            self._active_workflows[wf_id] 
            for wf_id in user_workflow_ids 
            if wf_id in self._active_workflows
        ]
    
    async def notify_workflow_progress(self, workflow_id: str, progress: int, status: str, step: str):
        """Notify clients about workflow progress"""
        if workflow_id not in self._active_workflows:
            return
        
        workflow = self._active_workflows[workflow_id]
        workflow["progress"] = max(workflow["progress"], progress)
        workflow["status"] = status
        workflow["current_step"] = step
        
        connection_id = workflow.get("connection_id")
        if connection_id:
            await self.send_message(connection_id, {
                "type": "imaging_workflow_progress",
                "workflow_id": workflow_id,
                "progress": progress,
                "status": status,
                "current_step": step
            })