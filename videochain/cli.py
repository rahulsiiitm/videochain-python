import argparse
import sys
import os

from videochain.processor import VideoProcessor
from videochain.rag import RAGEngine
from videochain.core.fusion import FusionEngine

# Import BOTH vision engines (we alias them so Python doesn't get confused)
from videochain.vision import VisionEngine as YoloEngine
from videochain.processors.vision_model import VisionEngine as ActionEngine

def main():
    parser = argparse.ArgumentParser(description="VideoChain: Multimodal RAG CLI")
    parser.add_argument("video_path", help="Path to the video file")
    parser.add_argument("--llm", default="gemini/gemini-2.5-flash", help="Choose the LLM")
    args = parser.parse_args()

    if not os.path.exists(args.video_path):
        print(f"[ERROR] Video file not found at {args.video_path}")
        sys.exit(1)

    print(f"\n[INFO] Starting VideoChain Analysis on: {args.video_path}")
    print(f"[INFO] Powered by: {args.llm}")
    print("-" * 50)

    # =================================================================
    # STEP 1: LOAD VISION MODELS (DUAL-BRAIN)
    # =================================================================
    print("\n[INFO] Step 1: Booting Dual-Vision Models...")
    # Load YOLO for Objects
    yolo_model = YoloEngine(model_path="yolov8n.pt") 
    # Load MobileNet for Intent
    action_model = ActionEngine(model_path="models/videochain_vision.pth") 

    # =================================================================
    # STEP 2: MULTIMODAL EXTRACTION
    # =================================================================
    print("[INFO] Step 2: Extracting Scene Graphs & Audio Timestamps...")
    processor = VideoProcessor(args.video_path)
    fusion = FusionEngine(output_file="knowledge_base.json")
    
    # Pass BOTH models into our new processor
    v_data, a_data, volume = processor.extract_context(yolo_model, action_model)
    
    print("[INFO] Step 3: Fusing Data into Knowledge Base...")
    # Pass the actual synced audio data, not the hardcoded string
    fusion.generate_knowledge_base(v_data, a_data)
    print(f"[SUCCESS] Extraction complete. Peak Audio Volume: {volume:.4f}")

    # =================================================================
    # STEP 3: THE FAISS RAG ENGINE
    # =================================================================
    print(f"\n[INFO] Step 4: Initializing AI Engine ({args.llm})...")
    rag = RAGEngine(model_name=args.llm)
    
    if not rag.load_knowledge("knowledge_base.json"):
        print("[ERROR] Failed to start chat. Knowledge base is missing or corrupted.")
        sys.exit(1)

    # =================================================================
    # STEP 4: CHAT LOOP
    # =================================================================
    print("\n[SYSTEM] VideoChain Chat Active. Type 'exit' or 'quit' to terminate.")
    
    while True:
        try:
            user_input = input("\nUser: ").strip()
            
            if user_input.lower() in ['exit', 'quit']:
                print("[SYSTEM] Exiting VideoChain. Session terminated.")
                break
            
            if not user_input:
                continue

            print(f"[SYSTEM] Analyzing video memory for: '{user_input}'...")
            response = rag.query(user_input, top_k=10)
            
            print(f"AI: {response}")

        except KeyboardInterrupt:
            print("\n[SYSTEM] Exiting VideoChain. Session terminated.")
            break
        except Exception as e:
            print(f"\n[ERROR] Chat Exception: {e}")

if __name__ == "__main__":
    main()