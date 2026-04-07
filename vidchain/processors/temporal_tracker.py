import cv2
import numpy as np
from collections import defaultdict


# ── Camera motion thresholds ───────────────────────────────────────────────
FLOW_PAN_THRESHOLD   = 2.0   # avg pixel/frame horizontal shift → panning
FLOW_TILT_THRESHOLD  = 2.0   # avg pixel/frame vertical shift → tilting
FLOW_ZOOM_THRESHOLD  = 0.15  # divergence magnitude → zooming
FLOW_STATIC_MAX      = 1.0   # below this → camera is static


class ObjectTracker:
    """
    Lightweight IoU-based object tracker.
    Assigns persistent IDs to YOLO detections across frames so we can say
    'person #1 has been at the desk since 0s' instead of '1 person' every frame.
    """

    def __init__(self, iou_threshold: float = 0.35, max_lost: int = 8):
        self.iou_threshold = iou_threshold
        self.max_lost = max_lost          # frames before a track is dropped
        self.tracks: dict = {}            # id → {box, label, age, lost}
        self.next_id = 1
        self.history: dict = defaultdict(list)  # id → [(timestamp, box)]

    def _iou(self, a, b) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            return 0.0
        ua = (ax2-ax1)*(ay2-ay1) + (bx2-bx1)*(by2-by1) - inter
        return inter / ua if ua > 0 else 0.0

    def update(self, detections: list, timestamp: float) -> list:
        """
        detections: list of (label, x1, y1, x2, y2) from YOLO
        Returns: list of (track_id, label, box, age_seconds)
        """
        # Mark all existing tracks as potentially lost
        for tid in self.tracks:
            self.tracks[tid]["lost"] += 1

        matched_tids = set()
        results = []

        for label, x1, y1, x2, y2 in detections:
            box = (x1, y1, x2, y2)
            best_tid, best_iou = None, self.iou_threshold

            for tid, track in self.tracks.items():
                if track["label"] != label:
                    continue
                
                # CRITICAL FIX: Skip if this ID was already claimed by another box in this frame
                if tid in matched_tids:
                    continue

                iou = self._iou(box, track["box"])
                if iou > best_iou:
                    best_iou, best_tid = iou, tid

            if best_tid is not None:
                # Matched existing track
                self.tracks[best_tid].update({"box": box, "lost": 0, "age": self.tracks[best_tid]["age"] + 1})
                matched_tids.add(best_tid)
                self.history[best_tid].append((timestamp, box))
                results.append((best_tid, label, box, self._age_seconds(best_tid, timestamp)))
            else:
                # New track
                tid = self.next_id
                self.next_id += 1
                self.tracks[tid] = {"box": box, "label": label, "lost": 0, "age": 1, "first_seen": timestamp}
                self.history[tid].append((timestamp, box))
                results.append((tid, label, box, 0.0))

        # Drop tracks that have been lost too long
        self.tracks = {
            tid: t for tid, t in self.tracks.items()
            if t["lost"] <= self.max_lost
        }

        return results

    def _age_seconds(self, tid: int, now: float) -> float:
        first = self.tracks[tid].get("first_seen", now)
        return round(now - first, 1)

    def get_trajectory(self, tid: int) -> str | None:
        """Describe how an object moved over its tracked history."""
        hist = self.history.get(tid, [])
        if len(hist) < 2:
            return None

        first_box = hist[0][1]
        last_box  = hist[-1][1]

        # Center points
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
    Uses Lucas-Kanade sparse optical flow to detect camera motion.
    Distinguishes: static, panning left/right, tilting up/down, zooming in/out.
    """

    def __init__(self):
        self.prev_gray: np.ndarray | None = None
        self.prev_pts:  np.ndarray | None = None

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
        """Returns a human-readable camera motion label."""
        if self.prev_gray is None:
            self.prev_gray = gray_frame
            self.prev_pts  = cv2.goodFeaturesToTrack(gray_frame, mask=None, **self.feature_params)
            return "static"

        if self.prev_pts is None or len(self.prev_pts) < 4:
            self.prev_pts = cv2.goodFeaturesToTrack(gray_frame, mask=None, **self.feature_params)
            self.prev_gray = gray_frame
            return "static"

        # Track points from previous frame
        curr_pts, status, _ = cv2.calcOpticalFlowPyrLK(
            self.prev_gray, gray_frame, self.prev_pts, None, **self.lk_params
        )

        if curr_pts is None:
            self.prev_gray = gray_frame
            return "static"

        good_prev = self.prev_pts[status == 1]
        good_curr = curr_pts[status == 1]

        if len(good_prev) < 4:
            self.prev_gray = gray_frame
            self.prev_pts  = cv2.goodFeaturesToTrack(gray_frame, mask=None, **self.feature_params)
            return "static"

        flow = good_curr - good_prev
        mean_dx = float(np.mean(flow[:, 0]))
        mean_dy = float(np.mean(flow[:, 1]))

        # Zoom: check if points are diverging (zoom in) or converging (zoom out)
        center = np.mean(good_prev, axis=0)
        vectors_from_center = good_prev - center
        dot_products = np.sum(vectors_from_center * flow, axis=1)
        zoom_score = float(np.mean(dot_products)) / (np.linalg.norm(center) + 1e-6)

        # Refresh feature points periodically
        self.prev_gray = gray_frame
        self.prev_pts  = cv2.goodFeaturesToTrack(gray_frame, mask=None, **self.feature_params) # type: ignore

        # Classify
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
    """
    Combines ObjectTracker + CameraMotionDetector into a single interface
    that plugs into VideoProcessor's frame loop.
    """

    def __init__(self):
        self.object_tracker = ObjectTracker()
        self.camera_detector = CameraMotionDetector()

    def process_frame(self, frame: np.ndarray, raw_detections: list, timestamp: float) -> dict:
        """
        raw_detections: list of (label, x1, y1, x2, y2) from YOLO boxes
        Returns temporal context dict to be merged into the KB entry.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Camera motion
        camera_motion = self.camera_detector.detect(gray)

        # Object tracking
        tracked = self.object_tracker.update(raw_detections, timestamp)

        # Build subject descriptions with persistence info
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