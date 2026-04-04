import argparse
import sys
import os
import warnings
import torch

# ==========================================
# 🛑 AGGRESSIVE WARNING SUPPRESSION
# ==========================================
warnings.filterwarnings("ignore")
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3" # Suppress TensorFlow if backend uses it
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1" # Avoid Hugging Face token warnings if not logged in

from vidchain.processor import VideoProcessor
from vidchain.rag import RAGEngine
from vidchain.core.fusion import FusionEngine
from vidchain.vision import VisionEngine as YoloEngine
from vidchain.processors.vision_model import VisionEngine as ActionEngine

def print_hardware_status(step=""):
    """Prints current GPU status and VRAM usage."""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated(0) / (1024 ** 2)
        print(f"🖥️  [GPU] {step} | VRAM Used: {allocated:.1f} MB")
    else:
        print(f"🖥️  [CPU] {step} | (CUDA NOT DETECTED)")

def main():
    parser = argparse.ArgumentParser(description="vidchain: Multimodal RAG CLI")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument("--llm", default="gemini/gemini-2.5-flash", help="LLM backend")
    parser.add_argument("--ocr-lang", nargs="+", default=["en"], help="OCR languages")
    parser.add_argument("--query", help="Single-shot query", default=None)
    args = parser.parse_args()

    if not os.path.exists(args.video_path):
        print(f"[ERROR] Video file not found: {args.video_path}")
        sys.exit(1)

    print(f"\n[INFO] vidchain Analysis — {args.video_path}")
    print(f"[INFO] LLM: {args.llm} | OCR languages: {args.ocr_lang}")
    print("-" * 50)

    # ── Hardware Check ─────────────────────────────────────
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"[SYSTEM] Hardware Engine: GPU Active ({gpu_name} - {vram_total:.1f} GB VRAM)")
    else:
        print("[SYSTEM] ⚠️ Hardware Engine: CPU ONLY. PyTorch cannot find your NVIDIA GPU.")
        print("[SYSTEM] ⚠️ Please reinstall PyTorch with CUDA support for hardware acceleration.")

    # ── Vision models ──────────────────────────────────────
    print("\n[INFO] Booting Dual-Vision Models...")
    yolo_model = YoloEngine(model_path="yolov8s.pt", confidence_threshold=0.25)
    action_model = ActionEngine(model_path="models/vidchain_vision.pth")
    print_hardware_status("Vision Models Loaded")

    # ── Extraction ─────────────────────────────────────────
    print("\n[INFO] Extracting Scene Graphs, Audio & OCR...")
    processor = VideoProcessor(args.video_path, ocr_languages=args.ocr_lang)
    fusion = FusionEngine(output_file="knowledge_base.json")

    v_data, a_data, ocr_data, volume = processor.extract_context(yolo_engine=yolo_model, action_engine=action_model)
    print_hardware_status("Extraction Complete")

    print("\n[INFO] Fusing into Knowledge Base...")
    fusion.generate_knowledge_base(v_data, a_data, ocr_data)
    print(f"[SUCCESS] Peak Audio Volume: {volume:.4f}")

    # ── RAG ────────────────────────────────────────────────
    print(f"\n[INFO] Initializing VidChain RAG Architecture ({args.llm})...")
    rag = RAGEngine(model_name=args.llm)
    
    print("-" * 50)
    print("[SYSTEM] B.A.B.U.R.A.O. Engine Online.")
    print("[SYSTEM] (Behavioral Analysis & Broadcasting Unit for Real-time Artificial Observation)")
    print("-" * 50)

    # ── Single-shot query mode ─────────────────────────────
    if args.query:
        print(f"\n[QUERY] {args.query}")
        print(f"AI: {rag.query(args.query)}")
        return

    # ── Interactive chat ───────────────────────────────────
    print("\n[SYSTEM] Chat active. Type 'exit' to quit.")
    while True:
        try:
            user_input = input("\nUser: ").strip()
            if user_input.lower() in ("exit", "quit"):
                print("[SYSTEM] Session terminated.")
                break
            if not user_input:
                continue
            print(f"AI: {rag.query(user_input, top_k=10)}")
        except KeyboardInterrupt:
            print("\n(┬┬﹏┬┬) Session terminated.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()