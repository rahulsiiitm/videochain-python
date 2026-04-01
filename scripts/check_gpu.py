import torch
import sys

print("-" * 30)
print(f"Python Version: {sys.version.split()[0]}")
print(f"PyTorch Version: {torch.__version__}")

cuda_available = torch.cuda.is_available()
print(f"CUDA Available: {cuda_available}")

if cuda_available:
    print(f"GPU Device: {torch.cuda.get_device_name(0)}")
    print(f"Current VRAM Usage: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")
else:
    print("❌ GPU NOT DETECTED. Running on CPU.")
    print("Tip: If you have an RTX 3050, reinstall torch with the CUDA index.")
print("-" * 30)