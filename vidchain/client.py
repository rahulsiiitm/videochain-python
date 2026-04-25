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


        # ── Knowledge Base Directory ──────────────────────────────────
        self.kb_dir = os.path.join(db_path, "knowledge_bases") if db_path else None
        if self.kb_dir:
            os.makedirs(self.kb_dir, exist_ok=True)

        self.rag_engine = RAGEngine(
            model_name=self.config["llm_provider"],
            vector_store=self.vector_store,
            embedding_model=self.config["embedding_provider"],
            kb_dir=self.kb_dir
        )

        # GraphRAG knowledge graph (Isolated per video)
        self.knowledge_graph = TemporalKnowledgeGraph()
        self.active_timeline: List[dict] = []  
        
        # ── Master Intelligence (Global Knowledge Graph) ────────────────
        self.global_graph = TemporalKnowledgeGraph()
        
        # In multi-video mode, graphs are loaded on-demand by video_id
        self.graph_dir = os.path.join(db_path, "knowledge_graphs") if db_path else None
        if self.graph_dir:
            os.makedirs(self.graph_dir, exist_ok=True)
            # Load Master Graph for cross-video intelligence
            global_p = os.path.join(self.graph_dir, "global_graph.pkl")
            if os.path.exists(global_p):
                self.global_graph.load_from_disk(global_p)
                if self.config["verbose"]:
                    print(f"[IRIS] Master Intelligence Loaded: {self.global_graph.describe()}")

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
            from vidchain.nodes import AdaptiveKeyframeNode, WhisperNode, LlavaNode, OcrNode, TrackerNode
            
            if self.config["verbose"]:
                print("[VidChain] Executing High-Fidelity Forensic Pipeline (VLM + Whisper + LK Tracking)...")
            
            # Build the same chain used in vidchain-analyze
            default_chain = VideoChain(
                nodes=[
                    AdaptiveKeyframeNode(change_threshold=5.0),
                    TrackerNode(),
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
        
        # ── Build GraphRAG Knowledge Graphs ────────────────────────────
        # 1. Update Local Session Graph
        self.knowledge_graph.build_from_timeline(fused_timeline, video_id=v_id)
        # 2. Update Master Intelligence Graph (Additive)
        self.global_graph.build_from_timeline(fused_timeline, video_id=v_id)
        
        if self.config["verbose"]:
            print(f"[IRIS] Local Intel: {self.knowledge_graph.describe()}")
            print(f"[IRIS] Master Intel: {self.global_graph.describe()}")
            
        # ── Save Isolated Graphs ───────────────────────────────────────
        if self.graph_dir:
            # Save local
            per_video_graph = os.path.join(self.graph_dir, f"graph_{v_id}.pkl")
            self.knowledge_graph.save_to_disk(per_video_graph)
            # Save Master
            global_p = os.path.join(self.graph_dir, "global_graph.pkl")
            self.global_graph.save_to_disk(global_p)
            
            if self.config["verbose"]:
                print(f"[IRIS] Global Intelligence Sync'd -> {global_p}")

        # ── Write knowledge_base.json (Persistent Storage Only) ───────
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

    def _load_video_context(self, video_id: Optional[str]):
        """Hot-swaps the active knowledge graph based on the video context."""
        if not video_id or not self.graph_dir:
            return

        per_video_graph = os.path.join(self.graph_dir, f"graph_{video_id}.pkl")
        if os.path.exists(per_video_graph):
            self.knowledge_graph.load_from_disk(per_video_graph)

    def ask(
        self, 
        query: str, 
        video_id: Optional[str] = None, 
        history: Optional[List[dict]] = None,
        stream: bool = False, 
        **kwargs
    ) -> str:
        # 1. Load the specific graph for this video context
        self._load_video_context(video_id)

        # 2. Extract Local Context (High-Precision)
        local_context = ""
        if self.knowledge_graph._is_built:
            local_context = self.knowledge_graph.get_graph_context(query, video_id=video_id)
        
        # 3. Extract Global Context (Cross-Video Intel)
        global_context = ""
        if self.global_graph._is_built:
            global_context = self.global_graph.get_graph_context(query)
            
        # 4. Neural Intersection: Combine both for the RAG Engine
        combined_graph_context = f"{local_context}\n\n[GLOBAL MASTER INTELLIGENCE]\n{global_context}"
        if "graph_context" not in kwargs:
            kwargs["graph_context"] = combined_graph_context
            
        # Context Binding: 
        # Ensure we are strictly using the provided timeline or searching the correct video_id.
        if "timeline" not in kwargs or not kwargs["timeline"]:
            pass
            
        return self.rag_engine.query(query, stream=stream, history=history, video_id=video_id, **kwargs)

    # ------------------------------------------------------------------
    # Developer utilities
    # ------------------------------------------------------------------

    def get_video_timeline(self, video_id: str) -> List[Dict[str, Any]]:
        """Retrieves the full event list for a specific video ID. Strictly ID-bound."""
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
        
        return []

    def set_llm(self, model_identifier: str):
        if self.config["verbose"]:
            print(f"[VidChain] Switching LLM -> {model_identifier}")
        self.config["llm_provider"] = model_identifier
        self.rag_engine.model_name  = model_identifier

    def list_indexed_videos(self) -> List[str]:
        return list(set(self.vector_store.list_videos()))

    def purge_storage(self, video_id: Optional[str] = None):
        if video_id:
            # 1. Purge Vectors
            self.vector_store.delete_video(video_id)
            
            # 2. Scrub Global Intelligence (Neural Amnesia)
            if self.global_graph:
                self.global_graph.remove_video_context(video_id)
                # Save the updated Master Graph
                if self.graph_dir:
                    global_p = os.path.join(self.graph_dir, "global_graph.pkl")
                    self.global_graph.save_to_disk(global_p)

            # 3. Scrub Physical Artifacts
            db_path = self.config.get("db_path")
            if db_path:
                kb_path = os.path.join(db_path, "knowledge_bases", f"{video_id}.json")
                if os.path.exists(kb_path):
                    try:
                        with open(kb_path, "r", encoding="utf-8") as f:
                            kb_data = json.load(f)
                            v_path = kb_data.get("metadata", {}).get("source")
                            if v_path:
                                audio_p = v_path.rsplit(".", 1)[0] + "_pipeline_temp.wav"
                                if os.path.exists(audio_p):
                                    os.remove(audio_p)
                                    if self.config["verbose"]:
                                        print(f"[VidChain] Purged temp audio: {audio_p}")
                    except: pass
                    os.remove(kb_path)
            
            if self.graph_dir:
                p = os.path.join(self.graph_dir, f"graph_{video_id}.pkl")
                if os.path.exists(p): os.remove(p)

            if self.config["verbose"]:
                print(f"[VidChain] Forensic memory fully purged for: {video_id}")
        else:
            # 1. Clear Vectors
            self.vector_store.client.delete_collection(self.config["collection_name"])
            
            # 2. Scrub Master Graph
            if self.graph_dir:
                global_p = os.path.join(self.graph_dir, "global_graph.pkl")
                if os.path.exists(global_p): os.remove(global_p)
                # Reset in-memory
                from vidchain.vectorstores.graph import TemporalKnowledgeGraph
                self.global_graph = TemporalKnowledgeGraph()
                
            if self.config["verbose"]:
                print("[VidChain] All global storage and master intelligence purged.")