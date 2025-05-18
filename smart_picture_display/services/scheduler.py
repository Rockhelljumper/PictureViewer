"""Background scheduler for periodic tasks like syncing Google Drive."""
import threading
import time
from typing import Callable, Dict, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.job import Job

from ..config import SYNC_INTERVAL
from ..utils.logger import logger

class TaskScheduler:
    """Manages scheduled background tasks."""
    
    def __init__(self):
        """Initialize the task scheduler."""
        self.scheduler = BackgroundScheduler()
        self.jobs: Dict[str, Job] = {}
        self.scheduler.start()
        logger.info("Task scheduler started")
    
    def scheduleTask(self, 
                  task_id: str, 
                  task_func: Callable, 
                  minutes: int = SYNC_INTERVAL, 
                  run_immediately: bool = True) -> bool:
        """Schedule a periodic task.
        
        Args:
            task_id: Unique identifier for the task.
            task_func: Function to execute.
            minutes: Interval in minutes.
            run_immediately: Whether to run the task immediately.
            
        Returns:
            True if the task was scheduled successfully, False otherwise.
        """
        try:
            # Remove any existing job with the same ID
            self.removeTask(task_id)
            
            # Schedule the new job
            trigger = IntervalTrigger(minutes=minutes)
            job = self.scheduler.add_job(
                task_func,
                trigger=trigger,
                id=task_id,
                replace_existing=True
            )
            
            self.jobs[task_id] = job
            logger.info(f"Scheduled task '{task_id}' every {minutes} minutes")
            
            # Run the task immediately if requested
            if run_immediately:
                threading.Thread(target=task_func).start()
                logger.info(f"Started initial run of task '{task_id}'")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to schedule task '{task_id}': {e}")
            return False
    
    def removeTask(self, task_id: str) -> bool:
        """Remove a scheduled task.
        
        Args:
            task_id: The ID of the task to remove.
            
        Returns:
            True if the task was removed, False if it wasn't found.
        """
        if task_id in self.jobs:
            try:
                self.scheduler.remove_job(task_id)
                del self.jobs[task_id]
                logger.info(f"Removed task '{task_id}'")
                return True
            except Exception as e:
                logger.error(f"Error removing task '{task_id}': {e}")
        return False
    
    def getTask(self, task_id: str) -> Optional[Job]:
        """Get a scheduled task by ID.
        
        Args:
            task_id: The ID of the task to get.
            
        Returns:
            The task object if found, None otherwise.
        """
        return self.jobs.get(task_id)
    
    def stop(self) -> None:
        """Stop the scheduler and all running tasks."""
        try:
            self.scheduler.shutdown()
            logger.info("Task scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping task scheduler: {e}")
    
    def __del__(self) -> None:
        """Clean up resources when the object is destroyed."""
        self.stop() 