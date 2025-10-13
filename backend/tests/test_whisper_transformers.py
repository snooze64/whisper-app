"""
Unit tests for WhisperTranscriberTransformers

Tests the transformers-based Whisper implementation for CUDA 11.4 compatibility.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import torch
import numpy as np


@pytest.fixture
def mock_transformers_available():
    """Mock transformers library availability"""
    with patch('app.tasks.whisper_transformers.TRANSFORMERS_AVAILABLE', True):
        yield


@pytest.fixture
def mock_processor():
    """Mock WhisperProcessor"""
    processor = Mock()
    processor.from_pretrained = Mock(return_value=processor)

    # Mock get_decoder_prompt_ids
    processor.get_decoder_prompt_ids = Mock(return_value=None)

    # Mock processing audio
    mock_features = Mock()
    mock_features.to = Mock(return_value=mock_features)
    mock_features.half = Mock(return_value=mock_features)
    processor.return_value.input_features = mock_features

    # Mock batch_decode
    processor.batch_decode = Mock(return_value=["<|0.00|> Test transcription <|5.50|>"])

    return processor


@pytest.fixture
def mock_model():
    """Mock WhisperForConditionalGeneration"""
    model = Mock()
    model.from_pretrained = Mock(return_value=model)
    model.to = Mock(return_value=model)
    model.eval = Mock(return_value=model)

    # Mock generate
    model.generate = Mock(return_value=torch.tensor([[1, 2, 3]]))

    return model


@pytest.fixture
def mock_audio_file(tmp_path):
    """Create a mock audio file"""
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(b"mock audio data")
    return str(audio_file)


@pytest.mark.unit
def test_model_name_conversion():
    """Test model name conversion from faster-whisper to HuggingFace format"""
    from app.tasks.whisper_transformers import WhisperTranscriberTransformers

    transcriber = WhisperTranscriberTransformers(model_name="large-v3-turbo")
    assert transcriber.model_name == "openai/whisper-large-v3-turbo"

    transcriber = WhisperTranscriberTransformers(model_name="tiny")
    assert transcriber.model_name == "openai/whisper-tiny"

    transcriber = WhisperTranscriberTransformers(model_name="openai/whisper-large-v3")
    assert transcriber.model_name == "openai/whisper-large-v3"


@pytest.mark.unit
def test_initialization_cuda():
    """Test initialization with CUDA device"""
    from app.tasks.whisper_transformers import WhisperTranscriberTransformers

    transcriber = WhisperTranscriberTransformers(
        model_name="large-v3-turbo",
        device="cuda",
        torch_dtype="float16"
    )

    assert transcriber.model_name == "openai/whisper-large-v3-turbo"
    assert transcriber.device == "cuda"
    assert transcriber.torch_dtype == torch.float16


@pytest.mark.unit
def test_initialization_cpu():
    """Test initialization with CPU device"""
    from app.tasks.whisper_transformers import WhisperTranscriberTransformers

    transcriber = WhisperTranscriberTransformers(
        model_name="tiny",
        device="cpu",
        torch_dtype="float32"
    )

    assert transcriber.device == "cpu"
    assert transcriber.torch_dtype == torch.float32


@pytest.mark.unit
@patch('app.tasks.whisper_transformers.TRANSFORMERS_AVAILABLE', False)
def test_load_model_without_transformers():
    """Test that load_model handles missing transformers library"""
    from app.tasks.whisper_transformers import WhisperTranscriberTransformers

    transcriber = WhisperTranscriberTransformers()
    transcriber.load_model()  # Should not raise, just log warning

    assert transcriber.model is None
    assert transcriber.processor is None


@pytest.mark.unit
def test_parse_segments():
    """Test parsing Whisper timestamp format"""
    from app.tasks.whisper_transformers import WhisperTranscriberTransformers

    transcriber = WhisperTranscriberTransformers()

    # Test with typical Whisper output format
    transcription = "<|0.00|> Hello world <|5.50|> How are you? <|10.00|>"
    duration = 12.0

    segments = transcriber._parse_segments(transcription, duration)

    assert len(segments) == 2
    assert segments[0]["text"] == "Hello world"
    assert segments[0]["start"] == 0.0
    assert segments[0]["end"] == 5.50

    assert segments[1]["text"] == "How are you?"
    assert segments[1]["start"] == 5.50
    assert segments[1]["end"] == 10.0


@pytest.mark.unit
def test_parse_segments_empty():
    """Test parsing empty transcription"""
    from app.tasks.whisper_transformers import WhisperTranscriberTransformers

    transcriber = WhisperTranscriberTransformers()

    # Test with empty transcription
    transcription = ""
    duration = 5.0

    segments = transcriber._parse_segments(transcription, duration)

    assert len(segments) == 0


@pytest.mark.unit
def test_parse_segments_no_timestamps():
    """Test parsing transcription without timestamps"""
    from app.tasks.whisper_transformers import WhisperTranscriberTransformers

    transcriber = WhisperTranscriberTransformers()

    # Test with plain text (fallback case)
    transcription = "Plain text without timestamps"
    duration = 10.0

    segments = transcriber._parse_segments(transcription, duration)

    # Should create one segment for entire duration
    assert len(segments) == 1
    assert segments[0]["text"] == "Plain text without timestamps"
    assert segments[0]["start"] == 0.0
    assert segments[0]["end"] == 10.0


@pytest.mark.unit
def test_mock_transcribe():
    """Test mock transcription fallback"""
    from app.tasks.whisper_transformers import WhisperTranscriberTransformers

    transcriber = WhisperTranscriberTransformers()

    # Mock librosa.load (patch where it's imported, inside the function)
    with patch('librosa.load') as mock_librosa_load:
        mock_audio = np.zeros(16000 * 30)  # 30 seconds of silence
        mock_librosa_load.return_value = (mock_audio, 16000)

        segments = transcriber._mock_transcribe("fake_audio.wav")

        # Should generate segments every 5 seconds
        # Formula: int(duration / 5) + 1 = int(30 / 5) + 1 = 7
        assert len(segments) == 7
        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 5.0
        assert "モック文字起こしセグメント" in segments[0]["text"]


@pytest.mark.unit
@patch('app.tasks.whisper_transformers.TRANSFORMERS_AVAILABLE', False)
def test_transcribe_without_transformers():
    """Test that transcribe returns mock data when transformers not available"""
    from app.tasks.whisper_transformers import WhisperTranscriberTransformers

    transcriber = WhisperTranscriberTransformers()

    with patch('librosa.load') as mock_librosa_load:
        mock_audio = np.zeros(16000 * 10)  # 10 seconds
        mock_librosa_load.return_value = (mock_audio, 16000)

        segments = transcriber.transcribe("fake_audio.wav")

        # Should return mock segments
        # Formula: int(duration / 5) + 1 = int(10 / 5) + 1 = 3
        assert len(segments) == 3
        assert "モック文字起こしセグメント" in segments[0]["text"]


@pytest.mark.unit
def test_cleanup():
    """Test cleanup method"""
    from app.tasks.whisper_transformers import WhisperTranscriberTransformers

    transcriber = WhisperTranscriberTransformers(device="cpu")

    # Set some mock objects
    transcriber.model = Mock()
    transcriber.processor = Mock()

    # Call cleanup
    transcriber.cleanup()

    # Should clear model and processor
    assert transcriber.model is None
    assert transcriber.processor is None


@pytest.mark.unit
@patch('torch.cuda.is_available', return_value=True)
@patch('torch.cuda.empty_cache')
def test_cleanup_with_cuda(mock_empty_cache, mock_cuda_available):
    """Test cleanup with CUDA device"""
    from app.tasks.whisper_transformers import WhisperTranscriberTransformers

    transcriber = WhisperTranscriberTransformers(device="cuda")
    transcriber.model = Mock()
    transcriber.processor = Mock()

    transcriber.cleanup()

    # Should clear CUDA cache
    mock_empty_cache.assert_called_once()


@pytest.mark.unit
def test_segment_structure():
    """Test that segments have correct structure matching faster-whisper format"""
    from app.tasks.whisper_transformers import WhisperTranscriberTransformers

    transcriber = WhisperTranscriberTransformers()

    transcription = "<|0.00|> Test segment <|5.00|>"
    duration = 6.0

    segments = transcriber._parse_segments(transcription, duration)

    # Check segment structure matches faster-whisper format
    assert len(segments) == 1
    segment = segments[0]

    # Required fields for compatibility
    assert "id" in segment
    assert "start" in segment
    assert "end" in segment
    assert "text" in segment
    assert "avg_logprob" in segment
    assert "no_speech_prob" in segment
    assert "words" in segment

    # Check types
    assert isinstance(segment["id"], int)
    assert isinstance(segment["start"], float)
    assert isinstance(segment["end"], float)
    assert isinstance(segment["text"], str)
    assert isinstance(segment["avg_logprob"], float)
    assert isinstance(segment["no_speech_prob"], float)
    assert isinstance(segment["words"], list)


@pytest.mark.unit
@patch('app.tasks.whisper_transformers.TRANSFORMERS_AVAILABLE', True)
def test_transcribe_api_compatibility():
    """Test that transcribe() method has same API as faster-whisper"""
    from app.tasks.whisper_transformers import WhisperTranscriberTransformers

    transcriber = WhisperTranscriberTransformers()

    with patch('librosa.load') as mock_librosa_load:
        mock_audio = np.zeros(16000 * 10)
        mock_librosa_load.return_value = (mock_audio, 16000)

        # Test that all parameters are accepted (API compatibility)
        segments = transcriber.transcribe(
            audio_file="test.wav",
            language="ja",
            task="transcribe",
            beam_size=5,
            vad_filter=True,
            vad_parameters={"threshold": 0.5}
        )

        # Should return list of segments
        assert isinstance(segments, list)
        assert all(isinstance(seg, dict) for seg in segments)
