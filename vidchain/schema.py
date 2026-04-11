"""
vidchain/schema.py
------------------
Canonical data models for VidChain.
These are the typed contracts between pipeline stages.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class VideoEvent:
    """
    The fundamental unit of data in VidChain.
    Represents a single fused scene block from the pipeline.
    """
    time: float                              # Timestamp in seconds
    video_id: str                            # Parent video identifier
    duration: float = 0.0                    # Scene block duration in seconds
    action: str = "NORMAL"                   # MobileNet action classification
    objects: str = "no significant objects"  # YOLO object summary string
    emotion: Optional[str] = None            # DeepFace emotion (human-readable)
    ocr: Optional[str] = None               # EasyOCR screen text
    audio: Optional[str] = None             # Whisper transcript (validated)
    camera: str = "static"                  # Camera motion label
    tracking: List[str] = field(default_factory=list)  # Tracked subject descriptions
    audio_anomaly: str = "NORMAL"           # HIGH_VOLUME or NORMAL

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any], video_id: str = "") -> "VideoEvent":
        """Construct a VideoEvent from a raw pipeline dict."""
        return cls(
            time=d.get("time", 0.0),
            video_id=video_id,
            duration=d.get("duration", 0.0),
            action=d.get("action", "NORMAL"),
            objects=d.get("objects", "no significant objects"),
            emotion=d.get("emotion"),
            ocr=d.get("ocr"),
            audio=d.get("audio"),
            camera=d.get("camera", "static"),
            tracking=d.get("tracking", []),
            audio_anomaly=d.get("audio_anomaly", "NORMAL"),
        )

    def serialize(self) -> str:
        """Human-readable string for embedding and LLM context."""
        parts = [f"[{self.time}s]"]
        if self.duration > 0:
            parts.append(f"Duration: {self.duration}s")
        if self.objects and self.objects != "no significant objects":
            parts.append(f"Visuals: {self.objects}")
        if self.action and self.action != "NORMAL":
            parts.append(f"Action: {self.action}")
        if self.emotion:
            parts.append(f"Emotion: {self.emotion}")
        if self.ocr:
            parts.append(f"Screen text: {self.ocr}")
        if self.audio:
            parts.append(f"Speech: \"{self.audio}\"")
        if self.camera and self.camera != "static":
            parts.append(f"Camera: {self.camera}")
        if self.tracking:
            parts.append(f"Tracking: {', '.join(self.tracking)}")
        return " | ".join(parts)


@dataclass
class VideoAnalysisResult:
    """Full result returned after processing a video."""
    video_id: str
    source_path: str
    total_events: int
    events: List[VideoEvent]
    summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "source_path": self.source_path,
            "total_events": self.total_events,
            "summary": self.summary,
            "events": [e.to_dict() for e in self.events],
        }