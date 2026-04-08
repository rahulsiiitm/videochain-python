"""
vidchain/processor.py
---------------------
Titan-Grade Multimodal Processor.
Fuses Audio, Vision, OCR, and Emotion into a single Unified Timeline.
"""

import os
import cv2
import torch
import whisper
import librosa
import numpy as np
from moviepy import VideoFileClip
from typing import List, Dict, Any, Tuple

# Internal VidChain Imports
from vidchain.processors.ocr_model import OCRProcessor
from vidchain.processors.emotion_model import ThreadedEmotionAnalyzer
from vidchain.processors.tracker import TemporalTracker

OCR_INTERVAL_SECONDS = 5.0

class VideoProcessor:
    def __init__(self, video_path: str, ocr_languages: list = ["en"]):
        self.video_path = video_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Initialize the "Locked" Providers
        self.audio_model = whisper.load_model("base", device=self.device)
        self.ocr = OCRProcessor(languages=ocr_languages)
        self.emotion = ThreadedEmotionAnalyzer()
        self.tracker = TemporalTracker()

    def _extract_wav(self) -> str:
        wav_path = self.video_path.rsplit(".", 1)[0] + "_audio.wav"
        if not os.path.exists(wav_path):
            with VideoFileClip(self.video_path) as clip:
                clip.audio.write_audiofile(wav_path, fps=16000, logger=None) #type: ignore
        return wav_path

    def extract_context(self, yolo_engine, action_engine) -> List[Dict[str, Any]]:
        """
        The Master Pipeline. Returns a FUSED list of VideoEvents.
        """
        # 1. AUDIO LAYER
        wav_path = self._extract_wav()
        raw_audio = self.audio_model.transcribe(wav_path, fp16=(self.device == "cuda"))
        
        # Audio Anomaly Detection (Peak Volume)
        y, sr = librosa.load(wav_path, sr=None)
        rms = librosa.feature.rms(y=y)
        peak_volume = float(np.max(rms))

        # 2. VISION + TEMPORAL LAYER
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        
        raw_events = []
        frame_idx = 0
        last_ocr_time = -OCR_INTERVAL_SECONDS
        last_emotion = None
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            timestamp = round(frame_idx / fps, 2)
            
            # Sub-sampling to save VRAM (Processing 1 frame per second)
            # YOLO + Action + Tracking
            objects, _, raw_detections = yolo_engine.predict(frame)
            action, _ = action_engine.predict(frame) if objects != "no significant objects" else ("NORMAL", 1.0)
            temporal = self.tracker.process_frame(frame, raw_detections, timestamp)

            # Threaded Emotion
            if self.emotion.processor.should_run(objects):
                self.emotion.submit(frame)
                res = self.emotion.collect()
                if res: last_emotion = res

            # OCR Rate-Limited
            current_ocr = None
            if self.ocr.should_run(objects) and (timestamp - last_ocr_time) >= OCR_INTERVAL_SECONDS:
                text = self.ocr.extract_text(frame)
                if text:
                    current_ocr = text
                    last_ocr_time = timestamp

            raw_events.append({
                "time": timestamp,
                "objects": objects,
                "action": action.upper(),
                "emotion": last_emotion,
                "ocr": current_ocr,
                "camera": temporal["camera_motion"],
                "tracking": temporal["tracked_subjects"]
            })

            # Jump to next second
            frame_idx += int(fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

        cap.release()
        if self.device == "cuda": torch.cuda.empty_cache()

        # 3. SEMANTIC FUSION (Snapping Audio to Vision)
        fused_timeline = self._fuse_multimodal_layers(
            raw_events, 
            raw_audio.get("segments", []),
            peak_volume
        )

        return fused_timeline

    def _fuse_multimodal_layers(self, visual_events, audio_segments, peak_vol) -> List[Dict]:
        """
        The 'Titan' step: Merges dialogue into the visual chunks based on time overlaps.
        """
        fused = []
        for v_evt in visual_events:
            # Find dialogue that happened during this visual timestamp
            overlapping_speech = [
                s["text"].strip() for s in audio_segments 
                if s["start"] <= v_evt["time"] <= s["end"]
            ]
            
            # Build a rich scene description
            v_evt["audio"] = " ".join(overlapping_speech) if overlapping_speech else None
            
            # Anomaly flagging
            v_evt["audio_anomaly"] = "HIGH_VOLUME" if peak_vol > 0.5 else "NORMAL"
            
            fused.append(v_evt)
        
        # Final Compression: Group identical sequential events into one 'Scene'
        return self._compress_timeline(fused)

    def _compress_timeline(self, events: List[Dict]) -> List[Dict]:
        """Groups contiguous identical actions into Scene Blocks."""
        if not events: return []
        
        compressed = []
        curr = events[0].copy()
        curr["duration"] = 0
        
        for next_evt in events[1:]:
            if next_evt["action"] == curr["action"] and next_evt["objects"] == curr["objects"]:
                curr["duration"] = round(next_evt["time"] - curr["time"], 2)
            else:
                compressed.append(curr)
                curr = next_evt.copy()
                curr["duration"] = 0
        
        compressed.append(curr)
        return compressed