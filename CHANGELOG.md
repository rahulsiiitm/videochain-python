# Changelog

All notable changes to VidChain are documented here.

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