import os
import json
import time
import uuid
import uvicorn
import webbrowser
import threading
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from vidchain.client import VidChain
from vidchain.telemetry import HardwareMonitor

app = FastAPI(
    title="IRIS (Intelligent Retrieval & Insight System)",
    description="Local 'Intelligent Retrieval & Insight System' API — Persistent Edition",
    version="1.0.0-Stable"
)

# ── Secure Media Gateway ──────────────────────────────────────────────────────
@app.get("/api/media-stream")
def stream_media(path: str):
    """IRIS Gateway: Streams local video assets for insight review."""
    if not os.path.exists(path):
        # Fallback: maybe it's just a filename in the current dir
        if os.path.exists(os.path.basename(path)):
            path = os.path.basename(path)
        else:
            raise HTTPException(status_code=404, detail=f"Media not found: {path}")
    return FileResponse(path)

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
# Stores kill signals for active sessions: {session_id: True}
interrupt_hub: Dict[str, bool] = {}

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

def _create_session(title: str = "New Insight Session", save: bool = True) -> dict:
    session = {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "created_at": time.time(),
        "updated_at": time.time(),
        "messages": []
    }
    if save:
        _save_session(session)
    return session

def _append_message(session_id: str, sender: str, text: str, video_id: Optional[str] = None, confidence: Optional[int] = None, telemetry: Optional[dict] = None, snapshots: Optional[list] = None) -> dict:
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
        "confidence": confidence,
        "telemetry": telemetry,
        "snapshots": snapshots
    }
    session["messages"].append(msg)
    
    # NEW: Securely and permanently bind the session to this video context
    # We update the root even if video_id is None to ensure consistency 
    # (though in practice v_id should always be present during ingest)
    if video_id and session.get("video_id") != video_id:
        session["video_id"] = video_id
        
    session["updated_at"] = time.time()

    # Auto-title from first user message
    if sender == "user" and session["title"] == "New Insight Session":
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
    title: str = "New Insight Session"

class RenameSessionRequest(BaseModel):
    title: str


# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup_event():
    global vc
    print("[IRIS] Waking up neural microservice...")
    os.makedirs(STORAGE_DIR, exist_ok=True)
    os.makedirs(SESSIONS_DIR, exist_ok=True)

    # Always persist to STORAGE_DIR — survives restarts
    vc = VidChain(db_path=STORAGE_DIR)
    indexed = vc.vector_store.list_videos()
    print(f"[IRIS] Intelligence online. Insights cached: {len(indexed)}")


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "indexed_videos": vc.list_indexed_videos() if vc else [],
    }


# ── Session CRUD ──────────────────────────────────────────────────────────────
@app.post("/api/sessions/{session_id}/interrupt")
def interrupt_session(session_id: str):
    """Neural Killswitch: Sends a stop signal to the active session nodes."""
    print(f"[IRIS] Interrupt signal received for session: {session_id}")
    interrupt_hub[session_id] = True
    return {"status": "interrupt_signal_sent"}

@app.get("/api/sessions")
def list_sessions():
    return {"sessions": _list_sessions()}

@app.post("/api/sessions")
def create_session(req: NewSessionRequest):
    if vc: vc.active_timeline = [] # Ensure memory isolation
    session = _create_session(req.title)
    return session

@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    if vc: vc.active_timeline = [] # Purge residues on context switch
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
    session = _load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # ── Full Memory Purge ──────────────────────────────────────────
    # IRIS ensures that deleting a session wipes the linked memory
    video_id = session.get("video_id")
    if video_id and vc:
        print(f"[IRIS] Purging all memory linked to video: {video_id}")
        
        # 1. Clear ChromaDB vectors
        try:
            vc.purge_storage(video_id)
        except Exception as e:
            print(f"[Purge Error] ChromaDB: {e}")

    # ── Session Deletion ───────────────────────────────────────────
    p = _session_path(session_id)
    if os.path.exists(p):
        os.remove(p)
        return {"status": "deleted", "purged_video": video_id}
    
    raise HTTPException(status_code=404, detail="Session file missing")


# ── Query ─────────────────────────────────────────────────────────────────────
@app.post("/api/query")
def query_video(req: QueryRequest):
    if not vc:
        raise HTTPException(status_code=500, detail="VidChain Engine offline")
        
    # ── Concurrency Locking (v1.0.0 Production Hardening) ───────────
    session_id = req.session_id
    current_status = status_hub.get(session_id, "Idle")
    if current_status not in ["Idle", "Error", "Interrupted"]:
        raise HTTPException(
            status_code=400, 
            detail="IRIS is currently busy. Please wait for the current background task to finish before asking questions."
        )

    # Load session and identify context
    session = _load_session(req.session_id) if req.session_id else None
    if not session:
        session = _create_session()
    
    session_id = session["id"]
    
    # ── Session isolation logic ───────────────────────────────────
    # 1. Resolve private chat history
    history = []
    for msg in session.get("messages", []):
        role = "assistant" if msg["sender"] in ["iris", "system"] else "user"
        history.append({"role": role, "content": msg["text"]})

    # 2. Resolve private video context
    video_id = req.video_id or session.get("video_id")
    timeline = vc.get_video_timeline(video_id) if video_id else []

    try:
        status_hub[session_id] = "Neural Retrieval: Finding evidence..."
        # ── Instant Persistence ───────────────────────────────────
        # Save the user's question immediately so it's not lost on refresh
        _append_message(session_id, "user", req.query, video_id)
        _save_session(_load_session(session_id))

        # Prepare arguments: only pass timeline if we actually found one
        def neural_status_cb(msg: str):
            status_hub[session_id] = msg

        ask_kwargs = {
            "video_id": video_id,
            "video_source": session.get("video_path"),
            "history": history,
            "return_raw": True,
            "status_callback": neural_status_cb
        }
        if timeline:
            ask_kwargs["timeline"] = timeline

        # Run engine with Neural HUD monitoring
        status_hub[session_id] = "Neural Reasoning: Consulting LLM..."
        result = vc.ask(req.query, **ask_kwargs)
        
        # Extract structured intel
        answer = result.get("answer", "")
        confidence = result.get("confidence", 75)
        telemetry_stats = result.get("telemetry", {})
        snapshots = result.get("snapshots", [])
        
        # Append IRIS response to persistent memory
        _append_message(session_id, "iris", answer, video_id, confidence=confidence, telemetry=telemetry_stats, snapshots=snapshots)
        _save_session(_load_session(session_id)) # Final persistence lock
        status_hub[session_id] = "Idle"
        
        return {
            "response": answer,
            "session_id": session_id,
            "confidence": confidence,
            "telemetry": telemetry_stats,
            "snapshots": snapshots
        }
    except Exception as e:
        print(f"[IRIS] Neural Error: {str(e)}")
        error_msg = "I've hit a bit of 'Neural Exhaustion'. My local processors timed out while analyzing this segment. Please try a simpler query or a shorter video."
        if "timeout" in str(e).lower():
            error_msg = "My 'Neural Timeout' was triggered. This segment is very complex and my local processors couldn't finish in time. Try asking for a shorter summary!"
        
        _append_message(session_id, "iris", error_msg, video_id)
        status_hub[session_id] = "Error"
        return {"response": error_msg, "status": "error"}


