from typing import Dict, Any, List
from .base import BaseNode
from vidchain.processors.ocr_model import OCRProcessor

class OcrNode(BaseNode):
    def __init__(self, languages: List[str] = ["en"], interval: float = 5.0):
        print("[OcrNode] Initializing EasyOCR Engine...")
        self.engine = OCRProcessor(languages=languages)
        self.interval = interval
        self.last_ocr_time = -interval
        
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        frame = context.get("current_frame")
        objects = context.get("objects", "")
        current_time = context.get("current_time", 0.0)
        
        context["ocr"] = None
        
        if frame is None:
            return context
            
        if self.engine.should_run(objects) and (current_time - self.last_ocr_time) >= self.interval:
            text = self.engine.extract_text(frame)
            if text:
                context["ocr"] = text
                self.last_ocr_time = current_time
                
        return context
