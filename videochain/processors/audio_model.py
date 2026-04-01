import os
import shutil
import whisper
import torch

# --- FORCED FFMPEG INJECTION ---
# This ensures Whisper can find the executable regardless of Windows PATH settings
FFMPEG_BIN = r"C:\Users\Rahul Sharma\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin"

if FFMPEG_BIN not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + FFMPEG_BIN

class AudioProcessor:
    def __init__(self, model_size="base"):
        # Detect your RTX 3050
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[VideoChain] Audio using device: {self.device}")
        
        # Load Whisper (will now find ffmpeg thanks to the injection above)
        self.model = whisper.load_model(model_size, device=self.device)

    def transcribe(self, audio_path):
        print("[VideoChain] Transcribing audio...")
        # Use FP16 for speed on your 3050
        use_fp16 = True if self.device == "cuda" else False
        result = self.model.transcribe(audio_path, fp16=use_fp16)
        
        segments = []
        for segment in result['segments']:
            segments.append({
                "start": round(segment['start'], 2), # type: ignore
                "end": round(segment['end'], 2), # type: ignore
                "text": segment['text'].strip() # type: ignore
            })
        return segments