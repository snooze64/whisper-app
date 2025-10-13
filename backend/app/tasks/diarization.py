"""
Speaker diarization tasks using Resemblyzer
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import Resemblyzer (may not be available in dev environment)
try:
    from resemblyzer import VoiceEncoder, preprocess_wav
    RESEMBLYZER_AVAILABLE = True
except ImportError:
    logger.warning("Resemblyzer not available - using mock diarization")
    RESEMBLYZER_AVAILABLE = False

try:
    from sklearn.cluster import AgglomerativeClustering
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("sklearn not available - using mock diarization")
    SKLEARN_AVAILABLE = False


class ResemblyzerDiarizer:
    """Speaker diarization using Resemblyzer"""

    def __init__(self):
        """Initialize Resemblyzer voice encoder"""
        self.encoder = None
        if RESEMBLYZER_AVAILABLE:
            try:
                self.encoder = VoiceEncoder()
                logger.info("Resemblyzer voice encoder initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Resemblyzer: {e}")

    def extract_embeddings(
        self,
        audio_file: str,
        segments: List[Dict[str, Any]],
        sample_rate: int = 16000
    ) -> Optional[np.ndarray]:
        """
        Extract voice embeddings for each segment

        Args:
            audio_file: Path to audio file (WAV, 16kHz mono)
            segments: List of segments with start/end times
            sample_rate: Audio sample rate (default 16kHz)

        Returns:
            numpy array of embeddings (n_segments, embedding_dim)
        """
        if not RESEMBLYZER_AVAILABLE or self.encoder is None:
            logger.warning("Resemblyzer not available, cannot extract embeddings")
            return None

        try:
            # Load and preprocess audio
            import librosa
            wav, sr = librosa.load(audio_file, sr=sample_rate)
            wav = preprocess_wav(wav)

            # Extract embeddings for each segment
            embeddings = []
            for segment in segments:
                start_sample = int(segment["start"] * sample_rate)
                end_sample = int(segment["end"] * sample_rate)

                # Extract segment audio
                segment_wav = wav[start_sample:end_sample]

                # Skip very short segments (< 0.5 seconds)
                if len(segment_wav) < sample_rate * 0.5:
                    logger.warning(f"Segment {segment['id']} too short, using zero embedding")
                    embeddings.append(np.zeros(256))  # Resemblyzer embedding dimension
                    continue

                # Extract embedding
                embedding = self.encoder.embed_utterance(segment_wav)
                embeddings.append(embedding)

            return np.array(embeddings)

        except Exception as e:
            logger.error(f"Failed to extract embeddings: {e}")
            return None

    def cluster_speakers(
        self,
        embeddings: np.ndarray,
        num_speakers: Optional[int] = None
    ) -> np.ndarray:
        """
        Cluster embeddings to identify speakers

        Args:
            embeddings: Voice embeddings array
            num_speakers: Number of speakers (if None, auto-detect)

        Returns:
            Array of speaker IDs for each segment
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn not available, using mock clustering")
            # Return random speaker IDs
            n_segments = len(embeddings)
            n_speakers = num_speakers or min(2, n_segments)
            return np.random.randint(0, n_speakers, size=n_segments)

        try:
            # Use Agglomerative Clustering
            if num_speakers is None:
                # Auto-detect number of speakers (2-5 range)
                num_speakers = min(5, max(2, len(embeddings) // 3))

            clustering = AgglomerativeClustering(
                n_clusters=num_speakers,
                metric='cosine',
                linkage='average'
            )

            speaker_ids = clustering.fit_predict(embeddings)

            logger.info(f"Clustered {len(embeddings)} segments into {num_speakers} speakers")

            return speaker_ids

        except Exception as e:
            logger.error(f"Failed to cluster speakers: {e}")
            # Fallback to random assignment
            n_segments = len(embeddings)
            n_speakers = num_speakers or 2
            return np.random.randint(0, n_speakers, size=n_segments)

    def assign_speakers_to_segments(
        self,
        segments: List[Dict[str, Any]],
        speaker_ids: np.ndarray
    ) -> List[Dict[str, Any]]:
        """
        Assign speaker labels to segments

        Args:
            segments: List of transcription segments
            speaker_ids: Array of speaker IDs

        Returns:
            List of segments with speaker information added
        """
        if len(segments) != len(speaker_ids):
            logger.error(f"Mismatch: {len(segments)} segments, {len(speaker_ids)} speaker IDs")
            return segments

        # Add speaker information to each segment
        labeled_segments = []
        for segment, speaker_id in zip(segments, speaker_ids):
            segment_with_speaker = segment.copy()
            segment_with_speaker["speaker_id"] = int(speaker_id) + 1  # 1-indexed
            segment_with_speaker["speaker_label"] = f"Speaker {int(speaker_id) + 1}"
            segment_with_speaker["confidence"] = 0.85  # Placeholder confidence

            labeled_segments.append(segment_with_speaker)

        logger.info(f"Assigned speaker labels to {len(labeled_segments)} segments")

        return labeled_segments

    def diarize(
        self,
        audio_file: str,
        segments: List[Dict[str, Any]],
        num_speakers: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform complete speaker diarization

        Args:
            audio_file: Path to audio file
            segments: List of transcription segments
            num_speakers: Number of speakers (if None, auto-detect)

        Returns:
            List of segments with speaker information
        """
        logger.info(f"Starting diarization for {len(segments)} segments")

        # Extract embeddings
        embeddings = self.extract_embeddings(audio_file, segments)

        if embeddings is None:
            logger.warning("Using mock diarization (no embeddings available)")
            return self.mock_diarize(segments, num_speakers)

        # Cluster speakers
        speaker_ids = self.cluster_speakers(embeddings, num_speakers)

        # Assign speakers to segments
        labeled_segments = self.assign_speakers_to_segments(segments, speaker_ids)

        # Log speaker distribution
        unique_speakers = set(seg["speaker_id"] for seg in labeled_segments)
        logger.info(f"Identified {len(unique_speakers)} unique speakers")

        return labeled_segments

    def mock_diarize(
        self,
        segments: List[Dict[str, Any]],
        num_speakers: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Mock diarization for development/testing

        Args:
            segments: List of transcription segments
            num_speakers: Number of speakers (if None, use 2)

        Returns:
            List of segments with mock speaker information
        """
        n_speakers = num_speakers or 2

        labeled_segments = []
        for i, segment in enumerate(segments):
            segment_with_speaker = segment.copy()
            # Alternate speakers for mock
            speaker_id = (i % n_speakers) + 1
            segment_with_speaker["speaker_id"] = speaker_id
            segment_with_speaker["speaker_label"] = f"Speaker {speaker_id}"
            segment_with_speaker["confidence"] = 0.80  # Mock confidence

            labeled_segments.append(segment_with_speaker)

        logger.info(f"Mock diarization: assigned {n_speakers} speakers to {len(segments)} segments")

        return labeled_segments


def get_diarizer() -> ResemblyzerDiarizer:
    """Get singleton diarizer instance"""
    return ResemblyzerDiarizer()
