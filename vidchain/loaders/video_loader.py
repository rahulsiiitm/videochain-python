"""
vidchain/loaders/video_loader.py
---------------------------------
DEPRECATED in VidChain v0.2.0.

Adaptive keyframe extraction is now handled directly inside
VideoProcessor.extract_context() in vidchain/processor.py using
the same Gaussian blur + frame differencing algorithm — but without
writing temporary .jpg files to disk.

This stub is kept for backward compatibility only.
"""

import warnings


class VideoLoader:
    """Deprecated. Use VidChain.ingest() instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "VideoLoader is deprecated in VidChain v0.2.0. "
            "Adaptive keyframe extraction now runs automatically inside VideoProcessor. "
            "Use VidChain.ingest('video.mp4') instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def extract_keyframes(self, *args, **kwargs):
        raise NotImplementedError(
            "VideoLoader.extract_keyframes() is removed. "
            "Use VidChain.ingest('video.mp4') — keyframe extraction is automatic."
        )

    def cleanup(self, *args, **kwargs):
        pass  # No-op for backward compatibility