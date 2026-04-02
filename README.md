# VideoChain
> Edge-optimized multimodal RAG framework for video understanding — transforms raw footage into a structured, queryable knowledge base.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![CUDA](https://img.shields.io/badge/CUDA-12.1-green) ![License](https://img.shields.io/badge/License-MIT-yellow) ![Status](https://img.shields.io/badge/Status-alpha-orange) [![PyPI version](https://badge.fury.io/py/videochain.svg)](https://pypi.org/project/videochain/)


---

## Overview

VideoChain is a lightweight, modular framework that combines computer vision, speech recognition, and LLM reasoning into a unified **late-fusion pipeline**. Designed to run on consumer-grade GPUs (tested on NVIDIA RTX 3050), it carefully schedules VRAM across concurrent vision and language inference — making on-device video intelligence practical without cloud dependency.

---

## Core Pipeline
```
Video Input → Frame Extraction → Vision Inference → Audio Transcription → Fusion Engine → Knowledge Base → LLM Query
```

---

## Key Capabilities

### Adaptive Keyframe Extraction
Gaussian-blurred frame differencing filters transient noise and isolates semantically significant motion events, reducing redundant frame processing by discarding visually similar consecutive frames.

### Multimodal Data Alignment
Visual labels from MobileNetV3 and Whisper-generated transcripts are synchronized via timestamp, producing a unified timeline for downstream retrieval and reasoning.

### Domain-Agnostic Design
Modular loader and processor interfaces allow straightforward adaptation to security, retail analytics, education, and personal content search — without restructuring the core pipeline.

### Edge-First Optimization
Concurrent vision and LLM inference with careful VRAM scheduling. Validated on RTX 3050 (4 GB). No cloud inference dependency for core pipeline execution.

---

## Installation
```bash
pip install videochain

# Clone the repository
git clone https://github.com/rahulsiiitm/videochain
cd videochain

# Install in editable mode (recommended for development)
pip install -e .
```

> ⚠️ **Requirement:** NVIDIA drivers and CUDA 12.1 are required for GPU-accelerated inference. CPU-only execution is supported but significantly slower for vision workloads.

---

## Quick Start

### 1 — Build a knowledge base

Analyze a video file and generate a structured JSON knowledge base:
```bash
videochain-analyze --input sample.mp4
```

Output: `knowledge_base.json`

### 2 — Train a custom vision model

Fine-tune the vision classifier on a domain-specific dataset:
```bash
videochain-train --epochs 15 --batch-size 16
```

Place labeled training images under `data/train/` before running. Class subdirectory names become label strings in the knowledge base.

### 3 — Query the knowledge base

Use Ollama (local) or Gemini API (cloud) to issue natural language queries over the generated knowledge base.

---

## System Architecture

VideoChain follows a **late-fusion architecture** — each modality is processed independently before being merged at the knowledge-base level. This decouples model upgrade paths and allows per-modality optimization.

| Layer | Component | Responsibility |
|---|---|---|
| 1 | **Loaders** | Frame extraction (OpenCV), audio separation (MoviePy), format normalization |
| 2 | **Processors** | Vision: MobileNetV3 classification · Audio: Whisper transcription with word-level timestamps |
| 3 | **Fusion Engine** | Timestamp synchronization, confidence-weighted merging of modalities |
| 4 | **LLM Reasoning** | Natural language querying via Ollama (Llama 3, local) or Gemini API (remote) |
| 5 | **Knowledge Base** | Structured JSON output — indexed by timestamp, designed for vector DB integration |

---

## Knowledge Base Schema

Each event entry in `knowledge_base.json` follows this structure:
```json
{
  "timestamp": "00:01:23",
  "visual": ["person", "running"],
  "audio": "Someone is running across the hallway",
  "confidence": 0.91,
  "frame_index": 2490
}
```

---

## Project Structure
```
videochain/
├── core/            # Fusion engine, LLM query interface, KB I/O
├── loaders/         # Video frame extraction, audio separation
├── processors/      # MobileNetV3 vision, Whisper audio inference
├── scripts/         # Training utilities, dataset prep helpers
├── data/
│   └── train/       # Class-labeled training images (one dir per class)
└── pyproject.toml   # Dependencies, CLI entry points, metadata
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Vision model | MobileNetV3 |
| ASR | OpenAI Whisper |
| Video I/O | OpenCV + MoviePy |
| ML framework | PyTorch |
| LLM (local) | Ollama / Llama 3 |
| LLM (cloud) | Gemini API |
| Language | Python 3.10+ |
| GPU runtime | CUDA 12.1 |
| Packaging | pyproject.toml |

---

## Use Cases

| # | Use Case | Description |
|---|---|---|
| 01 | **CCTV Surveillance** | Query footage for specific events, persons, or time windows in natural language |
| 02 | **Retail Analytics** | Track customer behavior patterns and dwell-time events across store zones |
| 03 | **Lecture Indexing** | Search educational video by spoken content or visual slide transitions |
| 04 | **Personal Media Search** | Find moments in home video archives using natural language descriptions |

---

## Roadmap

- [ ] **Real-time streaming pipeline** — live ingestion and indexing with low-latency event detection
- [ ] **Vector database integration** — FAISS or Chroma backends for semantic similarity search
- [ ] **Advanced temporal reasoning** — event co-occurrence detection, causal chain inference, multi-clip reasoning
- [ ] **Query dashboard** — browser-based UI for video playback, timeline visualization, and KB exploration

---

## Contributing

Contributions, issues, and feature requests are welcome. Open a GitHub issue or submit a pull request.

---

## Author

**Rahul Sharma** — B.Tech CSE, IIIT Manipur

## License

Distributed under the [MIT License](LICENSE).