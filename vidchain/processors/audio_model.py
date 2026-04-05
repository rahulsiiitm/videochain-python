import os
import shutil
import whisper
import torch
import imageio_ffmpeg

# =====================================================================
# 🚀 THE GHOST FFMPEG INJECTOR
# This completely eliminates the need for users to manually install FFmpeg.
# It hijacks the binary bundled with moviepy, aliases it, and forces 
# Whisper to use it seamlessly.
# =====================================================================
def inject_ffmpeg():
    bundled_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(bundled_exe)
    
    # Whisper strictly looks for "ffmpeg" or "ffmpeg.exe"
    alias_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    ffmpeg_alias = os.path.join(ffmpeg_dir, alias_name)
    
    # If the alias doesn't exist yet, create it silently
    if not os.path.exists(ffmpeg_alias):
        try:
            shutil.copyfile(bundled_exe, ffmpeg_alias)
            if os.name != "nt":
                os.chmod(ffmpeg_alias, 0o755) # Make executable on Mac/Linux
        except Exception as e:
            print(f"[WARNING] Could not create FFmpeg alias: {e}")

    # Inject this directory to the absolute front of the system PATH
    if ffmpeg_dir not in os.environ["PATH"]:
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]

# Run the injector the moment this file is imported
inject_ffmpeg()
# =====================================================================


class AudioProcessor:
    def __init__(self, model_size="base"):
        # Detect GPU mapping
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[VidChain] Audio Engine active on: {self.device}")
        
        # Load Whisper
        self.model = whisper.load_model(model_size, device=self.device)

    def transcribe(self, audio_path):
        """
        Extracts speech and maps it to timestamps.
        Optimized for RTX/CUDA hardware using FP16.
        """
        print(f"[VidChain] Transcribing: {os.path.basename(audio_path)}")
        
        # FP16 is much faster on CUDA, but Whisper requires FP32 for CPU
        use_fp16 = True if self.device == "cuda" else False
        
        try:
            result = self.model.transcribe(audio_path, fp16=use_fp16)
            
            segments = []
            for segment in result.get('segments', []):
                segments.append({
                    "start": round(segment['start'], 2),
                    "end": round(segment['end'], 2),
                    "text": segment['text'].strip()
                })
            return segments
        except Exception as e:
            print(f"⚠️ [Audio Error] Transcription failed: {e}")
            return []