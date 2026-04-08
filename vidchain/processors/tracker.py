"""
VidChain Core: Spatio-Temporal Tracking Engine
----------------------------------------------
Provides persistent object tracking (Object Permanence) and camera motion 
detection (Optical Flow) for edge-optimized video processing.
"""

import cv2
import numpy as np
from collections import defaultdict
from typing import List, Tuple, Dict, Optional, Any

# ── Camera Motion Thresholds ───────────────────────────────────────────────
FLOW_PAN_THRESHOLD   = 2.0   # avg pixel/frame horizontal shift → panning
FLOW_TILT_THRESHOLD  = 2.0   # avg pixel/frame vertical shift → tilting
FLOW_ZOOM_THRESHOLD  = 0.15  # divergence magnitude → zooming
FLOW_STATIC_MAX      = 1.0   # below this → camera is static


class SceneCutDetector:
    """
    Detects sudden scene changes (shot boundaries) using HSV Color Histograms.
    Vital for preventing tracker contamination when a video cuts to a new camera angle.
    """
    def __init__(self, threshold_score: float = 0.4):
        self.prev_hist = None
        self.threshold = threshold_score

    def detect(self, frame: np.ndarray) -> bool:
        # Convert to HSV for robust color comparison
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Calculate a 2D histogram (Hue and Saturation)
        hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

        if self.prev_hist is None:
            self.prev_hist = hist
            return False

        # Compare current frame colors to previous frame colors
        correlation = cv2.compareHist(self.prev_hist, hist, cv2.HISTCMP_CORREL)
        self.prev_hist = hist

        # If the correlation drops below the threshold, it's a hard cut
        return correlation < self.threshold

