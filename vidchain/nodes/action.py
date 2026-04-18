from typing import Dict, Any
from .base import BaseNode
from vidchain.processors.vision_model import VisionEngine as ActionEngine

class ActionNode(BaseNode):
    def __init__(self, model_path: str = "models/vidchain_vision.pth"):
        print("[ActionNode] Initializing MobileNet Action Engine...")
        self.engine = ActionEngine(model_path=model_path)
        
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        frame = context.get("current_frame")
        objects = context.get("objects", "no significant objects")
        
        context["action"] = "NORMAL"
        
        if frame is None:
            return context
            
        if objects != "no significant objects":
            try:
                action, _ = self.engine.predict(frame)
                if action.lower() not in ("uncertain", "unknown"):
                    context["action"] = action.upper()
            except:
                pass
                
        return context
