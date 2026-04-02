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
    data_dir = Path("data/train")
    model_save_dir = Path("models")
    model_save_dir.mkdir(exist_ok=True)
    model_save_path = model_save_dir / "videochain_vision.pth"
    
    batch_size = 32
    epochs = 10
    learning_rate = 0.001

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 Initializing VideoChain Vision Engine on: {device.type.upper()}")

    # ==========================================
    # 2. DATA PIPELINE (IN-MEMORY PROCESSING)
    # ==========================================
    print("⚙️ Setting up Data Pipeline...")
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(), # Data Augmentation
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # Load images and create batches
    dataset = datasets.ImageFolder(root=data_dir, transform=transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    
    class_names = dataset.classes
    num_classes = len(class_names)
    print(f"📂 Loaded {len(dataset)} frames. Classes detected: {class_names}")

    # ==========================================
    # 3. NEURAL NETWORK ARCHITECTURE
    # ==========================================
    print("🧠 Loading MobileNetV3-Small (Edge Optimized)...")
    # Load pre-trained brain
    weights = models.MobileNet_V3_Small_Weights.DEFAULT
    model = models.mobilenet_v3_small(weights=weights)
    
    # VRAM SAFETY PROTOCOL: Freeze the base layers so we don't overwork the RTX 3050
    for param in model.parameters():
        param.requires_grad = False
        
    # Replace the final classification head for our 4 specific categories
    num_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(num_features, num_classes)
    model = model.to(device)

    # ==========================================
    # 4. OPTIMIZER & LOSS FUNCTION
    # ==========================================
    criterion = nn.CrossEntropyLoss()
    # We ONLY train our new 4-class head, saving massive amounts of memory
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
        
        # tqdm progress bar
        progress_bar = tqdm(dataloader, desc=f"Epoch {epoch+1}/{epochs}", unit="batch")
        
        for inputs, labels in progress_bar:
            inputs, labels = inputs.to(device), labels.to(device)

            # Forward pass
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            
            # Backward pass (Learn from mistakes)
            loss.backward()
            optimizer.step()

            # Calculate Live Metrics
            running_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            # Update the terminal display
            current_acc = 100 * correct / total
            progress_bar.set_postfix({"Loss": f"{loss.item():.4f}", "Acc": f"{current_acc:.2f}%"})

        # End of Epoch Summary
        epoch_loss = running_loss / len(dataloader)
        epoch_acc = 100 * correct / total
        print(f"✅ Epoch {epoch+1} Summary -> Average Loss: {epoch_loss:.4f} | Accuracy: {epoch_acc:.2f}%")

    # ==========================================
    # 6. EXPORTING THE BRAIN
    # ==========================================
    torch.save(model.state_dict(), model_save_path)
    
    # Save the class mapping so the Inference Script knows what 0, 1, 2, 3 means
    with open(model_save_dir / "classes.txt", "w") as f:
        f.write("\n".join(class_names))

    elapsed_time = time.time() - start_time
    print(f"\n✨ Training Complete in {elapsed_time/60:.2f} minutes!")
    print(f"💾 Model weights saved to: {model_save_path}")

if __name__ == "__main__":
    train_edge_model()