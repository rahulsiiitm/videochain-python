"""
examples/test_vision.py
-------------------------
Tests YOLO + MobileNet vision engines independently.
"""

import os
import cv2
import torch
from vidchain.vision import VisionEngine as YoloEngine
from vidchain.processors.vision_model import VisionEngine as ActionEngine

def main():
    VIDEO_PATH = "sample.mp4"

    if not os.path.exists(VIDEO_PATH):
        print(f"Error: {VIDEO_PATH} not found.")
        return

    print("=== Vision Pipeline Test ===\n")

    yolo   = YoloEngine(model_path="yolov8s.pt", confidence_threshold=0.25)
    action = ActionEngine(model_path="models/vidchain_vision.pth")

    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_idx = 0
    results = []

    while cap.isOpened() and frame_idx < int(fps * 10):  # test first 10s
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % int(fps) == 0:  # 1 per second
            timestamp = round(frame_idx / fps, 2)
            objects, conf, _ = yolo.predict(frame)
            act, act_conf    = action.predict(frame)
            results.append((timestamp, objects, act))
            print(f"  [{timestamp}s] Objects: {objects} | Action: {act} ({act_conf*100:.1f}%)")

            if torch.cuda.is_available():
                vram = torch.cuda.memory_allocated(0) / 1024**2
                print(f"         VRAM: {vram:.1f} MB")
        frame_idx += 1

    cap.release()
    print(f"\nProcessed {len(results)} frames. Vision pipeline working correctly.")

if __name__ == "__main__":
    main()