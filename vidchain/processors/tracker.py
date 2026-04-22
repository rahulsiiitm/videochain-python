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




class SceneCutDetector:
    """
    Detects sudden scene changes (shot boundaries) using HSV Color Histograms.
    Vital for preventing tracker contamination when a video cuts to a new camera angle.
    """
    def __init__(self, threshold_score: float = 0.25): # Relaxed from 0.4
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
    Surgical Motion Engine: Uses ORB Features + RANSAC Global Motion Estimation.
    Effectively ignores moving objects (outliers) to detect true camera movement.
    """

    def __init__(self):
        self.orb = cv2.ORB_create(nfeatures=500)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        self.prev_kp = None
        self.prev_des = None
        
        # Sensitivity thresholds (pixels per keyframe-delta)
        self.PAN_T = 3.5
        self.TILT_T = 3.5
        self.ZOOM_T = 0.015 # 1.5% change
        
        # Temporal smoothing buffer
        self.history = []
        self.history_limit = 3

    def detect(self, gray_frame: np.ndarray) -> str:
        kp, des = self.orb.detectAndCompute(gray_frame, None)
        
        if self.prev_des is None or des is None or len(des) < 25:
            self.prev_kp, self.prev_des = kp, des
            self.history.clear()
            return "static"

        matches = self.matcher.match(self.prev_des, des)
        if len(matches) < 25:
            self.prev_kp, self.prev_des = kp, des
            self.history.clear()
            return "static"

        pts_prev = np.float32([self.prev_kp[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        pts_curr = np.float32([kp[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

        # Estimate Global Motion
        matrix, inliers = cv2.estimateAffinePartial2D(pts_prev, pts_curr, method=cv2.RANSAC, ransacReprojThreshold=3.0)

        self.prev_kp, self.prev_des = kp, des

        if matrix is None or inliers is None or np.sum(inliers) < 20:
            self.history.clear()
            return "static"

        # Extract raw components
        tx = matrix[0, 2]
        ty = matrix[1, 2]
        s = np.sqrt(matrix[0, 0]**2 + matrix[0, 1]**2)

        # Apply Smoothing (Moving Average)
        self.history.append((tx, ty, s))
        if len(self.history) > self.history_limit:
            self.history.pop(0)
        
        avg_tx = sum(h[0] for h in self.history) / len(self.history)
        avg_ty = sum(h[1] for h in self.history) / len(self.history)
        avg_s  = sum(h[2] for h in self.history) / len(self.history)

        # Classification Logic
        if abs(avg_s - 1.0) > self.ZOOM_T:
            return "zooming in" if avg_s > 1.0 else "zooming out"

        if abs(avg_tx) > self.PAN_T and abs(avg_tx) > abs(avg_ty):
            return "panning left" if avg_tx > 0 else "panning right"
        
        if abs(avg_ty) > self.TILT_T and abs(avg_ty) > abs(avg_tx):
            return "tilting up" if avg_ty > 0 else "tilting down"

        return "static"


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
            self.camera_detector.prev_des = None
            self.camera_detector.prev_kp = None
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