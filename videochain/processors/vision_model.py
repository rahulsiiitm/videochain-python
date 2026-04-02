import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import os

class VisionProcessor:
    def __init__(self, model_path="security_model.pth"):

        """
        Initializes the PyTorch model and loads your custom trained weights.
        """
        
        # Hardware Detection
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[VideoChain] Vision using device: {self.device}")
        
        # Exact same image transformations used during training
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        self.model_path = model_path
        self.classes = ["UNINITIALIZED"] 
        self.model = self._load_model()

    def _load_model(self):
        # 1. Check if the trained brain exists
        if not os.path.exists(self.model_path):
            print(f"⚠️ [WARNING] Custom model '{self.model_path}' not found!")
            print("⚠️ Have you run 'python scripts/train_vision.py' yet?")
            self.is_dummy = True
            return None

        self.is_dummy = False
        
        # 2. Load the checkpoint
        print(f"[VideoChain] Loading custom weights from {self.model_path}...")
        checkpoint = torch.load(self.model_path, map_location=self.device)
        
        # DYNAMIC LABELS: It reads your folder names! No hardcoded strings.
        self.classes = checkpoint['classes'] 
        
        # 3. Rebuild the MobileNetV3 Architecture
        model = models.mobilenet_v3_small(weights=None)
        num_features = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(num_features, len(self.classes))
        
        # 4. Inject your custom weights into the architecture
        model.load_state_dict(checkpoint['model_state_dict'])
        model = model.to(self.device)
        
        # CRITICAL: Put model in evaluation mode (disables dropout/gradients)
        model.eval() 
        
        print(f"[VideoChain] ✅ Custom Brain Loaded! Active Classes: {self.classes}")
        return model

    def predict_frame(self, image_path):
        """
        Takes an image path, runs it through the GPU, and returns the dynamic label.
        """
        if self.is_dummy or self.model is None:
            return "NEEDS_TRAINING"

        try:
            # Load and format the image
            image = Image.open(image_path).convert('RGB')
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            # Run inference without tracking gradients (Saves VRAM)
            with torch.no_grad():
                output = self.model(input_tensor)
                
                # Get the highest probability prediction
                _, predicted_idx = torch.max(output, 1)
                
            # Return the actual dynamic string
            return self.classes[int(predicted_idx.item())]
            
        except Exception as e:
            return f"ERROR: {str(e)}"