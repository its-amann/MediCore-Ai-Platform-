"""
Adaptive Timeout Manager for Workflow Processing
Dynamically adjusts timeouts based on workload and progress
"""

import logging
from datetime import datetime
import asyncio
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger(__name__)


class AdaptiveTimeoutManager:
    """Manages adaptive timeouts for long-running operations"""
    
    def __init__(self, 
                 base_timeout: int = 60,
                 timeout_per_image: int = 30,
                 max_timeout: int = 1800):  # 30 minutes max
        self.base_timeout = base_timeout
        self.timeout_per_image = timeout_per_image
        self.max_timeout = max_timeout
        self.last_progress_time = datetime.utcnow()
        self.last_progress_value = 0
        self.progress_history = []
        self.stall_threshold = 60  # seconds without progress
        
    def calculate_timeout(self, num_images: int) -> int:
        """Calculate timeout based on workload"""
        calculated = self.base_timeout + (num_images * self.timeout_per_image)
        return min(calculated, self.max_timeout)
        
    def record_progress(self, current_progress: int):
        """Record progress update"""
        now = datetime.utcnow()
        
        if current_progress > self.last_progress_value:
            # Progress made
            self.progress_history.append({
                "time": now,
                "progress": current_progress,
                "delta": current_progress - self.last_progress_value
            })
            self.last_progress_time = now
            self.last_progress_value = current_progress
            
    def should_extend_timeout(self, current_progress: int) -> bool:
        """Check if timeout should be extended based on progress"""
        self.record_progress(current_progress)
        
        # If we've made any progress recently, extend
        time_since_progress = (datetime.utcnow() - self.last_progress_time).seconds
        
        if time_since_progress < self.stall_threshold:
            return True
            
        # Check if we're making steady progress
        if len(self.progress_history) >= 2:
            # Calculate average progress rate
            recent_history = self.progress_history[-5:]  # Last 5 updates
            if len(recent_history) >= 2:
                time_span = (recent_history[-1]["time"] - recent_history[0]["time"]).seconds
                progress_span = recent_history[-1]["progress"] - recent_history[0]["progress"]
                
                if time_span > 0 and progress_span > 0:
                    # Making progress, even if slow
                    return True
                    
        return False
        
    def get_adaptive_poll_interval(self, current_progress: int) -> float:
        """Get adaptive polling interval based on activity"""
        if current_progress != self.last_progress_value:
            # Active progress - poll frequently
            return 1.0
        else:
            # No recent progress - slow down polling
            time_since_progress = (datetime.utcnow() - self.last_progress_time).seconds
            
            if time_since_progress < 10:
                return 2.0
            elif time_since_progress < 30:
                return 5.0
            else:
                return 10.0
                
    async def wait_with_progress(self,
                                workflow_id: str,
                                num_images: int,
                                get_status_func: Callable,
                                notifier: Optional[Any] = None) -> Dict[str, Any]:
        """Wait for completion with adaptive timeout and progress tracking"""
        max_timeout = self.calculate_timeout(num_images)
        start_time = datetime.utcnow()
        timeout_extensions = 0
        max_extensions = 3
        
        logger.info(f"Starting adaptive wait for workflow {workflow_id} with timeout {max_timeout}s")
        
        try:
            while True:
                # Get current status
                try:
                    status = await get_status_func(workflow_id)
                except Exception as e:
                    logger.error(f"Error getting workflow status: {e}")
                    await asyncio.sleep(5)
                    continue
                
                # Check if completed
                if status.get("status") in ["completed", "error", "cancelled", "failed"]:
                    logger.info(f"Workflow {workflow_id} finished with status: {status.get('status')}")
                    return status
                    
                # Get progress
                current_progress = status.get("progress_percentage", 0)
                self.record_progress(current_progress)
                
                # Send notification if provided
                if notifier:
                    try:
                        await notifier.send_progress(
                            status=status.get("status", "processing"),
                            progress_percentage=current_progress,
                            current_step=status.get("current_step", "processing"),
                            message=status.get("message", ""),
                            workflow_id=workflow_id
                        )
                    except Exception as e:
                        logger.error(f"Error sending progress notification: {e}")
                        
                # Check timeout
                elapsed = (datetime.utcnow() - start_time).seconds
                
                if elapsed > max_timeout:
                    if self.should_extend_timeout(current_progress) and timeout_extensions < max_extensions:
                        # Extend timeout if making progress
                        extension = min(300, self.timeout_per_image * num_images)  # 5 min or proportional
                        logger.info(
                            f"Extending timeout by {extension}s due to ongoing progress: {current_progress}%"
                        )
                        max_timeout += extension
                        timeout_extensions += 1
                    else:
                        # No progress or max extensions reached
                        logger.error(f"Workflow {workflow_id} timed out after {elapsed}s")
                        
                        # Try to get partial results
                        partial_results = status.get("partial_results", {})
                        
                        raise TimeoutError(
                            f"Workflow timed out after {elapsed} seconds. "
                            f"Progress: {current_progress}%. "
                            f"Partial results available: {len(partial_results) > 0}"
                        )
                        
                # Adaptive polling
                poll_interval = self.get_adaptive_poll_interval(current_progress)
                await asyncio.sleep(poll_interval)
                
        except asyncio.CancelledError:
            logger.warning(f"Wait cancelled for workflow {workflow_id}")
            raise
        except Exception as e:
            logger.error(f"Error waiting for workflow {workflow_id}: {e}")
            raise
            
    def get_progress_report(self) -> Dict[str, Any]:
        """Get progress statistics"""
        if not self.progress_history:
            return {
                "current_progress": 0,
                "time_since_last_progress": None,
                "average_progress_rate": 0,
                "is_stalled": True
            }
            
        time_since_progress = (datetime.utcnow() - self.last_progress_time).seconds
        
        # Calculate average progress rate
        avg_rate = 0
        if len(self.progress_history) >= 2:
            total_time = (self.progress_history[-1]["time"] - self.progress_history[0]["time"]).seconds
            total_progress = self.progress_history[-1]["progress"] - self.progress_history[0]["progress"]
            
            if total_time > 0:
                avg_rate = total_progress / total_time
                
        return {
            "current_progress": self.last_progress_value,
            "time_since_last_progress": time_since_progress,
            "average_progress_rate": avg_rate,
            "is_stalled": time_since_progress > self.stall_threshold,
            "progress_updates": len(self.progress_history)
        }