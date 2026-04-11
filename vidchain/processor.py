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

    def extract_context(self, yolo_engine, action_engine, on_progress=None) -> List[Dict[str, Any]]:
        """
        The Master Pipeline. Returns a FUSED list of VideoEvents.
        Features: Progress tracking and Signal Validation preparation.
        """
        # 1. AUDIO LAYER (Loaded at 16kHz for precise segment energy analysis)
        wav_path = self._extract_wav()
        
        # Heavy transcription call
        raw_audio = self.audio_model.transcribe(wav_path, fp16=(self.device == "cuda"))
        
        # Load raw signal data for the 'Bulletproof' squelch filter
        y_audio, _ = librosa.load(wav_path, sr=16000)
        rms = librosa.feature.rms(y=y_audio)
        peak_volume = float(np.max(rms))

        # 2. VISION + TEMPORAL LAYER
        cap = cv2.VideoCapture(self.video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        
        raw_events = []
        frame_idx = 0
        last_ocr_time = -OCR_INTERVAL_SECONDS
        last_emotion = None
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            timestamp = round(frame_idx / fps, 2)
            
            # Sub-sampling to 1 FPS for VRAM and speed efficiency
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
            
            # Library API: Progress Callback Hook
            if on_progress:
                percent = min(100.0, round((frame_idx / total_frames) * 100, 2))
                on_progress(percent)

            # Jump to next second
            frame_idx += int(fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

        cap.release()
        if self.device == "cuda": torch.cuda.empty_cache()

        # 3. SEMANTIC FUSION (Snapping Audio to Vision with Squelch Logic)
        # We pass 'y_audio' to handle energy-based hallucination filtering
        fused_timeline = self._fuse_multimodal_layers(
            raw_events, 
            raw_audio.get("segments", []),
            y_audio,
            peak_volume
        )

        return fused_timeline

    def _fuse_multimodal_layers(self, visual_events, audio_segments, y_audio, peak_vol) -> List[Dict]:
        """
        The 'Titan' step: Merges dialogue into visual chunks with Energy Validation.
        Uses y_audio to squelch 'ghost' audio hallucinations from Whisper.
        """
        fused = []
        # Constants for signal validation
        AUDIO_SENSE_THRESHOLD = 0.02 
        SAMPLE_RATE = 16000

        for v_evt in visual_events:
            valid_speech = []
            
            for s in audio_segments:
                # Check if the audio segment overlaps with the visual event timestamp
                if s["start"] <= v_evt["time"] <= s["end"]:
                    
                    # --- SIGNAL VALIDATION (The Bulletproof Check) ---
                    # Calculate the start and end samples in the raw audio signal
                    start_sample = int(max(0, s["start"] * SAMPLE_RATE))
                    end_sample = int(min(len(y_audio), s["end"] * SAMPLE_RATE))
                    
                    # Extract the audio slice
                    audio_slice = y_audio[start_sample:end_sample]
                    
                    # Calculate RMS (Root Mean Square) Energy - the 'loudness'
                    segment_energy = np.sqrt(np.mean(audio_slice**2)) if len(audio_slice) > 0 else 0
                    
                    # Only accept if it's loud enough and not just short gibberish
                    if segment_energy > AUDIO_SENSE_THRESHOLD and len(s["text"].strip()) > 2:
                        valid_speech.append(s["text"].strip())
            
            # Fuse the validated audio back into the event
            v_evt["audio"] = " ".join(valid_speech) if valid_speech else None
            
            # Preserve the global anomaly flagging
            v_evt["audio_anomaly"] = "HIGH_VOLUME" if peak_vol > 0.5 else "NORMAL"
            
            fused.append(v_evt)
        
        # Final Compression: Group identical sequential events into one 'Scene'
        return self._compress_and_smooth_timeline(fused)

    def _compress_and_smooth_timeline(self, events: List[Dict]) -> List[Dict]:
        """
        Titan Upgrade: Applies a temporal majority-vote filter to eliminate 
        flickering before grouping contiguous identical actions into Scene Blocks.
        """
        if not events: return []
        
        # 1. Temporal Smoothing (Majority Vote)
        # Prevents 1-frame glitches (e.g., 'NORMAL' -> 'VIOLENCE' -> 'NORMAL') 
        # from creating false forensic alerts.
        actions = [e['action'] for e in events]
        smoothed_actions = []
        
        for i in range(len(actions)):
            # Sliding window of 3: [previous_sample, current, next_sample]
            # This 'votes' on the true state of the scene.
            window = actions[max(0, i-1) : i+2]
            
            # Select the most frequent label in the local window
            consensus_action = max(set(window), key=window.count)
            smoothed_actions.append(consensus_action)
            
        # Update the event stream with the validated 'smoothed' labels
        for i, event in enumerate(events):
            event['action'] = smoothed_actions[i]

        # 2. Scene Compression
        # Merges identical sequential states into a single record with a 'duration'
        # to prevent context-window overflow in the RAG engine.
        compressed = []
        curr = events[0].copy()
        curr["duration"] = 0
        
        for next_evt in events[1:]:
            # A 'Scene' is defined by an identical Action AND identical Visual Subjects
            if next_evt["action"] == curr["action"] and next_evt["objects"] == curr["objects"]:
                # Calculate elapsed time from the start of the current block
                curr["duration"] = round(next_evt["time"] - curr["time"], 2)
            else:
                # Scene has changed; push the completed block and start a new one
                compressed.append(curr)
                curr = next_evt.copy()
                curr["duration"] = 0
        
        # Ensure the final block is indexed
        compressed.append(curr)
        return compressed