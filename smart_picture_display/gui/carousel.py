"""Image carousel widget for the Smart Picture Display application."""
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QPalette, QColor, QIcon
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
    QPushButton, QSizePolicy, QFrame
)
from pathlib import Path
from typing import Optional, Callable
import os

from ..config import SLIDESHOW_INTERVAL
from ..services.image_loader import ImageLoader
from ..utils.logger import logger

class ImageDisplay(QLabel):
    """Custom widget for displaying images with appropriate scaling."""
    
    def __init__(self, parent=None):
        """Initialize the image display widget.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 200)
        
        # Set up styling
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background-color: black;")
        
        # Current image path and pixmap
        self.current_image_path: Optional[Path] = None
        self.original_pixmap: Optional[QPixmap] = None
    
    def setImage(self, image_path: Optional[Path]) -> bool:
        """Set the image to display.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            True if the image was loaded successfully, False otherwise.
        """
        if not image_path or not image_path.exists():
            self.clear()
            self.current_image_path = None
            self.original_pixmap = None
            return False
        
        try:
            pixmap = QPixmap(str(image_path))
            if pixmap.isNull():
                logger.error(f"Failed to load image: {image_path}")
                return False
            
            self.current_image_path = image_path
            self.original_pixmap = pixmap
            self.updatePixmap()
            return True
            
        except Exception as e:
            logger.error(f"Error loading image {image_path}: {e}")
            return False
    
    def updatePixmap(self) -> None:
        """Update the displayed pixmap with appropriate scaling."""
        if not self.original_pixmap:
            return
            
        # Scale the pixmap to fit the widget while maintaining aspect ratio
        scaled_pixmap = self.original_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.setPixmap(scaled_pixmap)
    
    def resizeEvent(self, event) -> None:
        """Handle resize events to properly scale the image.
        
        Args:
            event: The resize event.
        """
        super().resizeEvent(event)
        self.updatePixmap()


class ImageCarousel(QWidget):
    """Widget for displaying images in a carousel format with controls."""
    
    # Signal emitted when the image changes
    imageChanged = pyqtSignal(Path)
    
    def __init__(self, image_loader: ImageLoader, parent=None):
        """Initialize the image carousel.
        
        Args:
            image_loader: The image loader service.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.image_loader = image_loader
        self.slideshow_active = False
        self.slideshow_timer = QTimer(self)
        self.slideshow_timer.timeout.connect(self.nextImage)
        self.slideshow_interval = SLIDESHOW_INTERVAL * 1000  # Convert to milliseconds
        
        self.setupUI()
        
        # Load the first image if available
        self.refreshImages()
    
    def setupUI(self) -> None:
        """Set up the user interface."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Image display
        self.image_display = ImageDisplay(self)
        layout.addWidget(self.image_display, 1)
        
        # Controls area
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(10, 5, 10, 5)
        controls_layout.setSpacing(10)
        
        # Previous button
        self.prev_button = self._createButton("Previous", self.previousImage, "◀")
        controls_layout.addWidget(self.prev_button)
        
        # Random button
        self.random_button = self._createButton("Random", self.randomImage, "🔀")
        controls_layout.addWidget(self.random_button)
        
        # Slideshow button
        self.slideshow_button = self._createButton("Slideshow", self.toggleSlideshow, "▶")
        controls_layout.addWidget(self.slideshow_button)
        
        # Next button
        self.next_button = self._createButton("Next", self.nextImage, "▶")
        controls_layout.addWidget(self.next_button)
        
        # Add controls to main layout
        controls_frame = QFrame()
        controls_frame.setLayout(controls_layout)
        controls_frame.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
        layout.addWidget(controls_frame)
        
        # Set up keyboard shortcuts
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def _createButton(self, tooltip: str, slot: Callable, text: str) -> QPushButton:
        """Create a styled button for the controls.
        
        Args:
            tooltip: Button tooltip text.
            slot: Function to call when clicked.
            text: Button text/icon.
            
        Returns:
            The created button.
        """
        button = QPushButton(text)
        button.setToolTip(tooltip)
        button.clicked.connect(slot)
        button.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: transparent;
                border: none;
                font-size: 24px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 30);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 50);
            }
        """)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # Don't take focus from main widget
        return button
    
    def refreshImages(self) -> None:
        """Refresh the image list and display the first image."""
        self.image_loader.refreshImageList()
        if self.image_loader.getImageCount() > 0:
            self.displayCurrentImage()
        else:
            self.image_display.clear()
            self.image_display.setText("No images available")
    
    def displayCurrentImage(self) -> None:
        """Display the current image from the loader."""
        current_image = self.image_loader.getCurrentImage()
        if current_image and self.image_display.setImage(current_image):
            self.imageChanged.emit(current_image)
        else:
            self.image_display.clear()
            self.image_display.setText("Error loading image")
    
    def nextImage(self) -> None:
        """Display the next image in the sequence."""
        if self.image_loader.getImageCount() > 0:
            self.image_loader.getNextImage()
            self.displayCurrentImage()
    
    def previousImage(self) -> None:
        """Display the previous image in the sequence."""
        if self.image_loader.getImageCount() > 0:
            self.image_loader.getPreviousImage()
            self.displayCurrentImage()
    
    def randomImage(self) -> None:
        """Display a random image."""
        if self.image_loader.getImageCount() > 0:
            self.image_loader.getRandomImage()
            self.displayCurrentImage()
    
    def toggleSlideshow(self) -> None:
        """Toggle the slideshow on/off."""
        self.slideshow_active = not self.slideshow_active
        
        if self.slideshow_active:
            self.slideshow_button.setText("⏸")
            self.slideshow_button.setToolTip("Pause Slideshow")
            self.slideshow_timer.start(self.slideshow_interval)
        else:
            self.slideshow_button.setText("▶")
            self.slideshow_button.setToolTip("Start Slideshow")
            self.slideshow_timer.stop()
    
    def keyPressEvent(self, event) -> None:
        """Handle key press events for navigation.
        
        Args:
            event: The key press event.
        """
        key = event.key()
        
        if key == Qt.Key.Key_Right or key == Qt.Key.Key_Space:
            self.nextImage()
        elif key == Qt.Key.Key_Left:
            self.previousImage()
        elif key == Qt.Key.Key_R:
            self.randomImage()
        elif key == Qt.Key.Key_S:
            self.toggleSlideshow()
        elif key == Qt.Key.Key_Escape:
            if self.slideshow_active:
                self.toggleSlideshow()
            else:
                # Let the main window handle this for fullscreen toggle
                event.ignore()
        else:
            super().keyPressEvent(event) 