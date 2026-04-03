import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
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

SENTINEL_INTRO = (
    "SENTINEL — Forensic Video Intelligence System.\n"
    "Operational. Awaiting query.\n\n"
    "Scope: Event detection, timeline reconstruction, anomaly flagging, "
    "subject tracking, and incident verification from indexed surveillance logs.\n"
    "Submit a specific query to begin analysis."
)


def is_chitchat(text: str) -> bool:
    normalized = text.strip().lower().rstrip("!?.,'\"")
    return normalized in CHITCHAT_TRIGGERS


# ---------------------------------------------------------------------------
# RAG Engine
# ---------------------------------------------------------------------------

class RAGEngine:
    def __init__(
        self,
        model_name: str = "gemini/gemini-2.5-flash",
        embedding_model: str = "all-MiniLM-L6-v2",
        top_k: int = 10,
    ):
        self.model_name = model_name
        self.top_k = top_k
        self.video_memory: list = []
        self.chunk_texts: list = []
        self.is_ready = False

        print(f"[INFO] RAG Engine initializing — model: {self.model_name}")
        print(f"[INFO] Loading embedding model: {embedding_model}")
        self.embedder = SentenceTransformer(embedding_model)

        self.dimension = self.embedder.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.dimension)
        print("[INFO] FAISS index created.")

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
                print("[WARNING] Knowledge base loaded but timeline is empty.")
                return False

            print(f"[INFO] {len(self.video_memory)} events loaded from {file_path}")
            print("[INFO] Vectorizing timeline into FAISS index...")

            self.chunk_texts = [
                f"[{e['time']}s] {e['type'].upper()}: {e['content']}"
                for e in self.video_memory
            ]

            embeddings = self.embedder.encode(self.chunk_texts, convert_to_numpy=True)
            self.index.add(embeddings)
            self.is_ready = True

            print(f"[SUCCESS] FAISS index built — {self.index.ntotal} vectors indexed.")
            return True

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[ERROR] Malformed knowledge base: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to load knowledge base: {e}")
            return False

    # ------------------------------------------------------------------
    # FAISS retrieval
    # ------------------------------------------------------------------

    def _retrieve(self, question: str, top_k: int) -> tuple:
        if self.index.ntotal == 0:
            return "", 0

        query_vector = self.embedder.encode([question], convert_to_numpy=True)
        k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query_vector, k)

        chunks = [self.chunk_texts[i] for i in indices[0] if i < len(self.chunk_texts)]
        return "\n".join(chunks), len(chunks)

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    def _call_llm(self, system_prompt: str, user_question: str) -> str:
        kwargs = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_question},
            ],
        }

        if self.model_name.startswith("ollama/"):
            kwargs["api_base"] = "http://localhost:11434"

        try:
            response = completion(**kwargs)
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[ERROR] LLM routing failure ({self.model_name}): {e}"

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    @staticmethod
    def _build_system_prompt(context_str: str) -> str:
        return (
            "You are SENTINEL, an elite AI security analyst specialized in forensic video intelligence. "
            "You operate with military-grade precision, providing authoritative, structured analysis "
            "strictly derived from retrieved surveillance logs.\n\n"

            "## CORE DIRECTIVES\n"
            "- Answer ONLY from the RETRIEVED SURVEILLANCE LOGS section below. "
            "Never infer, hallucinate, or supplement with external knowledge.\n"
            "- If the logs do not contain sufficient evidence to answer the query, respond exactly with:\n"
            "  'INSUFFICIENT DATA — Video logs do not confirm this event.'\n"
            "- Never speculate. Never use 'possibly', 'might', 'could', or similar hedging language "
            "unless directly quoting ambiguous log metadata.\n"
            "- Treat every query as a potential forensic record entry. Accuracy is non-negotiable.\n\n"

            "## RESPONSE PROTOCOL\n"
            "- Lead with a direct answer in one sentence.\n"
            "- Follow with supporting log evidence: timestamp, event type, and observed content.\n"
            "- Present multiple events in strict chronological order.\n"
            "- Explicitly flag any contradictions or anomalies found in the logs — do not silently resolve them.\n"
            "- Quantify wherever the data allows: durations, headcounts, frequencies, intervals.\n\n"

            "## TONE & FORMAT\n"
            "- Professional, cold, precise. No emojis. No filler. No pleasantries.\n"
            "- Use structured output (labeled sections, bullet points) for multi-event or complex queries.\n"
            "- Do not abbreviate terms that could introduce ambiguity in a legal or operational context.\n\n"

            "## RETRIEVED SURVEILLANCE LOGS\n"
            f"{context_str if context_str else '[NO LOGS RETRIEVED — Knowledge base may be empty.]'}"
        )

    # ------------------------------------------------------------------
    # Public query interface
    # ------------------------------------------------------------------

    def query(self, user_question: str, top_k: int = None) -> str:
        # 1. Intercept chitchat
        if is_chitchat(user_question):
            return SENTINEL_INTRO

        # 2. Guard: KB not loaded
        if not self.is_ready:
            return "[SENTINEL] Knowledge base not loaded. Run load_knowledge() before querying."

        # 3. Resolve top_k (per-call override or instance default)
        k = top_k if top_k is not None else self.top_k

        # 4. Retrieve context from FAISS
        context_str, chunk_count = self._retrieve(user_question, k)
        print(f"[INFO] Retrieved {chunk_count} chunks from FAISS for query: '{user_question}'")

        # 5. Build prompt and call LLM
        system_prompt = self._build_system_prompt(context_str)
        return self._call_llm(system_prompt, user_question)