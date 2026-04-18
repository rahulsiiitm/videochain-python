# VidChain: Embedded Library Use-Case Demo

This folder represents a **separate application** built on top of the VidChain framework. It demonstrates how a developer can embed the VidChain engine into their own custom solutions.

## 🚀 How to Run the "Embedded Agent"

### 1. Link the Framework
Since this application exists outside the framework codebase, you must ensure your environment can find the `vidchain` library. Link it in editable mode from the root directory:
```powershell
pip install -e .
```

### 2. Prepare the Feed
Ensure there is a sample video file in the project root (e.g., `sample.mp4`).

### 3. Launch the Audit
Run the standalone forensic script:
```powershell
python embedded_demo/forensic_monitor.py
```

## 🧠 Why this matters for the Project Presentation:
- **Separation of Concerns**: We have a clear split between the **Library** (Generic Framework) and the **Application** (Specific Use-Case).
- **Scalability**: Explains how other developers could build *Real-Time Security Hubs*, *Motion Detectors*, or *Brand Analysts* using your code as the "Base-Chain".
- **Advanced Logic**: The `ForensicAuditAgent` doesn't just chat; it generates a structured, academic-grade **Audit Report** automatically.
