"""
vidchain/loaders/audio_loader.py
---------------------------------
Adaptive Audio Loader — the audio equivalent of adaptive keyframe extraction.

Instead of dumping the full raw Whisper transcript, this loader:
  1. Validates each segment by RMS energy (rejects silence/noise)
  2. Filters content (rejects filler words, gibberish, too-short text)
  3. Merges nearby segments into coherent utterances
  4. Flags acoustic anomalies (sudden loud events) even without speech
  5. Returns a clean, deduplicated, timestamped transcript

Analogous to VideoLoader's Gaussian blur + frame differencing —
only "significant" audio moments make it into the knowledge base.
"""

import os
import re
import numpy as np
import librosa
from moviepy import VideoFileClip
from typing import List, Dict, Any, Optional


# ── Tunable Constants ──────────────────────────────────────────────────────
RMS_THRESHOLD        = 0.02   # min RMS energy to accept a segment (silence gate)
ANOMALY_RMS          = 0.15   # RMS above this = acoustic anomaly (shout/bang)
MIN_CHARS            = 4      # min transcript characters to keep
MERGE_GAP_SECONDS    = 1.5    # merge segments closer than this (seconds)
MAX_SEGMENT_WORDS    = 60     # split segments longer than this (context window safety)
SAMPLE_RATE          = 16000  # WAV sample rate

# Common Whisper hallucinations and filler words to strip
FILLER_PATTERNS = re.compile(
    r"^\s*("
    r"uh+|um+|hmm+|hm+|ah+|oh+|eh+|er+|"       # fillers
    r"thank you\.?|thanks\.?|you\.?|"            # common whisper ghosts
    r"\[.*?\]|"                                   # [BLANK_AUDIO], [Music], etc.
    r"\.{2,}|"                                    # ellipsis-only
    r"\s*\.\s*"                                   # lone period
    r")\s*$",
    re.IGNORECASE
)


