"""Main application window for the Smart Picture Display."""
import sys
import os
from pathlib import Path
from typing import Optional, Tuple
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QGuiApplication
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QVBoxLayout, QWidget, 
    QLabel, QStatusBar, QMessageBox
)

from ..config import APP_NAME, FULLSCREEN_THRESHOLD, SYNC_INTERVAL
from ..services.image_loader import ImageLoader
from ..services.drive_sync import DriveSync
from ..services.scheduler import TaskScheduler
from .carousel import ImageCarousel
from ..utils.logger import logger

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, 
                 image_loader: ImageLoader, 
                 drive_sync: DriveSync,
                 scheduler: TaskScheduler):
        """Initialize the main window.
        
        Args:
            image_loader: The image loader service.
            drive_sync: The Drive sync service.
            scheduler: The task scheduler service.
        """
        super().__init__()
        self.image_loader = image_loader
        self.drive_sync = drive_sync
        self.scheduler = scheduler
        self.is_fullscreen = False
        
        self.setupUI()
        self.setupSync()
        
        # Set window state based on screen size
        self.adjustWindowMode()
    
    def setupUI(self) -> None:
        """Set up the user interface."""
        # Basic window setup
        self.setWindowTitle(APP_NAME)
        self.resize(800, 600)
        
        # Central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create and add image carousel
        self.carousel = ImageCarousel(self.image_loader)
        layout.addWidget(self.carousel)
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Set focus policy for keyboard navigation
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def setupSync(self) -> None:
        """Set up Google Drive synchronization."""
        # Schedule periodic sync
        self.scheduler.scheduleTask(
            "drive_sync",
            self.syncDrive,
            minutes=SYNC_INTERVAL,
            run_immediately=True
        )
    
    def syncDrive(self) -> None:
        """Synchronize images from Google Drive."""
        try:
            self.status_bar.showMessage("Syncing with Google Drive...")
            files_synced, errors = self.drive_sync.syncDriveImages()
            
            if files_synced > 0:
                self.carousel.refreshImages()
                self.status_bar.showMessage(f"Sync completed: {files_synced} new images downloaded", 5000)
            else:
                self.status_bar.showMessage("Sync completed: No new images", 5000)
                
        except Exception as e:
            logger.error(f"Error syncing with Drive: {e}")
            self.status_bar.showMessage(f"Sync error: {str(e)}", 5000)
    
    def adjustWindowMode(self) -> None:
        """Adjust window mode (fullscreen/windowed) based on screen size."""
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
            
        screen_geometry = screen.geometry()
        screen_height = screen_geometry.height()
        
        # Set fullscreen mode on smaller screens (likely Raspberry Pi displays)
        if screen_height < FULLSCREEN_THRESHOLD:
            self.toggleFullscreen(True)
        else:
            # On larger screens, center the window
            self.center()
    
    def center(self) -> None:
        """Center the window on the screen."""
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
            
        center_point = screen.geometry().center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
    
    def toggleFullscreen(self, enabled: Optional[bool] = None) -> None:
        """Toggle fullscreen mode.
        
        Args:
            enabled: Explicitly set fullscreen state, or toggle if None.
        """
        if enabled is None:
            self.is_fullscreen = not self.is_fullscreen
        else:
            self.is_fullscreen = enabled
            
        if self.is_fullscreen:
            self.showFullScreen()
            self.status_bar.hide()
        else:
            self.showNormal()
            self.status_bar.show()
    
    def keyPressEvent(self, event) -> None:
        """Handle key press events.
        
        Args:
            event: The key press event.
        """
        key = event.key()
        
        if key == Qt.Key.Key_F11 or key == Qt.Key.Key_F:
            self.toggleFullscreen()
        elif key == Qt.Key.Key_Escape and self.is_fullscreen:
            self.toggleFullscreen(False)
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event) -> None:
        """Handle window close event, cleaning up resources.
        
        Args:
            event: The close event.
        """
        # Shut down the scheduler
        if hasattr(self, 'scheduler'):
            self.scheduler.stop()
            
        super().closeEvent(event)


def runApplication() -> None:
    """Initialize and run the application."""
    # Create QApplication instance
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    
    # Initialize services
    image_loader = ImageLoader()
    drive_sync = DriveSync()
    scheduler = TaskScheduler()
    
    # Create and show the main window
    main_window = MainWindow(image_loader, drive_sync, scheduler)
    main_window.show()
    
    # Run the application
    sys.exit(app.exec()) 