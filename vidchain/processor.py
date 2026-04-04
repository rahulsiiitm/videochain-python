import warnings
# Suppress noisy library warnings
warnings.filterwarnings("ignore")

import cv2
import torch
import whisper
import librosa
import numpy as np

from vidchain.processors.ocr_model import OCRProcessor

OCR_INTERVAL_SECONDS = 5.0

class VideoProcessor:
    def __init__(self, video_path: str, ocr_languages: list = ["en"]):
        self.video_path = video_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        print(f"[INFO] Loading Whisper Audio Model (base) on {self.device.upper()}...")
        self.audio_model = whisper.load_model("base", device=self.device)

        print(f"[INFO] Loading OCR Engine on {self.device.upper()}...")
        self.ocr = OCRProcessor(languages=ocr_languages)

    def extract_context(self, yolo_engine, action_engine):
        print(f"[INFO] Extracting Audio Timestamps (Whisper) via {self.device.upper()}...")
        raw_audio_result = self.audio_model.transcribe(self.video_path)

        audio_segments = []
        for segment in raw_audio_result.get("segments", []):
            audio_segments.append({
                "start": round(segment["start"], 2), # type: ignore
                "text": segment["text"].strip() # type: ignore
            })

        y, sr = librosa.load(self.video_path, sr=None)
        peak_volume = float(np.max(librosa.feature.rms(y=y)))

        print(f"[INFO] Extracting Scene Graphs + OCR (Dual-Brain) via {self.device.upper()}...")
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        raw_events = []
        ocr_events = []
        prev_gray = None
        frame_idx = 0
        last_ocr_time = -OCR_INTERVAL_SECONDS 

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if prev_gray is not None and np.mean(cv2.absdiff(prev_gray, gray)) > 2.0:
                timestamp = round(frame_idx / fps, 2)
                objects, _ = yolo_engine.predict(frame)

                if objects == "no significant objects":
                    action = "NORMAL"
                else:
                    action, _ = action_engine.predict(frame)
                    if action.lower() == "uncertain":
                        action = "NORMAL"

                raw_events.append({
                    "timestamp": timestamp,
                    "objects": objects,
                    "action": action.upper()
                })

                if self.ocr.should_run(objects) and (timestamp - last_ocr_time) >= OCR_INTERVAL_SECONDS:
                    text = self.ocr.extract_text(frame)
                    if text:
                        ocr_events.append({"timestamp": timestamp, "text": text})
                        last_ocr_time = timestamp
                        print(f"   🔤 OCR at {timestamp}s: {text[:60]}{'...' if len(text) > 60 else ''}")

            prev_gray = gray
            frame_idx += int(fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

        cap.release()

        print("[INFO] Compressing timeline via Semantic Chunking...")
        chunked_events = []

        if raw_events:
            current = raw_events[0].copy()
            current["start_time"] = current.pop("timestamp")
            current["end_time"] = current["start_time"]

            for event in raw_events[1:]:
                if event["action"] == current["action"] and event["objects"] == current["objects"]:
                    current["end_time"] = event["timestamp"]
                else:
                    chunked_events.append(self._build_scene_graph(current))
                    current = event.copy()
                    current["start_time"] = current.pop("timestamp")
                    current["end_time"] = current["start_time"]

            chunked_events.append(self._build_scene_graph(current))

        return chunked_events, audio_segments, ocr_events, peak_volume

    @staticmethod
    def _build_scene_graph(chunk: dict) -> dict:
        label = (
            f"Duration: [{chunk['start_time']}s - {chunk['end_time']}s] | "
            f"Subjects: {chunk['objects']} | "
            f"Action State: {chunk['action']}"
        )
        return {"timestamp": chunk["start_time"], "label": label}