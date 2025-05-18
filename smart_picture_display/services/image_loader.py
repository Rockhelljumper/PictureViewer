"""Service for loading and managing local images."""
import os
from pathlib import Path
from typing import List, Optional
import random
from PIL import Image, UnidentifiedImageError

from ..config import IMAGES_DIR, SUPPORTED_EXTENSIONS
from ..utils.logger import logger

class ImageLoader:
    """Handles loading and managing images from the local file system."""
    
    def __init__(self, images_dir: Path = IMAGES_DIR):
        """Initialize the image loader.
        
        Args:
            images_dir: Directory path where images are stored.
        """
        self.images_dir = images_dir
        self.image_paths: List[Path] = []
        self.current_index = 0
        self.refreshImageList()
    
    def refreshImageList(self) -> None:
        """Refresh the list of available images from the file system."""
        self.image_paths = []
        try:
            for file_path in self.images_dir.glob("*"):
                if self._isValidImage(file_path):
                    self.image_paths.append(file_path)
            
            # Sort by filename for consistent ordering
            self.image_paths.sort()
            
            if not self.image_paths:
                logger.warning(f"No images found in {self.images_dir}")
            else:
                logger.info(f"Found {len(self.image_paths)} images in {self.images_dir}")
                
            # Reset current index if needed
            if self.current_index >= len(self.image_paths):
                self.current_index = 0 if self.image_paths else -1
                
        except Exception as e:
            logger.error(f"Error refreshing image list: {e}")
    
    def _isValidImage(self, file_path: Path) -> bool:
        """Check if the file is a valid image.
        
        Args:
            file_path: Path to the file to check.
            
        Returns:
            True if the file is a valid image, False otherwise.
        """
        if not file_path.is_file():
            return False
            
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return False
            
        # Try to open the image to verify it's valid
        try:
            with Image.open(file_path) as img:
                img.verify()
            return True
        except (UnidentifiedImageError, IOError, SyntaxError):
            logger.warning(f"Invalid image file: {file_path}")
            return False
    
    def getCurrentImage(self) -> Optional[Path]:
        """Get the current image path.
        
        Returns:
            The current image path or None if no images are available.
        """
        if not self.image_paths:
            return None
        
        if self.current_index < 0 or self.current_index >= len(self.image_paths):
            self.current_index = 0
            
        return self.image_paths[self.current_index]
    
    def getNextImage(self) -> Optional[Path]:
        """Get the next image in the sequence.
        
        Returns:
            The next image path or None if no images are available.
        """
        if not self.image_paths:
            return None
            
        self.current_index = (self.current_index + 1) % len(self.image_paths)
        return self.getCurrentImage()
    
    def getPreviousImage(self) -> Optional[Path]:
        """Get the previous image in the sequence.
        
        Returns:
            The previous image path or None if no images are available.
        """
        if not self.image_paths:
            return None
            
        self.current_index = (self.current_index - 1) % len(self.image_paths)
        return self.getCurrentImage()
    
    def getRandomImage(self) -> Optional[Path]:
        """Get a random image from the available images.
        
        Returns:
            A random image path or None if no images are available.
        """
        if not self.image_paths:
            return None
            
        self.current_index = random.randint(0, len(self.image_paths) - 1)
        return self.getCurrentImage()
    
    def getImageCount(self) -> int:
        """Get the total number of available images.
        
        Returns:
            The number of available images.
        """
        return len(self.image_paths) 