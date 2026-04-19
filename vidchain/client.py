"""
vidchain/client.py
------------------
Titan-Class Orchestration Layer.
Features: Zero-Config Ingestion, Lazy Model Loading, and Lifecycle Callbacks.
"""

import os
import uuid
import json
from typing import Optional, Dict, Any, Callable, List
from vidchain.processor import VideoProcessor
from vidchain.core.summarizer import VideoSummarizer
from vidchain.rag import RAGEngine
from vidchain.vectorstores.chroma import ChromaStore
from vidchain.vectorstores.graph import TemporalKnowledgeGraph


class VidChain:
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        self.config = {
            "llm_provider":       "ollama/llama3",
            "embedding_provider": "BAAI/bge-base-en-v1.5",
            "db_path":            None,   # None = ephemeral; path = persistent
            "collection_name":    "video_index",
            "verbose":            True,
            "save_kb_json":       True,   # write knowledge_base.json alongside ChromaDB
            "kb_json_path":       "knowledge_base.json",
        }
        if config:
            self.config.update(config)
        
        # Merge keyword arguments into config
        if kwargs:
            self.config.update(kwargs)

        # Persistence: if db_path is provided, persist to disk
        db_path = self.config.get("db_path")

        self.vector_store = ChromaStore(
            persist_dir=db_path,
            collection_name=self.config["collection_name"]
        )

        self.rag_engine = RAGEngine(
            model_name=self.config["llm_provider"],
            vector_store=self.vector_store,
            embedding_model=self.config["embedding_provider"]
        )

        self.summarizer = VideoSummarizer(
            model_name=self.config["llm_provider"]
        )

        # Lazy-loaded vision engines
        self.yolo_engine   = None
        self.action_engine = None
        self.scene_engine  = None
        
        # GraphRAG knowledge graph (built automatically on every ingest)
        self.knowledge_graph = TemporalKnowledgeGraph()
        self.active_timeline: List[dict] = []  # In-memory cache for Agentic AI reasoning
        
        # Load graph if database is persistent
        if db_path:
            self.graph_path = os.path.join(db_path, "knowledge_graph.pkl")
            self.knowledge_graph.load_from_disk(self.graph_path)
        else:
            self.graph_path = None

    # ------------------------------------------------------------------
    # Internal engine management
    # ------------------------------------------------------------------

    def _init_engines(self):
        if self.yolo_engine is None:
            from vidchain.vision import VisionEngine as YoloEngine
            if self.config["verbose"]:
                print("[VidChain] Initializing YOLO Vision Engine...")
            self.yolo_engine = YoloEngine(model_path="yolov8s.pt", confidence_threshold=0.6)

        if self.action_engine is None:
            from vidchain.processors.vision_model import VisionEngine as ActionEngine
            if self.config["verbose"]:
                print("[VidChain] Initializing Action Engine...")
            self.action_engine = ActionEngine(model_path="models/vidchain_vision.pth")

        if self.scene_engine is None:
            from vidchain.processors.scene_model import SceneEngine
            if self.config["verbose"]:
                print("[VidChain] Initializing Scene Engine (CLIP)...")
            self.scene_engine = SceneEngine()

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    def ingest(
        self,
        video_source: str,
        video_id: Optional[str] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None,
        chain: Optional[Any] = None,
        **kwargs
    ) -> str:
        v_id = video_id or str(uuid.uuid4())[:8]
        _audio_path = None  # Internal tracking for nodes

        if self.config["verbose"]:
            print(f"\n[VidChain] Pipeline Start -> ID: {v_id}")
            print(f"[VidChain] Source: {video_source}")

        if chain:
            if self.config["verbose"]:
                print("[VidChain] Executing Custom VideoChain...")
            fused_timeline, _audio_path = chain.run(video_source)
        else:
            # ── High-Fidelity Default Pipeline ──────────────────────
            # This aligns the Web Dashboard with the 'analyze' CLI
            from vidchain.pipeline import VideoChain
            from vidchain.nodes import AdaptiveKeyframeNode, WhisperNode, LlavaNode, OcrNode
            
            if self.config["verbose"]:
                print("[VidChain] Executing High-Fidelity Forensic Pipeline (VLM + Whisper)...")
            
            # Build the same chain used in vidchain-analyze
            default_chain = VideoChain(
                nodes=[
                    AdaptiveKeyframeNode(change_threshold=5.0),
                    WhisperNode(model_size="base"),
                    LlavaNode(model_name="moondream"), 
                    OcrNode(),
                ],
                frame_skip=15 # 2 FPS
            )
            results = default_chain.run(video_source, progress_callback=progress_callback)
            # Robust destructuring to prevent 'list has no get' error
            if isinstance(results, tuple):
                fused_timeline, _audio_path = results
            else:
                fused_timeline = results
                _audio_path = None

        self.active_timeline = fused_timeline

        # ── Indexing Block ────────────────────────────────────────────
        if not fused_timeline:
            if self.config["verbose"]:
                print("[VidChain] Warning: No events detected. Skipping index.")
            return v_id

        if self.config["verbose"]:
            print(f"[VidChain] Indexing {len(fused_timeline)} events into ChromaDB...")
            
        self.vector_store.insert_video(
            video_id=v_id,
            chunk_texts=[self.rag_engine._serialize_entry(e) for e in fused_timeline],
            metadata=fused_timeline
        )
        self.rag_engine.is_ready = True
        
        # ── Build GraphRAG Knowledge Graph ────────────────────────────
        self.knowledge_graph.build_from_timeline(fused_timeline)
        if self.config["verbose"]:
            print(f"[VidChain] {self.knowledge_graph.describe()}")
            
        # ── Save Graph if persistent ──────────────────────────────────
        if self.graph_path:
            self.knowledge_graph.save_to_disk(self.graph_path)

        # ── Write knowledge_base.json ─────────────────────────────────
        if self.config.get("save_kb_json", True):
            kb = {
                "metadata": {
                    "video_id":             v_id,
                    "source":               video_source,
                    "video_path":           video_source,
                    "audio_path":           _audio_path,
                    "total_events":         len(fused_timeline),
                },
                "timeline": fused_timeline
            }
            # Save to standard path for backward compatibility
            kb_path = self.config.get("kb_json_path", "knowledge_base.json")
            with open(kb_path, "w", encoding="utf-8") as f:
                json.dump(kb, f, indent=4, ensure_ascii=False)
            
            # Save to persistent storage if available
            db_path = self.config.get("db_path")
            if db_path:
                kb_dir = os.path.join(db_path, "knowledge_bases")
                os.makedirs(kb_dir, exist_ok=True)
                per_video_path = os.path.join(kb_dir, f"{v_id}.json")
                with open(per_video_path, "w", encoding="utf-8") as f:
                    json.dump(kb, f, indent=4, ensure_ascii=False)
                if self.config["verbose"]:
                    print(f"[VidChain] Forensic Knowledge Base archived -> {per_video_path}")

        self.active_timeline = fused_timeline
        if self.config["verbose"]:
            print(f"[VidChain] Ingestion Complete. {len(fused_timeline)} scenes indexed.")

        return v_id

    def ask(
        self, 
        query: str, 
        video_id: Optional[str] = None, 
        history: Optional[List[dict]] = None,
        stream: bool = False, 
        **kwargs
    ) -> str:
        """
        Main query entry point. 
        If video_id is provided, it isolates search and context to that video.
        If history is provided, it maintains private session memory.
        """
        # Inject Graph Context if available
        if self.knowledge_graph._is_built and "graph_context" not in kwargs:
            kwargs["graph_context"] = self.knowledge_graph.get_graph_context(query)
            
        # Context Hotswapping: 
        # If we have no timeline or an empty one, fallback to the just-ingested active_timeline
        if "timeline" not in kwargs or not kwargs["timeline"]:
            if hasattr(self, "active_timeline") and self.active_timeline:
                kwargs["timeline"] = self.active_timeline
            
        return self.rag_engine.query(query, stream=stream, history=history, video_id=video_id, **kwargs)

    def graph_query(self, entity: str) -> Dict[str, Any]:
        """Direct knowledge graph lookup for a specific entity."""
        if not self.knowledge_graph._is_built:
            return {"error": "Graph not built yet. Run ingest() first."}
        return {
            "entity": entity,
            "timeline": self.knowledge_graph.get_entity_timeline(entity),
            "all_entities": self.knowledge_graph.get_all_entities(),
            "graph_summary": self.knowledge_graph.describe()
        }

    def summarize_video(self, video_id: str, depth: str = "concise") -> str:
        docs = self.vector_store.get_video_context(video_id)
        if not docs:
            return f"[ERROR] No data found for Video ID: {video_id}"
        return self.summarizer.generate(docs, mode=depth)  # type: ignore

    # ------------------------------------------------------------------
    # Developer utilities
    # ------------------------------------------------------------------

    def get_video_timeline(self, video_id: str) -> List[Dict[str, Any]]:
        """Retrieves the full event list for a specific video ID with deep fallback."""
        if not video_id:
            return []

        db_path = self.config.get("db_path")
        if db_path:
            kb_dir = os.path.join(db_path, "knowledge_bases")
            kb_path = os.path.join(kb_dir, f"{video_id}.json")
            
            if os.path.exists(kb_path):
                try:
                    with open(kb_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        events = data.get("timeline", [])
                        if events:
                            if self.config["verbose"]:
                                print(f"[VidChain] Context Reload Success -> ID {video_id} ({len(events)} events)")
                            return events
                except Exception as e:
                    print(f"[VidChain] [ERROR] Failed to load archived timeline for {video_id}: {e}")
        
        # Fallback 1: Is this video currently in active memory?
        if hasattr(self, "active_timeline") and self.active_timeline:
            if self.config["verbose"]:
                print(f"[VidChain] Using Active Brain fallback for {video_id}")
            return self.active_timeline
            
        # Fallback 2: Deep Discovery - find the most recent KB if we're lost
        if db_path:
            kb_dir = os.path.join(db_path, "knowledge_bases")
            if os.path.exists(kb_dir):
                files = [f for f in os.listdir(kb_dir) if f.endswith(".json")]
                if files:
                    # Sort by modification time to get the freshest one
                    files.sort(key=lambda x: os.path.getmtime(os.path.join(kb_dir, x)), reverse=True)
                    latest_kb = os.path.join(kb_dir, files[0])
                    try:
                        with open(latest_kb, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if self.config["verbose"]:
                                print(f"[VidChain] [Deep Discovery] Recalling latest available context: {files[0]}")
                            return data.get("timeline", [])
                    except: pass

        return []

    def set_llm(self, model_identifier: str):
        if self.config["verbose"]:
            print(f"[VidChain] Switching LLM -> {model_identifier}")
        self.config["llm_provider"] = model_identifier
        self.rag_engine.model_name  = model_identifier
        self.summarizer.model_name  = model_identifier

    def list_indexed_videos(self) -> List[str]:
        return list(set(self.vector_store.list_videos()))

    def purge_storage(self, video_id: Optional[str] = None):
        if video_id:
            self.vector_store.delete_video(video_id)
            if self.config["verbose"]:
                print(f"[VidChain] Purged video: {video_id}")
        else:
            self.vector_store.client.delete_collection(self.config["collection_name"])
            if self.config["verbose"]:
                print("[VidChain] All storage purged.")