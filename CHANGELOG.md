# Changelog

All notable changes to VidChain are documented here.

---

## [0.8.3] — 2026-04-21

### Fixed
- **Relative Forensic Uplink**: Removed all hardcoded `localhost:8000` URLs from the Spider-Net Portal source. The portal now uses relative API paths, resolving "broken fetch" errors when the suite is deployed or accessed via different IP addresses.
- **Evidence Stream Persistence**: Fixed the media player and semantic heatmap to use relative asset routing, ensuring forensic evidence loads correctly from the `STORAGE_DIR`.

---

## [0.8.2] — 2026-04-21

### Changed
- **Official NVIDIA Bindings**: Migrated from the deprecated community `pynvml` package to the official `nvidia-ml-py` package. This resolves the `FutureWarning` during server startup while maintaining identical hardware telemetry functionality.
- Bumbed metadata stability to v0.8.2.

---

## [0.8.1] — 2026-04-21

### Added
- **Auto-Launch Integration**: `vidchain-serve` now automatically opens the default web browser to the Spider-Net Portal once the server is initialized.
- **Hardware Telemetry Resilience**: Explicitly added `pynvml` to formal dependencies to prevent runtime crashes during GPU profiling on fresh installations.

### Changed
- Minor internal timing adjustments in the hardware monitor for more stable polling.
- Documented the new "Zero-Launch" workflow for forensic investigators.

---

## [0.8.0] — 2026-04-20

### Added
- **Modular Revolution**: Fully transitioned to a "Nodes & Chains" architecture. The monolithic `processor.py` has been deprecated and removed in favor of composable, independent sensory nodes.
- **Forensic Stability Patch**: Fixed critical CLI crash where modular progress callbacks were misaligned with the terminal status bar.
- **Extended Sensory Suite**: Introduced optional **`EmotionNode`** (Behavioral Sentiment) and **`ActionNode`** (Situational Verbs) as developer-triggerable sensors.
- **Neural Handshake v2**: Refined the CLI Hud to show real-time "Sensory Pulse" counters for each active node during ingestion.
- **Executive Summarization**: Integrated the recursive Map-Reduce narrative engine directly into the CLI. A forensic report is now automatically generated post-ingestion.
- **Fast-Mode Activation**: Re-aligned the `--fast` flag to use the high-speed **`YoloNode`** instead of the heavy VLM, optimizing ingestion for long-form CCTV.

### Changed
- **Codebase Purge**: Removed legacy files including `processor.py`, `audio_loader.py`, and `page_old_fixed.tsx` to ensure a 0% redundancy core.
- `vidchain.cli` now supports modular node injections via `--emotion` and `--action` flags.
- Documentation suite overhauled to align with the library-first, modular API.

---

## [0.7.5] — 2026-04-19

### Changed
- **Objective Intelligence** — Re-aligned the AI persona to act as an objective video observer/summarizer. Prioritizes sensor-ground-truth and chronological summaries over deductive reasoning.
- **Peak Hardware Telemetry** — Upgraded the telemetry monitor to use background polling, capturing absolute CPU/GPU stress peaks during processing.

## [0.7.3] — 2026-04-19

### Added
- **Formatted Intelligence** — Integrated `react-markdown` and `remark-gfm` into the Spider-Net Portal. Every forensic deduction is now broadcast with high-fidelity formatting (headers, lists, bold text, etc.).
- **Hybrid Marker Synthesis** — Custom markdown renderers that detect `[00.0s]` patterns, maintaining interactive "Jump-to-Evidence" capabilities within structured reports.

## [0.7.2] — 2026-04-19

### Added
- **Spider-Net Intelligence Portal** (`vidchain-web`) — A professional-grade, Stark-Tech forensic command center built with Next.js, Framer Motion, and Tailwind CSS. **Now bundled natively within the Python package.**
- **Unified Forensic Bundle** — `vidchain-serve` now automatically hosts the Spider-Net Portal on the root URL (`/`), providing a zero-config investigative experience out of the box.
- **Forensic Evidence Vault** — Multi-sensor video player integrated directly into the dashboard. Supports surgical frame-by-frame scrubbing (`[<]` and `[>]` precision) and real-time Neural HUD overlays.
- **Cognitive Bridge (Neural Handshake)** — Real-time telemetry connection between the B.A.B.U.R.A.O. backend and the web portal. Broadcasts active sensor states (Whisper, VLM, OCR) during ingestion to a live "Engine Status" HUD.
- **Semantic Heatmap** — Timeline-based intelligence density visualization. Automatically maps OCR detections, VLM scene captions, and audio events across the video duration.
- **Knowledge Gateway API** — New forensic endpoints in `serve.py` for structured timeline retrieval (`/api/knowledge/{video_id}`) and neural status polling (`/api/sessions/{session_id}/status`).
- **Forensic Reporting** — One-click "Finalize Report" feature to export session logs and AI deductions into academic-grade Markdown.

