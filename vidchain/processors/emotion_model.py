import threading
import numpy as np
from deepface import DeepFace

# YOLO labels that indicate a person is present
PERSON_TRIGGERS = {"person"}

# DeepFace → human-readable translation
EMOTION_MAP = {
    "angry":    "visibly agitated",
    "disgust":  "disgusted",
    "fear":     "fearful",
    "happy":    "relaxed and happy",
    "sad":      "distressed",
    "surprise": "startled",
    "neutral":  "calm and focused",
}


class EmotionProcessor:
    """
    Runs DeepFace emotion analysis on CPU in a background thread,
    so it never competes with YOLO/MobileNet for VRAM.
    """

    def __init__(self):
        # Force CPU — keeps VRAM free for YOLO + MobileNet
        print("[VideoChain] Emotion Engine initializing on: CPU (threaded)")
        # Warm up DeepFace on init so first frame isn't slow
        self._warmup()
        print("[VideoChain] Emotion Engine ready.")

    def _warmup(self):
        try:
            dummy = np.zeros((48, 48, 3), dtype=np.uint8)
            DeepFace.analyze(dummy, actions=["emotion"], enforce_detection=False, silent=True)
        except Exception:
            pass  # warmup failure is non-fatal

    def should_run(self, detected_objects: str) -> bool:
        """Only run when YOLO detected a person."""
        if not detected_objects or detected_objects == "no significant objects":
            return False
        return any(trigger in detected_objects.lower() for trigger in PERSON_TRIGGERS)

    def analyze(self, frame: np.ndarray) -> str | None:
        """
        Runs emotion analysis synchronously (called from a thread in processor.py).
        Returns a human-readable emotion string or None if no face found.
        """
        try:
            results = DeepFace.analyze(
                frame,
                actions=["emotion"],
                enforce_detection=False,  # don't crash if face is small/partial
                silent=True,
                detector_backend="opencv",  # fastest detector, good enough for surveillance
            )

            if not results:
                return None

            # DeepFace returns a list — take the dominant face
            dominant = results[0]
            raw_emotion = dominant.get("dominant_emotion", "neutral")
            confidence = dominant.get("emotion", {}).get(raw_emotion, 0)

            # Ignore low-confidence reads (< 40%) — avoids noise on partial faces
            if confidence < 40:
                return None

            return EMOTION_MAP.get(raw_emotion, raw_emotion)

        except Exception:
            return None  # face not found, bad frame — silently skip


class ThreadedEmotionAnalyzer:
    """
    Wraps EmotionProcessor to run analysis in a background thread.
    Vision loop submits frames and collects results non-blockingly.
    """

    def __init__(self):
        self.processor = EmotionProcessor()
        self._result: str | None = None
        self._thread: threading.Thread | None = None

    def submit(self, frame: np.ndarray):
        """Start emotion analysis on a frame in the background."""
        # Don't stack threads — skip if one is already running
        if self._thread and self._thread.is_alive():
            return

        frame_copy = frame.copy()  # copy so the vision loop can move on

        def _run():
            self._result = self.processor.analyze(frame_copy)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def collect(self) -> str | None:
        """
        Collect the result from the last submitted frame.
        Returns None if analysis is still running (non-blocking).
        """
        if self._thread and self._thread.is_alive():
            return None  # still computing — caller gets last known result
        return self._result