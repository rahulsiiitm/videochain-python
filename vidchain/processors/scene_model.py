# vidchain/processors/scene_model.py
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

class SceneEngine:
    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        
        # Define global environment categories
        self.categories = [
            "a computer workstation", "a messy hostel room", 
            "a professional office", "a laboratory", 
            "a kitchen", "a bedroom"
        ]

    def predict(self, frame):
        image = Image.fromarray(frame)
        inputs = self.processor(text=self.categories, images=image, return_tensors="pt", padding=True).to(self.device)
        
        outputs = self.model(**inputs)
        logits_per_image = outputs.logits_per_image
        probs = logits_per_image.softmax(dim=1)
        
        # Get the highest probability category
        idx = probs.argmax().item()
        return self.categories[idx]