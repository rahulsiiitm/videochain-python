import os
import torch
from vidchain.loaders.video_loader import VideoLoader
from vidchain.loaders.audio_loader import AudioLoader
from vidchain.processors.vision_model import VisionEngine
from vidchain.processors.audio_model import AudioProcessor
from vidchain.core.fusion import FusionEngine

def main():
    VIDEO_PATH = "sample.mp4"
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ Error: {VIDEO_PATH} not found in root directory.")
        return

    # --- PHASE 1: Initialization ---
    print("\n🚀 [Initializing vidchain Pipeline...]")
    v_loader = VideoLoader(output_dir="temp_frames")
    a_loader = AudioLoader(output_dir="temp_audio")
    
    # These will load your PyTorch/Whisper models onto the GPU
    vision_proc = VisionEngine(model_path="models/security_model.pth")
    audio_proc = AudioProcessor(model_size="base")
    fusion_engine = FusionEngine()

    # --- PHASE 2: Data Extraction ---
    print("\n📂 [Phase 2: Extracting Raw Data]")
    # 1. Get the frames using your adaptive Gaussian Blur logic
    keyframes = v_loader.extract_keyframes(VIDEO_PATH)
    
    # 2. Extract audio track from the video
    audio_path = a_loader.extract_audio(VIDEO_PATH)

    # --- PHASE 3: AI Inference ---
    print("\n🧠 [Phase 3: Running AI Inference]")
    
    # Vision Processing
    vision_results = []
    for frame in keyframes:
        label, confidence = vision_proc.predict(frame['path'])
        vision_results.append({
            "timestamp": frame['timestamp'],
            "label": label,
            "confidence": confidence
        })
    
    # Audio Processing (Whisper)
    audio_results = audio_proc.transcribe(audio_path)

    # --- PHASE 4: Multimodal Fusion ---
    print("\n🔗 [Phase 4: Data Fusion]")
    # This creates your knowledge_base.json
    final_kb = fusion_engine.generate_knowledge_base(vision_results, audio_results)

    print("\n✅ [Pipeline Complete!]")
    print(f"Total Events Logged: {len(final_kb['timeline'])}")
    print("Next Step: Use the UI or Ollama to query the knowledge_base.json")

if __name__ == "__main__":
    main()