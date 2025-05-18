"""Configuration settings for the Smart Picture Display application."""
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IMAGES_DIR = BASE_DIR / "images"
CACHE_DIR = BASE_DIR / ".cache"
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.pickle"

# Create directories if they don't exist
IMAGES_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# Google Drive settings
DRIVE_FOLDER_ID = "root"  # Default to root, should be overridden by user
GOOGLE_API_SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Application settings
APP_NAME = "Smart Picture Display"
SLIDESHOW_INTERVAL = 5  # seconds
SYNC_INTERVAL = 10  # minutes
MAX_STORAGE_PERCENT = 50  # maximum percentage of disk to use

# Supported image extensions
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}

# UI settings
FULLSCREEN_THRESHOLD = 800  # px - If screen height is less than this, use fullscreen 