import cv2
import whisper # type: ignore
import librosa
import numpy as np
from .vision import VisionEngine

class VideoProcessor:
    def __init__(self, video_path):
        self.video_path = video_path
        # We use 'base' for RTX 3050 efficiency
        self.audio_model = whisper.load_model("base")

    def extract_context(self, vision_engine: VisionEngine):
        print("🎙️ Processing Audio with Whisper and Librosa...")
        # 1. Transcribe text
        audio_text = self.audio_model.transcribe(self.video_path)["text"]
        
        # 2. Extract acoustic energy (volume)
        y, sr = librosa.load(self.video_path, sr=None)
        rms = librosa.feature.rms(y=y)
        peak_volume = np.max(rms)

        print("👁️ Analyzing Frames (Motion-Gated YOLO)...")
        cap = cv2.VideoCapture(self.video_path)
        vision_events = []
        fps = cap.get(cv2.CAP_PROP_FPS)
        prev_gray = None
        frame_idx = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            # Motion Gating: Note the difference before processing
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                diff = cv2.absdiff(prev_gray, gray)
                if np.mean(diff) > 2.0: 
                    desc, conf = vision_engine.predict(frame)
                    # FIXED: Changed key from 'time' to 'timestamp'
                    vision_events.append({"timestamp": frame_idx/fps, "label": desc})
            
            prev_gray = gray
            frame_idx += int(fps) # Sample 1 frame per second
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

        cap.release()
        return vision_events, audio_text, peak_volume