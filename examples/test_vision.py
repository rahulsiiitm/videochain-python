import torch
import os
from videochain.loaders.video_loader import VideoLoader
from videochain.processors.vision_model import VisionEngine

def test_vision():
    VIDEO_PATH = "sample.mp4"
    
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ Error: {VIDEO_PATH} not found.")
        return

    # 1. Initialize
    loader = VideoLoader(output_dir="temp_frames")
    proc = VisionEngine() # This should print "Vision using device: cuda"

    # 2. Extract Keyframes (Adaptive Sampling)
    print(f"\n[Step 1] Extracting keyframes from {VIDEO_PATH}...")
    keyframes = loader.extract_keyframes(VIDEO_PATH)
    
    if not keyframes:
        print("❌ No keyframes extracted. Check your video file.")
        return

    # 3. Run Inference on GPU
    print(f"\n[Step 2] Running Vision Inference on {len(keyframes)} frames...")
    
    for i, frame in enumerate(keyframes):
        # We run the actual model here
        label, confidence = proc.predict(frame['path'])
        
        print(f"Frame {i+1}: Time {frame['timestamp']:.2f}s | Result: {label} (Confidence: {confidence:.2f}%)")
        
        # Monitor GPU Memory every 5 frames
        if i % 5 == 0 and torch.cuda.is_available():
            vram = torch.cuda.memory_allocated(0) / 1024**2
            print(f"   📊 GPU VRAM in use: {vram:.2f} MB")

    print("\n✅ Vision Test Complete!")
    print(f"Check the 'temp_frames' folder to see the extracted .jpg files.")

if __name__ == "__main__":
    test_vision()