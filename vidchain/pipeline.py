import os
from typing import List, Dict, Any, Optional
import cv2  # type: ignore

from .nodes.base import BaseNode

class VideoChain:
    """
    The orchestrator for executing composable edge-vision pipelines.
    Runs a list of nodes sequentially per frame.
    """
    def __init__(self, nodes: List[BaseNode], frame_skip: int = 30):
        """
        Args:
            nodes (List[BaseNode]): The sequence of nodes to execute.
            frame_skip (int): The number of frames to skip to accelerate processing.
        """
        self.nodes = nodes
        self.frame_skip = frame_skip
        
    def run(self, video_path: str, audio_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Executes the chain over the given video.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        print(f"[VideoChain] Initializing pipeline with {len(self.nodes)} nodes...")
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        
        timeline = []
        frame_idx = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Check if we should process this specific frame based on frame_skip
                if frame_idx % self.frame_skip == 0:
                    current_time = round(frame_idx / fps, 2)
                    
                    # Initialize shared memory context
                    context: Dict[str, Any] = {
                        "video_path": video_path,
                        "audio_path": audio_path,
                        "current_frame": frame,
                        "current_time": current_time,
                        "time": current_time,  # Normalized key for RAG compatibility
                        "frame_idx": frame_idx
                    }
                    
                    # Sequentially execute each node
                    skip_entire_frame = False
                    for node in self.nodes:
                        context = node.process(context)
                        if context.get("skip_frame", False):
                            skip_entire_frame = True
                            break
                    
                    if not skip_entire_frame:
                        # Clean up memory-heavy items before saving to timeline
                        if "current_frame" in context:
                            del context["current_frame"]
                        timeline.append(context)
                
                # ALWAYS increment index to maintain real-world temporal sync
                frame_idx += 1
                
        finally:
            cap.release()
            
        print(f"[VideoChain] Pipeline complete. Extracted {len(timeline)} events.")
        return timeline
