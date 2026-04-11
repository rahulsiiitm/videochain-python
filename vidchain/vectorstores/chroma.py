import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional


class ChromaStore:
    def __init__(self, persist_dir: Optional[str] = None, collection_name: str = "video_index"):
        """
        If persist_dir is None, Chroma runs in Ephemeral (In-Memory) mode.
        If a path is provided, it becomes a persistent database.
        """
        if persist_dir:
            self.client = chromadb.PersistentClient(path=persist_dir)
            self.is_persistent = True
        else:
            self.client = chromadb.EphemeralClient()
            self.is_persistent = False

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="BAAI/bge-base-en-v1.5"
            )
        )

    def _sanitize_metadata(self, video_id: str, metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Returns a sanitized copy of metadata safe for ChromaDB:
        - Injects video_id
        - Converts None and empty lists to safe scalar values
        - Converts non-empty lists to comma-joined strings
        """
        sanitized = []
        for m in metadata:
            entry = m.copy()
            entry["video_id"] = video_id
            for key, value in entry.items():
                if value is None:
                    entry[key] = "n/a"
                elif isinstance(value, list):
                    entry[key] = ", ".join(str(v) for v in value) if value else "none"
            sanitized.append(entry)
        return sanitized

    def add_events(self, video_id: str, documents: List[str], metadatas: List[Dict[str, Any]]):
        """
        Inserts vectorized video events into the store.
        'documents' are the serialized strings (e.g., "[10s] Action: Walking")
        'metadatas' are the raw dictionaries for filtering.
        """
        ids = [f"{video_id}_{i}" for i in range(len(documents))]
        sanitized = self._sanitize_metadata(video_id, metadatas)

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=sanitized
        )
        print(f"[VectorStore] Successfully indexed {len(documents)} events for {video_id}.")

    def insert_video(self, video_id: str, chunk_texts: List[str], metadata: List[Dict[str, Any]]):
        """
        Fuses and saves the multimodal timeline to ChromaDB.
        Alias for add_events with consistent sanitization.
        """
        print(f"[VectorStore] Indexing {len(chunk_texts)} fused events for ID: {video_id}")
        self.add_events(video_id, chunk_texts, metadata)
        print(f"[VectorStore] Permanent storage sync complete.")

    def search(
        self,
        query_text: str,
        n_results: int = 10,
        video_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform a similarity search.
        If video_id is provided, it only searches inside that specific video.
        Clamps n_results to the collection size to avoid ChromaDB errors.
        """
        where_filter = {"video_id": video_id} if video_id else None
        n_results = min(n_results, self.collection.count()) or 1

        return self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_filter
        )

    def list_videos(self) -> List[str]:
        """Fetches all unique video_id values from metadata."""
        results = self.collection.get(include=["metadatas"])
        if not results["metadatas"]:
            return []
        return list(set(m["video_id"] for m in results["metadatas"]))

    def delete_video(self, video_id: str):
        """Purge a specific video's data."""
        self.collection.delete(where={"video_id": video_id})
        print(f"[VectorStore] Deleted all records for {video_id}.")

    def get_count(self) -> int:
        """Returns total number of events indexed."""
        return self.collection.count()

    def get_video_context(self, video_id: str) -> List[str]:
        """Fetches the serialized text for a specific video to build LLM prompts."""
        results = self.collection.get(
            where={"video_id": video_id},
            include=["documents"]
        )
        return results["documents"] if results["documents"] else []