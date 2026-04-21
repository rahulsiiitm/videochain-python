# VidChain: The "LangChain for Videos"
> **v0.8.2-Stable** — Edge-optimized, local-first multimodal RAG framework for forensic video intelligence. Compose modular sensory nodes into custom pipelines, deploy as a microservice, or query via the **Spider-Net Intelligence Portal**.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![CUDA](https://img.shields.io/badge/CUDA-12.1-green) ![License](https://img.shields.io/badge/License-MIT-yellow) ![Status](https://img.shields.io/badge/Status-v0.8.2--Stable-green) [![PyPI version](https://badge.fury.io/py/vidchain.svg)](https://pypi.org/project/VidChain/)

![Spider-Net Intelligence Portal](assets/forensic_portal.webp)

---

## Advanced Forensic Architecture

VidChain v0.8.0-Stable is powered by the **B.A.B.U.R.A.O. Engine** (Behavioral Analysis & Broadcasting Unit for Real-time Artificial Observation). It utilizes a modular "Nodes & Chains" framework to transform raw pixels into serialized forensic intelligence.

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

## Key Features (v0.8.0 Evolution)

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

VidChain is designed to be deeply extensible. Here are the core "Intelligence Recipes" for v0.8.0-Stable.

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

### 3. Behavioral Sentiment Investigation
Combine Kinetic and Emotional sensors for psychological profiling.
```python
from vidchain.nodes import EmotionNode, ActionNode, LlavaNode

profile_chain = VideoChain(nodes=[
    ActionNode(),             # Situational "Verbs"
    EmotionNode(),            # Facial Sentiment
    LlavaNode()               # Visual Context
])

vc.ingest("interview.mp4", chain=profile_chain)
print(vc.ask("Does the subject appear agitated when talking about the incident?"))
```

### 4. Direct Knowledge Graph Inquiry (No LLM)
Query entities directly from the **Temporal Knowledge Graph** without using LLM tokens.
```python
# Access the structured GraphRAG facts directly
graph_facts = vc.graph_query("Laptop")
print(f"Appearances: {graph_facts['timestamps']}")
print(f"Co-occurrences: {graph_facts['entities_seen_together']}")
```

---

## Forensic CLI Mastery
| Command | Mode | Intelligence Depth |
| :--- | :--- | :--- |
| `python -m vidchain.cli report.mp4` | **VLM-Standard** | Adaptive Keyframes + VLM + Summary. |
| `python -m vidchain.cli report.mp4 --fast` | **YOLO-Scan** | High-speed object detection for long CCTV. |
| `python -m vidchain.cli report.mp4 --emotion` | **Behavioral** | Injects EmotionNode for sentiment analysis. |
| `python -m vidchain.cli report.mp4 --query "..."` | **Direct** | Instant query without interactive chat. |

---

## Sensory Node Suite (The Matrix)

| Node | Type | Purpose |
| :--- | :--- | :--- |
| `LlavaNode` | VLM | Dense Contextual Scene Captioning (Moondream/LLaVA). |
| `WhisperNode` | Audio | Time-aligned speech-to-text forensics. |
| `OcrNode` | Text | Screen text and digital trace extraction. |
| `TrackerNode` | Motion | Optical flow subject tracking & persistence. |
| `ActionNode` | Verb | Situational classification (Emergency, Violation). |
| `EmotionNode` | Sentiment | Behavioral sentiment analysis (DeepFace). |
| `YoloNode` | Fast-Detect | Ultra-fast object detection (Fallback for VLM). |

---

## Research Position & Uniqueness
VidChain treats video as **Serialized Sensor Logs**, performing retrieval over structured multimodal narratives rather than raw pixel tokens. This significantly reduces hallucinations and enables multi-video GraphRAG reasoning. 
> See **[RESEARCH_COMPARISON.md](./RESEARCH_COMPARISON.md)** for detailed SOTA benchmarks.

---

## 📜 Changelog (The v0.8.0 Milestone)
- **v0.8.0**: **The Modular Revolution**. Deprecated monolithic processors for a 100% composable Node framework. Added internal hardware diagnostics, automatic reporting, and fresh Next.js UI bundling.
- **v0.7.2**: Integrated the **Spider-Net Portal** as a native microservice. Added Neural HUD and Evidence Vault.
- **v0.6.0**: Introduced **GraphRAG** and Temporal Knowledge Graphs for entity tracking.

---

## Author
**Rahul Sharma** — IIIT Manipur  
*SEM Project Version 0.8.1-Stable*