"""
Audio extraction tasks using FFmpeg

Extracts audio from video files and converts to format suitable for Whisper processing.
"""
import logging
import subprocess
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AudioExtractionError(Exception):
    """Audio extraction error"""
    pass


def extract_audio(
    input_file: str,
    output_file: str,
    sample_rate: int = 16000,
    channels: int = 1
) -> str:
    """
    Extract audio from video/audio file and convert to WAV format

    Args:
        input_file: Path to input file (MP3, WAV, MP4, etc.)
        output_file: Path to output WAV file
        sample_rate: Target sample rate (default: 16000 Hz for Whisper)
        channels: Number of audio channels (default: 1 for mono)

    Returns:
        Path to extracted audio file

    Raises:
        AudioExtractionError: If extraction fails
    """
    logger.info(f"Extracting audio from {input_file} to {output_file}")

    # Ensure output directory exists
    output_dir = Path(output_file).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if input file exists
    if not os.path.exists(input_file):
        raise AudioExtractionError(f"Input file not found: {input_file}")

    # FFmpeg command
    # -i: input file
    # -ar: sample rate
    # -ac: audio channels
    # -vn: no video
    # -y: overwrite output file
    command = [
        "ffmpeg",
        "-i", input_file,
        "-ar", str(sample_rate),
        "-ac", str(channels),
        "-vn",  # No video
        "-y",   # Overwrite output file
        output_file
    ]

    try:
        # Run FFmpeg
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=300  # 5 minutes timeout
        )

        logger.info(f"Audio extraction successful: {output_file}")
        logger.debug(f"FFmpeg stdout: {result.stdout}")

        # Verify output file was created
        if not os.path.exists(output_file):
            raise AudioExtractionError("Output file was not created")

        # Check file size
        file_size = os.path.getsize(output_file)
        if file_size == 0:
            raise AudioExtractionError("Output file is empty")

        logger.info(f"Extracted audio file size: {file_size / (1024 * 1024):.2f} MB")

        return output_file

    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timeout - file too large or processing too slow")
        raise AudioExtractionError("Audio extraction timeout (>5 minutes)")

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed with return code {e.returncode}")
        logger.error(f"FFmpeg stderr: {e.stderr}")
        raise AudioExtractionError(f"FFmpeg error: {e.stderr}")

    except Exception as e:
        logger.error(f"Unexpected error during audio extraction: {e}")
        raise AudioExtractionError(f"Audio extraction failed: {str(e)}")


def get_audio_duration(audio_file: str) -> Optional[float]:
    """
    Get duration of audio file in seconds

    Args:
        audio_file: Path to audio file

    Returns:
        Duration in seconds or None if failed
    """
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_file
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )

        duration = float(result.stdout.strip())
        logger.info(f"Audio duration: {duration:.2f} seconds ({duration / 60:.2f} minutes)")
        return duration

    except Exception as e:
        logger.error(f"Failed to get audio duration: {e}")
        return None


def get_audio_info(audio_file: str) -> Optional[dict]:
    """
    Get audio file information

    Args:
        audio_file: Path to audio file

    Returns:
        Dictionary with audio info or None if failed
    """
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration,size,bit_rate:stream=codec_name,sample_rate,channels",
        "-of", "json",
        audio_file
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )

        import json
        info = json.loads(result.stdout)
        logger.info(f"Audio info: {info}")
        return info

    except Exception as e:
        logger.error(f"Failed to get audio info: {e}")
        return None


def cleanup_temp_audio(audio_file: str):
    """
    Delete temporary audio file

    Args:
        audio_file: Path to audio file to delete
    """
    try:
        if os.path.exists(audio_file):
            os.remove(audio_file)
            logger.info(f"Deleted temporary audio file: {audio_file}")
    except Exception as e:
        logger.error(f"Failed to delete temporary audio file: {e}")
