"""
File service for handling file operations
"""
import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException

from app.core.config import settings


class FileService:
    """File service for upload, validation, and storage"""

    @staticmethod
    def validate_file_size(file_size: int) -> None:
        """
        Validate file size

        Args:
            file_size: File size in bytes

        Raises:
            HTTPException: If file size exceeds limit
        """
        if file_size > settings.MAX_FILE_SIZE:
            max_size_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {max_size_mb}MB"
            )

    @staticmethod
    def validate_file_format(filename: str) -> str:
        """
        Validate file format and return format

        Args:
            filename: Original filename

        Returns:
            File format (extension without dot)

        Raises:
            HTTPException: If file format is not allowed
        """
        file_ext = Path(filename).suffix.lower().lstrip('.')

        allowed_formats = (
            settings.ALLOWED_AUDIO_FORMATS +
            settings.ALLOWED_VIDEO_FORMATS
        )

        if file_ext not in allowed_formats:
            raise HTTPException(
                status_code=400,
                detail=f"File format '{file_ext}' is not allowed. "
                       f"Allowed formats: {', '.join(allowed_formats)}"
            )

        return file_ext

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal attacks

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove any path components
        filename = Path(filename).name

        # Remove or replace dangerous characters
        dangerous_chars = ['/', '\\', '..', '\x00']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')

        return filename

    @staticmethod
    async def save_upload_file(
        file: UploadFile,
        user_id: int
    ) -> tuple[str, str, int]:
        """
        Save uploaded file to storage

        Args:
            file: Uploaded file object
            user_id: User ID for organizing files

        Returns:
            Tuple of (file_path, sanitized_filename, file_size)

        Raises:
            HTTPException: If file operation fails
        """
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Get file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning

        # Validate file size
        FileService.validate_file_size(file_size)

        # Validate and get format
        file_format = FileService.validate_file_format(file.filename)

        # Sanitize filename
        safe_filename = FileService.sanitize_filename(file.filename)

        # Generate unique filename
        unique_id = str(uuid.uuid4())
        stored_filename = f"{unique_id}_{safe_filename}"

        # Create user-specific directory
        upload_dir = Path(settings.UPLOAD_DIR) / str(user_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Full file path
        file_path = upload_dir / stored_filename

        try:
            # Save file
            with open(file_path, "wb") as f:
                while True:
                    chunk = await file.read(1024 * 1024)  # Read 1MB at a time
                    if not chunk:
                        break
                    f.write(chunk)

            return str(file_path), safe_filename, file_size

        except Exception as e:
            # Clean up file if save failed
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save file: {str(e)}"
            )

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """
        Delete file from storage

        Args:
            file_path: Path to file

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            return False

    @staticmethod
    def get_file_info(file_path: str) -> Optional[dict]:
        """
        Get file information

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file info or None if file doesn't exist
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return None

            stat = path.stat()
            return {
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "exists": True
            }
        except Exception as e:
            print(f"Error getting file info {file_path}: {e}")
            return None