class AudioLoader:
    """
    Adaptive audio processor that mirrors the intelligence of VideoLoader's
    keyframe extraction — only meaningful audio moments pass through.
    """

    def __init__(self, output_dir: str = "temp_audio"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # WAV Extraction
    # ------------------------------------------------------------------

    def extract_wav(self, video_path: str) -> str:
        """
        Extracts 16kHz mono WAV from video.
        Cached — skips extraction if WAV already exists.
        """
        wav_path = os.path.join(
            self.output_dir,
            os.path.splitext(os.path.basename(video_path))[0] + "_audio.wav"
        )
        if os.path.exists(wav_path):
            print(f"[AudioLoader] Using cached WAV: {wav_path}")
            return wav_path

        print(f"[AudioLoader] Extracting audio from {os.path.basename(video_path)}...")
        with VideoFileClip(video_path) as clip:
            clip.audio.write_audiofile(wav_path, fps=SAMPLE_RATE, logger=None)  # type: ignore
        print(f"[AudioLoader] WAV saved: {wav_path}")
        return wav_path

    # ------------------------------------------------------------------
    # Core: Adaptive Segment Processing
    # ------------------------------------------------------------------

    def process_segments(
        self,
        raw_segments: List[Dict[str, Any]],
        y_audio: np.ndarray,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        The main adaptive filter. Takes raw Whisper segments + raw audio signal,
        returns a clean transcript with anomaly flags.

        Args:
            raw_segments: Whisper output segments (list of {start, end, text})
            y_audio:      Raw audio signal at SAMPLE_RATE (from librosa.load)
            verbose:      Print per-segment decisions

        Returns:
            {
                "segments":  List of clean {start, end, text, energy, merged} dicts,
                "anomalies": List of {time, type, energy} acoustic events,
                "peak_volume": float,
                "stats": {...}
            }
        """
        if verbose:
            print(f"[AudioLoader] Processing {len(raw_segments)} raw Whisper segments...")

        peak_volume = float(np.max(librosa.feature.rms(y=y_audio)))
        anomalies = self._detect_anomalies(y_audio, peak_volume)

        # ── Step 1: Validate each segment ─────────────────────────────
        validated = []
        rejected = 0

        for seg in raw_segments:
            start_t = seg.get("start", 0)
            end_t   = seg.get("end", start_t + 1.0)
            text    = seg.get("text", "").strip()

            # Content filter: filler words, hallucinations, too short
            if FILLER_PATTERNS.match(text) or len(text) < MIN_CHARS:
                rejected += 1
                continue

            # Energy filter: silence gate
            s_sample = int(max(0, start_t * SAMPLE_RATE))
            e_sample = int(min(len(y_audio), end_t * SAMPLE_RATE))
            audio_slice = y_audio[s_sample:e_sample]
            rms = float(np.sqrt(np.mean(audio_slice ** 2))) if len(audio_slice) > 0 else 0.0

            if rms < RMS_THRESHOLD:
                rejected += 1
                if verbose:
                    print(f"   🔇 Rejected (silent): [{start_t:.1f}s] \"{text[:40]}\"")
                continue

            validated.append({
                "start":  round(start_t, 2),
                "end":    round(end_t, 2),
                "text":   text,
                "energy": round(rms, 4),
                "merged": False,
            })

        if verbose:
            print(f"[AudioLoader] Validated: {len(validated)} | Rejected: {rejected}")

        # ── Step 2: Merge nearby segments ─────────────────────────────
        merged = self._merge_segments(validated, verbose)

        # ── Step 3: Deduplicate consecutive identical text ─────────────
        deduped = self._deduplicate(merged)

        if verbose:
            print(f"[AudioLoader] After merge+dedup: {len(deduped)} clean segments")
            print(f"[AudioLoader] Peak Volume: {peak_volume:.4f} | Anomalies: {len(anomalies)}")

        return {
            "segments":    deduped,
            "anomalies":   anomalies,
            "peak_volume": peak_volume,
            "stats": {
                "raw_count":       len(raw_segments),
                "validated_count": len(validated),
                "final_count":     len(deduped),
                "rejected_count":  rejected,
                "anomaly_count":   len(anomalies),
            }
        }

    # ------------------------------------------------------------------
    # Merge nearby segments into coherent utterances
    # ------------------------------------------------------------------

    def _merge_segments(
        self,
        segments: List[Dict],
        verbose: bool = False
    ) -> List[Dict]:
        """
        Joins segments that are within MERGE_GAP_SECONDS of each other.
        Treats them as one continuous utterance — more useful for RAG context.
        """
        if not segments:
            return []

        merged = []
        current = segments[0].copy()

        for next_seg in segments[1:]:
            gap = next_seg["start"] - current["end"]

            if gap <= MERGE_GAP_SECONDS:
                # Merge: extend current segment
                current["end"]    = next_seg["end"]
                current["text"]   = current["text"].rstrip(".") + " " + next_seg["text"]
                current["energy"] = max(current["energy"], next_seg["energy"])
                current["merged"] = True
            else:
                # Gap too large — finalize current, start new
                merged.append(self._trim_segment(current))
                current = next_seg.copy()

        merged.append(self._trim_segment(current))
        return merged

    # ------------------------------------------------------------------
    # Deduplicate consecutive identical utterances
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate(segments: List[Dict]) -> List[Dict]:
        """Remove consecutive segments with identical or near-identical text."""
        if not segments:
            return []

        deduped = [segments[0]]
        for seg in segments[1:]:
            # Normalize for comparison: lowercase, strip punctuation
            prev_norm = re.sub(r"[^a-z0-9\s]", "", deduped[-1]["text"].lower()).strip()
            curr_norm = re.sub(r"[^a-z0-9\s]", "", seg["text"].lower()).strip()

            if curr_norm != prev_norm:
                deduped.append(seg)

        return deduped

    # ------------------------------------------------------------------
    # Acoustic anomaly detection
    # ------------------------------------------------------------------

    def _detect_anomalies(
        self,
        y_audio: np.ndarray,
        peak_volume: float,
        window_seconds: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Scans audio in sliding windows for sudden loud events —
        shouts, bangs, crashes — even when there's no speech.
        These are flagged as acoustic anomalies in the KB.
        """
        anomalies = []
        window_samples = int(window_seconds * SAMPLE_RATE)

        for i in range(0, len(y_audio) - window_samples, window_samples):
            window = y_audio[i: i + window_samples]
            rms = float(np.sqrt(np.mean(window ** 2)))

            if rms >= ANOMALY_RMS:
                timestamp = round(i / SAMPLE_RATE, 2)
                anomaly_type = (
                    "SHOUT_OR_IMPACT" if rms > ANOMALY_RMS * 2
                    else "ELEVATED_NOISE"
                )
                anomalies.append({
                    "time":   timestamp,
                    "type":   anomaly_type,
                    "energy": round(rms, 4),
                })

        # Deduplicate anomalies within 1 second of each other
        if not anomalies:
            return []

        deduped = [anomalies[0]]
        for a in anomalies[1:]:
            if a["time"] - deduped[-1]["time"] > 1.0:
                deduped.append(a)

        return deduped

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _trim_segment(seg: Dict) -> Dict:
        """Clean up merged text — fix spacing and punctuation."""
        text = seg["text"]
        text = re.sub(r"\s+", " ", text).strip()
        if text and text[-1] not in ".!?":
            text += "."
        seg["text"] = text
        return seg