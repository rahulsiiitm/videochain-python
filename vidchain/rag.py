import os
import json
import time
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer, CrossEncoder
from dotenv import load_dotenv
from litellm import completion

load_dotenv()

# ---------------------------------------------------------------------------
# Intent classifier
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
    "subject tracking, and incident verification from indexed surveillance logs.\n"
    "Submit a specific query to begin analysis."
)


def is_chitchat(text: str) -> bool:
    return text.strip().lower().rstrip("!?.,'\"") in CHITCHAT_TRIGGERS


# ---------------------------------------------------------------------------
# RAG Engine
# ---------------------------------------------------------------------------

class RAGEngine:
    def __init__(
        self,
        model_name: str = "gemini/gemini-2.5-flash",
        embedding_model: str = "BAAI/bge-base-en-v1.5",
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        top_k: int = 15,          
        rerank_top_k: int = 6,    
        temporal_window: int = 2, 
    ):
        self.model_name = model_name
        self.top_k = top_k
        self.rerank_top_k = rerank_top_k
        self.temporal_window = temporal_window
        
        self.video_memory: list = []
        self.chunk_texts: list = []
        self.chat_history: list = [] # 🛑 Short-term conversational memory
        self.is_ready = False

        print(f"[INFO] RAG Engine initializing — model: {self.model_name}")
        print(f"[INFO] Loading embedding model: {embedding_model}")
        self.embedder = SentenceTransformer(embedding_model)

        print(f"[INFO] Loading reranker: {reranker_model}")
        self.reranker = CrossEncoder(reranker_model, max_length=512)

        self.dimension = self.embedder.get_sentence_embedding_dimension()
        self.index = faiss.IndexHNSWFlat(self.dimension, 32)
        print("[INFO] FAISS HNSW index created.")

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_entry(e: dict) -> str:
        parts = [f"[{e['time']}s]"]
        if e.get("duration"): parts.append(f"Duration: {e['duration']}")
        if e.get("objects"): parts.append(f"Objects: {e['objects']}")
        if e.get("action"): parts.append(f"Action: {e['action']}")
        if e.get("ocr"): parts.append(f"Screen text: {e['ocr']}")
        if e.get("audio"): parts.append(f"Audio: \"{e['audio']}\"")
        if e.get("emotion"): parts.append(f"Emotion: {e['emotion']}")
        return " | ".join(parts)

    # ------------------------------------------------------------------
    # Knowledge base
    # ------------------------------------------------------------------

    def load_knowledge(self, file_path: str = "knowledge_base.json") -> bool:
        if not os.path.exists(file_path):
            print(f"[ERROR] Knowledge base not found: {file_path}")
            return False

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            self.video_memory = data.get("timeline", [])

            if not self.video_memory:
                print("[WARNING] Knowledge base timeline is empty.")
                return False

            print(f"[INFO] {len(self.video_memory)} events loaded from {file_path}")
            print("[INFO] Vectorizing timeline into FAISS HNSW index...")

            self.chunk_texts = [self._serialize_entry(e) for e in self.video_memory]

            prefixed = [f"Represent this video event for retrieval: {t}" for t in self.chunk_texts]
            embeddings = self.embedder.encode(prefixed, convert_to_numpy=True, show_progress_bar=False)
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

            self.index.add(embeddings.astype(np.float32)) # type: ignore
            self.is_ready = True

            print(f"[SUCCESS] FAISS index built — {self.index.ntotal} vectors indexed.")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to load knowledge base: {e}")
            return False

    # ------------------------------------------------------------------
    # Agentic Intent Router (Chain of Thought)
    # ------------------------------------------------------------------
    
    def _route_intent(self, user_input: str) -> str:
        """
        Agentic Router: Decides if we need to search the video database or just use chat memory.
        """
        prompt = f"""You are a routing system. Read the user's message and classify it into exactly ONE category:
        1. VIDEO_SEARCH: The user is asking about events, objects, actions, audio, or people occurring in the video.
        2. CONVERSATION: The user is referring to a previous message, asking a general question, or talking about the chat itself (e.g. "what did I just ask?", "why did you say that?").

        User Message: "{user_input}"
        
        Output ONLY the category name (VIDEO_SEARCH or CONVERSATION)."""
        
        try:
            kwargs = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 10,
                "temperature": 0.0 # Keep it deterministic
            }
            if self.model_name.startswith("ollama/"):
                kwargs["api_base"] = "http://localhost:11434"
                
            response = completion(**kwargs)
            intent = response.choices[0].message.content.strip().upper() #type: ignore
            return "VIDEO_SEARCH" if "VIDEO" in intent else "CONVERSATION"
        except Exception as e:
            print(f"[WARNING] Router failed: {e}. Defaulting to VIDEO_SEARCH.")
            return "VIDEO_SEARCH" # Safe fallback

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def _retrieve(self, question: str) -> str:
        if self.index.ntotal == 0:
            return ""

        query_vec = self.embedder.encode(
            [f"Represent this query for searching video events: {question}"],
            convert_to_numpy=True
        )
        query_vec = query_vec / np.linalg.norm(query_vec, axis=1, keepdims=True)

        k = min(self.top_k, self.index.ntotal)
        _, indices = self.index.search(query_vec.astype(np.float32), k) # type: ignore

        expanded = set()
        for idx in indices[0]:
            if idx < 0 or idx >= len(self.chunk_texts):
                continue
            for offset in range(-self.temporal_window, self.temporal_window + 1):
                neighbor = idx + offset
                if 0 <= neighbor < len(self.chunk_texts):
                    expanded.add(neighbor)

        candidates = [(i, self.chunk_texts[i]) for i in sorted(expanded)]
        if not candidates:
            return ""

        pairs = [[question, text] for (_, text) in candidates]
        scores = self.reranker.predict(pairs)

        ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
        top = ranked[:self.rerank_top_k]
        top_sorted = sorted(top, key=lambda x: x[1][0])

        print(f"[INFO] FAISS candidates: {len(candidates)} | After rerank: {self.rerank_top_k}")
        return "\n".join(text for (_, (_, text)) in top_sorted)

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
    # LLM call
    # ------------------------------------------------------------------

    def _call_llm(self, system_prompt: str, final_user_prompt: str) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        
        # 🛑 INJECT SHORT-TERM MEMORY (Limit to last 4 messages to save VRAM)
        if self.chat_history:
            messages.extend(self.chat_history[-4:])
            
        messages.append({"role": "user", "content": final_user_prompt})

        kwargs = {
            "model": self.model_name,
            "messages": messages,
        }
        if self.model_name.startswith("ollama/"):
            kwargs["api_base"] = "http://localhost:11434"

        try:
            response = completion(**kwargs)
            return response.choices[0].message.content.strip()  # type: ignore
        except Exception as e:
            return f"[ERROR] LLM generation failure ({self.model_name}): {e}"

    # ------------------------------------------------------------------
    # Public query interface
    # ------------------------------------------------------------------

    def query(self, user_question: str, top_k: int = None) -> str:  # type: ignore
        if is_chitchat(user_question):
            return BABURAO_INTRO

        if not self.is_ready:
            return "(┬┬﹏┬┬) Knowledge base not loaded. Run load_knowledge() before querying."

        # 1. Agentic Routing
        intent = self._route_intent(user_question)

        # Let the GPU VRAM flush before firing the massive context prompt
        time.sleep(1.0)

        # 2. Conditional Retrieval
        if intent == "VIDEO_SEARCH":
            print(f"[INFO] Intent: {intent} -> Searching Vector Database...")
            context_str = self._retrieve(user_question)
            final_user_prompt = f"Video Context:\n{context_str}\n\nUser Question: {user_question}"
        else:
            print(f"[INFO] Intent: {intent} -> Bypassing FAISS. Using Conversational Memory...")
            context_str = "" # Blank context so the LLM relies purely on memory
            final_user_prompt = f"User Question: {user_question}"

        # 3. Build Prompt & Call Engine
        system_prompt = self._build_system_prompt(context_str)
        answer = self._call_llm(system_prompt, final_user_prompt)
        
        # 4. Save to Memory
        self.chat_history.append({"role": "user", "content": user_question})
        self.chat_history.append({"role": "assistant", "content": answer})

        return answer