import time
import torch
import psutil
import os
import cv2
from vidchain.client import VidChain
from vidchain.pipeline import VideoChain
from vidchain.nodes import AdaptiveKeyframeNode, TrackerNode, WhisperNode, YoloNode, OcrNode

def get_vram():
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated(0) / (1024 ** 2)
    return 0

def benchmark():
    video_path = "sample.mp4"
    if not os.path.exists(video_path):
        print("sample.mp4 not found")
        return

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    duration = total_frames / fps
    cap.release()

    print(f"--- Benchmarking VidChain on {video_path} ---")
    print(f"Duration: {duration:.2f}s | Total Frames: {total_frames}")
    
    vc = VidChain(config={
        "llm_provider": "gemini/gemini-2.5-flash",
        "db_path": "./vidchain_benchmark_storage"
    })

    frame_skip = 15 # 2 FPS
    chain = VideoChain(
        nodes=[
            AdaptiveKeyframeNode(change_threshold=5.0),
            TrackerNode(),
            WhisperNode(model_size="base"),
            YoloNode(confidence=0.5),
            OcrNode(languages=["en"]),
        ],
        frame_skip=frame_skip
    )

    start_time = time.time()
    initial_vram = get_vram()
    initial_ram = psutil.virtual_memory().used / (1024 ** 2)
    
    print("Starting ingestion...")
    video_id = vc.ingest(
        video_source=video_path,
        chain=chain
    )
    end_time = time.time()
    peak_vram = get_vram()
    peak_ram = psutil.virtual_memory().used / (1024 ** 2)
    
    total_time = end_time - start_time
    
    # Get timeline to calculate reduction rate
    kb_path = f"./vidchain_benchmark_storage/knowledge_bases/{video_id}.json"
    import json
    with open(kb_path, "r") as f:
        kb_data = json.load(f)
    
    timeline = kb_data.get("timeline", [])
    frames_sampled = total_frames // frame_skip
    frames_accepted = len(timeline)
    reduction_rate = (1 - (frames_accepted / frames_sampled)) * 100 if frames_sampled > 0 else 0
    
    print("\n" + "="*30)
    print("      REAL TEST RESULTS")
    print("="*30)
    print(f"Video ID: {video_id}")
    print(f"Ingestion Time: {total_time:.2f}s")
    print(f"Frames Sampled: {frames_sampled}")
    print(f"Frames Accepted: {frames_accepted}")
    print(f"Reduction Rate: {reduction_rate:.2f}%")
    print(f"Peak VRAM: {peak_vram:.2f}MB")
    print(f"RAM Usage Delta: {peak_ram - initial_ram:.2f}MB")
    
    # Query performance
    query = "What is happening in the video?"
    print(f"\nQuerying: '{query}'...")
    q_start = time.time()
    response = vc.ask(query, video_id=video_id)
    q_end = time.time()
    
    print(f"Query Response Time: {q_end - q_start:.2f}s")
    print(f"Response: {response}")
    print("="*30)

if __name__ == "__main__":
    benchmark()
