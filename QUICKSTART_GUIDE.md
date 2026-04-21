# VidChain v0.8.2 Developer Quickstart

This guide explains how to integrate the **VidChain Framework** as a library into your own security and forensics applications.

---

## 1. Core Architecture
VidChain v0.8.2-Stable is built on a **Modular Sensor Logic**. You construct a `VideoChain` (the "nervous system") and inject it into the `VidChain` orchestrator (the "brain").

---

## 2. Setting Up
```powershell
# Clone and install in editable mode
git clone https://github.com/rahulsiiitm/videochain-python
cd videochain-python
pip install -e .
```

---

## 3. High-Fidelity Python API Example

This is the recommended way to use VidChain for professional forensic analysis:

```python
from vidchain import VidChain
from vidchain.pipeline import VideoChain
from vidchain.nodes import AdaptiveKeyframeNode, LlavaNode, WhisperNode, OcrNode

# 1. Compose the Sensory Chain
# We use AdaptiveKeyframe to skip the boring stuff and Moondream for the smart stuff.
chain = VideoChain(
    nodes=[
        AdaptiveKeyframeNode(change_threshold=5.0), # Save GPU cycles
        LlavaNode(model_name="moondream"),          # Dense Scene Analysis
        WhisperNode(model_size="base"),            # Audio Forensics
        OcrNode()                                  # Text Trace
    ],
    frame_skip=15  # Process 2 frames per second
)

# 2. Initialize the B.A.B.U.R.A.O. Engine
vc = VidChain(verbose=True)

# 3. Analyze & Index
video_id = vc.ingest("incidents/break_in.mp4", chain=chain)

# 4. Generate Intelligence
summary = vc.summarize_video(video_id)
print(f"REPORT: {summary}")

# 5. Iterative Discovery
answer = vc.ask("What color was the getaway car's plates?", video_id=video_id)
print(f"AI: {answer}")
```

---

## 4. CLI Mastery (The "Stark-Tech" way)

For rapid triage, use the global CLI module:

| Task | Command |
| :--- | :--- |
| **Comprehensive Scan** | `python -m vidchain.cli surveillance.mp4` |
| **Silent High-Speed Scan** | `python -m vidchain.cli surveillance.mp4 --fast` |
| **Behavioral Incident Scan** | `python -m vidchain.cli surveillance.mp4 --emotion --action` |
| **Batch API Deployment** | `vidchain-serve` |

---

## 5. Live Surviellance (Watchdog Mode)
To build a live HUD, use the `watchdog` to monitor a CCTV folder and trigger `vc.ingest` automatically as files are closed by the recorder.

---
**VidChain v0.8.2-Stable | Stark-Tech Forensic Intelligence**
