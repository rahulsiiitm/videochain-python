import os
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any

from vidchain.client import VidChain

app = FastAPI(
    title="VidChain Edge Server",
    description="Local 'LangChain for Videos' API",
    version="0.6.0"
)

# Singleton global instance mapped upon startup
vc: Optional[VidChain] = None

class IngestRequest(BaseModel):
    video_source: str
    video_id: Optional[str] = None
    use_legacy_processor: bool = True
    
class QueryRequest(BaseModel):
    query: str
    video_id: Optional[str] = None
    stream: bool = False

@app.on_event("startup")
def startup_event():
    global vc
    print("[VidChain Server] Waking up edge microservice...")
    vc = VidChain()
    # Pings the DB to ensure chroma is mapped
    print(f"[VidChain Server] Memory online. Videos indexed: {len(vc.list_indexed_videos())}")

@app.get("/api/health")
def health_check():
    return {"status": "online", "indexed_videos": vc.list_indexed_videos() if vc else []}

@app.post("/api/query")
def query_video(req: QueryRequest):
    if not vc:
        raise HTTPException(status_code=500, detail="VidChain Engine offline")
        
    try:
        response = vc.ask(req.query, video_id=req.video_id, stream=req.stream)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _background_ingest(video_source: str, video_id: Optional[str], **kwargs):
    """Background ingestion to prevent API timeouts."""
    print(f"[VidChain Server] Background ingest started for: {video_source}")
    try:
        vc.ingest(video_source, video_id=video_id, **kwargs) # type: ignore
        print(f"[VidChain Server] Background ingest complete for: {video_source}")
    except Exception as e:
        print(f"[VidChain Server] Background ingest failed: {e}")

@app.post("/api/ingest")
def ingest_video(req: IngestRequest, background_tasks: BackgroundTasks):
    if not vc:
        raise HTTPException(status_code=500, detail="VidChain Engine offline")
        
    if not os.path.exists(req.video_source):
        raise HTTPException(status_code=404, detail=f"File not found: {req.video_source}")
        
    background_tasks.add_task(_background_ingest, req.video_source, req.video_id)
    return {"status": "processing", "message": f"Ingestion started in background for {req.video_source}"}

def main_cli():
    print("=========================================")
    print("🚀 VidChain Edge Microservice Starting...")
    print("=========================================")
    uvicorn.run("vidchain.serve:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main_cli()
