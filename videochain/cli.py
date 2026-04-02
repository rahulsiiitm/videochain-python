import sys
from .processor import VideoProcessor
from .vision import VisionEngine
from .rag import RAGEngine
from .core.fusion import FusionEngine

def main():
    if len(sys.argv) < 2:
        print("Usage: videochain-analyze <video_path>")
        return

    video_path = sys.argv[1]
    
    # Initialize YOLO-based components
    vision = VisionEngine(model_path="yolov8n.pt") 
    rag = RAGEngine(mode="Security")
    processor = VideoProcessor(video_path)
    fusion = FusionEngine()

    # 1. Run Advanced Multimodal Extraction
    v_data, a_text, volume = processor.extract_context(vision)
    
    # 2. Fuse the data and build the Knowledge Base
    # We wrap the text in the expected timeline format
    fusion.generate_knowledge_base(v_data, [{"start": 0, "text": a_text}])
    
    # 3. Load memory into the RAG
    rag.load_knowledge("knowledge_base.json")

    print(f"\n✅ Analysis Complete. Peak Audio Volume: {volume:.4f}")
    print("💬 VideoChain Chat Active. Ask about the burglary (Type 'exit' to quit).")

    while True:
        query = input("\n👤 User: ")
        if query.lower() in ['exit', 'quit']: break
        print(f"🤖 AI: {rag.query(query)}")

if __name__ == "__main__":
    main()