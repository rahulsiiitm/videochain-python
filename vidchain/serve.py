import os
import json
import time
import uuid
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict

from fastapi.staticfiles import StaticFiles
from vidchain.client import VidChain

app = FastAPI(
    title="VidChain Edge Server",
    description="Local 'LangChain for Videos' API — Persistent Edition",
    version="0.7.5"
)

# ── Secure Media Streaming ────────────────────────────────────────────────────
# This allows the Stark-Tech frontend to play local disk videos for forensic review.
# In a production environment, this should be restricted to the STORAGE_DIR.
app.mount("/media", StaticFiles(directory="."), name="media")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Storage & Status Hub ────────────────────────────────────────────────────────
STORAGE_DIR   = "vidchain_storage"
SESSIONS_DIR  = os.path.join(STORAGE_DIR, "sessions")

# Stores live status of processing session: {session_id: "status_text"}
status_hub: Dict[str, str] = {}

# Distribution paths for bundled Spider-Net Portal
WEB_DIST_DIR = os.path.join(os.path.dirname(__file__), "web_dist")

vc: Optional[VidChain] = None


# ── Session helpers ───────────────────────────────────────────────────────────
def _sessions_dir() -> str:
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    return SESSIONS_DIR

def _session_path(session_id: str) -> str:
    return os.path.join(_sessions_dir(), f"{session_id}.json")

def _load_session(session_id: str) -> dict:
    p = _session_path(session_id)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_session(session: dict):
    with open(_session_path(session["id"]), "w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)

def _create_session(title: str = "New Session") -> dict:
    session = {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "created_at": time.time(),
        "updated_at": time.time(),
        "messages": []
    }
    _save_session(session)
    return session

def _append_message(session_id: str, sender: str, text: str, video_id: Optional[str] = None) -> dict:
    session = _load_session(session_id)
    if not session:
        session = _create_session()
        session_id = session["id"]

    msg = {
        "id": f"{sender}-{int(time.time()*1000)}",
        "sender": sender,
        "text": text,
        "timestamp": time.strftime("%H:%M"),
        "video_id": video_id,
    }
    session["messages"].append(msg)
    
    # NEW: Securely and permanently bind the session to this video context
    # We update the root even if video_id is None to ensure consistency 
    # (though in practice v_id should always be present during ingest)
    if video_id and session.get("video_id") != video_id:
        session["video_id"] = video_id
        
    session["updated_at"] = time.time()

    # Auto-title from first user message
    if sender == "user" and session["title"] == "New Session":
        session["title"] = text[:48].strip() + ("..." if len(text) > 48 else "")

    _save_session(session)
    return msg

def _list_sessions() -> List[dict]:
    d = _sessions_dir()
    sessions = []
    for fn in os.listdir(d):
        if fn.endswith(".json"):
            try:
                with open(os.path.join(d, fn), "r", encoding="utf-8") as f:
                    s = json.load(f)
                    sessions.append({
                        "id": s["id"],
                        "title": s.get("title", "Untitled"),
                        "created_at": s.get("created_at", 0),
                        "updated_at": s.get("updated_at", 0),
                        "message_count": len(s.get("messages", [])),
                        "video_id": s.get("video_id")
                    })
            except Exception:
                pass
    return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)


# ── Request models ────────────────────────────────────────────────────────────
class IngestRequest(BaseModel):
    video_source: str
    video_id: Optional[str] = None
    session_id: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    video_id: Optional[str] = None
    session_id: Optional[str] = None
    stream: bool = False

class NewSessionRequest(BaseModel):
    title: str = "New Session"

class RenameSessionRequest(BaseModel):
    title: str


# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup_event():
    global vc
    print("[VidChain Server] Waking up edge microservice...")
    os.makedirs(STORAGE_DIR, exist_ok=True)
    os.makedirs(SESSIONS_DIR, exist_ok=True)

    # Always persist to STORAGE_DIR — survives restarts
    vc = VidChain(db_path=STORAGE_DIR)
    indexed = vc.list_indexed_videos()
    print(f"[VidChain Server] Memory online. Videos indexed: {len(indexed)}")


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "indexed_videos": vc.list_indexed_videos() if vc else [],
    }


# ── Session CRUD ──────────────────────────────────────────────────────────────
@app.get("/api/sessions")
def list_sessions():
    return {"sessions": _list_sessions()}

@app.post("/api/sessions")
def create_session(req: NewSessionRequest):
    session = _create_session(req.title)
    return session

@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    session = _load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.patch("/api/sessions/{session_id}")
def rename_session(session_id: str, req: RenameSessionRequest):
    session = _load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session["title"] = req.title
    _save_session(session)
    return {"status": "renamed"}

@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    p = _session_path(session_id)
    if os.path.exists(p):
        os.remove(p)
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


