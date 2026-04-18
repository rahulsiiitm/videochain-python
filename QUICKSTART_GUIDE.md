# 🕷️ VidChain Developer Quickstart Guide

This guide explains how to use the **VidChain Framework** as an embedded library in your own projects (like the Stark-Net Live Portal).

---

## 1. The "Library" Architecture
VidChain is a **Titan-Class Multimodal RAG Framework**. It is designed to be imported by other Python applications.
- **The Library (`vidchain/`)**: Contains the engine (VLM, OCR, GraphRAG).
- **The Application**: Your custom portal or script that uses the engine to solve real-world problems.

---

## 2. Setting Up a New "Embedded" Project
To use VidChain in a new folder elsewhere on your PC:
1.  **Initialize your new project folder**.
2.  **Install the framework** in editable mode:
    ```powershell
    pip install -e /path/to/videochain-python
    ```
3.  **Start Coding!**

---

## 3. Core Developer API (Python)
The entire framework is condensed into a single, powerful class.

### Initialization
```python
from vidchain import VidChain

# Uses local Llama3 for unlimited, private reasoning
vc = VidChain(verbose=True) 
```

### Video Ingestion (Knowledge Building)
```python
# Ingests a video and builds the forensic knowledge base & GraphRAG
vc.ingest("path/to/video.mp4", video_id="CAM_01")
```

### Forensic Inquiry (Retrieval)
```python
# Ask complex, multi-hop questions about the footage
response = vc.ask("Was there any suspicious activity involving a laptop at 00:15?")
print(response)
```

---

## 4. Key Features to Highlight for Presentation:
- **GraphRAG Precision**: We don't just search text; we track entities over time using a Knowledge Graph (`NetworkX`).
- **Local-First (Stark-Logic)**: Runs on your GPU/CPU (Ollama) with 0% cloud cost.
- **Multimodal Fusion**: Combines Audio (Whisper), Vision (Moondream), OCR, and Action classification into a single "Semantic Story."

---

## 5. Live Surveillance Recipe
For your live portal, use the **`hub.py`** logic:
1.  **Monitor** a directory via `watchdog`.
2.  **Ingest** new files as they arrive.
3.  **Audit** the feed automatically using specific prompts like *"Generate a 2-sentence security threat assessment."*
4.  **Display** results on your high-fidelity Stark-HUD Dashboard.

---
**Powered by VidChain v0.6.0 | Stark-Tech Intelligence**
