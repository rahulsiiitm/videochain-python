import os
import cv2
import shutil
from typing import Dict, Any
from vidchain.pipeline import VideoChain
from vidchain.nodes import BaseNode, AdaptiveKeyframeNode

class SaveFrameNode(BaseNode):
    """
    A custom node solely for debugging!
    It saves the active frame to disk to visualize what the firewall allowed through.
    """
    def __init__(self, output_dir: str = "temp_frames"):
        self.output_dir = output_dir
        # Purge the directory if it exists to start fresh
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir)
        self.saved_count = 0
            
    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        frame = context.get("current_frame")
        if frame is None:
            return context
            
        time_sec = context.get('current_time', 0.0)
        
        # Save it!
        filename = os.path.join(self.output_dir, f"frame_{time_sec}s.jpg")
        cv2.imwrite(filename, frame)
        self.saved_count += 1
        
        print(f"   📸 [SaveFrameNode] Visually significant frame explicitly saved at {time_sec}s!")
        return context

def test_adaptive_keyframing():
    print("==================================================")
    print("🕵️ TESTING VIDCHAIN: ADAPTIVE KEYFRAMER VISUALIZER")
    print("==================================================\n")
    print("This script will run at 2 FPS and save ONLY the frames that")
    print("survive the AdaptiveKeyframeNode into the 'temp_frames' folder.\n")
    
    my_chain = VideoChain(
        nodes=[
            AdaptiveKeyframeNode(change_threshold=5.0), # The Firewall
            SaveFrameNode(output_dir="temp_frames")     # The Logger
        ],
        frame_skip=15 # Assumes 30fps video -> 2 FPS extraction
    )
    
    my_chain.run("sample.mp4")
    
    print(f"\n✅ Testing complete! Check the 'temp_frames' folder to visually confirm which frames survived.")

if __name__ == "__main__":
    test_adaptive_keyframing()