### Fixed
- Resolved `NameError: session_id` in `serve.py` ingestion pipeline.
- Fixed critical `Dict` typing NameError in `serve.py` status hub.
- Corrected "Temporal Dead Zone" `ReferenceError` in React dashboard.
- Synchronized Heatmap keys with actual sensor outputs (`ocr`, `objects`, `transcript`).

### Changed
- `vidchain-serve` now mounts a `/media` static route to provide secure local evidence streaming to the web portal.
- Instrumented `VideoChain` orchestrator and `client.py` with `progress_callback` hooks for neural telemetry broadcast.

---

## [0.6.0] — 2026-04-18

### Added
- **VidChain Studio** (`vidchain/ui/desktop.py`) — Native `CustomTkinter` desktop application. Launches via `vidchain-studio`. Features live server status indicator, video file browser, pipeline selector (moondream / llava / yolo), ingestion progress bar, and full B.A.B.U.R.A.O. chat interface backed by the FastAPI edge server.
- **GraphRAG: Temporal Knowledge Graph** (`vidchain/vectorstores/graph.py`) — `TemporalKnowledgeGraph` built automatically on every `vc.ingest()` call using NetworkX. Tracks entity first/last seen timestamps, co-occurrence edges, and OCR text nodes. Graph context is silently injected into every `vc.ask()` call to enable multi-hop temporal reasoning.
- **`vc.graph_query(entity)`** — Direct structured entity lookup that returns appearance timeline, co-occurrence data, and graph-level summary without touching the LLM.
- **VLM-First default pipeline** — `vidchain-analyze` now defaults to Moondream (`--vlm moondream`) instead of YOLO. No flags needed for rich visual descriptions.
- **`--fast` CLI flag** — Explicitly opt-in to the legacy YOLO pipeline for speed on long videos.

### Changed
- `cli.py`: `--vlm` defaults to `moondream`. `--fast` replaces the old "no VLM" behavior.
- `client.ask()` now automatically injects `graph_context` from `TemporalKnowledgeGraph` into every RAG query.
- `client.ingest()` automatically builds the knowledge graph after every ingestion.
- `rag.py`: Added `_inject_graph_context()` static method to cleanly append graph facts to the system prompt.

### Architecture Impact
- VidChain is now a fully VLM-first framework. YOLO is a fallback, not the primary engine.
- Every query to B.A.B.U.R.A.O. is enriched by both ChromaDB semantic search AND structured graph entity facts simultaneously.

---

## [0.5.0] — 2026-04-18

### Added
- **Composable Node Architecture** — LangChain-inspired `VideoChain` orchestrator with modular `BaseNode` interface. Developers can now assemble custom analysis pipelines by snapping together nodes.
- **`LlavaNode`** (`vidchain/nodes/vlm.py`) — Vision Language Model node using Ollama. Replaces blind YOLO tags with rich, context-aware scene descriptions. Supports any Ollama VLM (`moondream`, `llava:7b`, etc.).
- **`AdaptiveKeyframeNode`** (`vidchain/nodes/keyframe.py`) — Gaussian-blurred frame-delta firewall. Blocks visually identical frames from reaching heavy compute nodes (YOLO, LLaVA), dramatically reducing GPU load.
- **`YoloNode`, `WhisperNode`, `OcrNode`, `ActionNode`** — All legacy processors wrapped as composable, reusable nodes.
- **FastAPI Edge Server** (`vidchain/serve.py`) — Launch `vidchain-serve` to expose VidChain as a local REST microservice. Endpoints: `POST /api/ingest` (background task), `POST /api/query`, `GET /api/health`. Interactive Swagger UI at `localhost:8000/docs`.
- **`vidchain-serve`** CLI entry point — instant edge server startup via one command.
- **`VideoChain.run()`** pipeline executor — multi-node sequential context passing with early abort support.
- **`VidChain.ingest(chain=...)`** — optional `chain` parameter to use custom `VideoChain` pipelines while maintaining full backward compatibility with legacy `VideoProcessor`.

### Changed
- Codebase cleaned: removed dead files (`core/fusion.py`, `core/ollama_engine.py`, `loaders/video_loader.py`, `ui/app.py`, `llm/` directory, `schema.py`).
- `vidchain/__init__.py` cleaned to only export `VidChain` — removed unused `VideoEvent`/`VideoAnalysisResult` lazy imports.
- `pyproject.toml` updated with new dependencies: `fastapi`, `uvicorn`, `ollama`, `customtkinter`, `requests`.

### Performance
- `AdaptiveKeyframeNode` achieves compute savings of 60-80% on static footage by blocking successive identical frames before they reach heavy AI models.
- Moondream VLM achieves ~2-5 seconds per keyframe (186x faster than LLaVA 7B on 4GB VRAM setups).

---

## [0.4.0] — 2026-04-18

### Added
- First public release of the composable node system (superseded by v0.5.0 full implementation).
- `vidchain-serve` FastAPI microservice entry point.

