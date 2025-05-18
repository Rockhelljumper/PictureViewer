"""Logging utility for the Smart Picture Display application."""
import logging
import os
from pathlib import Path
import sys

def setupLogger(name: str = "SmartPictureDisplay") -> logging.Logger:
    """Configure and return a logger for the application.
    
    Args:
        name: The name of the logger.
        
    Returns:
        A configured logger instance.
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers when called multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler
    try:
        log_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        log_file = log_dir / "smart_picture_display.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not create log file: {str(e)}")
    
    return logger

# Create a default logger instance
logger = setupLogger() 