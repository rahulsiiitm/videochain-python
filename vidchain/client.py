"""
vidchain/client.py
------------------
The main orchestration layer for the VidChain framework.
Allows developers to easily ingest videos, generate Map-Reduce summaries, 
and query the temporal knowledge base.
"""

from vidchain.processor import VideoProcessor
# from vidchain.processors.tracker import TemporalTracker
from vidchain.core.summarizer import VideoSummarizer
from vidchain.rag import RAGEngine
import os

class VidChain:
    def __init__(self, llm="gemini/gemini-2.5-flash", vector_store_path="./vidchain_db"):
        """Initializes the VidChain framework."""
        self.llm = llm
        self.db_path = vector_store_path
        self.rag_engine = RAGEngine(model_name=self.llm)
        self.summarizer = VideoSummarizer(model_name=self.llm)

    def ingest(self, video_path: str, extract_audio: bool = True, ocr: bool = True):
        """
        Processes a video through the multimodal pipeline and saves it to the vector store.
        For a 2-hour movie, developers run this once as a background job.
        """
        print(f"[VidChain] Ingesting target: {video_path}")
        
        # 1. Run the YOLO + MobileNet + Tracker pipeline
        processor = VideoProcessor(video_path, ocr_languages=["en"] if ocr else [])
        
        # (Assuming your internal processor saves to a standard JSON or ChromaDB here)
        kb_path = os.path.join(self.db_path, "knowledge_base.json")
        processor.extract_and_save(output_path=kb_path) # type: ignore
        
        # 2. Load the newly built DB into the RAG engine
        self.rag_engine.load_knowledge(kb_path)
        print("[VidChain] Ingestion complete. Knowledge base active.")

    def summarize(self, force_recompute: bool = False) -> str:
        """
        Generates a master plot summary using Hierarchical Map-Reduce.
        Handles massive contexts (like full movies) without blowing up VRAM.
        """
        kb_path = os.path.join(self.db_path, "knowledge_base.json")
        summary_path = os.path.join(self.db_path, "master_summary.txt")

        # Developer Experience (DX) Fix: Don't re-summarize a 2-hour movie if we already did it!
        if os.path.exists(summary_path) and not force_recompute:
            print("[VidChain] Loading pre-computed master summary...")
            with open(summary_path, 'r') as f:
                return f.read()

        print("[VidChain] Executing Map-Reduce Global Summarization...")
        summary = self.summarizer.generate_master_summary(kb_path)
        
        # Cache the summary so the next call is instant
        with open(summary_path, 'w') as f:
            f.write(summary)
            
        return summary

    def ask(self, query: str) -> str:
        """
        Agentic routing: Answers specific temporal questions using the RAG Engine.
        """
        if not self.rag_engine.is_ready:
            raise RuntimeError("Knowledge base not loaded. Call .ingest() first.")
            
        print(f"[VidChain] Querying temporal vector store: '{query}'")
        return self.rag_engine.query(query)