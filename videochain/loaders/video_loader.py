import cv2
import os
import numpy as np
import shutil

class VideoLoader:
    def __init__(self, output_dir="temp_frames"):
        """
        Initializes the VideoLoader and ensures a clean temporary workspace.
        """
        self.output_dir = output_dir
        
        # Memory Management: Clear old frames
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_keyframes(self, video_path, change_threshold=12.0):
        """
        Smart Adaptive Extraction via Frame Differencing & Gaussian Blur.
        Only extracts a frame if it is significantly different from the LAST SAVED baseline.
        
        change_threshold: The % of pixels that must change to trigger a save.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"❌ Target video not found at: {video_path}")

        print(f"[VideoChain] Running Robust Adaptive Extraction on {video_path}...")
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0 or fps is None: fps = 30.0
        
        ret, prev_frame = cap.read()
        if not ret:
            print("[VideoChain] ❌ Error: Could not read the first frame.")
            return []

        # 1. Establish the Initial Baseline (Grayscale + Blur to remove noise/glare)
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)
        
        # Save the very first frame to establish context (Save the color one, not the blurred one!)
        frame_path = os.path.join(self.output_dir, "scene_0_0.00.jpg")
        cv2.imwrite(frame_path, prev_frame)
        
        keyframes = [{"path": frame_path, "timestamp": 0.0}]
        
        frame_count = 1
        saved_count = 1
        
        # We don't need to check every single frame. Checking 3 times a second is plenty.
        check_interval = int(max(1, fps // 3)) 

        while True:
            ret, curr_frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            
            # Skip frames to save CPU time
            if frame_count % check_interval != 0:
                continue

            # Convert current frame to grayscale and apply the EXACT same blur
            curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
            curr_gray = cv2.GaussianBlur(curr_gray, (21, 21), 0)
            
            # 2. The Subtraction (Spot the difference)
            diff = cv2.absdiff(prev_gray, curr_gray)
            
            # 3. Calculate % of significant pixel changes (Intensity diff > 50 ignores shadows/glare)
            non_zero_count = np.count_nonzero(diff > 50)
            change_percentage = (non_zero_count / diff.size) * 100

            # 4. The Decision Logic
            if change_percentage > change_threshold:
                timestamp = frame_count / fps
                frame_path = os.path.join(self.output_dir, f"scene_{saved_count}_{timestamp:.2f}.jpg")
                
                # Save the image
                cv2.imwrite(frame_path, curr_frame)
                keyframes.append({
                    "path": frame_path, 
                    "timestamp": round(timestamp, 2)
                })
                
                # 🎯 YOUR OPTIMIZATION: Update the blurred baseline!
                prev_gray = curr_gray  
                
                saved_count += 1
                print(f"   📸 Saved Frame at {timestamp:.1f}s (Change: {change_percentage:.1f}%)")

        cap.release()
        print(f"[VideoChain] Adaptive Extraction Complete: Compressed {frame_count} frames down to {saved_count} keyframes.")
        return keyframes

    def cleanup(self):
        """
        Deletes the temporary frames after the Knowledge Base is generated.
        """
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
            print("[VideoChain] Temporary frame cache cleared.")