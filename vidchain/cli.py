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
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

from vidchain.client import VidChain

def print_hardware_status():
    """Prints current GPU status and VRAM usage."""
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        allocated = torch.cuda.memory_allocated(0) / (1024 ** 2)
        print(f"[SYSTEM] Hardware Engine: GPU Active ({gpu_name})")
        print(f"[VRAM] Total: {vram_total:.1f} GB | Currently Used: {allocated:.1f} MB")
    else:
        print("[SYSTEM] Hardware Engine: CPU ONLY. (CUDA NOT DETECTED)")

def main():
    parser = argparse.ArgumentParser(description="vidchain: Multimodal RAG CLI")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument("--llm", default="gemini/gemini-2.5-flash", help="LLM backend")
    parser.add_argument("--ocr-lang", nargs="+", default=["en"], help="OCR languages")
    parser.add_argument("--query", help="Single-shot query", default=None)
    parser.add_argument(
        "--vlm",
        default="moondream",
        metavar="MODEL",
        help="Ollama VLM model for visual captioning (default: moondream). Use --fast to skip VLM."
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Use legacy YOLO pipeline instead of VLM. Faster for long videos but less descriptive."
    )
    parser.add_argument(
        "--emotion",
        action="store_true",
        help="Enable modular EmotionNode for behavioral sentiment analysis (DeepFace)."
    )
    parser.add_argument(
        "--action",
        action="store_true",
        help="Enable modular ActionNode for situational 'verb' analysis (MobileNet)."
    )
    args = parser.parse_args()

    if not os.path.exists(args.video_path):
        print(f"[ERROR] Video file not found: {args.video_path}")
        sys.exit(1)

    print(f"\n[INFO] VidChain Analysis — {args.video_path}")
    print(f"[INFO] LLM: {args.llm} | OCR languages: {args.ocr_lang}")
    print("-" * 50)

    # ── Hardware Check ─────────────────────────────────────
    print_hardware_status()

    # ── Initialize VidChain Orchestrator ───────────────────
    # Zero-Config: Engines (YOLO/Action) are NOT loaded yet.
    vc = VidChain(config={
        "llm_provider": args.llm,
        "db_path": "./vidchain_storage"
    })

    # ── Progress Callback (Multi-Sensor Pulse) ─────────────
    def progress_callback(node_name: str, msg: str):
        """Unified status ticker for the modular sensory chain."""
        sys.stdout.write(f'\r\033[K[SENSORY PULSE] {node_name}: {msg}')
        sys.stdout.flush()

    # ── Build pipeline chain ──────────────────────────────
    chain = None
    from vidchain.pipeline import VideoChain
    from vidchain.nodes import AdaptiveKeyframeNode, WhisperNode, OcrNode, ActionNode, TrackerNode
    
    if not args.fast:
        vlm_model = args.vlm  # defaults to "moondream"
        from vidchain.nodes import LlavaNode
        print(f"[INFO] Mode: HIGH-FIDELITY (VLM: {vlm_model} + Action + OCR)")
        chain = VideoChain(
            nodes=[
                AdaptiveKeyframeNode(change_threshold=5.0),
                TrackerNode(),
                WhisperNode(model_size="base"),
                LlavaNode(model_name=vlm_model),
                OcrNode(languages=args.ocr_lang),
            ],
            frame_skip=15  # 2 FPS
        )
    else:
        from vidchain.nodes import YoloNode
        print("[INFO] Mode: FAST (YOLOv8 + Action + OCR)")
        chain = VideoChain(
            nodes=[
                AdaptiveKeyframeNode(change_threshold=5.0),
                TrackerNode(),
                WhisperNode(model_size="base"),
                YoloNode(confidence=0.5),
                OcrNode(languages=args.ocr_lang),
            ],
            frame_skip=30 # 1 FPS for speed
        )

    # ── Modular Node Injections ──────────────────────────
    if args.emotion:
        from vidchain.nodes import EmotionNode
        print("[INFO] SENSOR INJECTION: EmotionNode Active.")
        chain.nodes.append(EmotionNode())
    
    if args.action:
        from vidchain.nodes import ActionNode
        print("[INFO] SENSOR INJECTION: ActionNode Active.")
        chain.nodes.append(ActionNode())

    # ── Extraction & Ingestion ──────────────────────────────
    print("\n[INFO] Initializing Forensic Intelligence Scan...")
    
    try:
        video_id = vc.ingest(
            video_source=args.video_path,
            progress_callback=progress_callback,
            chain=chain
        )
        print(f"\n\n[SUCCESS] Ingestion Complete. Video ID: {video_id}")
        
        # ── NEW: Automatic Forensic Executive Summary ──────────
        print("\n[SYSTEM] Generating Forensic Executive Summary...")
        summary = vc.summarize_video(video_id, depth="detailed")
        print("\n" + "="*60)
        print("📜 INTELLIGENCE REPORT")
        print("="*60)
        print(summary)
        print("="*60 + "\n")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n\n[ERROR] Ingestion failed: {e}")
        sys.exit(1)

    print("-" * 50)
    print("[SYSTEM] B.A.B.U.R.A.O. Engine Online.")
    print("[SYSTEM] (Behavioral Analysis & Broadcasting Unit for Real-time Artificial Observation)")
    print("-" * 50)

    # ── Single-shot query mode ─────────────────────────────
    if args.query:
        print(f"\n[QUERY] {args.query}")
        print(f"AI: {vc.ask(args.query, video_id=video_id)}")
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
            
            # vc.ask handles both video search and conversational memory
            response = vc.ask(user_input, video_id=video_id)
            print(f"AI: {response}")
            
        except KeyboardInterrupt:
            print("\n\n(┬┬﹏┬┬) Session terminated.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()