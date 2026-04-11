"""
vidchain/client.py
------------------
Titan-Class Orchestration Layer.
Features: Zero-Config Ingestion, Lazy Model Loading, and Lifecycle Callbacks.
"""

import os
import uuid
from typing import Optional, Dict, Any, Callable, List
from vidchain.processor import VideoProcessor
from vidchain.core.summarizer import VideoSummarizer
from vidchain.rag import RAGEngine
from vidchain.vectorstores.chroma import ChromaStore

class VidChain:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        
        self.config = {
            "llm_provider": "gemini/gemini-2.5-flash",
            "embedding_provider": "BAAI/bge-base-en-v1.5",  # <--- ADD THIS LINE
            "persistent": False,
            "db_path": None,
            "collection_name": "temp_index",
            "verbose": True
        }
        if config:
            self.config.update(config)

        # Initialize Memory based on the 'persistent' flag
        db_path = self.config["db_path"] if self.config["persistent"] else None
        
        # 1. Memory Layer (ChromaDB)
        self.vector_store = ChromaStore(
            persist_dir=db_path, 
            collection_name=self.config["collection_name"]
        )

        # 2. Reasoning Layer (RAG Engine with Intent Routing)   
        self.rag_engine = RAGEngine(
            model_name=self.config["llm_provider"], 
            vector_store=self.vector_store,
            embedding_model=self.config["embedding_provider"]
        )
        
        # 3. Narrative Layer (Map-Reduce Summarizer)
        self.summarizer = VideoSummarizer(
            model_name=self.config["llm_provider"]
        )

        # Engine Placeholders for Lazy Loading
        self.yolo_engine = None
        self.action_engine = None

    # ------------------------------------------------------------------
    # INTERNAL ENGINE MANAGEMENT
    # ------------------------------------------------------------------

    def _init_engines(self):
        """
        Lazy-loads heavy vision models only when ingestion starts.
        This prevents consuming VRAM if the user only wants to chat/summarize.
        """
        if self.yolo_engine is None:
            from vidchain.vision import VisionEngine as YoloEngine
            if self.config["verbose"]:
                print("[vidchain] Initializing default Vision Engine (YOLOv8)...")
            self.yolo_engine = YoloEngine(model_path="yolov8s.pt")

        if self.action_engine is None:
            from vidchain.processors.vision_model import VisionEngine as ActionEngine
            if self.config["verbose"]:
                print("[vidchain] Initializing default Action Engine...")
            self.action_engine = ActionEngine(model_path="models/vidchain_vision.pth")

    # ------------------------------------------------------------------
    # CORE PIPELINE
    # ------------------------------------------------------------------

    def ingest(
        self, 
        video_source: str, 
        video_id: Optional[str] = None, 
        on_progress: Optional[Callable[[float], None]] = None,
        **kwargs
    ) -> str:
        """
        Full Pipeline: Extraction -> Fusion -> Vector Indexing.
        """
        v_id = video_id or str(uuid.uuid4())[:8]
        
        if self.config["verbose"]:
            print(f"\n[VidChain] Pipeline Start -> ID: {v_id}")
            print(f"[VidChain] Source: {video_source}")

        self._init_engines()
        processor = VideoProcessor(video_source, **kwargs)

        # --- FIX: CALL THIS ONLY ONCE ---
        if self.config["verbose"]:
            print("[VidChain] Executing Multimodal Fusion (Vision + Audio + OCR + Emotion)...")
            
        # This one call handles everything and returns the fused timeline
        fused_timeline = processor.extract_context(
            yolo_engine=self.yolo_engine, 
            action_engine=self.action_engine,
            on_progress=on_progress
        )
        # --------------------------------

        # 2. PERMANENT INDEXING
        self.vector_store.insert_video(
            video_id=v_id, 
            chunk_texts=[self.rag_engine._serialize_entry(e) for e in fused_timeline],
            metadata=fused_timeline
        )
        
        self.rag_engine.is_ready = True
        
        if self.config["verbose"]:
            print(f"[VidChain] Ingestion Complete. {len(fused_timeline)} semantic scenes indexed.")
            
        return v_id

    def ask(self, query: str, stream: bool = False, **kwargs) -> str:
        """
        The Entry Point for QA. Supports Agentic Routing between 
        Video Search and Conversational Memory.
        """
        return self.rag_engine.query(query, stream=stream, **kwargs)

    def summarize_video(self, video_id: str, depth: str = "concise") -> str:
        """
        Fetches the persistent context for a video and generates a forensic narrative.
        """
        docs = self.vector_store.get_video_context(video_id)
        if not docs:
            return f"[ERROR] No data found in storage for Video ID: {video_id}"
        return self.summarizer.generate(docs, mode=depth)

    # ------------------------------------------------------------------
    # DEVELOPER UTILITIES
    # ------------------------------------------------------------------

    def set_llm(self, model_identifier: str):
        """
        Titan Upgrade: Hot-swaps the Reasoning and Narrative engines.
        Useful for multi-model forensic benchmarking.
        """
        if self.config["verbose"]:
            print(f"[vidchain] Switching LLM Engine to: {model_identifier}")
            
        self.config["llm_provider"] = model_identifier
        self.rag_engine.model_name = model_identifier
        self.summarizer.model_name = model_identifier

    def list_indexed_videos(self) -> List[str]:
        """Returns all video IDs currently residing in the persistent database."""
        # Using a list comprehension to ensure we only get unique IDs
        return list(set(self.vector_store.list_videos()))

    def purge_storage(self, video_id: Optional[str] = None):
        """Clears specific video data or nukes the entire local database."""
        if video_id:
            self.vector_store.delete_video(video_id)
        else:
            # Dangerous utility: nukes the entire collection
            self.vector_store.client.delete_collection(self.config["collection_name"])
            print("[vidchain] Local storage purged.")