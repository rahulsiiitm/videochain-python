import cv2
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import librosa
import numpy as np
import json
import os
import sys

# ==========================
# Vision Model
# ==========================
class VisionEngine:
    def __init__(self, model_path="models/videochain_vision.pth", confidence_threshold=0.65):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.threshold = confidence_threshold

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        self.model_path = model_path
        self.classes = []
        self.model = self._load_model()

    def _load_model(self):
        if not os.path.exists(self.model_path):
            print(f"[WARNING] Model not found at {self.model_path}, running in dummy mode.")
            return None

        # Load the checkpoint (removed weights_only=True to allow reading the 'classes' list)
        checkpoint = torch.load(self.model_path, map_location=self.device)
        
        # 1. Initialize the blank MobileNet architecture
        model = models.mobilenet_v3_small(weights=None)
        
        # 2. Robust Loading Logic
        if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
            # Format A: Modern save (contains both weights and classes)
            self.classes = checkpoint.get('classes', ["emergency", "normal", "suspicious", "violence"])
            state_dict = checkpoint['model_state_dict']
        elif isinstance(checkpoint, dict):
            # Format B: Legacy save (just the raw weights)
            self.classes = ["emergency", "normal", "suspicious", "violence"]
            state_dict = checkpoint
        else:
            # Format C: Full model object saved
            self.classes = ["emergency", "normal", "suspicious", "violence"]
            state_dict = checkpoint.state_dict() # type: ignore

        # 3. Resize the final classification layer to match the number of classes
        num_features = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(num_features, len(self.classes))

        try:
            # 4. Inject the weights into the architecture
            model.load_state_dict(state_dict)
            model = model.to(self.device).eval()

            # RTX 3050 Memory Optimization
            if self.device.type == 'cuda':
                model = model.half()
                
            print(f"[SUCCESS] ActionEngine loaded successfully with classes: {self.classes}")
            return model
            
        except Exception as e:
            print(f"[ERROR] Failed to map weights to the ActionEngine: {e}")
            sys.exit(1)

    def predict(self, frame_array):
        if self.model is None:
            return "unknown", 0.0

        img = Image.fromarray(frame_array).convert('RGB')
        input_tensor = self.transform(img).unsqueeze(0).to(self.device) # type: ignore

        if self.device.type == 'cuda':
            input_tensor = input_tensor.half()

        with torch.no_grad():
            output = self.model(input_tensor)
            probs = torch.nn.functional.softmax(output[0], dim=0)
            conf, idx = torch.max(probs, 0)

        label = self.classes[int(idx.item())]
        confidence = conf.item()

        if confidence < self.threshold:
            return "uncertain", confidence

        return label, confidence


# ==========================
# Video Processing Helpers
# ==========================
def extract_frames(video_path, frame_skip=5):
    cap = cv2.VideoCapture(video_path)
    frames = []
    count = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        if count % frame_skip == 0:
            frames.append(frame)
        count += 1
    cap.release()
    return frames

def extract_audio(video_path):
    audio, sr = librosa.load(video_path, sr=None)
    return audio, sr

def analyze_audio(audio, sr):
    energy = float(np.mean(audio ** 2))
    duration = len(audio) / sr
    return {"energy": energy, "duration": duration}

def analyze_frames(frames, vision_engine):
    results = []
    prev_frame = None
    for i, frame in enumerate(frames):
        label, conf = vision_engine.predict(frame)
        motion_score = 0
        if prev_frame is not None:
            diff = cv2.absdiff(prev_frame, frame)
            motion_score = float(np.mean(diff))
        results.append({
            "frame_index": i,
            "label": label,
            "confidence": float(conf),
            "motion": motion_score
        })
        prev_frame = frame
    return results

def fuse_results(frame_data, audio_data):
    label_counts = {}
    for f in frame_data:
        if f["label"] != "uncertain":
            label_counts[f["label"]] = label_counts.get(f["label"], 0) + 1
    final_label = max(label_counts, key=lambda x: label_counts[x]) if label_counts else "unknown"
    avg_conf = float(np.mean([f["confidence"] for f in frame_data]))
    return {
        "final_prediction": final_label,
        "average_confidence": avg_conf,
        "audio_energy": audio_data["energy"],
        "detected_events": label_counts
    }

def generate_json(fusion_result, frame_data):
    output = {"summary": fusion_result, "frames": frame_data}
    return json.dumps(output, indent=4)

def process_video(video_path, model_path="models/videochain_vision.pth"):
    vision = VisionEngine(model_path=model_path)
    print("📹 Extracting frames...")
    frames = extract_frames(video_path)
    print("🔊 Extracting audio...")
    audio, sr = extract_audio(video_path)
    print("🧠 Analyzing frames...")
    frame_data = analyze_frames(frames, vision)
    print("🎧 Analyzing audio...")
    audio_data = analyze_audio(audio, sr)
    print("🔗 Fusing results...")
    fusion = fuse_results(frame_data, audio_data)
    print("📄 Generating JSON...")
    return generate_json(fusion, frame_data)

if __name__ == "__main__":
    video_path = "sample.mp4"
    output = process_video(video_path)
    print(output)
    with open("output.json", "w") as f:
        f.write(output)