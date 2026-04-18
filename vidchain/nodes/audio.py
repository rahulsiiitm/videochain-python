from typing import Dict, Any
from .base import BaseNode
from vidchain.processors.audio_model import AudioProcessor

class WhisperNode(BaseNode):
    """
    Audio extraction node using OpenAI Whisper.
    Executes once per video to extract all temporal speech segments.
    """
    def __init__(self, model_size: str = "base"):
        self.engine = AudioProcessor(model_size=model_size)
        self.segments_cache = None
        
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expects 'audio_path' and 'current_time' (float) in context.
        Writes 'audio' (the transcribed text at that exact time) to context.
        """
        # Run transcription exactly once and cache it
        if self.segments_cache is None:
            audio_path = context.get("audio_path")
            if audio_path:
                self.segments_cache = self.engine.transcribe(audio_path)
            else:
                self.segments_cache = []
                
        current_time = context.get("current_time", 0.0)
        
        # Binary search or simple iteration to find if someone is speaking right now
        current_speech = None
        if self.segments_cache:
            for seg in self.segments_cache:
                if seg["start"] <= current_time <= seg["end"]:
                    current_speech = seg["text"]
                    break
        
        context["audio"] = current_speech
        return context