# ── Ingest ────────────────────────────────────────────────────────────────────
def _background_ingest(video_source: str, video_id: Optional[str], session_id: str):
    fname = os.path.basename(video_source)
    print(f"[VidChain Server] Background ingest started: {fname} (ID: {video_id})")
    try:
        status_hub[session_id] = "Initializing Transformers..."
        
        # We hook into the pipeline's progress callback to update our status hub
        def _progress_cb(node_name: str, msg: str):
            # Check for interrupt signal
            if interrupt_hub.get(session_id):
                print(f"[IRIS] Aborting ingest for {session_id} per user request.")
                status_hub[session_id] = "Interrupted"
                raise InterruptedError("Operation cancelled by user.")
            
            status_hub[session_id] = f"[{node_name}] {msg}"
            print(f"[Neural Telemetry] {session_id} -> {node_name}: {msg}")

        # Ensure interrupt flag is cleared before starting
        interrupt_hub[session_id] = False

        # Ingest with explicit ID binding
        v_id = vc.ingest(video_source, video_id=video_id, progress_callback=_progress_cb) # type: ignore
        
        status_hub[session_id] = "Idle"
        _append_message(
            session_id,
            "system",
            f"Ingestion complete — {fname}. Evidence locked and isolated.",
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

    # Resolve session identity
    session_id = req.session_id
    session = _load_session(session_id) if session_id else None
    if not session:
        session = _create_session()
        session_id = session["id"]

    # ── Concurrency Locking (v1.0.0 Production Hardening) ───────────
    current_status = status_hub.get(session_id, "Idle")
    if current_status not in ["Idle", "Error", "Interrupted"]:
        raise HTTPException(
            status_code=400, 
            detail="IRIS is currently busy processing this session. Please wait for the current operation to finish."
        )

    # ── Early Context Locking ─────────────────────────────────────
    video_id = req.video_id or str(uuid.uuid4())[:8]
    session["video_id"] = video_id
    session["video_path"] = req.video_source
    session["updated_at"] = time.time()
    _save_session(session)

    status_hub[session_id] = "Starting Ingestion..."
    background_tasks.add_task(_background_ingest, req.video_source, video_id, session_id)
    return {
        "status": "processing",
        "session_id": session_id,
        "video_id": video_id,
        "video_path": req.video_source,
        "message": f"Ingestion started for {req.video_source}",
    }


# ── Knowledge Gateway ──────────────────────────────────────────────────────────
@app.get("/api/knowledge/{video_id}")
def get_video_knowledge(video_id: str):
    """Provides the Semantic Heatmap with temporal activity mapping and metadata."""
    if not vc:
        raise HTTPException(status_code=500, detail="VidChain Engine offline")
    
    # Resolve the full knowledge base record to get the 'source' path
    db_path = vc.config.get("db_path")
    if db_path:
        kb_path = os.path.join(db_path, "knowledge_bases", f"{video_id}.json")
        if os.path.exists(kb_path):
            with open(kb_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Normalize path for the /media static mount
                src = data.get("metadata", {}).get("source")
                if src and os.path.isabs(src):
                    try:
                        data["metadata"]["source"] = os.path.relpath(src, start=os.getcwd())
                    except: pass
                return data

    # Fallback to just timeline if full KB not found
    timeline = vc.get_video_timeline(video_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
        
    return {
        "metadata": {"video_id": video_id},
        "timeline": timeline
    }


@app.get("/api/sessions/{session_id}/status")
def get_live_status(session_id: str):
    """Neural Handshake: Returns the current active sensor node and hardware load."""
    return {
        "status": status_hub.get(session_id, "Idle"),
        "telemetry": HardwareMonitor.get_instant_sample()
    }


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
def open_browser():
    """Waits for server to start and then opens the portal."""
    time.sleep(10.0) # Extended delay for IRIS neural warmup
    print("[IRIS] Launching Intelligence Portal...")
    webbrowser.open("http://localhost:8000")

def main_cli():
    print("=========================================")
    print("  IRIS Intelligence Suite v1.0.0-Stable")
    print("  Portal : http://localhost:8000")
    print("  Storage: ./vidchain_storage")
    print("=========================================")
    
    # Auto-launch the browser in a background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run("vidchain.serve:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main_cli()
