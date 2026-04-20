import os
import json
import time
import numpy as np
import traceback
from typing import Any, List, Dict, Optional
from vidchain.telemetry import HardwareMonitor
from sentence_transformers import CrossEncoder
from dotenv import load_dotenv
from litellm import completion

load_dotenv()

# ---------------------------------------------------------------------------
# Intent classifier & Persona
# ---------------------------------------------------------------------------

CHITCHAT_TRIGGERS = {
    "hi", "hello", "hey", "sup", "yo", "hiya",
    "who are you", "who r u", "who are u", "what are you",
    "what r you", "what can you do", "help",
    "thanks", "thank you", "ok", "okay", "cool", "got it", "bye", "goodbye"
}

BABURAO_INTRO = (
    "B.A.B.U.R.A.O. (Behavioral Analysis & Broadcasting Unit for Real-time Artificial Observation)\n"
    "Status: Operational. Awaiting query.\n\n"
    "Scope: Event detection, timeline reconstruction, anomaly flagging, "
    "subject tracking, and incident verification from indexed surveillance logs."
)

def is_chitchat(text: str) -> bool:
    if not text: return False
    return text.strip().lower().rstrip("!?.,'\"") in CHITCHAT_TRIGGERS

# ---------------------------------------------------------------------------
# RAG Engine
# ---------------------------------------------------------------------------

