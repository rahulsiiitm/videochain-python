"""
examples/multi_video_search.py
--------------------------------
Demonstrates querying across multiple ingested videos
and scoping queries to a specific video.
"""

import os
from vidchain import VidChain

def main():
    vc = VidChain(config={
        "llm_provider": "gemini/gemini-2.5-flash",
        "db_path": "./vidchain_storage"
    }) #type: ignore

    # Ingest multiple videos with explicit IDs
    videos = {
        "cam1": "cam1.mp4",
        "cam2": "cam2.mp4",
    }

    for vid_id, path in videos.items():
        if not os.path.exists(path):
            print(f"Skipping {path} — file not found.")
            continue
        print(f"\nIngesting {path} as '{vid_id}'...")
        vc.ingest(path, video_id=vid_id)

    print("\n--- Cross-video query (all cameras) ---")
    print(vc.ask("Was anyone seen acting suspiciously?"))

    print("\n--- Scoped query (cam1 only) ---")
    print(vc.ask("What happened in this footage?", video_id="cam1"))

    print("\n--- Indexed videos ---")
    print(vc.list_indexed_videos())

if __name__ == "__main__":
    main()