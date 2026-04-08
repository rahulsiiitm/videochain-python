from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

@dataclass
class VideoEvent:
    """The fundamental unit of data in VidChain."""
    timestamp: float
    video_id: str
    action: str = "normal"
    objects: List[str] = field(default_factory=list)
    ocr_text: Optional[str] = None
    audio_transcript: Optional[str] = None
    emotion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self):
        return asdict(self)

@dataclass
class VideoAnalysisResult:
    """The full result returned after processing a video."""
    video_id: str
    source_path: str
    total_duration: float
    events: List[VideoEvent]
    summary: Optional[str] = None