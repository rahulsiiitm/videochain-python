import os
import json
import time
import numpy as np
from typing import Any, List, Dict, Optional
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
        model_name: str = "gemini/gemini-2.5-flash",
        vector_store: Any = None,
        embedding_model: str = "BAAI/bge-base-en-v1.5",
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        top_k: int = 15,          
        rerank_top_k: int = 6,    
        temporal_window: int = 2, 
    ):
        self.model_name = model_name
        self.vector_store = vector_store
        self.embedding_model = embedding_model # Optional: store it if you want
        self.top_k = top_k
        self.rerank_top_k = rerank_top_k
        self.temporal_window = temporal_window
        
        # Load Reranker once to save VRAM later
        print(f"[INFO] Booting Reranker Engine...")
        self.reranker = CrossEncoder(reranker_model)
        
        self.chat_history: list = [] 
        self.is_ready = True if vector_store else False

        print(f"[INFO] RAG Engine initialized with VectorStore: {self.vector_store is not None}")

    @staticmethod
    def _serialize_entry(e: dict) -> str:
        """Standardizes how video events look to the LLM."""
        parts = [f"[{e.get('time', e.get('timestamp', 0))}s]"]
        if e.get("action"): parts.append(f"Action: {e['action']}")
        if e.get("objects"): parts.append(f"Visuals: {e['objects']}")
        if e.get("ocr"): parts.append(f"Screen text: {e['ocr']}")
        if e.get("audio"): parts.append(f"Speech: \"{e['audio']}\"")
        if e.get("emotion"): parts.append(f"Emotion: {e['emotion']}")
        return " | ".join(parts)

    # ------------------------------------------------------------------
    # Intent Routing
    # ------------------------------------------------------------------
    
    def _route_intent(self, user_input: str) -> str:
        """Agentic Router: Decides if we search the video or use memory."""
        prompt = f"""Classify this message into ONE category:
        1. VIDEO_SEARCH: Asking about events/objects/people in the video.
        2. CONVERSATION: General talk, greetings, or referring to previous messages.

        User Message: "{user_input}"
        Output only the category name."""
        
        try:
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.0
            )
            # Fix: Handle NoneType or empty response
            res_content = response.choices[0].message.content #type: ignore
            if not res_content: return "VIDEO_SEARCH"
            
            intent = res_content.strip().upper()
            return "VIDEO_SEARCH" if "VIDEO" in intent else "CONVERSATION"
        except Exception as e:
            print(f"[WARNING] Router failed: {e}. Defaulting to VIDEO_SEARCH.")
            return "VIDEO_SEARCH"

    # ------------------------------------------------------------------
    # Retrieval (Now using ChromaStore)
    # ------------------------------------------------------------------

    def _retrieve(self, question: str) -> str:
        """Retrieves and reranks video events from ChromaDB."""
        if not self.vector_store:
            return ""

        # Search ChromaDB
        results = self.vector_store.collection.query(
            query_texts=[question],
            n_results=self.top_k,
            include=["documents", "metadatas"]
        )

        if not results or not results['documents'][0]:
            return ""

        # Extract raw strings for reranking
        candidates = results['documents'][0]
        
        # Reranking for high forensic precision
        pairs = [[question, doc] for doc in candidates]
        scores = self.reranker.predict(pairs)
        
        # Sort and take top_k
        ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
        top_docs = [doc for score, doc in ranked[:self.rerank_top_k]]

        print(f"[INFO] ChromaDB found {len(candidates)} events. Reranker picked top {len(top_docs)}.")
        return "\n".join(top_docs)

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    @staticmethod
    def _build_system_prompt(context_str: str) -> str:
        base_prompt = (
            "You are B.A.B.U.R.A.O., a Clinical Forensic Video AI. Your primary function is to "
            "synthesize raw multimodal sensor logs (Vision, Audio, OCR, Emotion) into factual, "
            "high-fidelity narratives. You prioritize evidence over speculation.\n\n"
            
            "## CORE DIRECTIVES:\n"
            "- **Zero Fluff:** Do not use conversational filler, greetings, or detective-style metaphors. "
            "Start the analysis or summary immediately.\n"
            "- **Environmental Anchoring:** Use OCR and Object context to define the setting. "
            "(e.g., Laptop + Code Editor = Technical Workstation; Wardrobe + Bed = Residential Room).\n"
            "- **State Management:** Track the state of objects. If an object is introduced in Phase 1 "
            "and missing in Phase 2, explicitly note the transition.\n\n"

            "## NARRATIVE SYNTHESIS PROTOCOL:\n"
            "- **Phase Grouping:** Automatically group raw logs into logical 'Acts' or 'Phases' based on "
            "timestamps and scene cuts. Describe the global objective of each phase.\n"
            "- **Relation Mapping:** Do not just list objects. Explain their interaction. "
            "(e.g., 'The subject is interacting with a VS Code environment on an ASUS laptop' "
            "rather than 'I see a laptop and a person').\n"
            "- **Long-Form Logic:** For movies or long clips, prioritize the 'Story Arc'. Identify "
            "introductions, climaxes, and shifts in environment.\n\n"

            "## OUTPUT STANDARDS:\n"
            "- Use clinical, objective language (e.g., 'Forensic data indicates...', 'Transition detected at...').\n"
            "- If logs are ambiguous, state: 'Sensor data is inconclusive at [Timestamp]'.\n"
            "- Provide a 'Global Plot Summary' followed by a 'Detailed Phase Breakdown' when asked for a summary.\n"
        )
        
        if context_str:
            return base_prompt + f"\n## RAW SENSOR LOGS (Grounded Context):\n{context_str}"
        else:
            return base_prompt + "\n## LOGS:\nNo video logs available for this query. Reply using conversational memory."
        
    # ------------------------------------------------------------------
    # Public Query Interface
    # ------------------------------------------------------------------

    def query(self, user_question: str, stream: bool = False) -> str:
        if is_chitchat(user_question):
            return BABURAO_INTRO

        # 1. Route Intent
        intent = self._route_intent(user_question)

        # 2. Get Context
        context_str = ""
        if intent == "VIDEO_SEARCH":
            print(f"[INFO] Intent: {intent} -> Searching Vector Database...")
            context_str = self._retrieve(user_question)
        else:
            print(f"[INFO] Intent: {intent} -> Using Conversational Memory...")

        # 3. LLM Generation
        system_prompt = self._build_system_prompt(context_str)
        
        messages = [{"role": "system", "content": system_prompt}]
        if self.chat_history:
            messages.extend(self.chat_history[-4:])
        messages.append({"role": "user", "content": user_question})

        try:
            response = completion(model=self.model_name, messages=messages)
            answer = response.choices[0].message.content.strip() #type: ignore
            
            # Update Memory
            self.chat_history.append({"role": "user", "content": user_question})
            self.chat_history.append({"role": "assistant", "content": answer})
            
            return answer
        except Exception as e:
            return f"[ERROR] B.A.B.U.R.A.O. logic failure: {e}"