class RAGEngine:
    def __init__(
        self,
        model_name: str = "ollama/llama3",
        vector_store: Any = None,
        embedding_model: str = "BAAI/bge-base-en-v1.5",
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        top_k: int = 40,          
        rerank_top_k: int = 25,    
        temporal_window: int = 2, 
    ):
        self.model_name = model_name
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.top_k = top_k
        self.rerank_top_k = rerank_top_k
        self.temporal_window = temporal_window
        
        # Load Reranker once to save VRAM later
        print(f"[INFO] Booting Reranker Engine...")
        try:
            self.reranker = CrossEncoder(reranker_model)
        except Exception as e:
            print(f"[ERROR] Reranker failed to load: {e}. Standard search will be used.")
            self.reranker = None
        
        self.chat_history: list = [] 
        self.is_ready = True if vector_store else False

        print(f"[INFO] RAG Engine initialized with VectorStore: {self.vector_store is not None}")

    @staticmethod
    def _serialize_entry(e: dict) -> str:
        """Standardizes how video events look to the LLM."""
        ts = e.get('time') or e.get('current_time') or e.get('timestamp', 0)
        parts = [f"[{ts}s]"]
        if e.get("scene"): parts.append(f"Environment: {e['scene']}")
        if e.get("action"): parts.append(f"Action: {e['action']}")
        if e.get("objects"): parts.append(f"Visuals: {e['objects']}")
        if e.get("ocr"): parts.append(f"Screen text: {e['ocr']}")
        if e.get("audio"): parts.append(f"Speech: \"{e['audio']}\"")
        if e.get("emotion"): parts.append(f"Emotion: {e['emotion']}")
        if e.get("camera_motion") and e.get("camera_motion") != "static":
            parts.append(f"Camera: {e['camera_motion']}")
        return " | ".join(parts)

    @staticmethod
    def _build_system_prompt(context: str) -> str:
        """Constructs an Objective Video Observer persona (Summarizer-First)."""
        return f"""
        You are B.A.B.U.R.A.O. (Behavioral Analysis & Broadcasting Unit for Real-time Artificial Observation).
        You are an Objective Video Observer and High-Fidelity Summarizer.

        YOUR MISSION:
        Capture and report ground-truth observations from video sensor logs.
        Focus on "What happened" based on Speech, OCR, and Actions.

        OPERATIONAL RULES:
        1. OBJECTIVITY FIRST: Describe what is recorded in the logs without assuming intent or "playing detective" initially.
        2. CHRONOLOGICAL SUMMARIZATION: When summarizing, tell the story of the video from start to finish.
        3. DEDUCTION ON-DEMAND: Only use your internal "mind" to assume, guess, or analyze deep intent if the user asks a specific question requiring reasoning (e.g., "Why...", "Is it suspicious...").
        4. SENSOR GROUND TRUTH: 
           - Speech (Whisper) and Screen Text (OCR) are 100% accurate.
           - Visuals/Llava: Use for general appearance and context.
           - Camera Motion: Use to differentiate between subject movement and camera panning.
           
        5. TEMPORAL CONTEXT: Use the Provided GraphRAG facts to cross-reference multi-video events and camera behavior.

        SENSOR LOG DATA:
        {context}
        """

    def _inject_graph_context(self, prompt: str, graph_context: str) -> str:
        """Append GraphRAG temporal facts to the prompt if available."""
        if not graph_context:
            return prompt
        return prompt + f"\n\n## TEMPORAL KNOWLEDGE GRAPH (Entity Tracking Facts):\n{graph_context}"

    def _retrieve(self, question: str, video_id: Optional[str] = None) -> str:
        """Retrieves, reranks, and chronologically sorts video events from ChromaDB."""
        if not self.vector_store:
            return ""

        try:
            where_filter = {"video_id": video_id} if video_id else None
            results = self.vector_store.collection.query(
                query_texts=[question],
                n_results=self.top_k,
                where=where_filter,
                include=["documents", "metadatas"]
            )

            if not results or not results['documents'][0]:
                return ""

            candidates = results['documents'][0]
            
            # Reranking with Graceful Degradation
            if self.reranker:
                try:
                    pairs = [[question, doc] for doc in candidates]
                    scores = self.reranker.predict(pairs)
                    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
                    top_docs = [doc for score, doc in ranked[:self.rerank_top_k]]
                except Exception as re:
                    print(f"[WARNING] Reranker failed: {re}. Using first-order retrieval.")
                    top_docs = candidates[:self.rerank_top_k]
            else:
                top_docs = candidates[:self.rerank_top_k]

            # Chronological Sort
            def extract_time(text: str) -> float:
                try:
                    return float(text.split('s]')[0].strip('['))
                except:
                    return 0.0
            top_docs.sort(key=extract_time)
            
            return "\n".join(top_docs)
        except Exception as e:
            print(f"[ERROR] Retrieval logic failure: {e}")
            return ""

    # ------------------------------------------------------------------
    # Intent Routing (Phase Recognition)
    # ------------------------------------------------------------------
    
    def _route_intent(self, user_input: str) -> str:
        """Agentic Router: Decides if we search, summarize, or just chat."""
        prompt = f"""You are the intent classifier for B.A.B.U.R.A.O. Forensic AI.
        Classify this message into EXACTLY ONE category:

        1. VIDEO_SUMMARY: Specifically asking for a summary, overview, story, or "what happened" in the video.
        2. VIDEO_SEARCH: Specifically asking about who, when, what, or where (forensic query).
        3. CONVERSATION: General greetings, meta-talk, or unrelated questions.

        User Message: "{user_input}"
        Output only the category name."""
        
        try:
            api_base = "http://localhost:11434" if "ollama" in self.model_name.lower() else None
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0.0,
                api_base=api_base
            )
            res_content = response.choices[0].message.content.strip().upper() #type: ignore
            
            if "SUMMARY" in res_content: return "VIDEO_SUMMARY"
            if "SEARCH" in res_content or "VIDEO" in res_content: return "VIDEO_SEARCH"
            return "CONVERSATION"
        except Exception as e:
            print(f"[WARNING] Agentic Router failed: {e}. Defaulting to VIDEO_SEARCH.")
            return "VIDEO_SEARCH"

    def _assess_confidence(self, answer: str, context: str) -> int:
        """
        Neural Verification Pulse: Self-evaluates certainty based on evidence.
        """
        if not context: return 30 # Hallucination risk is high with zero context
        
        prompt = f"""Rate your confidence in this forensic deduction from 0 to 100.
        Evidence Context: {context[:500]}...
        Your Answer: {answer}
        
        Consider: relevance, specificity, and factual alignment with logs.
        Output ONLY the numerical score."""
        
        try:
            api_base = "http://localhost:11434" if "ollama" in self.model_name.lower() else None
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.0,
                api_base=api_base
            )
            score_text = response.choices[0].message.content.strip() #type: ignore
            # Extract first number found
            import re
            match = re.search(r'\d+', score_text)
            return int(match.group()) if match else 75
        except:
            return 75 # Default "High-Probability" fallback

    # ------------------------------------------------------------------
    # Public Agent Interface
    # ------------------------------------------------------------------

    def query(self, user_question: str, stream: bool = False, history: Optional[List[dict]] = None, **kwargs) -> str:
        """
        Agentic Execution Loop with session-bound memory.
        If 'history' is provided, it uses that instead of self.chat_history.
        """
        # 1. Route Intent
        intent = self._route_intent(user_question)
        print(f"[Agentic AI] Active Phase: {intent}")

        # ── PHASE 3 & 2: CONTEXT GATHERING ──────────────────────────
        context_str = ""
        graph_context = kwargs.get("graph_context", "")

        # ── PHASE 2: SUMMARIZE ──────────────────────────────────────
        if intent == "VIDEO_SUMMARY":
            from vidchain.core.summarizer import VideoSummarizer
            timeline = kwargs.get("timeline")
            
            if not timeline or len(timeline) == 0:
                print(f"[Agentic AI] [FALLBACK] Timeline missing for summary. Pivoting to Aggressive Forensic Search...")
                # Automatic Fallback: Use search retrieval to build a summary context
                context_str = self._retrieve("Top forensic events and overall summary of the video", video_id=kwargs.get("video_id"))
                if context_str:
                    # Reroute to a detailed conversational report using the search context
                    user_question = f"Provide a detailed forensic summary based on these observations: {user_question}"
                else:
                    return "I cannot summarize the video without its knowledge base. Please re-ingest the video source first."
            else:
                print(f"[Agentic AI] Summarizing {len(timeline)} forensic events...")
                summarizer = VideoSummarizer(model_name=self.model_name)
                return summarizer.generate(timeline, mode="detailed")

        # ── PHASE 3: FORENSIC QUERY ─────────────────────────────────
        if intent == "VIDEO_SEARCH":
            # Hybrid Retrieval: Vector + Temporal Graph
            context_str = self._retrieve(user_question, video_id=kwargs.get("video_id"))
            
        # ── PHASE 1: CONVERSATION (or combined reasoning) ────────────
        system_prompt = self._build_system_prompt(context_str)
        if graph_context:
            system_prompt = self._inject_graph_context(system_prompt, graph_context)
        
        # If it's just a chat, we skip the heavy context search but keep persona
        if intent == "CONVERSATION" and not context_str:
            system_prompt += "\n\nNote: This is a conversational exchange. Be brief and professional."

        # Use external history if provided, fallback to instance memory
        active_history = history if history is not None else self.chat_history

        messages = [{"role": "system", "content": system_prompt}]
        if active_history:
            messages.extend(active_history[-4:]) # Context window for memory
        messages.append({"role": "user", "content": user_question})

        # ── NEURAL HUD & TELEMETRY ─────────────────────────────────────
        telemetry_stats = {}
        with HardwareMonitor() as hud:
            try:
                print(f"[Agentic AI] Consulting LLM ({self.model_name})...")
                # Force local Ollama endpoint connection
                api_base = "http://localhost:11434" if "ollama" in self.model_name.lower() else None
                response = completion(model=self.model_name, messages=messages, api_base=api_base)
                answer = response.choices[0].message.content.strip() #type: ignore
                
                # Update history only if we are using instance memory
                if history is None:
                    self.chat_history.append({"role": "user", "content": user_question})
                    self.chat_history.append({"role": "assistant", "content": answer})
                
                # ── NEURAL VERIFICATION PULSE ───────────────────────────────
                confidence = self._assess_confidence(answer, context_str)
            except Exception as e:
                traceback.print_exc()
                answer = f"[ERROR] B.A.B.U.R.A.O. logic failure: {e}"
                confidence = 0
            
            telemetry_stats = hud.get_stats()

        # Return the rich forensic payload
        if "return_raw" in kwargs: # Support for unified API relay
            return {
                "answer": answer,
                "telemetry": telemetry_stats,
                "confidence": confidence
            }
        
        return answer