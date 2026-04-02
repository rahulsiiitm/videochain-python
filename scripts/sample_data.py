import os
import cv2
import random
import shutil
from pathlib import Path

def extract_multipurpose_frames():
    # 🌟 Notice the updated nested path from your screenshot!
    raw_path = Path("data/raw/cctv_actions/Videos/Videos")
    train_path = Path("data/train")
    
    mapping = {
        "walk": "normal",
        "sneak": "suspicious",
        "fall": "emergency",
        "hit": "violence"
    }

    print("🧹 Preparing fresh training directory...")
    if train_path.exists():
        shutil.rmtree(train_path)
    train_path.mkdir(parents=True)

    for raw_label, clean_label in mapping.items():
        source_dir = raw_path / raw_label
        target_dir = train_path / clean_label
        
        if not source_dir.exists():
            print(f"⚠️ Folder '{raw_label}' not found at {source_dir}. Skipping.")
            continue
            
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Grab the video files
        videos = [f for f in os.listdir(source_dir) if f.lower().endswith(('.mp4', '.avi', '.mkv'))]
        
        if not videos:
            print(f"⚠️ No videos found in {source_dir}")
            continue

        # We sample 20 random videos per category
        sample_videos = random.sample(videos, min(len(videos), 20))
        frames_per_video = 10 # 20 videos * 10 frames = 200 images per class
        
        print(f"🎬 Processing {len(sample_videos)} videos for '{clean_label}'...")
        
        frame_count = 0
        for vid_file in sample_videos:
            vid_path = str(source_dir / vid_file)
            cap = cv2.VideoCapture(vid_path)
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames <= 0:
                continue

            # Calculate interval to get evenly spaced frames across the whole clip
            interval = max(1, total_frames // frames_per_video)

            for i in range(frames_per_video):
                frame_id = i * interval
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
                ret, frame = cap.read()
                
                if ret:
                    # Save the frame as a JPG in your train folder
                    save_path = str(target_dir / f"{raw_label}_{vid_file.split('.')[0]}_f{i}.jpg")
                    cv2.imwrite(save_path, frame)
                    frame_count += 1
                    
            cap.release()

        print(f"✅ Extracted {frame_count} frames for '{clean_label}'.")

    print("\n✨ Dataset Extraction Complete! Your training images are ready.")

if __name__ == "__main__":
    extract_multipurpose_frames()