import os
import cv2
import torch
import whisper  # type: ignore
import librosa
import numpy as np
from moviepy import VideoFileClip

from vidchain.processors.ocr_model import OCRProcessor
from vidchain.processors.emotion_model import ThreadedEmotionAnalyzer
from vidchain.processors.temporal_tracker import TemporalTracker

OCR_INTERVAL_SECONDS = 5.0


class VideoProcessor:
    def __init__(self, video_path: str, ocr_languages: list = ["en"]):
        self.video_path = video_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        print(f"[INFO] Pipeline device: {self.device.upper()}")
        print("[INFO] Loading Whisper Audio Model (base)...")
        self.audio_model = whisper.load_model("base", device=self.device)

        print("[INFO] Loading OCR Engine...")
        self.ocr = OCRProcessor(languages=ocr_languages)

        print("[INFO] Loading Emotion Engine...")
        self.emotion = ThreadedEmotionAnalyzer()

        print("[INFO] Loading Temporal Tracker...")
        self.tracker = TemporalTracker()

    def _extract_wav(self) -> str:
        wav_path = self.video_path.rsplit(".", 1)[0] + "_audio.wav"
        if os.path.exists(wav_path):
            return wav_path
        print("[INFO] Extracting audio to WAV...")
        with VideoFileClip(self.video_path) as clip:
            clip.audio.write_audiofile(wav_path, fps=16000, logger=None)  # type: ignore
        return wav_path

    def extract_context(self, yolo_engine, action_engine):
        # ── Audio ──────────────────────────────────────────────────
        wav_path = self._extract_wav()

        print("[INFO] Transcribing audio (Whisper)...")
        raw_audio = self.audio_model.transcribe(wav_path, fp16=(self.device == "cuda"))
        audio_segments = [
            {"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip()}
            for s in raw_audio.get("segments", [])
        ]

        print("[INFO] Analyzing audio energy (librosa)...")
        y, sr = librosa.load(wav_path, sr=None)
        peak_volume = float(np.max(librosa.feature.rms(y=y)))

        # ── Vision + OCR + Emotion + Temporal ─────────────────────
        print("[INFO] Extracting Scene Graphs + OCR + Emotions + Temporal Context...")
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        raw_events = []
        ocr_events = []
        prev_gray = None
        frame_idx = 0
        last_ocr_time = -OCR_INTERVAL_SECONDS
        last_emotion: str | None = None

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if prev_gray is not None and np.mean(cv2.absdiff(prev_gray, gray)) > 2.0:
                timestamp = round(frame_idx / fps, 2)

                # ── YOLO (now returns raw boxes too) ──
                objects, _, raw_detections = yolo_engine.predict(frame)

                # ── Action ──
                if objects == "no significant objects":
                    action = "NORMAL"
                else:
                    action, _ = action_engine.predict(frame)
                    if action.lower() == "uncertain":
                        action = "NORMAL"

                # ── Temporal tracking (object persistence + camera motion) ──
                temporal = self.tracker.process_frame(frame, raw_detections, timestamp)

                # ── Emotion (threaded) ──
                if self.emotion.processor.should_run(objects):
                    self.emotion.submit(frame)
                result = self.emotion.collect()
                if result:
                    last_emotion = result

                raw_events.append({
                    "timestamp":        timestamp,
                    "objects":          objects,
                    "action":           action.upper(),
                    "emotion":          last_emotion,
                    "camera_motion":    temporal["camera_motion"],
                    "tracked_subjects": temporal["tracked_subjects"],
                })

                # ── OCR (rate-limited) ──
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

        # ── Semantic Chunking ──────────────────────────────────────
        print("[INFO] Compressing timeline via Semantic Chunking...")
        chunked_events = []

        if raw_events:
            current = raw_events[0].copy()
            current["start_time"] = current.pop("timestamp")
            current["end_time"]   = current["start_time"]

            for event in raw_events[1:]:
                same_scene = (
                    event["action"]        == current["action"]
                    and event["objects"]   == current["objects"]
                    and event["emotion"]   == current["emotion"]
                    and event["camera_motion"] == current["camera_motion"]
                )
                if same_scene:
                    current["end_time"] = event["timestamp"]
                else:
                    chunked_events.append(self._build_scene_graph(current))
                    current = event.copy()
                    current["start_time"] = current.pop("timestamp")
                    current["end_time"]   = current["start_time"]

            chunked_events.append(self._build_scene_graph(current))

        return chunked_events, audio_segments, ocr_events, peak_volume

    @staticmethod
    def _build_scene_graph(chunk: dict) -> dict:
        label = (
            f"Duration: [{chunk['start_time']}s - {chunk['end_time']}s] | "
            f"Subjects: {chunk['objects']} | "
            f"Action State: {chunk['action']}"
        )
        if chunk.get("emotion"):
            label += f" | Emotion: {chunk['emotion']}"
        if chunk.get("camera_motion") and chunk["camera_motion"] != "static":
            label += f" | Camera: {chunk['camera_motion']}"
        if chunk.get("tracked_subjects"):
            label += f" | Tracking: {', '.join(chunk['tracked_subjects'])}"

        return {
            "timestamp":        chunk["start_time"],
            "label":            label,
            "emotion":          chunk.get("emotion"),
            "camera_motion":    chunk.get("camera_motion"),
            "tracked_subjects": chunk.get("tracked_subjects", []),
        }