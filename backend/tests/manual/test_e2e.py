#!/usr/bin/env python3
"""
End-to-end test for transformers backend on Celery worker
"""
import os
import sys

# Set backend
os.environ['WHISPER_BACKEND'] = 'transformers'

print("=== Celery Worker Transformers Test ===")
print(f"WHISPER_BACKEND: {os.environ.get('WHISPER_BACKEND')}")
print()

from app.tasks.transcription_tasks import get_transcriber, TRANSFORMERS_AVAILABLE

print(f"TRANSFORMERS_AVAILABLE: {TRANSFORMERS_AVAILABLE}")
print()

print("Creating transcriber...")
transcriber = get_transcriber("tiny", "cpu", "float32")
print(f"Type: {type(transcriber).__name__}")
print(f"Model: {transcriber.model_name}")
print()

print("Loading Whisper model (may take a minute on first run)...")
try:
    transcriber.load_model()
    print("✅ Model loaded successfully")
    print()

    print("Performing transcription...")
    segments = transcriber.transcribe("/tmp/test_audio.wav", language="en")
    print(f"✅ Transcription complete: {len(segments)} segments")

    if segments:
        print()
        print("First segment details:")
        seg = segments[0]
        print(f"  Start: {seg['start']:.2f}s")
        print(f"  End: {seg['end']:.2f}s")
        print(f"  Text: {seg['text'][:100]}")
        print(f"  Confidence: {seg['avg_logprob']:.3f}")
        print()

        # Verify segment structure
        required_fields = ['id', 'start', 'end', 'text', 'avg_logprob', 'no_speech_prob', 'words']
        print("Segment structure validation:")
        for field in required_fields:
            status = "✅" if field in seg else "❌"
            print(f"  {status} {field}")

    print()
    print("✅ Full end-to-end test PASSED!")
    print("   - Model loaded successfully")
    print("   - Transcription completed")
    print("   - Segment structure valid")
    sys.exit(0)

except Exception as e:
    print(f"❌ Test FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
