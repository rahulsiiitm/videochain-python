from videochain.loaders.video_loader import VideoLoader
from videochain.processors.vision_model import VisionProcessor

# 1. Setup
loader = VideoLoader()
vision = VisionProcessor()

# 2. Extract Keyframes (The iRAG adaptive sampling step)
keyframes = loader.extract_keyframes("sample.mp4")

print("\n--- 👁️ Vision Analysis Results ---")
for frame in keyframes[:5]: # Check first 5 keyframes
    # For now, this uses a pre-trained MobileNetV3
    label = vision.predict_frame(frame['path'])
    print(f"[{frame['timestamp']:.2f}s] Detected: {label}")