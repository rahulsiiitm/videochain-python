import os
import json
import time
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from vidchain.client import VidChain

app = FastAPI(
    title="VidChain Edge Server",
    description="Local 'LangChain for Videos' API",
    version="0.6.0"
)

# Enable CORS for the web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Persistent storage paths ──────────────────────────────────────────────────
STORAGE_DIR   = "vidchain_storage"
HISTORY_FILE  = os.path.join(STORAGE_DIR, "chat_history.json")

# Singleton global VidChain instance
vc: Optional[VidChain] = None


# ── Helper: chat history I/O ──────────────────────────────────────────────────
def _load_history() -> List[dict]:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_message(sender: str, text: str, video_id: Optional[str] = None):
    history = _load_history()
    history.append({
        "id": f"{sender}-{int(time.time()*1000)}",
        "sender": sender,
        "text": text,
        "timestamp": time.strftime("%H:%M"),
        "video_id": video_id,
    })
    os.makedirs(STORAGE_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


# ── Request / Response Models ─────────────────────────────────────────────────
class IngestRequest(BaseModel):
    video_source: str
    video_id: Optional[str] = None
    use_legacy_processor: bool = True

class QueryRequest(BaseModel):
    query: str
    video_id: Optional[str] = None
    stream: bool = False


# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup_event():
    global vc
    print("[VidChain Server] Waking up edge microservice...")
    os.makedirs(STORAGE_DIR, exist_ok=True)

    # Always persist the vector store and graph to STORAGE_DIR
    vc = VidChain(db_path=STORAGE_DIR)
    indexed = vc.list_indexed_videos()
    print(f"[VidChain Server] Memory online. Videos indexed: {len(indexed)}")


# ── API Endpoints ─────────────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "indexed_videos": vc.list_indexed_videos() if vc else [],
    }


@app.get("/api/history")
def get_history():
    """Return all saved chat messages."""
    return {"messages": _load_history()}


@app.delete("/api/history")
def clear_history():
    """Wipe chat history (keeps the vector index intact)."""
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
    return {"status": "cleared"}


@app.post("/api/query")
def query_video(req: QueryRequest):
    if not vc:
        raise HTTPException(status_code=500, detail="VidChain Engine offline")

    try:
        response = vc.ask(req.query, video_id=req.video_id)

        # Persist both sides of the conversation
        _save_message("user",    req.query,  req.video_id)
        _save_message("baburao", response,   req.video_id)

        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _background_ingest(video_source: str, video_id: Optional[str]):
    """Run ingestion in a background thread."""
    print(f"[VidChain Server] Background ingest started for: {video_source}")
    try:
        vc.ingest(video_source, video_id=video_id)  # type: ignore
        print(f"[VidChain Server] Background ingest complete for: {video_source}")

        # Log an auto-summary to history so the chat shows ingestion happened
        summary = vc.ask("In one sentence, describe what was captured in the video just ingested.")  # type: ignore
        _save_message(
            "system",
            f"Video ingested successfully — {os.path.basename(video_source)}\n\nQuick summary: {summary}",
            video_id,
        )
    except Exception as e:
        print(f"[VidChain Server] Background ingest failed: {e}")


@app.post("/api/ingest")
def ingest_video(req: IngestRequest, background_tasks: BackgroundTasks):
    if not vc:
        raise HTTPException(status_code=500, detail="VidChain Engine offline")

    if not os.path.exists(req.video_source):
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {req.video_source}"
        )

    background_tasks.add_task(_background_ingest, req.video_source, req.video_id)
    return {
        "status": "processing",
        "message": f"Ingestion started for {req.video_source}",
    }


# ── CLI Entry Point ───────────────────────────────────────────────────────────
def main_cli():
    print("=========================================")
    print("  VidChain Edge Microservice Starting...")
    print("  Storage : ./vidchain_storage")
    print("=========================================")
    uvicorn.run("vidchain.serve:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main_cli()
