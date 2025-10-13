"""
Subtitle file generation utilities
Supports SRT and VTT formats
"""
from typing import List, Dict, Any
from datetime import timedelta


def format_timestamp_srt(seconds: float) -> str:
    """
    Format timestamp for SRT format (HH:MM:SS,mmm)

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    td = timedelta(seconds=seconds)
    hours = int(td.total_seconds() // 3600)
    minutes = int((td.total_seconds() % 3600) // 60)
    secs = int(td.total_seconds() % 60)
    millis = int((td.total_seconds() % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_timestamp_vtt(seconds: float) -> str:
    """
    Format timestamp for WebVTT format (HH:MM:SS.mmm)

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    td = timedelta(seconds=seconds)
    hours = int(td.total_seconds() // 3600)
    minutes = int((td.total_seconds() % 3600) // 60)
    secs = int(td.total_seconds() % 60)
    millis = int((td.total_seconds() % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def generate_srt(segments: List[Dict[str, Any]]) -> str:
    """
    Generate SRT subtitle file content from segments

    Args:
        segments: List of segment dictionaries with start, end, text, speaker_label

    Returns:
        SRT formatted string

    Example SRT format:
        1
        00:00:00,000 --> 00:00:05,500
        [Speaker 1] Hello, welcome to the meeting.

        2
        00:00:05,500 --> 00:00:10,000
        [Speaker 2] Thank you for inviting me.
    """
    srt_content = []

    for idx, segment in enumerate(segments, start=1):
        start_time = format_timestamp_srt(segment.get("start", 0))
        end_time = format_timestamp_srt(segment.get("end", 0))
        text = segment.get("text", "").strip()
        speaker_label = segment.get("speaker_label", "")

        # Add speaker label if available
        if speaker_label:
            text = f"[{speaker_label}] {text}"

        # Skip empty segments
        if not text:
            continue

        # Format: sequence number, timestamps, text
        srt_content.append(f"{idx}")
        srt_content.append(f"{start_time} --> {end_time}")
        srt_content.append(text)
        srt_content.append("")  # Empty line between subtitles

    return "\n".join(srt_content)


def generate_vtt(segments: List[Dict[str, Any]]) -> str:
    """
    Generate WebVTT subtitle file content from segments

    Args:
        segments: List of segment dictionaries with start, end, text, speaker_label

    Returns:
        WebVTT formatted string

    Example VTT format:
        WEBVTT

        00:00:00.000 --> 00:00:05.500
        <v Speaker 1>Hello, welcome to the meeting.

        00:00:05.500 --> 00:00:10.000
        <v Speaker 2>Thank you for inviting me.
    """
    vtt_content = ["WEBVTT", ""]  # VTT header

    for segment in segments:
        start_time = format_timestamp_vtt(segment.get("start", 0))
        end_time = format_timestamp_vtt(segment.get("end", 0))
        text = segment.get("text", "").strip()
        speaker_label = segment.get("speaker_label", "")

        # Skip empty segments
        if not text:
            continue

        # Add timestamps
        vtt_content.append(f"{start_time} --> {end_time}")

        # Add speaker voice tag if available
        if speaker_label:
            vtt_content.append(f"<v {speaker_label}>{text}")
        else:
            vtt_content.append(text)

        vtt_content.append("")  # Empty line between subtitles

    return "\n".join(vtt_content)


def save_subtitle_file(
    segments: List[Dict[str, Any]],
    file_path: str,
    format: str = "srt"
) -> str:
    """
    Generate and save subtitle file

    Args:
        segments: List of segment dictionaries
        file_path: Base file path (without extension)
        format: Subtitle format ('srt' or 'vtt')

    Returns:
        Full path to the saved subtitle file

    Raises:
        ValueError: If format is not 'srt' or 'vtt'
    """
    format = format.lower()

    if format == "srt":
        content = generate_srt(segments)
        full_path = f"{file_path}.srt"
    elif format == "vtt":
        content = generate_vtt(segments)
        full_path = f"{file_path}.vtt"
    else:
        raise ValueError(f"Unsupported subtitle format: {format}. Use 'srt' or 'vtt'.")

    # Write to file
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

    return full_path
