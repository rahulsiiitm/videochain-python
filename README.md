# VidChain: The "LangChain for Videos"
> **v0.8.3-Stable** — Edge-optimized, local-first multimodal RAG framework for forensic video intelligence. Compose modular sensory nodes into custom pipelines, deploy as a microservice, or query via the **Spider-Net Intelligence Portal**.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![CUDA](https://img.shields.io/badge/CUDA-12.1-green) ![License](https://img.shields.io/badge/License-MIT-yellow) ![Status](https://img.shields.io/badge/Status-v0.8.3--Stable-green) [![PyPI version](https://badge.fury.io/py/vidchain.svg)](https://pypi.org/project/VidChain/)

![Spider-Net Intelligence Portal](assets/forensic_portal.webp)

---

## Advanced Forensic Architecture

VidChain v0.8.3-Stable is powered by the **B.A.B.U.R.A.O. Engine** (Behavioral Analysis & Broadcasting Unit for Real-time Artificial Observation). It utilizes a modular "Nodes & Chains" framework to transform raw pixels into serialized forensic intelligence.

```mermaid
graph TD
    %% --- Ingestion Stage ---
    subgraph "1. Ingestion & Optimization Layer"
        VS[Video Source] --> AK[Adaptive Gaussian Filter]
        AK -- "Delta > Threshold" --> PK[Promote to Keyframe]
        AK -- "Redundant" --> DROP{{GPU Compute Firewall}}
    end

    %% --- Inference Stage ---
    subgraph "2. Sensory Node Matrix (Late Fusion)"
        PK --> VLM[LlavaNode: Scene Semantics]
        PK --> ASR[WhisperNode: Audio Trace]
        PK --> OCR[OcrNode: Digital Trace]
        PK --> TRK[TrackerNode: Motion Flow]
        
        %% Optional Sensors
        PK -.-> ACT[ActionNode: Situational Verbs]
        PK -.-> EMT[EmotionNode: Sentiment]
    end

    %% --- Intelligence Logic ---
    subgraph "3. B.A.B.U.R.A.O. Cognitive Engine"
        VLM & ASR & OCR & TRK & ACT & EMT --> FUSE[Semantic Fusion Pipeline]
        FUSE --> RDN[Recursive Map-Reduce Summarizer]
    end

    %% --- Persistence ---
    subgraph "4. Forensic Memory Vault"
        FUSE --> KV[(ChromaDB Vector Store)]
        FUSE --> KG[[Temporal Knowledge Graph]]
    end

    %% --- Interaction Stage ---
    subgraph "5. Spider-Net Intelligence Portal"
        USER[User Query] --> IR{Intent Router}
        IR -- "Forensic Search" --> RAG[RAG Retrieval Loop]
        IR -- "Executive Overview" --> RDN
        RAG <--> KV
        RAG <--> KG
        RDN --> REPORT([Intelligence Report])
        RAG --> DISCOVERY([Discovery Hub])
    end

    %% --- Hardware Loop ---
    HM[NVML Hardware Monitor] -.-> AK
    HM -.-> VLM
    HM -.-> DISCOVERY

    style VS fill:#1e1e2e,stroke:#74c7ec,stroke-width:2px;
    style DISCOVERY fill:#11111b,stroke:#a6e3a1,stroke-width:3px;
    style REPORT fill:#11111b,stroke:#a6e3a1,stroke-width:3px;
    style DROP fill:#313244,stroke-dasharray: 5 5;
    style AK fill:#1e1e2e,stroke:#fab387;
```

---

## Key Features (v0.8.3 Evolution)

### Relative Forensic Uplink [NEW]
The Spider-Net Portal now uses relative API paths. This ensures the suite works out-of-the-box whether accessed via `localhost`, industrial IPs, or local VPNs, resolving all "broken fetch" errors in production.

### Composable Sensory Chains
Snap together modular nodes to build custom forensic pipelines. Optimized for **Hardware Awareness**, the system scales its inference depth based on live GPU/VRAM telemetry.
- **Adaptive Keyframe Firewall**: Gaussian-blur differential filtering blocks identical frames, saving 70% of GPU compute in static scenes.
- **VLM-First Captions**: Replaces blind tags with dense semantic descriptions (*"Subject is hiding a silver object in their left pocket"*).

### Spider-Net Intelligence Portal
A professional-grade forensic command center served natively via `vidchain-serve`.
- **Evidence Vault**: surgical frame-by-frame seeking with 33ms precision.
- **Neural HUD**: Real-time visualization of sensor activity and hardware stress.
- **Semantic Heatmap**: Intelligence density mapping across the video timeline.

### Automated Intelligence Reporting
The built-in **Recursive Map-Reduce** engine automatically iterates over forensic logs to generate high-fidelity executive summaries, complete with verified timestamps and entity relationship discovery.

---

## Installation

```bash
# Core installation
pip install VidChain

# Setup local AI backends (Ollama)
ollama pull moondream   # Optimized Edge VLM (1.7GB)
ollama pull llama3      # Local Reasoning Hub (4.7GB)

# Verify Hardware Readiness (Bundled utility)
python -m vidchain.scripts.check_gpu
```

---

## Developer API Recipes (Python)

VidChain is designed to be deeply extensible. Here are the core "Intelligence Recipes" for v0.8.3-Stable.

### 1. High-Fidelity Forensic Scan (Default)
Best for evidence reconstruction where detail matters more than speed.
```python
from vidchain import VidChain, VideoChain
from vidchain.nodes import AdaptiveKeyframeNode, LlavaNode, WhisperNode, OcrNode

# Build the chain
chain = VideoChain(nodes=[
    AdaptiveKeyframeNode(change_threshold=5.0),
    LlavaNode(model_name="moondream"), 
    WhisperNode(),
    OcrNode()
])

vc = VidChain()
vid = vc.ingest("evidence.mp4", chain=chain)
print(vc.summarize_video(vid))
```

### 2. "CCTV Ultra-Fast" Scan (Low Latency)
Prioritize object detection speed over descriptive captioning.
```python
from vidchain.nodes import YoloNode, TrackerNode

# Swap the VLM for a fast YOLOv8 tracker
fast_chain = VideoChain(nodes=[
    YoloNode(confidence=0.5), # Ultra-fast detection
    TrackerNode()             # Subject persistence
], frame_skip=30)             # 1 FPS skip for massive speedup

vc.ingest("cctv_feed.mp4", chain=fast_chain)
```

---

## Research Position & Uniqueness
VidChain treats video as **Serialized Sensor Logs**, performing retrieval over structured multimodal narratives rather than raw pixel tokens. This significantly reduces hallucinations and enables multi-video GraphRAG reasoning. 
> See **[RESEARCH_COMPARISON.md](./RESEARCH_COMPARISON.md)** for detailed SOTA benchmarks.

---

## 📜 Changelog (The v0.8.0 Milestone)
- **v0.8.3**: **Relative Path Migration**. Fixed broken production fetches and asset routing.
- **v0.8.2**: Migrated to official NVIDIA `nvidia-ml-py` bindings.
- **v0.8.1**: Implemented **Auto-Launch** browser integration for `vidchain-serve`.
- **v0.8.0**: **The Modular Revolution**. Deprecated monolithic processors for Node framework.

---

## Author
**Rahul Sharma** — IIIT Manipur  
*SEM Project Version 0.8.3-Stable*