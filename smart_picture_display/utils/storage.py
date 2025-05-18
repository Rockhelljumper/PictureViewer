"""Utilities for managing storage and disk space."""
import os
import shutil
from pathlib import Path
from typing import Tuple, List
import datetime

from ..config import IMAGES_DIR, MAX_STORAGE_PERCENT
from .logger import logger

def checkAvailableStorage(path: Path = IMAGES_DIR) -> Tuple[float, float, float]:
    """Check available storage in the given path.
    
    Args:
        path: The path to check storage for.
        
    Returns:
        A tuple of (free_bytes, total_bytes, free_percent)
    """
    total, used, free = shutil.disk_usage(path)
    free_percent = (free / total) * 100
    return free, total, free_percent

def hasAvailableStorage(required_bytes: int = 0, path: Path = IMAGES_DIR) -> bool:
    """Check if there is enough storage available for a given operation.
    
    Args:
        required_bytes: The number of bytes required for an operation.
        path: The path to check storage for.
        
    Returns:
        True if there is enough storage, False otherwise.
    """
    free, total, free_percent = checkAvailableStorage(path)
    used_percent = 100 - free_percent
    
    # Check if we've exceeded our maximum storage percentage
    if used_percent >= MAX_STORAGE_PERCENT:
        logger.warning(f"Storage limit reached: {used_percent:.1f}% used (limit: {MAX_STORAGE_PERCENT}%)")
        return False
    
    # Also check if the specific operation would exceed limits
    if required_bytes > 0 and required_bytes > free:
        logger.warning(f"Not enough free space for operation. Requires {required_bytes} bytes, only {free} available")
        return False
    
    return True

def cleanupOldestImages(target_percent: float = MAX_STORAGE_PERCENT - 10) -> int:
    """Remove oldest downloaded images to free up space.
    
    Args:
        target_percent: The target percentage of disk usage to reach.
        
    Returns:
        The number of files removed.
    """
    _, total, free_percent = checkAvailableStorage()
    used_percent = 100 - free_percent
    
    if used_percent <= target_percent:
        return 0  # No cleanup needed
    
    # Get all images sorted by modification time (oldest first)
    image_files = []
    for file_path in IMAGES_DIR.glob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            stat = file_path.stat()
            image_files.append((file_path, stat.st_mtime))
    
    # Sort by modification time (oldest first)
    image_files.sort(key=lambda x: x[1])
    
    removed_count = 0
    for file_path, _ in image_files:
        try:
            file_size = file_path.stat().st_size
            file_path.unlink()
            removed_count += 1
            logger.info(f"Removed old image: {file_path.name} ({file_size} bytes)")
            
            # Check if we've reached the target usage
            _, _, free_percent = checkAvailableStorage()
            used_percent = 100 - free_percent
            if used_percent <= target_percent:
                break
        except Exception as e:
            logger.error(f"Failed to remove file {file_path}: {e}")
    
    logger.info(f"Cleanup completed: removed {removed_count} files")
    return removed_count 