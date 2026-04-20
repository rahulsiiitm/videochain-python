"""
VidChain: Video Intelligence RAG Framework
------------------------------------------
Edge-optimized multimodal RAG framework for video understanding.
Transforms raw footage into a structured, queryable knowledge base.

Quick Start:
    from vidchain import VidChain

    vc = VidChain()
    vc.ingest("video.mp4")
    print(vc.ask("what happened?"))

Full docs: https://github.com/rahulsiiitm/videochain-python
"""

# Lazy import — heavy deps (torch, cv2, etc.) only load when actually used
def __getattr__(name):
    if name == "VidChain":
        from vidchain.client import VidChain
        return VidChain
    if name == "VideoChain":
        from vidchain.pipeline import VideoChain
        return VideoChain
    raise AttributeError(f"module 'vidchain' has no attribute '{name}'")


__version__ = "0.8.0"
__author__ = "Rahul Sharma"
__license__ = "MIT"
__all__ = ["VidChain", "VideoChain"]