"""
vidchain/processor.py
---------------------
Titan-Grade Multimodal Processor.
Fuses Audio, Vision, OCR, Emotion, Scene Context, and Temporal Tracking
into a single Unified Timeline using Adaptive Keyframe Extraction.

Designed for robustness: every inference stage fails gracefully —
a single model crash never brings down the full pipeline.
"""

import os
import cv2
import torch
import whisper
import librosa
import numpy as np
from moviepy import VideoFileClip
from typing import List, Dict, Any, Optional, Callable

from vidchain.processors.ocr_model import OCRProcessor
from vidchain.loaders.audio_loader import AudioLoader
from vidchain.processors.emotion_model import ThreadedEmotionAnalyzer
from vidchain.processors.tracker import TemporalTracker

# ── Tunable Constants ──────────────────────────────────────────────────────
OCR_INTERVAL_SECONDS   = 5.0
SCENE_INTERVAL_SECONDS = 10.0
CHANGE_THRESHOLD       = 8.0
BLUR_KERNEL            = (21, 21)
DIFF_INTENSITY_CUTOFF  = 50
AUDIO_SQUELCH_RMS      = 0.02
AUDIO_SQUELCH_CHARS    = 2


class VideoProcessor:
    def __init__(self, video_path: str, ocr_languages: list = ["en"]):
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"[VidChain] Video not found: {video_path}")

        self.video_path = video_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._errors: List[str] = []  # collect non-fatal errors for reporting

        print(f"[VidChain] Pipeline device: {self.device.upper()}")

        # Each engine loads independently — failure is non-fatal
        self.audio_model = self._load_whisper()
        self.audio_loader = AudioLoader()
        self.ocr          = self._load_ocr(ocr_languages)
        self.emotion      = self._load_emotion()
        self.tracker      = TemporalTracker()

    # ------------------------------------------------------------------
    # Safe engine loaders
    # ------------------------------------------------------------------

    def _load_whisper(self):
        try:
            print("[VidChain] Loading Whisper (base)...")
            return whisper.load_model("base", device=self.device)
        except Exception as e:
            self._errors.append(f"Whisper load failed: {e}")
            print(f"[VidChain] WARNING: Whisper unavailable — audio will be skipped. ({e})")
            return None

    def _load_ocr(self, languages):
        try:
            print("[VidChain] Loading OCR Engine...")
            return OCRProcessor(languages=languages)
        except Exception as e:
            self._errors.append(f"OCR load failed: {e}")
            print(f"[VidChain] WARNING: OCR unavailable — text extraction skipped. ({e})")
            return None

    def _load_emotion(self):
        try:
            print("[VidChain] Loading Emotion Engine...")
            return ThreadedEmotionAnalyzer()
        except Exception as e:
            self._errors.append(f"Emotion load failed: {e}")
            print(f"[VidChain] WARNING: Emotion engine unavailable — emotion skipped. ({e})")
            return None

    # ------------------------------------------------------------------
    # Audio extraction
    # ------------------------------------------------------------------

    def _extract_wav(self) -> Optional[str]:
        wav_path = self.video_path.rsplit(".", 1)[0] + "_audio.wav"
        if os.path.exists(wav_path):
            return wav_path
        try:
            print("[VidChain] Extracting audio to WAV...")
            with VideoFileClip(self.video_path) as clip:
                if clip.audio is None:
                    print("[VidChain] WARNING: Video has no audio track.")
                    return None
                clip.audio.write_audiofile(wav_path, fps=16000, logger=None)  # type: ignore
            return wav_path
        except Exception as e:
            self._errors.append(f"WAV extraction failed: {e}")
            print(f"[VidChain] WARNING: Audio extraction failed — audio skipped. ({e})")
            return None

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def extract_context(
        self,
        yolo_engine,
        action_engine,
        scene_engine: Optional[Any] = None,
        on_progress: Optional[Callable[[float], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Master pipeline. Returns a fused, compressed list of VideoEvent dicts.
        Every stage degrades gracefully — partial results are always returned.
        """

        # ── 1. Audio ──────────────────────────────────────────────────
        audio_segments: List[Dict] = []
        audio_anomalies: List[Dict] = []
        peak_volume = 0.0
        y_audio = np.zeros(16000, dtype=np.float32)

        wav_path = self._extract_wav()
        if wav_path and self.audio_model:
            try:
                print("[VidChain] Transcribing audio (Whisper)...")
                raw_audio    = self.audio_model.transcribe(wav_path, fp16=(self.device == "cuda"))
                raw_segments = raw_audio.get("segments", [])

                print("[VidChain] Running Adaptive Audio Filter...")
                y_audio, _ = librosa.load(wav_path, sr=16000)
                audio_result   = self.audio_loader.process_segments(raw_segments, y_audio) #type:ignore
                audio_segments  = audio_result["segments"]
                audio_anomalies = audio_result["anomalies"]
                peak_volume     = audio_result["peak_volume"]

                s = audio_result["stats"]
                print(f"[VidChain] Audio: {s['raw_count']} raw → {s['final_count']} clean | "
                      f"{s['anomaly_count']} anomalies")
            except Exception as e:
                self._errors.append(f"Audio processing failed: {e}")
                print(f"[VidChain] WARNING: Audio processing error — continuing without audio. ({e})")

        # ── 2. Vision — Adaptive Keyframe Loop ────────────────────────
        print("[VidChain] Running Adaptive Keyframe Extraction...")
        cap = cv2.VideoCapture(self.video_path)

        if not cap.isOpened():
            raise RuntimeError(f"[VidChain] Cannot open video: {self.video_path}")

        fps          = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        check_interval = max(1, int(fps // 3))

        raw_events: List[Dict[str, Any]] = []
        prev_gray:   Optional[np.ndarray] = None
        last_ocr_time   = -OCR_INTERVAL_SECONDS
        last_scene_time = -SCENE_INTERVAL_SECONDS
        last_emotion:  Optional[str] = None
        last_scene:    Optional[str] = None
        frame_idx = 0
        keyframes_processed = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1

            if on_progress and total_frames > 0:
                on_progress(min(99.0, round((frame_idx / total_frames) * 100, 1)))

            if frame_idx % check_interval != 0:
                continue

            timestamp = round(frame_idx / fps, 2)

            # ── CLIP scene classification (rate-limited) ───────────────
            if scene_engine and (timestamp - last_scene_time) >= SCENE_INTERVAL_SECONDS:
                try:
                    result = scene_engine.predict(frame)
                    if result:
                        last_scene      = result
                        last_scene_time = timestamp
                        print(f"   🌍 Scene at {timestamp}s: {last_scene}")
                except Exception as e:
                    self._errors.append(f"CLIP error at {timestamp}s: {e}")

            # ── Adaptive keyframe decision ─────────────────────────────
            curr_gray_blurred = cv2.GaussianBlur(
                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), BLUR_KERNEL, 0
            )
            if prev_gray is None:
                prev_gray = curr_gray_blurred
            else:
                diff       = cv2.absdiff(prev_gray, curr_gray_blurred)
                non_zero   = np.count_nonzero(diff > DIFF_INTENSITY_CUTOFF)
                change_pct = (non_zero / diff.size) * 100
                if change_pct < CHANGE_THRESHOLD:
                    continue
                prev_gray = curr_gray_blurred

            keyframes_processed += 1

            # ── YOLO ──────────────────────────────────────────────────
            objects        = "no significant objects"
            raw_detections = []
            try:
                objects, _, raw_detections = yolo_engine.predict(frame)
            except Exception as e:
                self._errors.append(f"YOLO error at {timestamp}s: {e}")

            # ── Action ────────────────────────────────────────────────
            action = "NORMAL"
            try:
                if objects != "no significant objects":
                    a, _ = action_engine.predict(frame)
                    if a.lower() not in ("uncertain", "unknown"):
                        action = a.upper()
            except Exception as e:
                self._errors.append(f"Action engine error at {timestamp}s: {e}")

            # ── Temporal tracking ─────────────────────────────────────
            temporal = {"camera_motion": "static", "tracked_subjects": []}
            try:
                temporal = self.tracker.process_frame(frame, raw_detections, timestamp)
            except Exception as e:
                self._errors.append(f"Tracker error at {timestamp}s: {e}")

            # ── Emotion (threaded) ────────────────────────────────────
            try:
                if self.emotion and self.emotion.processor.should_run(objects):
                    self.emotion.submit(frame)
                if self.emotion:
                    result = self.emotion.collect()
                    if result:
                        last_emotion = result
            except Exception as e:
                self._errors.append(f"Emotion error at {timestamp}s: {e}")

            # ── OCR (rate-limited) ────────────────────────────────────
            current_ocr = None
            try:
                if (self.ocr
                        and self.ocr.should_run(objects)
                        and (timestamp - last_ocr_time) >= OCR_INTERVAL_SECONDS):
                    text = self.ocr.extract_text(frame)
                    if text:
                        current_ocr   = text
                        last_ocr_time = timestamp
                        print(f"   🔤 OCR at {timestamp}s: {text[:60]}{'...' if len(text) > 60 else ''}")
            except Exception as e:
                self._errors.append(f"OCR error at {timestamp}s: {e}")

            raw_events.append({
                "time":     timestamp,
                "scene":    last_scene,
                "objects":  objects,
                "action":   action,
                "emotion":  last_emotion,
                "ocr":      current_ocr,
                "camera":   temporal["camera_motion"],
                "tracking": temporal["tracked_subjects"],
            })

        cap.release()

        if on_progress:
            on_progress(100.0)
        if self.device == "cuda":
            torch.cuda.empty_cache()

        print(f"[VidChain] Extraction: {total_frames // check_interval} checked "
              f"→ {keyframes_processed} keyframes processed")

        if self._errors:
            print(f"[VidChain] Non-fatal warnings during pipeline: {len(self._errors)}")
            for err in self._errors[:5]:
                print(f"   ⚠ {err}")

        # ── 3. Fusion ─────────────────────────────────────────────────
        print("[VidChain] Fusing multimodal layers...")
        fused = self._fuse_multimodal_layers(
            raw_events, audio_segments, y_audio, peak_volume, audio_anomalies
        )

        # ── 4. Smooth + Compress ──────────────────────────────────────
        print("[VidChain] Compressing timeline...")
        compressed = self._compress_and_smooth_timeline(fused)

        print(f"[VidChain] ✅ Pipeline complete — {len(compressed)} semantic scenes indexed.")
        return compressed

    # ------------------------------------------------------------------
    # Fusion
    # ------------------------------------------------------------------

    def _fuse_multimodal_layers(
        self,
        visual_events: List[Dict],
        audio_segments: List[Dict],
        y_audio: np.ndarray,
        peak_vol: float,
        anomalies: List[Dict]
    ) -> List[Dict]:
        SAMPLE_RATE = 16000
        fused = []

        for v_evt in visual_events:
            valid_speech = []
            for s in audio_segments:
                start_t = s.get("start", 0)
                end_t   = s.get("end", start_t + 3.0)
                if not (start_t <= v_evt["time"] <= end_t):
                    continue
                s_sample    = int(max(0, start_t * SAMPLE_RATE))
                e_sample    = int(min(len(y_audio), end_t * SAMPLE_RATE))
                audio_slice = y_audio[s_sample:e_sample]
                rms  = float(np.sqrt(np.mean(audio_slice ** 2))) if len(audio_slice) > 0 else 0.0
                text = s.get("text", "").strip()
                if rms >= AUDIO_SQUELCH_RMS and len(text) > AUDIO_SQUELCH_CHARS:
                    valid_speech.append(text)

            v_evt["audio"]         = " ".join(valid_speech) if valid_speech else None
            v_evt["audio_anomaly"] = "HIGH_VOLUME" if peak_vol > 0.5 else "NORMAL"
            fused.append(v_evt)

        visual_times = {e["time"] for e in fused}
        for anomaly in anomalies:
            if not any(abs(anomaly["time"] - vt) < 0.5 for vt in visual_times):
                fused.append({
                    "time":          anomaly["time"],
                    "scene":         None,
                    "objects":       "no significant objects",
                    "action":        "NORMAL",
                    "emotion":       None,
                    "ocr":           None,
                    "audio":         None,
                    "camera":        "static",
                    "tracking":      [],
                    "audio_anomaly": anomaly["type"],
                    "duration":      0.0,
                })

        fused.sort(key=lambda x: x["time"])
        return fused

    # ------------------------------------------------------------------
    # Compression
    # ------------------------------------------------------------------

    def _compress_and_smooth_timeline(self, events: List[Dict]) -> List[Dict]:
        if not events:
            return []

        # Majority-vote smoothing
        actions  = [e["action"] for e in events]
        smoothed = []
        for i in range(len(actions)):
            window = actions[max(0, i - 1): i + 2]
            smoothed.append(max(set(window), key=window.count))
        for i, evt in enumerate(events):
            evt["action"] = smoothed[i]

        # Scene compression
        compressed = []
        curr = events[0].copy()
        curr["duration"] = 0.0

        for next_evt in events[1:]:
            same = (
                next_evt["action"]          == curr["action"]
                and next_evt["objects"]     == curr["objects"]
                and next_evt["emotion"]     == curr["emotion"]
                and next_evt["camera"]      == curr["camera"]
                and next_evt.get("scene")   == curr.get("scene")
            )
            if same:
                curr["duration"] = round(next_evt["time"] - curr["time"], 2)
                if next_evt.get("ocr")   and not curr.get("ocr"):
                    curr["ocr"]   = next_evt["ocr"]
                if next_evt.get("audio") and not curr.get("audio"):
                    curr["audio"] = next_evt["audio"]
            else:
                compressed.append(curr)
                curr = next_evt.copy()
                curr["duration"] = 0.0

        compressed.append(curr)
        return compressed