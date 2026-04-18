# VidChain: The "LangChain for Videos"
> Edge-optimized, local-first multimodal RAG framework for video intelligence — compose modular nodes into custom pipelines, deploy as a microservice, or query with a conversational AI.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![CUDA](https://img.shields.io/badge/CUDA-12.1-green) ![License](https://img.shields.io/badge/License-MIT-yellow) ![Status](https://img.shields.io/badge/Status-beta-orange) [![PyPI version](https://badge.fury.io/py/vidchain.svg)](https://pypi.org/project/VidChain/)

---

## Overview

VidChain v0.6.0 is a modular, composable framework for on-device multimodal video understanding. Inspired by LangChain's node-based design, it lets developers snap together processing components — Vision Language Models, Audio, OCR — into custom pipelines running entirely on your local GPU.

**VLM-First by design** — Moondream runs by default, delivering rich contextual descriptions (*"a red Honda Civic with a dented bumper"*) instead of blind YOLO tags (*"car"*). Use `--fast` for legacy YOLO when speed matters on long videos.

At the heart is **B.A.B.U.R.A.O.** (*Behavioral Analysis & Broadcasting Unit for Real-time Artificial Observation*) — a conversational AI copilot that combines ChromaDB vector search with a **Temporal Knowledge Graph** (GraphRAG) to answer multi-hop temporal questions about video content.

---

## What's New in v0.5.0 🚀

### Composable Node Architecture
VidChain now works like LangChain — build your own pipelines by snapping together modular nodes:

```python
from vidchain import VidChain
from vidchain.pipeline import VideoChain
from vidchain.nodes import YoloNode, WhisperNode, OcrNode, AdaptiveKeyframeNode
from vidchain.nodes import LlavaNode  # New: Vision Language Model node

# Build a fully custom pipeline
my_chain = VideoChain(nodes=[
    AdaptiveKeyframeNode(change_threshold=5.0),  # Skip identical frames
    LlavaNode(model_name="moondream"),           # Deep scene captioning
    WhisperNode(),                               # Speech transcription
    OcrNode(),                                   # Screen text extraction
])

vc = VidChain()
video_id = vc.ingest("surveillance.mp4", chain=my_chain)
print(vc.ask("Was anyone at the desk?"))
```

### VLM Vision Node (`LlavaNode`)
Replace blind YOLO object tags with rich, contextual scene descriptions powered by a local Vision Language Model:

- **Before (YOLO):** `"1 person, 1 laptop"`
- **After (LlavaNode):** `"A person is typing Python code in VS Code. A terminal window is open showing a running script. The screen displays file explorer with project files visible."`

Supports any Ollama-compatible VLM model (recommended: `moondream` for speed, `llava:7b` for detail).

### Adaptive Keyframe Firewall
The `AdaptiveKeyframeNode` acts as a compute firewall. It computes a Gaussian-blurred frame delta to detect visual change — identical frames are instantly rejected before reaching heavy models like YOLO or LLaVA, dramatically reducing GPU load.

### FastAPI Edge Server (`vidchain-serve`)
Deploy VidChain as a local microservice accessible from any app or language:

```bash
# Terminal 1: Start the Edge Server
vidchain-serve

# Terminal 2: Ingest + Query via REST API
Invoke-RestMethod -Uri "http://localhost:8000/api/ingest" -Method Post -ContentType "application/json" -Body '{"video_source": "sample.mp4"}'
Invoke-RestMethod -Uri "http://localhost:8000/api/query" -Method Post -ContentType "application/json" -Body '{"query": "Summarize the video"}'
```

Interactive Swagger UI available at **http://localhost:8000/docs**

---

## Installation

```bash
pip install vidchain

# GPU-accelerated PyTorch (recommended)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --force-reinstall

# For LlavaNode (VLM support)
# Install Ollama: https://ollama.com
ollama pull moondream   # Fast edge VLM (~1.7GB, fits 4GB VRAM)
ollama pull llava       # High quality VLM (~4.7GB, requires 8GB+ VRAM)
```

> Run `python scripts/check_gpu.py` to verify CUDA is detected.

---

## Quick Start

### Python API (Library)

```python
from vidchain import VidChain

# Initialize
vc = VidChain(config={
    "llm_provider": "ollama/llama3",   # Fully offline
    "db_path": "./vidchain_storage"
})

# Ingest a video (uses legacy YOLO pipeline by default)
video_id = vc.ingest("surveillance.mp4")

# Query
print(vc.ask("what happened in the video?"))
print(vc.ask("was anyone acting suspiciously?"))

# Multi-video: scope query to a specific video
vc.ingest("cam1.mp4", video_id="cam1")
vc.ingest("cam2.mp4", video_id="cam2")
print(vc.ask("did anyone enter the room?", video_id="cam1"))
```

### Composable Node Pipeline

```python
from vidchain import VidChain
from vidchain.pipeline import VideoChain
from vidchain.nodes import AdaptiveKeyframeNode, LlavaNode, WhisperNode

# Build a VLM-powered pipeline with adaptive keyframing
chain = VideoChain(
    nodes=[
        AdaptiveKeyframeNode(change_threshold=5.0),
        LlavaNode(model_name="moondream"),
        WhisperNode(),
    ],
    frame_skip=15  # 2 FPS extraction
)

vc = VidChain()
vc.ingest("video.mp4", chain=chain)
print(vc.ask("describe what is on the screen"))
```

### CLI

```bash
# Default: Moondream VLM pipeline (rich descriptions)
vidchain-analyze video.mp4

# Single-shot query with VLM
vidchain-analyze video.mp4 --query "describe the car in detail"

# Switch VLM model (e.g. LLaVA for higher quality)
vidchain-analyze video.mp4 --vlm llava --query "what brand is the laptop?"

# Fast mode: Legacy YOLO pipeline (for long videos where speed > detail)
vidchain-analyze video.mp4 --fast

# Start Edge API Server
vidchain-serve

# Launch Desktop UI
vidchain-studio

# Train Custom Action Engine
vidchain-train
```

---

## Available Nodes

| Node | Description |
|---|---|
| `YoloNode` | YOLOv8 object detection — outputs class labels and counts |
| `WhisperNode` | Whisper speech-to-text transcription |
| `OcrNode` | EasyOCR screen text extraction (triggered on readable surfaces) |
| `ActionNode` | MobileNetV3 action intent classification (NORMAL/SUSPICIOUS/VIOLENCE) |
| `LlavaNode` | Ollama VLM node — deep contextual scene captioning (NEW in v0.5.0) |
| `AdaptiveKeyframeNode` | Frame-delta firewall — skips visually identical frames (NEW in v0.5.0) |

---

## Core Pipeline (Legacy)

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

## Tech Stack

| Component | Technology |
|---|---|
| Object Detection | YOLOv8s (Ultralytics) |
| VLM Vision | LLaVA / Moondream (via Ollama) — NEW |
| Action Classification | MobileNetV3 (custom fine-tuned) |
| Speech Recognition | OpenAI Whisper (base) |
| OCR | EasyOCR |
| Emotion Analysis | DeepFace (opencv backend) |
| Temporal Tracking | IoU tracker + Lucas-Kanade optical flow |
| Embedder | `BAAI/bge-base-en-v1.5` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Vector Store | ChromaDB (persistent) |
| LLM Routing | LiteLLM (`ollama/llama3` default, Gemini supported) |
| Edge API | FastAPI + Uvicorn — NEW |
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

- [x] **Dual-Brain Vision Engine** — YOLO + MobileNetV3 (v0.2.0)
- [x] **CLIP scene understanding** — zero-shot environment classification (v0.3.0)
- [x] **Adaptive audio filtering** — energy gating, anomaly detection (v0.3.0)
- [x] **Multi-video scoped queries** (v0.3.0)
- [x] **Composable Node Architecture** — LangChain-style pipelines (v0.5.0)
- [x] **VLM Node** — LLaVA/Moondream contextual captioning (v0.5.0)
- [x] **Adaptive Keyframe Firewall** — GPU compute optimization (v0.5.0)
- [x] **FastAPI Edge Microservice** — `vidchain-serve` (v0.5.0)
- [x] **VLM-First default pipeline** — Moondream as default, YOLO via `--fast` (v0.6.0)
- [x] **GraphRAG + Temporal Knowledge Graph** — entity tracking with NetworkX (v0.6.0)
- [x] **VidChain Studio** — native `CustomTkinter` desktop application (v0.6.0)
- [ ] **Real-time streaming** — live camera ingestion

---

## Contributing

Contributions, issues, and feature requests are welcome. Open a GitHub issue or submit a pull request.

---

## Author

**Rahul Sharma** — B.Tech CSE, IIIT Manipur

## License

Distributed under the [MIT License](LICENSE).