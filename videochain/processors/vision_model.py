import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import os

class VisionProcessor:
    def __init__(self, model_path="models/security_model.pth"):
        """
        Multipurpose Vision Engine. 
        Instead of hardcoded labels, it dynamically adapts to whatever 
        dataset was used during the training phase.
        """
        # 1. Hardware Detection (Crucial for your RTX 3050)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[VideoChain] Vision Engine active on: {self.device}")
        
        # 2. Universal Image Preprocessing
        # These constants (mean/std) are standard for ImageNet-based models
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        self.model_path = model_path
        self.classes = [] 
        self.is_dummy = False
        self.model = self._load_model()

    def _load_model(self):
        """
        Reconstructs the neural network and injects custom weights.
        """
        # Safety Check: If no model exists, enter 'Dummy Mode'
        if not os.path.exists(self.model_path):
            print(f"⚠️ [System] Custom brain '{self.model_path}' not found.")
            print("⚠️ [System] Running in generic mode. Please train the model to see real results.")
            self.is_dummy = True
            return None

        try:
            # 1. Load the checkpoint onto your specific device
            checkpoint = torch.load(self.model_path, map_location=self.device)
            
            # 2. Extract Dynamic Labels 
            # This is what makes it multipurpose! It reads your folder names.
            self.classes = checkpoint['classes'] 
            
            # 3. Build the MobileNetV3 Architecture (Small version for Edge efficiency)
            model = models.mobilenet_v3_small(weights=None)
            
            # 4. Modify the 'Head' to match your number of categories
            # Whether you have 3 categories or 30, this line adapts automatically.
            num_features = model.classifier[3].in_features
            model.classifier[3] = nn.Linear(num_features, len(self.classes))
            
            # 5. Load the trained weights
            model.load_state_dict(checkpoint['model_state_dict'])
            model = model.to(self.device)
            
            # 6. Evaluation Mode (Crucial: Turns off dropout/batchnorm training)
            model.eval() 
            
            print(f"[VideoChain] ✅ Multipurpose Brain Loaded!")
            print(f"[VideoChain] Active Categories: {self.classes}")
            return model

        except Exception as e:
            print(f"❌ [Error] Failed to load model: {e}")
            self.is_dummy = True
            return None

    def predict_frame(self, image_path):
        """
        Analyzes a single frame and returns the classified category.
        """
        if self.is_dummy or self.model is None:
            return "ANALYSIS_PENDING"

        try:
            # Open and preprocess image
            image = Image.open(image_path).convert('RGB')
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            # Disable gradient tracking to save VRAM on your 3050
            with torch.no_grad():
                output = self.model(input_tensor)
                
                # Softmax/Max logic to find the highest confidence class
                _, predicted_idx = torch.max(output, 1)
                
            # Convert index back to your dynamic folder name
            label = self.classes[int(predicted_idx.item())]
            return label
            
        except Exception as e:
            return f"PROCESS_ERROR: {str(e)}"

    def update_model(self, new_path):
        """
        Allows you to swap 'brains' on the fly (e.g., from Security to Retail).
        """
        self.model_path = new_path
        self.model = self._load_model()