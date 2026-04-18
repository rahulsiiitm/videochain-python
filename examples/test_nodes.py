import json
from vidchain.pipeline import VideoChain
from vidchain.nodes import YoloNode, OcrNode

def test_composable_pipeline():
    print("===========================================")
    print("🧪 TESTING VIDCHAIN 'LANGCHAIN' ARCHITECTURE")
    print("===========================================\n")
    
    # 1. Build a custom, lightweight pipeline
    # We are skipping Audio and Emotion to prove that Nodes are totally modular!
    my_chain = VideoChain(
        nodes=[
            YoloNode(model_path="yolov8n.pt", confidence=0.6),
            OcrNode(interval=2.0) # Check for text more aggressively
        ],
        frame_skip=30 # Processes 1 frame per second (assuming 30fps)
    )

    # 2. Run the pipeline on the local sample
    print("\n[Test] Running pipeline on sample.mp4...")
    timeline = my_chain.run("sample.mp4")
    
    # 3. Output results
    print("\n[Test] Success! Generated raw timeline payload:")
    print(json.dumps(timeline[:3], indent=2)) # Print first 3 events
    
if __name__ == "__main__":
    test_composable_pipeline()
