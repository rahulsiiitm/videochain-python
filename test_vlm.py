import json
import time
from vidchain.pipeline import VideoChain
from vidchain.nodes import LlavaNode, AdaptiveKeyframeNode

def test_autonomous_vlm_pipeline():
    print("==================================================")
    print("🤖 TESTING VIDCHAIN PHASE 3: AUTONOMOUS VLM AGENTS")
    print("==================================================\n")
    
    # 1. We replace blind YOLO completely with an intelligent VLM Agent!
    # A VLM requires an LLM payload, usually 'moondream' or 'llava'
    my_chain = VideoChain(
        nodes=[
            AdaptiveKeyframeNode(change_threshold=5.0), # Blocks VLM if frame hasn't visually changed
            LlavaNode(model_name="llava") # Make sure you have 'ollama run llava' previously pulled!
        ],
        frame_skip=15 # Process exactly 2 frames per second (assuming 30fps)
    )

    t0 = time.time()
    
    # 2. Run the pipeline on the local sample
    print("\n[Test] Launching Agentic VLM analysis on sample.mp4...")
    try:
        timeline = my_chain.run("sample.mp4")
        t1 = time.time()
        
        # 3. Output results
        print(f"\n[Test] Success! Generated raw timeline payload in {round(t1-t0, 1)} seconds:")
        print(json.dumps(timeline[:2], indent=2)) # Print first 2 deeply-captioned events
        
    except Exception as e:
        print(f"\n❌ [Test Failed] {e}")
        print("Note: If the error says 'pip install ollama' or connection refused, ensure Ollama is actively running, and 'pip install ollama' is in your .venv!")
    
if __name__ == "__main__":
    test_autonomous_vlm_pipeline()
