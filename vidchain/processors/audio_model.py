import os
import shutil
import whisper
import torch

# --- DYNAMIC FFMPEG RESOLUTION ---
FFMPEG_PATH = shutil.which("ffmpeg")

class AudioProcessor:
    def __init__(self, model_size="base"):
        # 1. Check for FFmpeg presence
        if not FFMPEG_PATH:
            raise RuntimeError(
                "❌ FFmpeg not found! vidchain requires FFmpeg to be installed "
                "and added to your System PATH. \n"
                "👉 Windows: 'winget install ffmpeg' \n"
                "👉 Mac: 'brew install ffmpeg'"
            )

        # 2. Detect your RTX 3050 (or current GPU)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[vidchain] Audio Engine active on: {self.device}")
        
        # 3. Load Whisper
        self.model = whisper.load_model(model_size, device=self.device)

    def transcribe(self, audio_path):
        """
        Extracts speech and maps it to timestamps.
        Optimized for RTX 3050 using FP16.
        """
        print(f"[vidchain] Transcribing: {os.path.basename(audio_path)}")
        
        # FP16 is 2x faster on your 3050, but Whisper requires FP32 for CPU
        use_fp16 = True if self.device == "cuda" else False
        
        try:
            result = self.model.transcribe(audio_path, fp16=use_fp16)
            
            segments = []
            for segment in result.get('segments', []):
                segments.append({
                    "start": round(segment['start'], 2), #type: ignore
                    "end": round(segment['end'], 2), #type: ignore
                    "text": segment['text'].strip() #type: ignore
                })
            return segments
        except Exception as e:
            print(f"⚠️ [Audio Error] Transcription failed: {e}")
            return []