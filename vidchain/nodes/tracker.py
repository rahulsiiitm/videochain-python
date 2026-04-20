from typing import Dict, Any, List, Tuple
from vidchain.nodes.base import BaseNode
from vidchain.processors.tracker import TemporalTracker

class TrackerNode(BaseNode):
    """
    A processing node that handles persistence and camera motion detection.
    Wraps the TemporalTracker processor which uses Lucas-Kanade optical flow.
    """
    
    def __init__(self):
        self.tracker = TemporalTracker()
    
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes the current frame for object tracking and camera motion.
        
        Args:
            context: Shared memory containing:
                - 'frame': np.ndarray (current video frame)
                - 'raw_detections': List[Tuple[str, int, int, int, int]] (latest YOLO outputs)
                - 'timestamp': float (current video time)
        """
        frame = context.get("current_frame")
        detections = context.get("raw_detections", [])
        timestamp = context.get("timestamp", 0.0)
        
        if frame is None:
            return context
            
        # Execute Temporal Tracking logic (IK + IOU)
        tracker_results = self.tracker.process_frame(frame, detections, timestamp)
        
        # Inject results into context for subsequent nodes and indexing
        context["camera_motion"] = tracker_results.get("camera_motion", "static")
        context["tracked_subjects"] = tracker_results.get("tracked_subjects", [])
        
        return context
