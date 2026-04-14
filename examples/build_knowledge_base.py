"""
examples/build_knowledge_base.py
---------------------------------
Demonstrates VidChain's Python API for programmatic video ingestion.
"""

import os
from vidchain import VidChain

def main():
    VIDEO_PATH = "sample.mp4"

    if not os.path.exists(VIDEO_PATH):
        print(f"Error: {VIDEO_PATH} not found.")
        return

    print("\n=== VidChain Library Demo ===\n")

    vc = VidChain(config={
        "llm_provider": "gemini/gemini-2.5-flash",
        "db_path": "./vidchain_storage"
    }) #type: ignore

    print(f"Ingesting: {VIDEO_PATH}")
    video_id = vc.ingest(VIDEO_PATH)
    print(f"Video ID: {video_id}")

    print("\n--- Querying ---")
    for q in [
        "What is happening in the video?",
        "Was anyone acting suspiciously?",
        "What objects were detected?",
    ]:
        print(f"\nQ: {q}")
        print(f"A: {vc.ask(q)}")

    print("\n--- Summary ---")
    print(vc.summarize_video(video_id, depth="concise"))

if __name__ == "__main__":
    main()