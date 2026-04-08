import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from chromadb.utils import embedding_functions

class ChromaStore:
    """
    Persistent Vector Storage for VidChain.
    Allows developers to manage video embeddings on the hard drive.
    """
    def __init__(self, persist_dir: str = "./vidchain_db", collection_name: str = "video_events"):
        self.persist_dir = persist_dir
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        
        # Use a standard local embedding function to avoid SSL timeouts
        # This uses the SentenceTransformer you likely already have cached
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-base-en-v1.5"
        )
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name, 
            embedding_function=self.emb_fn # type: ignore
        )

    def add_events(self, video_id: str, documents: List[str], metadatas: List[Dict[str, Any]]):
        """
        Inserts vectorized video events into the store.
        'documents' are the serialized strings (e.g., "[10s] Action: Walking")
        'metadatas' are the raw dictionaries for filtering.
        """
        # Create unique IDs for every event chunk
        ids = [f"{video_id}_{i}" for i in range(len(documents))]
        
        # Add the video_id to every metadata entry for easier filtering later
        for m in metadatas:
            m["video_id"] = video_id

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        print(f"[VectorStore] Successfully indexed {len(documents)} events for {video_id}.")

    def search(self, query_text: str, n_results: int = 10, video_id: Optional[str] = None):
        """
        Perform a similarity search.
        If video_id is provided, it only searches inside that specific video.
        """
        where_filter = {"video_id": video_id} if video_id else None
        
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_filter
        )
        return results

    # --- Developer Management Tools ---

    def list_videos(self) -> List[str]:
        """Returns a list of all unique video IDs in the store."""
        # Chroma doesn't have a direct 'unique' call, so we fetch metadatas
        data = self.collection.get(include=['metadatas'])
        return list(set([m['video_id'] for m in data['metadatas']]))

    def delete_video(self, video_id: str):
        """Purge a specific video's data."""
        self.collection.delete(where={"video_id": video_id})
        print(f"[VectorStore] Deleted all records for {video_id}.")

    def get_count(self) -> int:
        """Returns total number of events indexed."""
        return self.collection.count()
    
    def get_video_context(self, video_id: str) -> list[dict]:
        """Fetches all indexed events for a specific video."""
        results = self.collection.get(
            where={"video_id": video_id},
            include=["metadatas", "documents"]
        )
        return results["metadatas"] if results["metadatas"] else []

    def insert_video(self, video_id: str, chunk_texts: list[str], metadata: list[dict]):
        """
        Titan Upgrade: Fuses and saves the multimodal timeline 
        permanently to ChromaDB.
        """
        print(f"[VectorStore] Indexing {len(chunk_texts)} fused events for ID: {video_id}")
        
        # --- SANITIZATION LOOP ---
        sanitized_metadata = []
        for m in metadata:
            entry = m.copy()
            entry["video_id"] = video_id
            
            # ChromaDB Fix: Convert empty lists/objects to strings or None
            for key, value in entry.items():
                if isinstance(value, list) and not value:
                    entry[key] = "none"  # Convert [] to "none"
                elif value is None:
                    entry[key] = "n/a"
            sanitized_metadata.append(entry)
        # --------------------------

        ids = [f"{video_id}_{i}" for i in range(len(chunk_texts))]
        
        self.collection.add(
            ids=ids,
            documents=chunk_texts,
            metadatas=sanitized_metadata # Use the sanitized version here
        )
        print(f"[VectorStore] Permanent storage sync complete.")