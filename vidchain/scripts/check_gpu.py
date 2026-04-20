import torch
import sys

def main():
    print("\n" + "="*40)
    print(" 🚀 vidchain HARDWARE DIAGNOSTIC 🚀 ")
    print("="*40)

    print(f"Python Version:  {sys.version.split()[0]}")
    print(f"PyTorch Version: {torch.__version__}")

    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available:  {cuda_available}")

    print("-" * 40)

    if cuda_available:
        gpu_name = torch.cuda.get_device_name(0)
        vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        cuda_version = torch.version.cuda
        
        print("✅ STATUS: PERFECT")
        print(f"🖥️  GPU Detected: {gpu_name}")
        print(f"💾 Total VRAM:   {vram_total:.2f} GB")
        print(f"⚙️  CUDA Version: {cuda_version}")
        print("="*40)
        print("You are ready to run the vidchain CLI!")
    else:
        print("❌ STATUS: CPU ONLY")
        print("PyTorch cannot see your NVIDIA GPU.")
        print("="*40)
        print("\nTo fix this, run the following command in your terminal:")
        print("pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --force-reinstall")

if __name__ == "__main__":
    main()
