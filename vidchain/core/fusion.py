"""
vidchain/core/fusion.py
-----------------------
DEPRECATED in v0.2.0.

Fusion is now handled internally by VideoProcessor._fuse_multimodal_layers()
and VideoProcessor._compress_and_smooth_timeline() in vidchain/processor.py.

This file is kept for backward compatibility with any external code
that imports FusionEngine directly.
"""

import warnings

class FusionEngine:
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "FusionEngine is deprecated in VidChain v0.2.0. "
            "Fusion is now handled automatically inside VideoProcessor. "
            "Use VidChain.ingest() instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def generate_knowledge_base(self, *args, **kwargs):
        raise NotImplementedError(
            "FusionEngine.generate_knowledge_base() is removed. "
            "Use VidChain.ingest(video_path) — fusion happens automatically."
        )