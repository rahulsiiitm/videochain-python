import numpy as np
from typing import Dict, Any
from .base import BaseNode
from vidchain.processors.emotion_model import ThreadedEmotionAnalyzer

class EmotionNode(BaseNode):
    """
    Modular Sensor Node: Behavioral & Sentiment Analysis.
    Wraps the DeepFace-based ThreadedEmotionAnalyzer.
    
    This node runs in the background to avoid blocking the main vision loop.
    It identifies dominant emotions (Agitated, Calm, Distressed, etc.) 
    when a person is detected in the frame.
    """
    
    def __init__(self):
        print("[EmotionNode] Initializing Behavioral Sentiment Engine (DeepFace)...")
        self.analyzer = ThreadedEmotionAnalyzer()
        
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submits the current frame for behavioral analysis if a person is present.
        """
        frame = context.get("current_frame")
        objects = context.get("objects", "")
        
        if frame is None:
            return context
            
        # Trigger analysis only if someone is in the scene (Optimization)
        if self.analyzer.processor.should_run(objects):
            # Non-blocking submission
            self.analyzer.submit(frame)
            
        # Collect last known result (may be from a previous frame if still computing)
        emotion = self.analyzer.collect()
        
        # Inject into context for RAG and Indexing
        context["emotion"] = emotion
        
        return context