---

## [0.3.0] — 2026-04-14

### Added
- **Adaptive AudioLoader** — mirrors VideoLoader's keyframe intelligence for audio:
  RMS energy gating, filler word filtering, segment merging, deduplication,
  and acoustic anomaly detection (shouts, impacts)
- **CLIP Scene Engine** (`SceneEngine`) — zero-shot environment classification
  using `openai/clip-vit-base-patch32`; rate-limited to once per 10s
- **`scene` field** in every KB entry — BABURAO now knows if the room is an
  office, kitchen, hallway, etc.
- **`VideoEvent` schema** and **`VideoAnalysisResult`** — typed dataclasses
  as the canonical contract between pipeline stages
- **Multi-video scoped queries** — `vc.ask("query", video_id="cam1")` scopes
  retrieval to a specific ingested video
- **`knowledge_base.json` auto-write** — every ingest now writes a human-readable
  JSON alongside ChromaDB for inspection and debugging
- **Graceful degradation** — every inference stage (Whisper, YOLO, OCR, DeepFace,
  CLIP) now fails independently; partial results always returned

### Changed
- `VideoProcessor.extract_context()` now accepts optional `scene_engine` argument
- `AudioLoader` resurrected from deprecated stub into a full adaptive processor
- `VideoLoader` replaced with proper deprecation stub (adaptive logic ported into processor)
- `FusionEngine` replaced with deprecation stub (fusion is now internal to processor)
- `RAGEngine._serialize_entry()` now includes `scene`, `camera`, `tracking`,
  `audio_anomaly` fields — previously these were silently dropped
- `VideoSummarizer._serialize_for_summary()` fixed to use `'time'` key
  (was incorrectly using `'timestamp'`)
- `ChromaDB` persistence now triggered by `db_path` alone — `persistent` flag removed
- `pyproject.toml` updated to include all runtime deps

### Fixed
- ChromaDB running in ephemeral mode despite `db_path` being set
- `knowledge_base.json` not updating between runs
- `action` field contaminated with camera/tracking strings (old format bleed)
- Whisper hallucinations (`"4-3"`, `"8-4"`, `"1-Laf再巴"`) passing audio filter
- `CUDA_VISIBLE_DEVICES` race condition causing EasyOCR to init on CPU

---

## [0.2.0] — 2026-03-20

### Added
- **Dual-Brain Vision Engine** — YOLO (objects) + MobileNetV3 (action intent)
- **EasyOCR integration** — smart trigger: only fires when YOLO detects readable surfaces
- **DeepFace emotion analysis** — threaded CPU execution, non-blocking
- **TemporalTracker** — IoU object persistence + Lucas-Kanade optical flow camera motion
- **SceneCutDetector** — HSV histogram correlation resets trackers on hard cuts
- **ChromaDB vector store** — persistent across sessions
- **BGE embedder** (`BAAI/bge-base-en-v1.5`) replacing `all-MiniLM-L6-v2`
- **Cross-encoder reranker** (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- **FAISS HNSW index** replacing flat L2
- **Temporal window retrieval** — pulls neighboring timestamps around FAISS hits
- **Intent router** — classifies queries as VIDEO_SEARCH vs CONVERSATION
- **Chat memory** — maintains last 4 turns for conversational follow-ups
- **Majority-vote temporal smoothing** — eliminates 1-frame action flickers
- **Semantic scene compression** — groups identical consecutive scenes into blocks
- **WAV extraction via MoviePy** — eliminates librosa audioread deprecation warning
- **Ghost FFmpeg Injector** — no system FFmpeg install required
- **`VidChain` client class** — unified Python API: `ingest()`, `ask()`, `summarize_video()`
- **Lazy engine loading** — YOLO/MobileNet only load when `ingest()` is called
- **Progress callback** — `on_progress` hook for CLI and UI integration
- **`--query` flag** — single-shot CLI mode without entering interactive chat
- **`set_llm()`** — hot-swap LLM without re-ingesting
- **`purge_storage()`** — clear specific video or full DB

### Changed
- Full pipeline refactored from multi-file to unified `VideoProcessor`
- Knowledge base schema unified: all modalities in one entry per timestamp
- RAG system prompt upgraded to BABURAO with abductive reasoning directives

### Removed
- Legacy `VideoLoader` (deprecated stub remains)
- Legacy `AudioLoader` (replaced with adaptive version in v0.3.0)
- Legacy `FusionEngine` (deprecated stub remains)

---

## [0.1.0] — 2026-02-10

### Added
- Initial release
- Basic frame extraction with Gaussian blur keyframing
- Whisper audio transcription
- MobileNetV3 action classification
- FAISS flat L2 vector index with `all-MiniLM-L6-v2`
- Ollama + Gemini LLM routing via LiteLLM
- `knowledge_base.json` output
- CLI entry point `vidchain-analyze`
- Training script `vidchain-train`