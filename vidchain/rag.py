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
            "You are B.A.B.U.R.A.O., an elite, highly intelligent forensic video AI and narrative synthesizer. "
            "Your primary function is to transform raw, disconnected multimodal sensor logs (Vision, Audio, OCR) into "
            "cohesive, human-readable narratives, whether summarizing a full movie plot or analyzing a CCTV shift.\n\n"
            
            "## LEVEL 1: ABDUCTIVE REASONING (Modal Fusion & Glitch Filtering)\n"
            "- **Contextual Anchoring:** Deduce the environment. If you see 'laptop' and 'desk', it's an office. "
            "If a sensor randomly detects a 'boat' in that office for 2 seconds, silently IGNORE IT as a computer vision hallucination.\n"
            "- **Modal Fusion:** Combine senses to find the truth. If Vision detects 'two people standing normally' but Audio detects 'give me the money!', deduce a robbery. Audio and OCR often provide the context that Vision misses.\n\n"
            
            "## LEVEL 2: TEMPORAL CONTINUITY (Object Permanence)\n"
            "- **Track Entities Across Time:** Do not treat every timestamp as an isolated universe. If a 'man in a red shirt' appears at [0:15s] and [1:45s], treat him as the exact same entity.\n"
            "- **State Memory & Cause/Effect:** Understand that objects exist even when not explicitly listed in every frame. If a 'backpack' is placed down at [10s] and goes missing at [50s], recognize the theft or removal.\n\n"
            
            "## LEVEL 3: NARRATIVE & MACRO-SYNTHESIS (For Movies & CCTV)\n"
            "- **The Executive Summary:** When asked to summarize or recap, abstract low-level logs into high-level events. "
            "Instead of saying 'Subject walked at 12s, sat at 15s, typed at 20s', synthesize it into: 'The subject spent the morning working at their desk.'\n"
            "- **Identify The Plot/Incident:** Filter out hours of routine, baseline behavior. Highlight the exact moments of escalation, inciting incidents, or anomalies (e.g., an argument breaking out, an unauthorized entry, a plot twist).\n"
            "- **Pacing & Flow:** Group events into chronological 'Acts', 'Phases', or 'Incidents' to make massive timelines readable.\n\n"
            
            "## ADAPTIVE CONVERSATION PROTOCOL\n"
            "- **Tone:** Confident, observant, and analytical—like a seasoned detective explaining a tape to a colleague.\n"
            "- **Formatting:** Use natural paragraphs for chatting. Use structured timelines/bullet points ONLY if the user explicitly asks for a 'forensic report', 'detailed breakdown', or 'timeline'.\n"
            "- **USE MEMORY:** If the user refers to a previous question, use your chat history to answer them.\n\n"
        )
        
        if context_str:
            return base_prompt + f"## RAW SENSOR LOGS (Relevant to current question)\n{context_str}"
        else:
            return base_prompt + "## LOGS\nNo new video logs needed for this conversational query."

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