"""
vidchain/processor.py
---------------------
Titan-Grade Multimodal Processor.
Fuses Audio, Vision, OCR, Emotion, and Temporal Tracking
into a single Unified Timeline using Adaptive Keyframe Extraction.
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
OCR_INTERVAL_SECONDS  = 5.0   # min gap between OCR calls
CHANGE_THRESHOLD      = 8.0   # % pixel change to trigger keyframe processing
BLUR_KERNEL           = (21, 21)  # Gaussian blur kernel (noise suppression)
DIFF_INTENSITY_CUTOFF = 50    # pixel intensity delta to count as "changed"
AUDIO_SQUELCH_RMS     = 0.02  # min RMS energy to accept a Whisper segment
AUDIO_SQUELCH_CHARS   = 2     # min transcript length to accept


class VideoProcessor:
    def __init__(self, video_path: str, ocr_languages: list = ["en"]):
        self.video_path = video_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        print(f"[VidChain] Pipeline device: {self.device.upper()}")
        print("[VidChain] Loading Whisper (base)...")
        self.audio_model = whisper.load_model("base", device=self.device)

        print("[VidChain] Loading OCR Engine...")
        self.ocr = OCRProcessor(languages=ocr_languages)

        print("[VidChain] Loading Emotion Engine...")
        self.emotion = ThreadedEmotionAnalyzer()

        print("[VidChain] Loading Temporal Tracker...")
        self.tracker = TemporalTracker()

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------

    def _extract_wav(self) -> str:
        """Extract video audio to 16kHz WAV — soundfile handles this natively."""
        wav_path = self.video_path.rsplit(".", 1)[0] + "_audio.wav"
        if not os.path.exists(wav_path):
            print("[VidChain] Extracting audio to WAV...")
            with VideoFileClip(self.video_path) as clip:
                clip.audio.write_audiofile(wav_path, fps=16000, logger=None)  # type: ignore
        return wav_path

    # ------------------------------------------------------------------
    # Main Pipeline
    # ------------------------------------------------------------------

    def extract_context(
        self,
        yolo_engine,
        action_engine,
        on_progress: Optional[Callable[[float], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Master pipeline. Returns a fused, compressed list of VideoEvent dicts.

        Steps:
          1. Whisper ASR on extracted WAV
          2. Adaptive keyframe extraction (Gaussian blur + frame differencing)
          3. Per-keyframe: YOLO + MobileNet + OCR + Emotion + TemporalTracker
          4. Multimodal fusion (audio snapped to visual timestamps)
          5. Temporal smoothing + semantic scene compression
        """

        # ── 1. Audio (Adaptive AudioLoader) ───────────────────────────
        wav_path = self._extract_wav()

        print("[VidChain] Transcribing audio (Whisper)...")
        raw_audio = self.audio_model.transcribe(wav_path, fp16=(self.device == "cuda"))
        raw_segments = raw_audio.get("segments", [])

        print("[VidChain] Running Adaptive Audio Filter...")
        y_audio, _ = librosa.load(wav_path, sr=16000)
        audio_result = self.audio_loader.process_segments(raw_segments, y_audio)

        audio_segments = audio_result["segments"]
        self._audio_anomalies = audio_result["anomalies"]
        peak_volume = audio_result["peak_volume"]

        stats = audio_result["stats"]
        print(f"[VidChain] Audio: {stats['raw_count']} raw -> {stats['final_count']} clean | "
              f"{stats['anomaly_count']} anomalies detected")

        # ── 2. Vision — Adaptive Keyframe Loop ────────────────────────
        print("[VidChain] Running Adaptive Keyframe Extraction + Multimodal Inference...")
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # How often to check for scene change (3 checks/sec is plenty)
        check_interval = max(1, int(fps // 3))

        raw_events: List[Dict[str, Any]] = []
        prev_gray: Optional[np.ndarray] = None
        last_ocr_time = -OCR_INTERVAL_SECONDS
        last_emotion: Optional[str] = None
        frame_idx = 0
        keyframes_processed = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1

            # ── Progress callback ──
            if on_progress and total_frames > 0:
                on_progress(min(99.0, round((frame_idx / total_frames) * 100, 1)))

            # ── Skip frames between check intervals ──
            if frame_idx % check_interval != 0:
                continue

            timestamp = round(frame_idx / fps, 2)

            # ── Gaussian blur frame differencing ──────────────────────
            curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            curr_gray_blurred = cv2.GaussianBlur(curr_gray, BLUR_KERNEL, 0)

            if prev_gray is None:
                # Always process the very first frame
                prev_gray = curr_gray_blurred
            else:
                diff = cv2.absdiff(prev_gray, curr_gray_blurred)
                non_zero = np.count_nonzero(diff > DIFF_INTENSITY_CUTOFF)
                change_pct = (non_zero / diff.size) * 100

                if change_pct < CHANGE_THRESHOLD:
                    continue  # Scene hasn't changed enough — skip this frame

                prev_gray = curr_gray_blurred  # Update baseline to current

            keyframes_processed += 1

            # ── YOLO object detection ─────────────────────────────────
            objects, _, raw_detections = yolo_engine.predict(frame)

            # ── Action classification ─────────────────────────────────
            if objects == "no significant objects":
                action = "NORMAL"
            else:
                action, _ = action_engine.predict(frame)
                if action.lower() in ("uncertain", "unknown"):
                    action = "NORMAL"

            # ── Temporal tracking (object persistence + camera motion) ─
            temporal = self.tracker.process_frame(frame, raw_detections, timestamp)

            # ── Emotion (threaded, non-blocking) ─────────────────────
            if self.emotion.processor.should_run(objects):
                self.emotion.submit(frame)
            result = self.emotion.collect()
            if result:
                last_emotion = result

            # ── OCR (rate-limited + deduplicated) ─────────────────────
            current_ocr = None
            if self.ocr.should_run(objects) and (timestamp - last_ocr_time) >= OCR_INTERVAL_SECONDS:
                text = self.ocr.extract_text(frame)
                if text:
                    current_ocr = text
                    last_ocr_time = timestamp
                    print(f"   🔤 OCR at {timestamp}s: {text[:60]}{'...' if len(text) > 60 else ''}")

            raw_events.append({
                "time":     timestamp,
                "objects":  objects,
                "action":   action.upper(),
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

        total_checked = total_frames // check_interval
        print(f"[VidChain] Adaptive Extraction: {total_checked} frames checked → {keyframes_processed} keyframes processed")

        # ── 3. Multimodal Fusion ───────────────────────────────────────
        print("[VidChain] Fusing multimodal layers...")
        anomalies = getattr(self, "_audio_anomalies", [])
        fused = self._fuse_multimodal_layers(raw_events, audio_segments, y_audio, peak_volume, anomalies)

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
        anomalies: List[Dict] = []
    ) -> List[Dict]:
        """
        Snaps validated audio to visual timestamps.
        Uses RMS energy validation to squelch Whisper hallucinations.
        """
        SAMPLE_RATE = 16000
        fused = []

        for v_evt in visual_events:
            valid_speech = []

            for s in audio_segments:
                start_t = s.get("start", 0)
                end_t   = s.get("end", start_t + 3.0)

                if not (start_t <= v_evt["time"] <= end_t):
                    continue

                # Energy validation — reject ghost transcriptions
                s_sample = int(max(0, start_t * SAMPLE_RATE))
                e_sample = int(min(len(y_audio), end_t * SAMPLE_RATE))
                audio_slice = y_audio[s_sample:e_sample]

                rms = float(np.sqrt(np.mean(audio_slice ** 2))) if len(audio_slice) > 0 else 0.0
                text = s.get("text", "").strip()

                if rms >= AUDIO_SQUELCH_RMS and len(text) > AUDIO_SQUELCH_CHARS:
                    valid_speech.append(text)

            v_evt["audio"] = " ".join(valid_speech) if valid_speech else None
            v_evt["audio_anomaly"] = "HIGH_VOLUME" if peak_vol > 0.5 else "NORMAL"
            fused.append(v_evt)

        # Inject acoustic anomalies that don't overlap any visual timestamp
        visual_times = {e["time"] for e in fused}
        for anomaly in anomalies:
            if not any(abs(anomaly["time"] - vt) < 0.5 for vt in visual_times):
                fused.append({
                    "time":          anomaly["time"],
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
        """
        1. Majority-vote temporal smoothing (eliminates 1-frame action flickers)
        2. Scene compression (groups identical consecutive scenes into blocks)
        """
        if not events:
            return []

        # ── Smoothing ─────────────────────────────────────────────────
        actions = [e["action"] for e in events]
        smoothed = []
        for i in range(len(actions)):
            window = actions[max(0, i - 1): i + 2]
            smoothed.append(max(set(window), key=window.count))

        for i, evt in enumerate(events):
            evt["action"] = smoothed[i]

        # ── Scene Compression ─────────────────────────────────────────
        compressed = []
        curr = events[0].copy()
        curr["duration"] = 0.0

        for next_evt in events[1:]:
            same_scene = (
                next_evt["action"]  == curr["action"]
                and next_evt["objects"] == curr["objects"]
                and next_evt["emotion"] == curr["emotion"]
                and next_evt["camera"]  == curr["camera"]
            )
            if same_scene:
                curr["duration"] = round(next_evt["time"] - curr["time"], 2)
                # Carry forward any new OCR or audio from merged frames
                if next_evt.get("ocr") and not curr.get("ocr"):
                    curr["ocr"] = next_evt["ocr"]
                if next_evt.get("audio") and not curr.get("audio"):
                    curr["audio"] = next_evt["audio"]
            else:
                compressed.append(curr)
                curr = next_evt.copy()
                curr["duration"] = 0.0

        compressed.append(curr)
        return compressed