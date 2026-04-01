import torch
import torchvision.models as models # type: ignore
import torchvision.transforms as transforms # type: ignore
from PIL import Image

class VisionProcessor:
    def __init__(self):
        # 1. Detect your RTX 3050 (Crucial for 15-day speed)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[VideoChain] Vision using device: {self.device}")

        # 2. Load MobileNetV3 (Lightweight, perfect for rapid prototyping)
        # Using 'DEFAULT' weights for pre-trained ImageNet knowledge
        self.model = models.mobilenet_v3_small(weights="DEFAULT")
        self.model.to(self.device)
        self.model.eval()

        # 3. Standard Image Transformations for Computer Vision
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def predict_frame(self, image_path):
        """
        Processes a single frame. Currently returns a placeholder,
        but runs through the actual model to verify CUDA works.
        """
        img = Image.open(image_path).convert("RGB")
        img_t = self.transform(img).unsqueeze(0).to(self.device) # type: ignore

        with torch.no_grad():
            _ = self.model(img_t) # Run inference
        
        return "Normal Activity"