# ── Query ─────────────────────────────────────────────────────────────────────
@app.post("/api/query")
def query_video(req: QueryRequest):
    if not vc:
        raise HTTPException(status_code=500, detail="VidChain Engine offline")

    # Load session and identify context
    session = _load_session(req.session_id) if req.session_id else None
    if not session:
        session = _create_session()
    
    session_id = session["id"]
    
    # ── Session isolation logic ───────────────────────────────────
    # 1. Resolve private chat history
    history = []
    for msg in session.get("messages", []):
        role = "assistant" if msg["sender"] in ["baburao", "system"] else "user"
        history.append({"role": role, "content": msg["text"]})

    # 2. Resolve private video context
    video_id = req.video_id or session.get("video_id")
    timeline = vc.get_video_timeline(video_id) if video_id else []

    try:
        # Prepare arguments: only pass timeline if we actually found one
        ask_kwargs = {
            "video_id": video_id,
            "history": history,
            "return_raw": True # NEW: Request high-fidelity telemetry payload
        }
        if timeline:
            ask_kwargs["timeline"] = timeline

        # Run engine with Neural HUD monitoring
        result = vc.ask(req.query, **ask_kwargs)
        
        # Extract structured intel
        answer = result.get("answer", "")
        telemetry = result.get("telemetry", {})
        confidence = result.get("confidence", 75)
        
        # 3. Save the interaction with telemetry metadata
        _append_message(session_id, "user",    req.query,  video_id)
        msg = _append_message(session_id, "baburao", answer, video_id)
        
        # Enrich stored message with neural scores
        msg["telemetry"]  = telemetry
        msg["confidence"] = confidence
        _save_session(_load_session(session_id)) # Final persistence lock
        
        return {
            "response": answer, 
            "session_id": session_id,
            "telemetry": telemetry,
            "confidence": confidence
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── Ingest ────────────────────────────────────────────────────────────────────
def _background_ingest(video_source: str, video_id: Optional[str], session_id: str):
    fname = os.path.basename(video_source)
    print(f"[VidChain Server] Background ingest started: {fname} (ID: {video_id})")
    try:
        status_hub[session_id] = "Initializing Transformers..."
        
        # We hook into the pipeline's progress callback to update our status hub
        def _progress_cb(node_name: str, msg: str):
            status_hub[session_id] = f"[{node_name}] {msg}"
            print(f"[Neural Telemetry] {session_id} -> {node_name}: {msg}")

        # Ingest with explicit ID binding
        v_id = vc.ingest(video_source, video_id=video_id, progress_callback=_progress_cb) # type: ignore
        
        status_hub[session_id] = "Summarizing Intelligence..."
        summary = vc.ask(
            "In exactly two sentences, describe the most important event from the video just ingested.",
            video_id=v_id
        )
        
        status_hub[session_id] = "Idle"
        _append_message(
            session_id,
            "system",
            f"Ingestion complete — {fname}\n\n{summary}",
            v_id,
        )
    except Exception as e:
        status_hub[session_id] = "Error"
        print(f"[VidChain Server] Ingest failed: {e}")
        _append_message(session_id, "system", f"Ingestion failed for {fname}: {e}")

@app.post("/api/ingest")
def ingest_video(req: IngestRequest, background_tasks: BackgroundTasks):
    if not vc:
        raise HTTPException(status_code=500, detail="VidChain Engine offline")
    if not os.path.exists(req.video_source):
        raise HTTPException(status_code=404, detail=f"File not found: {req.video_source}")

    # Create or validate session
    # ── Early Context Locking ─────────────────────────────────────
    # We resolve the ID early and lock it to the session root 
    # so that the UI/RAG can permanently anchor to it.
    video_id = req.video_id or str(uuid.uuid4())[:8]
    session_id = req.session_id

    session = _load_session(session_id)
    if session:
        session["video_id"] = video_id
        session["updated_at"] = time.time()
        _save_session(session)

    background_tasks.add_task(_background_ingest, req.video_source, video_id, session_id)
    return {
        "status": "processing",
        "session_id": session_id,
        "video_id": video_id,
        "message": f"Ingestion started for {req.video_source}",
    }


# ── Knowledge Gateway ──────────────────────────────────────────────────────────
@app.get("/api/knowledge/{video_id}")
def get_video_knowledge(video_id: str):
    """Provides the Semantic Heatmap with temporal activity mapping."""
    if not vc:
        raise HTTPException(status_code=500, detail="VidChain Engine offline")
    
    timeline = vc.get_video_timeline(video_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
        
    return {
        "video_id": video_id,
        "timeline": timeline
    }


@app.get("/api/sessions/{session_id}/status")
def get_live_status(session_id: str):
    """Neural Handshake: Returns the current active sensor node."""
    return {"status": status_hub.get(session_id, "Idle")}


# ── Spider-Net Portal Serving ────────────────────────────────────────────────
@app.get("/{rest_of_path:path}", include_in_schema=False)
def serve_dashboard(rest_of_path: str):
    """Serves the static Next.js export or redirects to index.html for SPA."""
    asset_path = os.path.join(WEB_DIST_DIR, rest_of_path)
    if os.path.isfile(asset_path):
        return FileResponse(asset_path)
    
    # Fallback to index.html for React routing
    index_path = os.path.join(WEB_DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return {"message": "VidChain Server Online. Dashboard bundle missing."}

# ── CLI ───────────────────────────────────────────────────────────────────────
def main_cli():
    print("=========================================")
    print("  VidChain Forensic Suite v0.7.2")
    print("  Portal : http://localhost:8000")
    print("  Storage: ./vidchain_storage")
    print("=========================================")
    uvicorn.run("vidchain.serve:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main_cli()
