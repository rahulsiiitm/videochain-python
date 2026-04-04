import os
import sys

# --- FORCED FFMPEG PATH INJECTION ---
ffmpeg_bin = r"C:\Users\Rahul Sharma\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin"

if ffmpeg_bin not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + ffmpeg_bin
    print(f"🛠️ System path updated with FFmpeg: {ffmpeg_bin}")
    
# ------------------------------------
from vidchain.loaders.audio_loader import AudioLoader
from vidchain.processors.audio_model import AudioProcessor

def main():
    # 1. Configuration
    VIDEO_FILE = "sample.mp4"  # Ensure this file exists in your root folder!
    
    if not os.path.exists(VIDEO_FILE):
        print(f"❌ Error: {VIDEO_FILE} not found in the root directory.")
        print("Please place a small .mp4 file here and rename it to 'sample.mp4'.")
        return

    # 2. Initialize components
    # Using 'tiny' for the first test as it's lightning fast
    loader = AudioLoader()
    processor = AudioProcessor(model_size="tiny")

    print("🚀 Starting Audio Pipeline Test...")
    print("-" * 30)

    try:
        # Step A: Extract Audio
        audio_path = loader.extract_audio(VIDEO_FILE)
        print(f"✅ Audio extracted to: {audio_path}")

        # Step B: Transcribe
        segments = processor.transcribe(audio_path)

        # 3. Display Results (The "Research Proof")
        print("\n--- 🎤 Transcription Results ---")
        for i, segment in enumerate(segments[:10]):  # Show first 10 segments
            print(f"[{segment['start']:>5}s - {segment['end']:>5}s] | {segment['text']}")
        
        if len(segments) > 10:
            print(f"... and {len(segments) - 10} more segments.")
            
        print("-" * 30)
        print("🎉 SUCCESS: Audio-Temporal indexing is functional!")

    except Exception as e:
        print(f"❌ Pipeline failed: {str(e)}")

if __name__ == "__main__":
    main()