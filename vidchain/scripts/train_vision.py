import os
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader
from tqdm import tqdm
from pathlib import Path

def train_edge_model():
    # ==========================================
    # 1. CONFIGURATION & HARDWARE SETUP
    # ==========================================
    # Use paths relative to current execution context
    data_dir = Path("data/train")
    model_save_dir = Path("models")
    model_save_dir.mkdir(exist_ok=True, parents=True)
    model_save_path = model_save_dir / "vidchain_vision.pth"
    
    batch_size = 32
    epochs = 10
    learning_rate = 0.001

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 Initializing vidchain Vision Engine on: {device.type.upper()}")

    # ==========================================
    # 2. DATA PIPELINE
    # ==========================================
    if not data_dir.exists():
        print(f"❌ Error: Training data not found at {data_dir.absolute()}")
        return

    print("⚙️ Setting up Data Pipeline...")
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    dataset = datasets.ImageFolder(root=data_dir, transform=transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    
    class_names = dataset.classes
    num_classes = len(class_names)
    print(f"📂 Loaded {len(dataset)} frames. Classes detected: {class_names}")

    # ==========================================
    # 3. NEURAL NETWORK ARCHITECTURE
    # ==========================================
    print("🧠 Loading MobileNetV3-Small (Edge Optimized)...")
    weights = models.MobileNet_V3_Small_Weights.DEFAULT
    model = models.mobilenet_v3_small(weights=weights)
    
    for param in model.parameters():
        param.requires_grad = False
        
    num_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(num_features, num_classes)
    model = model.to(device)

    # ==========================================
    # 4. OPTIMIZER & LOSS FUNCTION
    # ==========================================
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.classifier.parameters(), lr=learning_rate)

    # ==========================================
    # 5. THE TRAINING LOOP
    # ==========================================
    print("\n🔥 Starting Training Sequence...")
    start_time = time.time()

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        progress_bar = tqdm(dataloader, desc=f"Epoch {epoch+1}/{epochs}", unit="batch")
        
        for inputs, labels in progress_bar:
            inputs, labels = inputs.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            current_acc = 100 * correct / total
            progress_bar.set_postfix({"Loss": f"{loss.item():.4f}", "Acc": f"{current_acc:.2f}%"})

        epoch_loss = running_loss / len(dataloader)
        epoch_acc = 100 * correct / total
        print(f"✅ Epoch {epoch+1} Summary -> Average Loss: {epoch_loss:.4f} | Accuracy: {epoch_acc:.2f}%")

    # ==========================================
    # 6. EXPORTING THE BRAIN
    # ==========================================
    torch.save({
        "model_state_dict": model.state_dict(),
        "classes": class_names
    }, model_save_path)

    elapsed_time = time.time() - start_time
    print(f"\n✨ Training Complete in {elapsed_time/60:.2f} minutes!")
    print(f"💾 Model saved to: {model_save_path}")

def main():
    train_edge_model()

if __name__ == "__main__":
    main()
