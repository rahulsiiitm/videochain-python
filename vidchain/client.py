"""
vidchain/client.py
------------------
Titan-Class Orchestration Layer.
Fixed: Handled unified multimodal fusion stream from VideoProcessor.
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
        """
        Standardizes initialization. 
        Devs can pass a dict to override anything from LLM choice to DB persistence.
        """
        self.config = {
            "llm_provider": "ollama/llama3",
            "embedding_provider": "BAAI/bge-base-en-v1.5",
            "db_path": "./vidchain_storage",
            "collection_name": "global_video_index",
            "processing_device": "cuda", # 'cuda', 'cpu', or 'mps'
            "verbose": True
        }
        if config:
            self.config.update(config)

        # 1. Memory Layer (Persistent ChromaDB)
        self.vector_store = ChromaStore(
            persist_dir=self.config["db_path"], 
            collection_name=self.config["collection_name"]
        )
        
        # 2. Reasoning Layer (RAG Engine with Intent Routing)
        self.rag_engine = RAGEngine(
            model_name=self.config["llm_provider"], 
            vector_store=self.vector_store, # type: ignore
            embedding_model=self.config["embedding_provider"]
        )
        
        # 3. Narrative Layer (Map-Reduce Summarizer)
        self.summarizer = VideoSummarizer(
            model_name=self.config["llm_provider"]
        )

    # ------------------------------------------------------------------
    # CORE PIPELINE
    # ------------------------------------------------------------------

    def ingest(
        self, 
        video_source: str, 
        yolo_engine: Any, 
        action_engine: Any,
        video_id: Optional[str] = None, 
        on_progress: Optional[Callable[[float], None]] = None,
        **processor_kwargs
    ) -> str:
        """
        High-level ingestion. Now handles the FUSED timeline output.
        """
        v_id = video_id or str(uuid.uuid4())[:8]
        if self.config["verbose"]:
            print(f"[VidChain] Pipeline Start -> ID: {v_id} | Source: {video_source}")

        # Initialize the Fused Processor
        processor = VideoProcessor(
            video_source, 
            **processor_kwargs
        )
        
        # FIX: The processor now returns ONE fused timeline object
        # This prevents the "ValueError: too many values to unpack"
        print("[VidChain] Executing Multimodal Fusion (Vision + Audio + OCR + Emotion)...")
        fused_timeline = processor.extract_context(
            yolo_engine=yolo_engine, 
            action_engine=action_engine
        )
        
        # Multi-modal Injection into Vector DB
        # We serialize each fused entry so the RAG engine can read it as text
        self.vector_store.insert_video( # type: ignore
            video_id=v_id, 
            chunk_texts=[self.rag_engine._serialize_entry(e) for e in fused_timeline],
            metadata=fused_timeline
        )
        
        # Set RAG engine to ready since data is now indexed
        self.rag_engine.is_ready = True
        
        if self.config["verbose"]:
            print(f"[VidChain] Ingestion Complete. {len(fused_timeline)} semantic events indexed.")
            
        return v_id

    def ask(self, query: str, stream: bool = False, **kwargs) -> Any:
        """
        The Entry Point for QA. Supports Agentic Routing.
        """
        return self.rag_engine.query(query, stream=stream, **kwargs) # type: ignore

    def summarize_video(self, video_id: str, depth: str = "concise") -> str:
        """
        Advanced Summarization using the persistent DB context.
        """
        # Fetching context from ChromaDB for the specific video
        docs = self.vector_store.get_video_context(video_id) # type: ignore
        return self.summarizer.generate(docs, mode=depth)

    # ------------------------------------------------------------------
    # DEVELOPER UTILITIES
    # ------------------------------------------------------------------

    def set_llm(self, model_identifier: str):
        """Hot-swap the LLM engine (e.g., switch from Llama3 to Gemini)."""
        self.config["llm_provider"] = model_identifier
        self.rag_engine.model_name = model_identifier
        self.summarizer.model_name = model_identifier

    def list_indexed_videos(self) -> List[str]:
        """Returns all video IDs currently in the persistent database."""
        return self.vector_store.list_videos()

    def purge_storage(self, video_id: Optional[str] = None):
        """Clear specific video or nuke the entire library."""
        if video_id:
            self.vector_store.delete_video(video_id)
        else:
            self.vector_store.nuke_database() # type: ignore