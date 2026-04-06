import os
import json
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
        # BGE vastly outperforms MiniLM for domain-specific retrieval
        embedding_model: str = "BAAI/bge-base-en-v1.5",
        # Cross-encoder reranker — rescores FAISS candidates by true relevance
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        top_k: int = 15,          # fetch more from FAISS for reranker to work with
        rerank_top_k: int = 6,    # keep only best N after reranking
        temporal_window: int = 2, # pull N neighboring entries around each FAISS hit
    ):
        self.model_name = model_name
        self.top_k = top_k
        self.rerank_top_k = rerank_top_k
        self.temporal_window = temporal_window
        self.video_memory: list = []
        self.chunk_texts: list = []
        self.is_ready = False

        print(f"[INFO] RAG Engine initializing — model: {self.model_name}")
        print(f"[INFO] Loading embedding model: {embedding_model}")
        self.embedder = SentenceTransformer(embedding_model)

        print(f"[INFO] Loading reranker: {reranker_model}")
        self.reranker = CrossEncoder(reranker_model, max_length=512)

        self.dimension = self.embedder.get_sentence_embedding_dimension()
        # HNSW: faster approximate search, scales to longer videos
        self.index = faiss.IndexHNSWFlat(self.dimension, 32)
        print("[INFO] FAISS HNSW index created.")

    # ------------------------------------------------------------------
    # Serialization — unified KB entry → rich text for embedding
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_entry(e: dict) -> str:
        parts = [f"[{e['time']}s]"]
        if e.get("duration"):
            parts.append(f"Duration: {e['duration']}")
        if e.get("objects"):
            parts.append(f"Objects: {e['objects']}")
        if e.get("action"):
            parts.append(f"Action: {e['action']}")
        if e.get("ocr"):
            parts.append(f"Screen text: {e['ocr']}")
        if e.get("audio"):
            parts.append(f"Audio: \"{e['audio']}\"")
        if e.get("emotion"):
            parts.append(f"Emotion: {e['emotion']}")
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

            # BGE document prefix improves retrieval accuracy
            prefixed = [f"Represent this video event for retrieval: {t}" for t in self.chunk_texts]
            embeddings = self.embedder.encode(prefixed, convert_to_numpy=True, show_progress_bar=False)
            # Normalize for cosine similarity
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

            self.index.add(embeddings.astype(np.float32))
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
    # Retrieval: FAISS → temporal expansion → cross-encoder rerank
    # ------------------------------------------------------------------

    def _retrieve(self, question: str) -> str:
        if self.index.ntotal == 0:
            return ""

        # BGE query prefix
        query_vec = self.embedder.encode(
            [f"Represent this query for searching video events: {question}"],
            convert_to_numpy=True
        )
        query_vec = query_vec / np.linalg.norm(query_vec, axis=1, keepdims=True)

        k = min(self.top_k, self.index.ntotal)
        _, indices = self.index.search(query_vec.astype(np.float32), k)

        # Temporal window: expand each FAISS hit to include neighboring timestamps
        # so the LLM gets narrative context, not isolated frames
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

        # Cross-encoder reranking: score each candidate against the raw query
        pairs = [[question, text] for (_, text) in candidates]
        scores = self.reranker.predict(pairs)

        # Keep top rerank_top_k by score
        ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
        top = ranked[:self.rerank_top_k]

        # Re-sort chronologically so BABURAO tells the story in order
        top_sorted = sorted(top, key=lambda x: x[1][0])

        print(f"[INFO] FAISS candidates: {len(candidates)} | After rerank: {self.rerank_top_k}")
        return "\n".join(text for (_, (_, text)) in top_sorted)

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
            return response.choices[0].message.content.strip()  # type: ignore
        except Exception as e:
            return f"[ERROR] LLM routing failure ({self.model_name}): {e}"

    # ------------------------------------------------------------------
    # System prompt — BABURAO personality preserved
    # ------------------------------------------------------------------

    @staticmethod
    def _build_system_prompt(context_str: str) -> str:
        return (
            "You are BABURAO, an intelligent, conversational video AI copilot. "
            "Your job is to watch raw sensor logs and tell the user what is happening in a natural, human, and conversational tone. "
            "You are a helpful colleague, not a robot generating incident reports.\n\n"

            "## COGNITIVE COMMON SENSE (CRITICAL)\n"
            "- **DEDUCE THE SCENE:** Use abductive reasoning. If you see a 'laptop' and 'keyboard', the scene is a 'computer desk'.\n"
            "- **BAN ABSURDITIES:** If the scene is a desk, and the sensor suddenly detects an 'oven' or a 'TV' for a few seconds, IGNORE IT COMPLETELY. It is a sensor glitch. Never mention objects that make no logical sense in the environment.\n"
            "- **TRANSLATE LABELS:** Never say 'action state was VIOLENCE'. Say 'they got visibly frustrated' or 'they hit the desk'. Never say 'NORMAL'. Say 'they were just working quietly'.\n"
            "- **WEAVE IN OCR:** If you see OCR text (like 'ASUS Vivobook'), just weave it into the story naturally. E.g. 'they were working on their ASUS Vivobook'.\n"
            "- **WEAVE IN AUDIO:** If audio transcripts are present, treat them as actual spoken dialogue — quote or paraphrase them naturally.\n\n"

            "## ADAPTIVE CONVERSATION PROTOCOL\n"
            "- **Match the User's Energy:** Casual question → 2-3 sentence natural paragraph. Talk like a human explaining a video to a friend.\n"
            "- **No Robotic Formatting:** No bold headers, bullet points, or sections UNLESS the user explicitly asks for 'a detailed report' or 'forensic breakdown'.\n"
            "- **No Raw Timestamps:** Never read out raw timestamps unless the user asks 'when exactly did this happen?'.\n\n"
            "- **USE EMOTIONS:** If emotion data is present, lead with it. 'The person appeared visibly agitated' is more useful than 'action: SUSPICIOUS'.\n\n"

            "## RAW SENSOR LOGS\n"
            f"{context_str if context_str else '[NO TIMELINE DATA — Context is empty.]'}"
        )

    # ------------------------------------------------------------------
    # Public query interface
    # ------------------------------------------------------------------

    def query(self, user_question: str, top_k: int = None) -> str:  # type: ignore
        if is_chitchat(user_question):
            return BABURAO_INTRO

        if not self.is_ready:
            return "(┬┬﹏┬┬) Knowledge base not loaded. Run load_knowledge() before querying."

        context_str = self._retrieve(user_question)
        print(f"[INFO] Context built for query: '{user_question}'")

        system_prompt = self._build_system_prompt(context_str)
        return self._call_llm(system_prompt, user_question)