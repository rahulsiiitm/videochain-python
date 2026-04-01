import cv2
import os
from scenedetect import detect, ContentDetector

class VideoLoader:
    def __init__(self, output_dir="temp_frames"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_keyframes(self, video_path):
        """
        Uses ContentDetector (Adaptive Sampling) to find scene changes.
        This follows the 'Query-Aware Extraction' logic from iRAG (2026).
        """
        print(f"[VideoChain] Detecting scenes in {video_path}...")
        scene_list = detect(video_path, ContentDetector())
        
        cap = cv2.VideoCapture(video_path)
        keyframes = []

        for i, scene in enumerate(scene_list):
            # Get the middle frame of the scene for the best semantic representation
            start_frame = scene[0].get_frames()
            end_frame = scene[1].get_frames()
            mid_frame = (start_frame + end_frame) // 2
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
            ret, frame = cap.read()
            
            if ret:
                timestamp = mid_frame / cap.get(cv2.CAP_PROP_FPS)
                frame_path = os.path.join(self.output_dir, f"scene_{i}_{timestamp:.2f}.jpg")
                cv2.imwrite(frame_path, frame)
                keyframes.append({"path": frame_path, "timestamp": timestamp})
        
        cap.release()
        print(f"[VideoChain] Extracted {len(keyframes)} keyframes.")
        return keyframes