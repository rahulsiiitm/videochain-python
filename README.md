# VidChain: Video Intelligence RAG Framework
> Edge-optimized multimodal RAG framework for video understanding — transforms raw footage into a structured, queryable knowledge base.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![CUDA](https://img.shields.io/badge/CUDA-12.1-green) ![License](https://img.shields.io/badge/License-MIT-yellow) ![Status](https://img.shields.io/badge/Status-beta-orange) [![PyPI version](https://badge.fury.io/py/vidchain.svg)](https://pypi.org/project/VidChain/)

---

## Overview

VidChain v0.3.0 is a lightweight, modular framework that combines computer vision, OCR, speech recognition, emotion analysis, and LLM reasoning into a unified **late-fusion pipeline**. Designed to run on consumer-grade GPUs (tested on NVIDIA RTX 3050 4GB), it makes on-device video intelligence practical without cloud dependency.

At the heart is **B.A.B.U.R.A.O.** (*Behavioral Analysis & Broadcasting Unit for Real-time Artificial Observation*) — a conversational AI copilot that translates raw sensor logs into human-readable narratives using abductive reasoning.

---

## Core Pipeline

```
Video → WAV Extraction → Whisper ASR → Frame Loop →
  ├── YOLO (Objects)
  ├── MobileNetV3 (Action)
  ├── EasyOCR (Screen Text)
  ├── DeepFace (Emotion, threaded)
  └── TemporalTracker (Object Persistence + Camera Motion)
→ Semantic Fusion → ChromaDB → B.A.B.U.R.A.O. RAG
```

---

## Key Capabilities

### Dual-Brain Vision Engine
- **YOLO (Nouns):** Detects objects with bounding boxes — `"1 person, 1 laptop"`
- **MobileNetV3 (Verbs):** Classifies scene intent — `NORMAL / SUSPICIOUS / VIOLENCE / EMERGENCY`

### Context-Aware OCR
EasyOCR runs only when YOLO detects readable surfaces (laptop, monitor, whiteboard) — saves compute while capturing ground-truth text.

### 😶 Threaded Emotion Analysis
DeepFace runs on CPU in a background thread so it never competes with YOLO/MobileNet for VRAM.

### Temporal Tracking
- **Object Persistence:** IoU tracker assigns persistent IDs across frames (`person #1 present 12s, moving left`)
- **Camera Motion:** Lucas-Kanade optical flow detects pan, tilt, zoom, static
- **Scene Cut Detection:** HSV histogram correlation resets trackers on hard cuts

### B.A.B.U.R.A.O. RAG Engine
- **BGE embedder** (`BAAI/bge-base-en-v1.5`) for domain-specific retrieval
- **Cross-encoder reranker** for precision before LLM call
- **Intent routing** — distinguishes video search from conversational follow-ups
- **Chat memory** — maintains context across multi-turn conversations

---

## Installation

```bash
pip install vidchain

# GPU-accelerated PyTorch (recommended)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --force-reinstall
```

> Run `python scripts/check_gpu.py` to verify CUDA is detected.

---

## Quick Start

### Python API (Library)

```python
from vidchain import VidChain

# Initialize
vc = VidChain(config={
    "llm_provider": "gemini/gemini-2.5-flash",  # or "ollama/llama3" for offline
    "db_path": "./vidchain_storage"              # omit for in-memory (no persistence)
})

# Ingest a video
video_id = vc.ingest("surveillance.mp4")

# Query
print(vc.ask("what happened in the video?"))
print(vc.ask("was anyone acting suspiciously?"))

# Multi-video: scope query to a specific video
vc.ingest("cam1.mp4", video_id="cam1")
vc.ingest("cam2.mp4", video_id="cam2")
print(vc.ask("did anyone enter the room?", video_id="cam1"))
```

### CLI

```bash
# Analyze and chat
vidchain-analyze video.mp4

# Single-shot query
vidchain-analyze video.mp4 --query "what happened at the desk?"

# Offline with Ollama
vidchain-analyze video.mp4 --llm ollama/llama3

# Multilingual OCR
vidchain-analyze video.mp4 --ocr-lang en fr
```

### Train Custom Action Engine

```bash
# Place labeled images in data/train/<class>/
vidchain-train
```

---

## Knowledge Base Schema

Each fused timeline entry contains all modalities at that moment:

```json
{
    "time": 5.8,
    "duration": 3.2,
    "objects": "1 person, 1 laptop",
    "action": "SUSPICIOUS",
    "emotion": "visibly agitated",
    "ocr": "ASUS Vivobook",
    "audio": "I told you this would happen",
    "camera": "static",
    "tracking": ["person #1 (present 4.8s), moving left", "laptop #2 (present 5.8s)"],
    "audio_anomaly": "NORMAL"
}
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Object Detection | YOLOv8s (Ultralytics) |
| Action Classification | MobileNetV3 (custom fine-tuned) |
| Speech Recognition | OpenAI Whisper (base) |
| OCR | EasyOCR |
| Emotion Analysis | DeepFace (opencv backend) |
| Temporal Tracking | IoU tracker + Lucas-Kanade optical flow |
| Embedder | `BAAI/bge-base-en-v1.5` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Vector Store | ChromaDB (persistent) |
| LLM Routing | LiteLLM (`gemini-2.5-flash` default, Ollama supported) |
| GPU Runtime | CUDA 12.1 (4GB+ VRAM, RTX 30-series tested) |

---

## Developer Utilities

```python
# List all indexed videos
vc.list_indexed_videos()

# Generate a narrative summary
vc.summarize_video(video_id, depth="concise")  # or "detailed"

# Hot-swap LLM
vc.set_llm("ollama/llama3")

# Purge a specific video
vc.purge_storage(video_id="cam1")

# Purge everything
vc.purge_storage()
```

---

## Roadmap

- [ ] **Real-time streaming** — live camera ingestion with low-latency indexing
- [ ] **Cross-video subject tracking** — link the same person across multiple camera feeds
- [ ] **CLIP scene understanding** — environment classification (`office`, `kitchen`, `street`)
- [ ] **Export to JSON/CSV** — structured timeline export for downstream analysis

---

## Contributing

Contributions, issues, and feature requests are welcome. Open a GitHub issue or submit a pull request.

---

## Author

**Rahul Sharma** — B.Tech CSE, IIIT Manipur

## License

Distributed under the [MIT License](LICENSE).