"""
HuggingFace Transformers-based Whisper implementation for CUDA 11.4 compatibility

This implementation uses transformers.WhisperProcessor and WhisperForConditionalGeneration
instead of faster-whisper, enabling compatibility with CUDA 11.4 environments.

Performance Note:
- transformers: Standard PyTorch implementation, slightly slower than faster-whisper
- faster-whisper: CTranslate2 optimization, 2-4x faster but requires CUDA 11.8+

Memory Note:
- transformers may use 1.5-2x more VRAM than faster-whisper
- For CUDA 11.4 environments where faster-whisper is not available
"""
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import torch
import numpy as np

logger = logging.getLogger(__name__)

# Try to import transformers
try:
    from transformers import (
        WhisperProcessor,
        WhisperForConditionalGeneration,
        pipeline
    )
    TRANSFORMERS_AVAILABLE = True
    logger.info("transformers library available")
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers library not available")


class WhisperTranscriberTransformers:
    """
    Whisper transcription wrapper using HuggingFace Transformers

    This implementation is compatible with CUDA 11.4 environments.
    """

    def __init__(
        self,
        model_name: str = "openai/whisper-large-v3-turbo",
        device: str = "cuda",
        torch_dtype: str = "float16"
    ):
        """
        Initialize Whisper transcriber with transformers backend

        Args:
            model_name: HuggingFace model ID (e.g., "openai/whisper-large-v3")
            device: Device to use ("cuda" or "cpu")
            torch_dtype: Torch data type ("float16", "float32", or "int8")
        """
        self.model_name = self._convert_model_name(model_name)
        self.device = device

        # Determine torch dtype
        # Note: Whisper models require floating point dtypes
        if torch_dtype == "float16" and device == "cuda":
            self.torch_dtype = torch.float16
        elif torch_dtype == "int8":
            # int8 is not supported for model weights in transformers Whisper
            # Fall back to float32 for CPU compatibility
            logger.warning(
                f"int8 dtype not supported for Whisper models, using float32 instead"
            )
            self.torch_dtype = torch.float32
        else:
            self.torch_dtype = torch.float32

        self.processor = None
        self.model = None

        logger.info(
            f"Initializing Whisper transcriber (transformers): "
            f"model={self.model_name}, device={device}, dtype={torch_dtype}"
        )

    def _convert_model_name(self, model_name: str) -> str:
        """
        Convert faster-whisper model name to HuggingFace model ID

        Args:
            model_name: faster-whisper model name (e.g., "large-v3-turbo", "large-v3")

        Returns:
            HuggingFace model ID (e.g., "openai/whisper-large-v3-turbo")
        """
        # Mapping from faster-whisper names to HuggingFace model IDs
        model_mapping = {
            "tiny": "openai/whisper-tiny",
            "tiny.en": "openai/whisper-tiny.en",
            "base": "openai/whisper-base",
            "base.en": "openai/whisper-base.en",
            "small": "openai/whisper-small",
            "small.en": "openai/whisper-small.en",
            "medium": "openai/whisper-medium",
            "medium.en": "openai/whisper-medium.en",
            "large": "openai/whisper-large",
            "large-v1": "openai/whisper-large-v1",
            "large-v2": "openai/whisper-large-v2",
            "large-v3": "openai/whisper-large-v3",
            "large-v3-turbo": "openai/whisper-large-v3-turbo"
        }

        # If already a HuggingFace ID, return as-is
        if model_name.startswith("openai/"):
            return model_name

        # Otherwise, convert from faster-whisper name
        return model_mapping.get(model_name, f"openai/whisper-{model_name}")

    def load_model(self):
        """Load Whisper model and processor"""
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("transformers library not available - skipping model load")
            return

        try:
            logger.info(f"Loading Whisper model: {self.model_name}")

            # Check GPU availability
            if self.device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA not available, falling back to CPU")
                self.device = "cpu"
                self.torch_dtype = torch.float32

            # Load processor
            logger.info("Loading Whisper processor...")
            self.processor = WhisperProcessor.from_pretrained(self.model_name)

            # Load model
            logger.info(f"Loading Whisper model on device={self.device}, dtype={self.torch_dtype}...")
            self.model = WhisperForConditionalGeneration.from_pretrained(
                self.model_name,
                torch_dtype=self.torch_dtype,
                low_cpu_mem_usage=True,
                use_safetensors=True
            )
            self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode

            # Log memory usage if on CUDA
            if self.device == "cuda":
                memory_allocated = torch.cuda.memory_allocated() / 1024**3  # GB
                memory_reserved = torch.cuda.memory_reserved() / 1024**3  # GB
                logger.info(
                    f"GPU memory: allocated={memory_allocated:.2f}GB, "
                    f"reserved={memory_reserved:.2f}GB"
                )

            logger.info("Whisper model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def transcribe(
        self,
        audio_file: str,
        language: Optional[str] = None,
        task: str = "transcribe",
        beam_size: int = 5,
        vad_filter: bool = True,
        vad_parameters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Transcribe audio file

        Args:
            audio_file: Path to audio file
            language: Language code (e.g., "ja", "en") or None for auto-detection
            task: Task type ("transcribe" or "translate")
            beam_size: Beam size for decoding
            vad_filter: Enable VAD (Voice Activity Detection) filter (not fully supported)
            vad_parameters: VAD parameters (not fully supported)

        Returns:
            List of segments with transcription results
        """
        if not TRANSFORMERS_AVAILABLE or self.model is None or self.processor is None:
            # Return mock data for development
            logger.warning("Using mock transcription (transformers backend)")
            return self._mock_transcribe(audio_file)

        try:
            logger.info(f"Transcribing audio file: {audio_file}")
            logger.info(
                f"Parameters: language={language}, task={task}, "
                f"beam_size={beam_size}, vad_filter={vad_filter}"
            )

            # Load audio file
            import librosa
            audio_array, sampling_rate = librosa.load(audio_file, sr=16000, mono=True)

            # Get audio duration
            duration = len(audio_array) / sampling_rate
            logger.info(f"Audio duration: {duration:.2f} seconds")

            # Process audio
            input_features = self.processor(
                audio_array,
                sampling_rate=sampling_rate,
                return_tensors="pt"
            ).input_features

            # Move to device
            input_features = input_features.to(self.device)
            if self.torch_dtype == torch.float16:
                input_features = input_features.half()

            # Set forced decoder IDs for language and task
            forced_decoder_ids = self.processor.get_decoder_prompt_ids(
                language=language,
                task=task
            )

            # Generate transcription with timestamps
            with torch.no_grad():
                predicted_ids = self.model.generate(
                    input_features,
                    forced_decoder_ids=forced_decoder_ids,
                    return_timestamps=True,
                    num_beams=beam_size,
                    max_new_tokens=448,  # Whisper's max length
                )

            # Decode transcription
            transcription = self.processor.batch_decode(
                predicted_ids,
                skip_special_tokens=False,
                decode_with_timestamps=True
            )[0]

            # Parse segments from transcription
            segments = self._parse_segments(transcription, duration)

            logger.info(f"Transcription complete: {len(segments)} segments")
            return segments

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def _parse_segments(
        self,
        transcription: str,
        duration: float
    ) -> List[Dict[str, Any]]:
        """
        Parse segments from Whisper transcription with timestamps

        Args:
            transcription: Raw transcription with timestamps
            duration: Audio duration in seconds

        Returns:
            List of segment dictionaries
        """
        # Parse Whisper timestamp format: <|0.00|> text <|5.50|> text <|10.00|>
        import re

        # Pattern to match timestamps and text
        pattern = r'<\|(\d+\.?\d*)\|>(.*?)(?=<\||\Z)'
        matches = re.findall(pattern, transcription, re.DOTALL)

        segments = []
        for i in range(len(matches)):
            if i == len(matches) - 1:
                # Last segment
                start_time = float(matches[i][0])
                text = matches[i][1].strip()
                end_time = duration
            else:
                # Regular segment
                start_time = float(matches[i][0])
                text = matches[i][1].strip()
                end_time = float(matches[i + 1][0])

            # Skip empty segments
            if not text or text == "":
                continue

            segments.append({
                "id": len(segments),
                "start": start_time,
                "end": end_time,
                "text": text,
                "avg_logprob": -0.3,  # Dummy value (transformers doesn't provide this)
                "no_speech_prob": 0.1,  # Dummy value (transformers doesn't provide this)
                "words": []  # Word-level timestamps not supported in this implementation
            })

        # If no segments parsed (might happen with simple transcription), create one segment
        if not segments and transcription.strip():
            # Remove special tokens
            clean_text = re.sub(r'<\|.*?\|>', '', transcription).strip()
            if clean_text:
                segments.append({
                    "id": 0,
                    "start": 0.0,
                    "end": duration,
                    "text": clean_text,
                    "avg_logprob": -0.3,
                    "no_speech_prob": 0.1,
                    "words": []
                })

        return segments

    def _mock_transcribe(self, audio_file: str) -> List[Dict[str, Any]]:
        """
        Mock transcription for development environment

        Args:
            audio_file: Path to audio file

        Returns:
            Mock transcription segments
        """
        # Get audio duration
        try:
            import librosa
            audio_array, _ = librosa.load(audio_file, sr=16000, mono=True)
            duration = len(audio_array) / 16000
        except:
            duration = 60.0  # Default to 60 seconds if unable to load

        # Generate mock segments (every 5 seconds)
        segments = []
        num_segments = int(duration / 5) + 1

        for i in range(num_segments):
            start = i * 5.0
            end = min((i + 1) * 5.0, duration)

            segments.append({
                "id": i,
                "start": start,
                "end": end,
                "text": f"これはモック文字起こしセグメント {i + 1} です（transformers backend）",
                "avg_logprob": -0.3,
                "no_speech_prob": 0.1,
                "words": []
            })

        logger.info(
            f"Mock transcription (transformers): {len(segments)} segments "
            f"for {duration:.2f} seconds"
        )
        return segments

    def cleanup(self):
        """Clean up model from memory"""
        if self.model is not None:
            del self.model
            self.model = None

        if self.processor is not None:
            del self.processor
            self.processor = None

        # Clear CUDA cache if on GPU
        if self.device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("Cleaned up Whisper model and cleared CUDA cache")
