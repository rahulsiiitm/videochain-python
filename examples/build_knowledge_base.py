from videochain.loaders.audio_loader import AudioLoader
from videochain.loaders.video_loader import VideoLoader
from videochain.processors.audio_model import AudioProcessor
from videochain.processors.vision_model import VisionProcessor
from videochain.core.fusion import FusionEngine
import json

# 1. Init
v_loader = VideoLoader()
a_loader = AudioLoader()
v_proc = VisionProcessor()
a_proc = AudioProcessor(model_size="base") # Ensure this is updated to use CUDA!
fusion = FusionEngine()

# 2. Process
print("🚀 Starting Multimodal Extraction...")
audio_path = a_loader.extract_audio("sample.mp4")
audio_data = a_proc.transcribe(audio_path)

keyframes = v_loader.extract_keyframes("sample.mp4")
vision_data = [{"timestamp": f['timestamp'], "label": v_proc.predict_frame(f['path'])} for f in keyframes]

# 3. Fuse & Save
knowledge_base = fusion.fuse(audio_data, vision_data)

with open("knowledge_base.json", "w") as f:
    json.dump(knowledge_base, f, indent=4)

print("🎉 Knowledge Base created: knowledge_base.json")