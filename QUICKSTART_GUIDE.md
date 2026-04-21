# VidChain v0.8.3 Developer Quickstart

This guide explains how to integrate the **VidChain Framework** as a library into your own security and forensics applications.

---

## 1. Core Architecture
VidChain v0.8.3-Stable is built on a **Modular Sensor Logic**. You construct a `VideoChain` (the "nervous system") and inject it into the `VidChain` orchestrator (the "brain").

---

## 2. Basic Ingestion Pipeline
The simplest way to transform a video file into a searchable forensic database.

```python
from vidchain import VidChain

# Initialize the brain
vc = VidChain(db_path="./my_forensic_vault")

# Ingest evidence
# Defaults to the Standard VLM-based chain
vc.ingest("C:/evidence/cam_01.mp4")

# Query the intelligence
response = vc.ask("Is there any suspicious movement around the perimeter?")
print(f"BABURAO: {response}")
```

---

## 3. High-Fidelity Custom Chain
For advanced control, assemble specific sensory nodes.

```python
from vidchain.nodes import AdaptiveKeyframeNode, LlavaNode, WhisperNode

# Create a chain optimized for interview forensics
interview_chain = VideoChain(nodes=[
    AdaptiveKeyframeNode(change_threshold=2.0), # Higher sensitivity
    LlavaNode(model_name="moondream"), 
    WhisperNode()
])

# Use the custom chain
vc.ingest("interview_01.mp4", chain=interview_chain)
```

---

## 4. Serving the Spider-Net Portal
To launch the forensic dashboard programmatically:

```python
from vidchain.serve import main_cli

# This starts the FastAPI edge server and auto-launches the browser
if __name__ == "__main__":
    main_cli()
```

---

## 5. Deployment Checklist
- **Python**: 3.11+
- **CUDA**: 12.1+ (Recommended for VLM/Whisper)
- **Ollama**: Must be running in the background for LLM/VLM logic.

---
**VidChain v0.8.3-Stable | Stark-Tech Forensic Intelligence**
