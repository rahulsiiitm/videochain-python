import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import os
import sys

# ==========================
# Vision Model
# ==========================
class VisionEngine:
    def __init__(self, model_path="models/vidchain_vision.pth", confidence_threshold=0.65):
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
