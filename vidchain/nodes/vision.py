from typing import Dict, Any
from .base import BaseNode
from vidchain.vision import VisionEngine

class YoloNode(BaseNode):
    def __init__(self, model_path: str = "yolov8n.pt", confidence: float = 0.6):
        print(f"[YoloNode] Initializing base vision engine (conf={confidence})...")
        self.engine = VisionEngine(model_path=model_path, confidence_threshold=confidence)
        
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts objects from the current frame using YOLO.
        Expects 'current_frame' (NumPy array) in context memory.
        Writes 'objects' and 'raw_detections' back to context.
        """
        frame = context.get("current_frame")
        if frame is None:
            return context
            
        summary, avg_conf, raw_detections = self.engine.predict(frame)
        context["objects"] = summary
        context["raw_detections"] = raw_detections
        
        return context
