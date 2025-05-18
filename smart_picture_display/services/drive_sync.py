"""Service for synchronizing images from Google Drive."""
import os
import io
import pickle
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import mimetypes

import google.auth.exceptions
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from ..config import (
    IMAGES_DIR, CREDENTIALS_PATH, TOKEN_PATH, 
    DRIVE_FOLDER_ID, GOOGLE_API_SCOPES, SUPPORTED_EXTENSIONS
)
from ..utils.logger import logger
from ..utils.storage import hasAvailableStorage, cleanupOldestImages

class DriveSync:
    """Handles synchronization of images from Google Drive."""
    
    def __init__(self, 
                 folder_id: str = DRIVE_FOLDER_ID,
                 credentials_path: Path = CREDENTIALS_PATH,
                 token_path: Path = TOKEN_PATH,
                 images_dir: Path = IMAGES_DIR):
        """Initialize the Drive sync service.
        
        Args:
            folder_id: The ID of the Google Drive folder to sync from.
            credentials_path: Path to the Google API credentials file.
            token_path: Path to save the authentication token.
            images_dir: Directory to save downloaded images.
        """
        self.folder_id = folder_id
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.images_dir = images_dir
        self.service = None
        self.is_authenticated = False
        self.last_sync_time = 0
        
        # Ensure the images directory exists
        self.images_dir.mkdir(parents=True, exist_ok=True)
    
    def authenticate(self) -> bool:
        """Authenticate with Google Drive API.
        
        Returns:
            True if authentication succeeded, False otherwise.
        """
        creds = None
        
        # Load existing token, if it exists
        if self.token_path.exists():
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                logger.error(f"Error loading token: {e}")
        
        # Check if credentials are valid or need refresh
        if creds and creds.valid:
            pass
        elif creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except google.auth.exceptions.RefreshError as e:
                logger.error(f"Failed to refresh token: {e}")
                creds = None
        else:
            # No valid credentials available, need to re-authenticate
            if not self.credentials_path.exists():
                logger.error(f"Credentials file not found: {self.credentials_path}")
                return False
                
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, GOOGLE_API_SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f"Authentication failed: {e}")
                return False
        
        # Save the credentials for next run
        try:
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        except Exception as e:
            logger.warning(f"Failed to save token: {e}")
        
        # Build the service
        try:
            self.service = build('drive', 'v3', credentials=creds)
            self.is_authenticated = True
            logger.info("Successfully authenticated with Google Drive")
            return True
        except Exception as e:
            logger.error(f"Failed to build Drive service: {e}")
            self.is_authenticated = False
            return False
    
    def listDriveImages(self) -> List[Dict[str, Any]]:
        """List all images in the configured Google Drive folder.
        
        Returns:
            A list of file metadata for images in the Drive folder.
        """
        if not self.is_authenticated and not self.authenticate():
            logger.error("Not authenticated, cannot list Drive images")
            return []
        
        try:
            # File mimetypes to search for
            query = f"'{self.folder_id}' in parents and (mimeType contains 'image/') and trashed = false"
            
            # List files in the folder
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType, size, modifiedTime)'
            ).execute()
            
            files = results.get('files', [])
            if not files:
                logger.info(f"No images found in Drive folder {self.folder_id}")
                return []
                
            logger.info(f"Found {len(files)} images in Drive folder")
            return files
            
        except HttpError as e:
            logger.error(f"Error listing Drive files: {e}")
            return []
    
    def downloadImage(self, file_id: str, file_name: str) -> bool:
        """Download a single image from Google Drive.
        
        Args:
            file_id: The ID of the file to download.
            file_name: The name to save the file as.
            
        Returns:
            True if the download succeeded, False otherwise.
        """
        if not self.is_authenticated and not self.authenticate():
            return False
        
        file_path = self.images_dir / file_name
        
        # Skip if file already exists (assuming we don't want duplicates)
        if file_path.exists():
            logger.debug(f"File already exists, skipping: {file_name}")
            return True
        
        try:
            # Get file metadata to check size
            file_metadata = self.service.files().get(fileId=file_id, fields='size').execute()
            file_size = int(file_metadata.get('size', 0))
            
            # Check if we have enough storage space
            if not hasAvailableStorage(file_size):
                # Try to clean up some space
                if cleanupOldestImages() == 0 or not hasAvailableStorage(file_size):
                    logger.error(f"Not enough storage space for {file_name} ({file_size} bytes)")
                    return False
            
            # Download the file
            request = self.service.files().get_media(fileId=file_id)
            
            with io.BytesIO() as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                
                while not done:
                    status, done = downloader.next_chunk()
                    
                # Write the downloaded file
                fh.seek(0)
                with open(file_path, 'wb') as f:
                    f.write(fh.read())
            
            logger.info(f"Downloaded: {file_name}")
            return True
            
        except HttpError as e:
            logger.error(f"Error downloading {file_name}: {e}")
            # Clean up partial download if it exists
            if file_path.exists():
                file_path.unlink()
            return False
    
    def syncDriveImages(self) -> Tuple[int, int]:
        """Sync images from Google Drive to local storage.
        
        Returns:
            A tuple of (number of files synced, number of errors).
        """
        # Update last sync time regardless of success
        self.last_sync_time = time.time()
        
        # Get list of images from Drive
        drive_files = self.listDriveImages()
        if not drive_files:
            return 0, 0
        
        # Track metrics
        files_synced = 0
        errors = 0
        
        # Filter files with supported extensions
        for file in drive_files:
            file_name = file['name']
            _, ext = os.path.splitext(file_name)
            
            # Skip unsupported file types
            if ext.lower() not in SUPPORTED_EXTENSIONS:
                continue
                
            # Download the file
            success = self.downloadImage(file['id'], file_name)
            if success:
                files_synced += 1
            else:
                errors += 1
                
            # Check if we've hit storage limits
            if not hasAvailableStorage():
                logger.warning("Storage limit reached, stopping sync")
                break
        
        logger.info(f"Sync completed: {files_synced} files downloaded, {errors} errors")
        return files_synced, errors

    def getTimeSinceLastSync(self) -> float:
        """Get the time since the last sync in seconds.
        
        Returns:
            Time in seconds since the last sync.
        """
        if self.last_sync_time == 0:
            return float('inf')
        return time.time() - self.last_sync_time 