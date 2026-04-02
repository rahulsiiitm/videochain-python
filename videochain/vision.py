import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

class VisionEngine:
    def __init__(self, model_path, class_path, device=None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load Classes
        with open(class_path, "r") as f:
            self.classes = f.read().splitlines()

        # Rebuild Architecture
        self.model = models.mobilenet_v3_small(weights=None)
        num_features = self.model.classifier[3].in_features
        self.model.classifier[3] = nn.Linear(num_features, len(self.classes))
        
        # Load Weights
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device).eval()

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def predict(self, frame):
        # Convert CV2 frame to PIL
        img = Image.fromarray(frame).convert('RGB')
        input_tensor = self.transform(img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            output = self.model(input_tensor)
            prob, idx = torch.max(torch.nn.functional.softmax(output[0], dim=0), 0)
            
        return self.classes[idx.item()], prob.item() * 100