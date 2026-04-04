# VidChain: Video Intelligence RAG Framework
> Edge-optimized multimodal RAG framework for video understanding — transforms raw footage into a structured, queryable knowledge base.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![CUDA](https://img.shields.io/badge/CUDA-12.1-green) ![License](https://img.shields.io/badge/License-MIT-yellow) ![Status](https://img.shields.io/badge/Status-beta-orange) [![PyPI version](https://badge.fury.io/py/vidchain.svg)](https://pypi.org/project/VidChain/)

---

## Overview

vidchain v0.2.0 is a lightweight, modular framework that combines computer vision, smart OCR, speech recognition, and LLM reasoning into a unified **late-fusion pipeline**. Designed to run efficiently on consumer-grade GPUs (tested on NVIDIA RTX 3050), it extracts human-readable stories from raw sensor data, making on-device video intelligence practical without massive cloud dependency.

At the heart of the framework is **B.A.B.U.R.A.O.** (*Behavioral Analysis & Broadcasting Unit for Real-time Artificial Observation*), an elite AI copilot that uses abductive reasoning to translate raw, flickering object/action logs into flowing, conversational narratives.

---

## Core Pipeline
```text
Video Input → Adaptive Keyframes → Dual-Brain Vision (YOLO + MobileNet) + OCR → Audio Transcription → Semantic Chunking → FAISS Vector DB → B.A.B.U.R.A.O. RAG
````

-----

## Key Capabilities

### 🧠 Dual-Brain Vision Engine

Instead of basic classification, vidchain uses a two-pronged visual approach:

  * **The "Noun" Engine (YOLOv8):** Detects specific objects (e.g., "1 person, 2 laptops").
  * **The "Verb" Engine (MobileNetV3):** Classifies the intent or state of the scene (e.g., NORMAL, SUSPICIOUS, VIOLENCE).

### 🔤 Context-Aware OCR

Powered by EasyOCR, the system intelligently scans for text *only* when YOLO detects readable surfaces (monitors, laptops, books, whiteboards), saving massive compute power while capturing ground-truth data (e.g., reading the brand "ASUS Vivobook" off a laptop).

### B.A.B.U.R.A.O. RAG Engine (Conversational)

Unlike standard RAGs that read out robotic timelines, B.A.B.U.R.A.O. acts as a human copilot:

  * **Abductive Reasoning:** If it sees a "laptop" and a "keyboard", it deduces the scene is a "computer desk."
  * **Sensor Filtering:** Automatically ignores momentary hardware glitches/hallucinations (e.g., a TV briefly misidentified as an oven).
  * **Natural Translation:** Translates raw model labels like `VIOLENCE` into contextual human behaviors like "the person became visibly frustrated and hit the desk."

### Edge-First GPU Optimization

Engineered to prevent VRAM crashes. Smart memory routing disables PyTorch's buggy layer fusion during YOLO inference and safely manages VRAM across concurrent vision, audio, and language models.

-----

## Installation

```bash
# 1. Install the core package
pip install vidchain

# 2. IMPORTANT: Install GPU-accelerated PyTorch (CUDA 12.1 recommended)
pip install torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/cu121](https://download.pytorch.org/whl/cu121) --force-reinstall
```

> ⚠️ **Requirement:** NVIDIA drivers and CUDA are strongly recommended. To verify your hardware is correctly mapped, run the built-in diagnostic script: `python scripts/check_gpu.py`

-----

## Quick Start

### 1 — Analyze a Video (Build Knowledge Base)

Analyze a video file, extract multimodal context, and generate a structured JSON timeline:

```bash
vidchain-analyze sample.mp4
```

*This command automatically builds a FAISS index and drops you into the interactive B.A.B.U.R.A.O. chat terminal.*

### 2 — Train the Action Engine

Fine-tune the MobileNetV3 "Verb" classifier on your domain-specific dataset:

```bash
vidchain-train
```

Place labeled training images under `data/train/` before running.

-----

## Knowledge Base Schema

The framework utilizes **Semantic Chunking** to compress repetitive frames. The `knowledge_base.json` outputs a clean, fused timeline:

```json
{
    "time": 0.97,
    "type": "ocr",
    "content": "ASUS Vivabook"
},
{
    "time": 3.87,
    "type": "visual",
    "content": "Duration: [3.87s - 6.77s] | Subjects: 1 laptop, 1 tv | Action State: SUSPICIOUS"
},
{
    "time": 19.34,
    "type": "visual",
    "content": "Duration: [19.34s - 19.34s] | Subjects: 1 tv | Action State: VIOLENCE"
}
```

-----

## Tech Stack

| Component | Technology |
|---|---|
| Object Detection (Nouns) | YOLOv8s |
| Intent Classification (Verbs) | MobileNetV3 (Custom fine-tuned) |
| Text Extraction (OCR) | EasyOCR |
| ASR (Audio) | OpenAI Whisper (Base) |
| Vector Database | FAISS + Sentence-Transformers (`all-MiniLM-L6-v2`) |
| LLM Routing | LiteLLM (`gemini-2.5-flash` default, Ollama supported) |
| GPU Runtime | CUDA 12.1 (Optimized for 4GB+ VRAM) |

-----

## Roadmap

  - [ ] **Real-time streaming pipeline** — live ingestion and indexing with low-latency event detection.
  - [ ] **Advanced temporal reasoning** — multi-clip reasoning and cross-camera subject tracking.
  - [ ] **Interactive Dashboard** — PyQt5 HUD for video playback, timeline visualization, and KB exploration.

-----

## Contributing

Contributions, issues, and feature requests are highly welcome\! Open a GitHub issue or submit a pull request.

-----

## Author

**Rahul Sharma** — B.Tech CSE, IIIT Manipur

## License

Distributed under the [MIT License](https://www.google.com/search?q=LICENSE).
