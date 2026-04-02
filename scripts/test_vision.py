import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from pathlib import Path
import random
import os

def test_inference():
    # 1. Load the Class Map
    class_file = Path("models/classes.txt")
    if not class_file.exists():
        print("❌ Error: classes.txt not found. Did the training script finish?")
        return
        
    with open(class_file, "r") as f:
        classes = f.read().splitlines()

    # 2. Rebuild the Brain Architecture
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 Booting Inference Engine on: {device.type.upper()}")
    
    model = models.mobilenet_v3_small(weights=None) # We don't need internet weights anymore!
    num_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(num_features, len(classes))
    
    # Load YOUR custom weights
    model_path = "models/videochain_vision.pth"
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model = model.to(device)
    model.eval() # Set to evaluation mode (turns off training features)

    # 3. Vision Preprocessing (No data augmentation here, just resizing)
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # 4. Grab a Random Test Subject
    train_dir = Path("data/train")
    random_class = random.choice(classes)
    class_dir = train_dir / random_class
    images = [f for f in os.listdir(class_dir) if f.endswith(('.jpg', '.png'))]
    test_image_name = random.choice(images)
    test_image_path = class_dir / test_image_name

    print(f"\n📸 Analyzing Image: {test_image_name}")
    print(f"✅ True Category: {random_class.upper()}")

    # 5. Make the Prediction
    image = Image.open(test_image_path).convert('RGB')
    input_tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad(): # No gradients needed for inference (saves VRAM)
        output = model(input_tensor)
        probabilities = torch.nn.functional.softmax(output[0], dim=0)
        
        # Get top prediction
        confidence, predicted_idx = torch.max(probabilities, 0)
        predicted_class = classes[predicted_idx.item()]

    # 6. Display Results
    print("-" * 30)
    if predicted_class == random_class:
        print(f"🎯 PREDICTION: {predicted_class.upper()} (CORRECT!)")
    else:
        print(f"❌ PREDICTION: {predicted_class.upper()} (INCORRECT)")
        
    print(f"📊 Confidence: {confidence.item() * 100:.2f}%")
    print("-" * 30)

if __name__ == "__main__":
    test_inference()