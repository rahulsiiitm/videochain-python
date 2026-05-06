# VidChain

> **High-Fidelity Multimodal RAG Framework for Forensic Video Intelligence**

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![CUDA](https://img.shields.io/badge/CUDA-12.1-green) ![License](https://img.shields.io/badge/License-MIT-yellow) ![Status](https://img.shields.io/badge/Status-v1.0.0--Stable-green) [![PyPI version](https://badge.fury.io/py/vidchain.svg)](https://pypi.org/project/VidChain/) [![Downloads](https://static.pepy.tech/badge/vidchain)](https://pepy.tech/project/vidchain)

VidChain is a local-first multimodal RAG framework powered by the **IRIS Engine** (Intelligent Retrieval & Insight System). It parses video through a modular sensory matrix — fusing visual, auditory, OCR, and temporal signals into a queryable intelligence layer — designed for forensic analysis, security auditing, and automated video summarization with strict on-device privacy.

![VidChain v1.0 Dashboard](assets/image.png)

---

## Features

- **4-Route Agentic Router** — Classifies queries into Narrative Summarization, Local Forensic Search, Global Master Intelligence, and Conversational Dialogue.
- **Global Master Intelligence** — Cross-video entity tracking via a macro-graph, enabling pattern recognition across isolated sessions.
- **Temporal Persistence** — Chronological reasoning that bridges frame gaps and maintains state continuity between sensor logs.
- **Recursive Map-Reduce Summarizer** — Collapses hours of video into coherent reports without hitting LLM context limits.
- **Neural Concurrency Locking** — Prevents state corruption during simultaneous ingestion and query operations.
- **100% Local Execution** — All inference runs on host hardware; no data leaves the machine.

---

## Installation

### Prerequisites

| Requirement | Version |
| :--- | :--- |
| Python | 3.11+ |
| CUDA | 12.1+ |
| [Ollama](https://ollama.com) | Latest (running) |
| Node.js | v18+ (for web portal) |

### Steps

**1. Install PyTorch with CUDA support**

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**2. Clone and install VidChain**

```bash
git clone https://github.com/rahulsiiitm/videochain-python
cd videochain-python
pip install -e .
```

**3. Pull model weights**

```bash
ollama pull moondream   # Vision Language Model
ollama pull llama3      # Language Model for reasoning & routing
```

> **CPU Fallback**: If no CUDA device is detected, VidChain automatically degrades to CPU mode — no code changes required.

---

## Quick Start

```python
from vidchain import VidChain

vc = VidChain(db_path="./forensic_vault")

# Ingest video (runs full default pipeline)
video_id = vc.ingest(video_source="interview_01.mp4")

# Query
response = vc.ask("What is the main topic of discussion?", video_id=video_id)
print(response["text"])

# Summarize
summary = vc.summarize_video(video_id=video_id, mode="concise")
print(summary)
```

---

## CLI Reference

### `vidchain-serve`

Launches the FastAPI backend and Next.js dashboard.

```bash
vidchain-serve
```

- API available at `http://localhost:8000`
- Dashboard opens at `http://localhost:3000`
- Includes a 7-second neural warmup before accepting requests

### `vidchain-analyze`

Headless video ingestion from the terminal.

```bash
vidchain-analyze path/to/video.mp4 --vlm moondream
```

| Flag | Description |
| :--- | :--- |
| `--vlm <model>` | Vision model to use (default: `moondream`) |
| `--llm <model>` | Reasoning model to use (default: `gemini/gemini-2.5-flash`) |
| `--fast` | Replaces VLM with YOLO for high-speed detection (ideal for long CCTV footage) |
| `--emotion` | Injects DeepFace emotion analysis node |
| `--action` | Injects MobileNetV3 action classification node |

**Swapping models** — VidChain uses LiteLLM, so any compatible model can be hot-swapped:

```bash
# Local
vidchain-analyze video.mp4 --llm "ollama/llama3"

# Cloud (requires API key export)
export GEMINI_API_KEY="your_api_key"
vidchain-analyze video.mp4 --llm "gemini/gemini-2.5-flash"

# Custom VLM
vidchain-analyze video.mp4 --vlm "llava:7b"
```

---

## SDK: Modular Sensor Matrix

VidChain uses a LangChain-inspired composable pipeline. Each `Node` handles one sensing modality; chains are assembled per use case.

### Available Nodes

| Node | Modality | Description |
| :--- | :--- | :--- |
| `AdaptiveKeyframeNode` | Logic | Gaussian-differential sampling — drops redundant frames to reduce compute load |
| `LlavaNode` | Visual | Scene semantics, descriptive captions, and situational context |
| `YoloNode` | Visual | High-speed discrete object detection (lightweight fallback for `LlavaNode`) |
| `WhisperNode` | Audio | Speech transcription and acoustic anomaly detection (e.g., shouts) |
| `OcrNode` | Text | Digital trace extraction — license plates, screens, documents |
| `TrackerNode` | Motion | Persistent object tracking (IoU) and camera motion estimation (Optical Flow) |
| `EmotionNode` | Behavioral | Facial sentiment analysis |
| `ActionNode` | Behavioral | Human activity classification via MobileNetV3 |

### Custom Pipeline Example

```python
from vidchain import VidChain
from vidchain.pipeline import VideoChain
from vidchain.nodes import AdaptiveKeyframeNode, LlavaNode, OcrNode, TrackerNode

vc = VidChain(db_path="./forensic_vault")

surveillance_chain = VideoChain(nodes=[
    AdaptiveKeyframeNode(change_threshold=1.5),  # High sensitivity
    LlavaNode(model="moondream"),
    OcrNode(),
    TrackerNode()
])

video_id = vc.ingest(
    video_source="gate_camera_04.mp4",
    chain=surveillance_chain
)

response = vc.ask(
    "Were there any vehicles with visible license plates after 14:00?",
    video_id=video_id
)
print(response)
```

---

## REST API

Exposed when running `vidchain-serve`.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | System status and list of ingested video IDs |
| `POST` | `/api/sessions` | Create a new isolated neural session |
| `POST` | `/api/ingest` | Submit a video file path for background processing |
| `POST` | `/api/query` | Run a natural language query through the Agentic Router |
| `GET` | `/api/media-stream` | Serve local video securely for frontend playback |

---

## Architecture

### Isolated GraphRAG

Each ingested video generates a dedicated Temporal Knowledge Graph (`.pkl`). The RAG engine retrieves semantically relevant chunks from ChromaDB and fuses them with structured graph data (co-occurrences, tracking IDs, timestamps). Memory boundaries are strictly enforced — no cross-video context bleed.

### The Neural Lens

Every query response is paired with a Base64-encoded visual snapshot extracted directly from the referenced timestamp, providing visual proof for AI-generated claims.

---

## License

MIT — See [LICENSE](LICENSE) for details.

**Author:** Rahul Sharma — IIIT Manipur