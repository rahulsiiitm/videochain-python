import cv2
import numpy as np
from typing import Dict, Any, Optional
from .base import BaseNode

class AdaptiveKeyframeNode(BaseNode):
    """
    Acts as a high-speed firewall.
    Computes difference between current frame and previous frame via Gaussian Blur.
    If the frames are nearly identical, it injects 'skip_frame = True' into context
    so other heavy nodes (like YOLO or LLaVA) don't process redundant data!
    """
    def __init__(self, change_threshold: float = 8.0, blur_kernel: tuple = (21, 21), diff_cutoff: int = 50):
        self.change_threshold = change_threshold
        self.blur_kernel = blur_kernel
        self.diff_cutoff = diff_cutoff
        
        self.prev_gray: Optional[np.ndarray] = None
        print(f"[AdaptiveKeyframeNode] Initialized (Threshold: {self.change_threshold}%)")
        
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        frame = context.get("current_frame")
        if frame is None:
            return context
            
        context["skip_frame"] = False
        
        curr_gray_blurred = cv2.GaussianBlur(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 
            self.blur_kernel, 
            0
        )
        
        if self.prev_gray is None:
            self.prev_gray = curr_gray_blurred
            return context # Always process the first frame
            
        # Calculate visual delta
        diff = cv2.absdiff(self.prev_gray, curr_gray_blurred)
        non_zero = np.count_nonzero(diff > self.diff_cutoff)
        change_pct = (non_zero / diff.size) * 100
        
        if change_pct < self.change_threshold:
            # Frame is too visually identical. Abort the pipeline here to save GPU compute.
            context["skip_frame"] = True
            print(f"   ⏩ [Keyframe Tracker] Skipping identical frame at {context.get('current_time')}s")
        else:
            # Significant visual change detected. Process it and update reference frame.
            self.prev_gray = curr_gray_blurred
            
        return context