class ObjectTracker:
    """
    Lightweight Intersection-over-Union (IoU) object tracker.
    Assigns persistent IDs to YOLO detections across frames to establish
    causal relationships (e.g., 'Person #1 has been at the desk since 0s').
    """

    def __init__(self, iou_threshold: float = 0.35, max_lost: int = 8):
        self.iou_threshold = iou_threshold
        self.max_lost = max_lost          # Frames to wait before dropping a lost track
        self.tracks: Dict[int, Dict[str, Any]] = {}  # id → {box, label, age, lost, first_seen}
        self.next_id = 1
        self.history: Dict[int, List[Tuple[float, Tuple[int, int, int, int]]]] = defaultdict(list)

    def _iou(self, a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
        """Calculates the Intersection over Union (IoU) of two bounding boxes."""
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            return 0.0
            
        union_area = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
        return inter / union_area if union_area > 0 else 0.0

    def update(self, detections: List[Tuple[str, int, int, int, int]], timestamp: float) -> List[Tuple[int, str, Tuple[int, int, int, int], float]]:
        """
        Updates tracking IDs based on new YOLO detections.
        
        Args:
            detections: List of tuples (label, x1, y1, x2, y2)
            timestamp: Current video timestamp in seconds
            
        Returns:
            List of (track_id, label, box, age_seconds)
        """
        # 1. Mark all existing tracks as potentially lost
        for tid in self.tracks:
            self.tracks[tid]["lost"] += 1

        matched_tids = set()
        results = []

        # 2. Match new detections to existing tracks
        for label, x1, y1, x2, y2 in detections:
            box = (x1, y1, x2, y2)
            best_tid = None
            best_iou = self.iou_threshold

            for tid, track in self.tracks.items():
                # Must be the same object class
                if track["label"] != label:
                    continue
                
                # Prevent Double-Assignment Collision
                if tid in matched_tids:
                    continue

                iou = self._iou(box, track["box"])
                if iou > best_iou:
                    best_iou, best_tid = iou, tid

            if best_tid is not None:
                # Update existing track
                self.tracks[best_tid].update({
                    "box": box, 
                    "lost": 0, 
                    "age": self.tracks[best_tid]["age"] + 1
                })
                matched_tids.add(best_tid)
                self.history[best_tid].append((timestamp, box))
                results.append((best_tid, label, box, self._age_seconds(best_tid, timestamp)))
            else:
                # Register new track
                tid = self.next_id
                self.next_id += 1
                self.tracks[tid] = {
                    "box": box, 
                    "label": label, 
                    "lost": 0, 
                    "age": 1, 
                    "first_seen": timestamp
                }
                self.history[tid].append((timestamp, box))
                results.append((tid, label, box, 0.0))

        # 3. Purge dead tracks
        self.tracks = {
            tid: t for tid, t in self.tracks.items()
            if t["lost"] <= self.max_lost
        }

        return results

    def _age_seconds(self, tid: int, now: float) -> float:
        """Calculates how long the object has been in the frame."""
        first = self.tracks[tid].get("first_seen", now)
        return round(now - first, 1)

    def get_trajectory(self, tid: int) -> Optional[str]:
        """Mathematically determines object movement direction over its history."""
        hist = self.history.get(tid, [])
        if len(hist) < 2:
            return None

        first_box = hist[0][1]
        last_box  = hist[-1][1]

        # Calculate Center Points
        fx = (first_box[0] + first_box[2]) / 2
        fy = (first_box[1] + first_box[3]) / 2
        lx = (last_box[0]  + last_box[2])  / 2
        ly = (last_box[1]  + last_box[3])  / 2

        dx, dy = lx - fx, ly - fy

        if abs(dx) < 20 and abs(dy) < 20:
            return "stationary"

        parts = []
        if abs(dx) > 20:
            parts.append("moving right" if dx > 0 else "moving left")
        if abs(dy) > 20:
            parts.append("moving down" if dy > 0 else "moving up")

        return " and ".join(parts) if parts else "stationary"


class CameraMotionDetector:
    """
    Uses Lucas-Kanade (LK) sparse optical flow to detect physical camera movement.
    Vital for differentiating between a 'moving person' and a 'panning camera'.
    """

    def __init__(self):
        self.prev_gray: Optional[np.ndarray] = None
        self.prev_pts:  Optional[np.ndarray] = None

        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        self.feature_params = dict(
            maxCorners=80,
            qualityLevel=0.2,
            minDistance=7,
            blockSize=7
        )

    def detect(self, gray_frame: np.ndarray) -> str:
        """Analyzes frame differences to classify camera motion intent."""
        
        # 1. Initialize or Reset if we lack enough features to track
        if self.prev_gray is None or self.prev_pts is None or len(self.prev_pts) < 4:
            self.prev_gray = gray_frame.copy() # Use .copy() to isolate memory
            pts = cv2.goodFeaturesToTrack(gray_frame, mask=None, **self.feature_params) # type: ignore
            self.prev_pts = pts if pts is not None else None
            return "static"

        # 2. 🛑 CRITICAL FIX: Force strict Float32 typing and exact shape for OpenCV C++ backend
        try:
            self.prev_pts = np.float32(self.prev_pts).reshape(-1, 1, 2)
            
            # Track points from previous frame to current frame
            curr_pts, status, _ = cv2.calcOpticalFlowPyrLK(
                self.prev_gray, gray_frame, self.prev_pts, None, **self.lk_params # type: ignore
            ) # pyright: ignore[reportCallIssue]
        except Exception as e:
            # If OpenCV panics (e.g. corrupted frame), safely reset the tracker instead of crashing
            self.prev_gray = None
            self.prev_pts = None
            return "static"

        # 3. Handle cases where Optical Flow fails to track anything
        if curr_pts is None or status is None:
            self.prev_gray = gray_frame.copy()
            return "static"

        # 4. Filter out bad tracking points
        status_flat = status.flatten()
        good_prev = self.prev_pts.reshape(-1, 2)[status_flat == 1]
        good_curr = curr_pts.reshape(-1, 2)[status_flat == 1]

        if len(good_prev) < 4:
            self.prev_gray = gray_frame.copy()
            pts = cv2.goodFeaturesToTrack(gray_frame, mask=None, **self.feature_params) # type: ignore
            self.prev_pts = pts if pts is not None else None
            return "static"

        # 5. Calculate vector shifts
        flow = good_curr - good_prev
        mean_dx = float(np.mean(flow[:, 0]))
        mean_dy = float(np.mean(flow[:, 1]))

        # 6. Calculate Zoom Divergence/Convergence
        center = np.mean(good_prev, axis=0)
        vectors_from_center = good_prev - center
        dot_products = np.sum(vectors_from_center * flow, axis=1)
        zoom_score = float(np.mean(dot_products)) / (np.linalg.norm(center) + 1e-6)

        # 7. Refresh memory for the next frame
        self.prev_gray = gray_frame.copy()
        pts = cv2.goodFeaturesToTrack(gray_frame, mask=None, **self.feature_params) # type: ignore
        self.prev_pts = pts if pts is not None else None

        # 8. Apply Threshold Classifications
        if abs(zoom_score) > FLOW_ZOOM_THRESHOLD:
            return "zooming in" if zoom_score > 0 else "zooming out"
        if abs(mean_dx) > FLOW_PAN_THRESHOLD and abs(mean_dx) > abs(mean_dy):
            return "panning right" if mean_dx > 0 else "panning left"
        if abs(mean_dy) > FLOW_TILT_THRESHOLD and abs(mean_dy) > abs(mean_dx):
            return "tilting down" if mean_dy > 0 else "tilting up"
        if abs(mean_dx) < FLOW_STATIC_MAX and abs(mean_dy) < FLOW_STATIC_MAX:
            return "static"

        return "moving"


class TemporalTracker:
    def __init__(self):
        self.object_tracker = ObjectTracker()
        self.camera_detector = CameraMotionDetector()
        self.cut_detector = SceneCutDetector() # 🛑 ADD THIS

    def process_frame(self, frame: np.ndarray, raw_detections: List[Tuple[str, int, int, int, int]], timestamp: float) -> Dict[str, Any]:
        
        # 🛑 1. Check for Scene Cuts FIRST
        is_cut = self.cut_detector.detect(frame)
        if is_cut:
            # Wipe the tracking history so objects don't bleed into the new scene
            self.object_tracker.tracks.clear()
            self.camera_detector.prev_gray = None
            return {
                "camera_motion": "SCENE CUT DETECTED",
                "tracked_subjects": ["All previous tracks reset."]
            }

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 2. Evaluate Scene Camera Motion
        camera_motion = self.camera_detector.detect(gray)

        # 3. Update Entity Persistence
        tracked = self.object_tracker.update(raw_detections, timestamp)

        # 4. Format Human-Readable Knowledge Base Entries
        subject_descriptions = []
        for tid, label, box, age in tracked:
            trajectory = self.object_tracker.get_trajectory(tid)
            desc = f"{label} #{tid}"
            
            if age > 1.0:
                desc += f" (present {age}s)"
            if trajectory and trajectory != "stationary":
                desc += f", {trajectory}"
                
            subject_descriptions.append(desc)

        return {
            "camera_motion":  camera_motion,
            "tracked_subjects": subject_descriptions,
        }