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
        on_progress: Optional[Callable[[float], None]] = None,
        chain: Optional[Any] = None,
        **kwargs
    ) -> str:
        v_id = video_id or str(uuid.uuid4())[:8]

        if self.config["verbose"]:
            print(f"\n[VidChain] Pipeline Start -> ID: {v_id}")
            print(f"[VidChain] Source: {video_source}")

        if chain:
            if self.config["verbose"]:
                print("[VidChain] Executing Custom VideoChain...")
            fused_timeline = chain.run(video_source)
        else:
            self._init_engines()
            processor = VideoProcessor(video_source, **kwargs)

            if self.config["verbose"]:
                print("[VidChain] Executing Legacy Multimodal Fusion...")

            fused_timeline = processor.extract_context(
                yolo_engine=self.yolo_engine,
                action_engine=self.action_engine,
                scene_engine=self.scene_engine,
                on_progress=on_progress
            )

        # ── Index into ChromaDB ───────────────────────────────────────
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
                    "total_events":         len(fused_timeline),
                },
                "timeline": fused_timeline
            }
            kb_path = self.config.get("kb_json_path", "knowledge_base.json")
            with open(kb_path, "w", encoding="utf-8") as f:
                json.dump(kb, f, indent=4, ensure_ascii=False)
            if self.config["verbose"]:
                print(f"[VidChain] knowledge_base.json written -> {kb_path}")

        if self.config["verbose"]:
            print(f"[VidChain] Ingestion Complete. {len(fused_timeline)} scenes indexed.")

        return v_id

    def ask(self, query: str, stream: bool = False, **kwargs) -> str:
        # Auto-inject GraphRAG temporal context if the graph is built
        if self.knowledge_graph._is_built and "graph_context" not in kwargs:
            kwargs["graph_context"] = self.knowledge_graph.get_graph_context(query)
        return self.rag_engine.query(query, stream=stream, **kwargs)

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