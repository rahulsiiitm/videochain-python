"""
VidChain: Video Intelligence RAG Framework
------------------------------------------
Edge-optimized multimodal RAG framework for video understanding.
Transforms raw footage into a structured, queryable knowledge base.

Quick Start:
    from vidchain import VidChain

    vc = VidChain()
    vc.ingest("video.mp4")
    print(vc.ask("what happened in the video?"))
"""

from vidchain.client import VidChain
from vidchain.schema import VideoEvent, VideoAnalysisResult

__version__ = "0.3.0"
__author__ = "Rahul Sharma"
__license__ = "MIT"

__all__ = [
    "VidChain",
    "VideoEvent",
    "VideoAnalysisResult",
]