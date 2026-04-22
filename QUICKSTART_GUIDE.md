# VidChain v0.9.0 Developer Quickstart
> Featuring the IRIS Intelligence Assistant.

This guide explains how to integrate the VidChain Framework as a library into your own security and forensics applications, powered by the IRIS (Intelligent Retrieval & Insight System) agent.

---

## 1. Core Architecture
VidChain v0.9.0-Final is built on a Modular Sensor Matrix. You construct a VideoChain (the "nervous system") and inject it into the VidChain orchestrator (the "brain"). IRIS acts as the intelligent interface that translates complex graph data into human-readable insights.

---

## 2. Basic Ingestion Pipeline
The simplest way to transform a video file into a searchable intelligence database.

```python
from vidchain import VidChain

# Initialize the IRIS Brain
vc = VidChain(db_path="./my_insight_vault")

# Ingest evidence
# IRIS defaults to the High-Fidelity VLM + GraphRAG chain
vc.ingest("C:/data/video_01.mp4")

# Query the IRIS Assistant
response = vc.query("What was the most significant event in this video?", session_id="my_session")
print(f"IRIS: {response['text']}")
```

---

## 3. High-Fidelity Custom Chain
For advanced control, assemble specific sensory nodes from the B.A.B.U.R.A.O. matrix.

```python
from vidchain.nodes import AdaptiveKeyframeNode, LlavaNode, WhisperNode

# Create a chain optimized for interview insights
interview_chain = VideoChain(nodes=[
    AdaptiveKeyframeNode(change_threshold=2.5), # Optimized for low-motion scenes
    LlavaNode(model="moondream"), 
    WhisperNode()
])

# Use the custom chain
vc.ingest("interview_01.mp4", chain=interview_chain)
```

---

## 4. Serving the IRIS Portal
To launch the full glassmorphic dashboard programmatically:

```python
from vidchain.serve import main_cli

# This starts the FastAPI edge server and performs a 7s Neural Warmup
if __name__ == "__main__":
    main_cli()
```

---

## 5. Neural Deployment Checklist
- **Python**: 3.11+
- **CUDA**: 12.1+ (Essential for VLM/Whisper acceleration)
- **Ollama**: Must be active for LLM/VLM nodes (moondream, llama3).
- **Memory Isolation**: v0.9.0 automatically handles per-video graph isolation.

---
**VidChain v0.9.0-Final | IRIS Intelligence Suite**
