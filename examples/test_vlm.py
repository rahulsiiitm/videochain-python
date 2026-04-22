import json
import time
from vidchain import VidChain
from vidchain.pipeline import VideoChain
from vidchain.nodes import LlavaNode, AdaptiveKeyframeNode

def test_autonomous_vlm_pipeline():
    print("==================================================")
    print("🤖 TESTING VIDCHAIN PHASE 3: AUTONOMOUS VLM AGENTS")
    print("==================================================\n")
    
    # 1. Build the Moondream-powered pipeline
    my_chain = VideoChain(
        nodes=[
            AdaptiveKeyframeNode(change_threshold=5.0), # Skip identical frames
            LlavaNode(model_name="moondream"),           # Deep visual captioning
        ],
        frame_skip=15  # 2 FPS (assuming 30fps video)
    )

    t0 = time.time()
    
    # 2. Ingest into ChromaDB via VidChain — this is where RAG gets its data!
    print("\n[Test] Ingesting via Moondream VLM pipeline into ChromaDB...")
    vc = VidChain(config={
        "llm_provider": "ollama/llama3",
        "db_path": "./vidchain_storage"  # Persist to disk
    })
    
    try:
        video_id = vc.ingest("sample.mp4", chain=my_chain)
        t1 = time.time()
        
        print(f"\n[Test] ✅ Indexed {video_id} in {round(t1-t0, 1)}s via Moondream!")
        print("[Test] Now querying IRIS with VLM-enriched data...\n")
        
        # 3. Query IRIS using the new rich descriptions
        response = vc.ask("Describe what is visible on the screen in detail", video_id=video_id)
        print(f"IRIS: {response}")
        
    except Exception as e:
        print(f"\n❌ [Test Failed] {e}")
    
if __name__ == "__main__":
    test_autonomous_vlm_pipeline()
