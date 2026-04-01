import whisper
import torch

class AudioProcessor:
    def __init__(self, model_size="base"):
        # Detect your RTX 3050
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[VideoChain] Audio using device: {self.device}")
        
        # Load model to GPU
        self.model = whisper.load_model(model_size, device=self.device)

    def transcribe(self, audio_path):
        # Setting fp16=True for GPU speed
        use_fp16 = True if self.device == "cuda" else False
        result = self.model.transcribe(audio_path, fp16=use_fp16)
        
        segments = []
        for segment in result['segments']:
            segments.append({
                "start": round(segment['start'], 2),
                "end": round(segment['end'], 2),
                "text": segment['text'].strip()
            })
        return segments