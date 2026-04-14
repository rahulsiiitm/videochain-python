"""
examples/test_audio.py
------------------------
Tests the Adaptive AudioLoader independently.
"""

import os
import numpy as np
import librosa
import whisper
from vidchain.loaders.audio_loader import AudioLoader
from vidchain.processor import VideoProcessor

def main():
    VIDEO_FILE = "sample.mp4"

    if not os.path.exists(VIDEO_FILE):
        print(f"Error: {VIDEO_FILE} not found.")
        return

    print("=== Adaptive Audio Pipeline Test ===\n")

    # Extract WAV
    processor = VideoProcessor.__new__(VideoProcessor)
    processor.video_path = VIDEO_FILE
    processor._errors = []
    wav_path = processor._extract_wav()
    print(f"WAV extracted: {wav_path}")

    # Load audio signal
    y_audio, sr = librosa.load(wav_path, sr=16000)
    print(f"Audio loaded: {len(y_audio)/sr:.1f}s at {sr}Hz")

    # Transcribe
    print("\nTranscribing with Whisper...")
    model = whisper.load_model("base")
    result = model.transcribe(wav_path, fp16=False)
    raw_segments = result.get("segments", [])
    print(f"Raw segments: {len(raw_segments)}")

    # Adaptive filter
    loader = AudioLoader()
    output = loader.process_segments(raw_segments, y_audio, verbose=True)

    print("\n--- Clean Segments ---")
    for seg in output["segments"]:
        print(f"  [{seg['start']}s - {seg['end']}s] (RMS: {seg['energy']}) {seg['text']}")

    print(f"\n--- Acoustic Anomalies ---")
    for a in output["anomalies"]:
        print(f"  [{a['time']}s] {a['type']} (energy: {a['energy']})")

    print(f"\nStats: {output['stats']}")

if __name__ == "__main__":
    main()