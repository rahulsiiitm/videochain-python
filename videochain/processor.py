import cv2
import whisper # type: ignore
import librosa
import numpy as np

class VideoProcessor:
    def __init__(self, video_path):
        self.video_path = video_path
        print("[INFO] Loading Whisper Audio Model (base)...")
        self.audio_model = whisper.load_model("base")

    def extract_context(self, yolo_engine, action_engine):
        print("[INFO] Extracting Audio Timestamps (Whisper)...")
        raw_audio_result = self.audio_model.transcribe(self.video_path)
        
        audio_segments = []
        for segment in raw_audio_result.get('segments', []):
            audio_segments.append({
                "start": round(segment['start'], 2),
                "text": segment['text'].strip()
            })
        
        y, sr = librosa.load(self.video_path, sr=None)
        peak_volume = np.max(librosa.feature.rms(y=y))

        print("[INFO] Extracting Scene Graphs (Dual-Brain)...")
        cap = cv2.VideoCapture(self.video_path)
        raw_events = []
        fps = cap.get(cv2.CAP_PROP_FPS)
        prev_gray = None
        frame_idx = 0

        # ==========================================
        # 1. RAW EXTRACTION & NOISE SUPPRESSION
        # ==========================================
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                diff = cv2.absdiff(prev_gray, gray)
                
                if np.mean(diff) > 2.0: 
                    objects, _ = yolo_engine.predict(frame)
                    
                    # --- NOISE SUPPRESSION ---
                    # If the room is empty, force action to NORMAL to prevent hallucinations
                    if objects == "no significant objects":
                        action = "NORMAL"
                    else:
                        action, _ = action_engine.predict(frame)
                        # Clean up uncertainty
                        if action.lower() == "uncertain":
                            action = "NORMAL"
                    
                    raw_events.append({
                        "timestamp": round(frame_idx/fps, 2),
                        "objects": objects,
                        "action": action.upper()
                    })
            
            prev_gray = gray
            frame_idx += int(fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

        cap.release()

        # ==========================================
        # 2. SEMANTIC CHUNKING (The Magic)
        # ==========================================
        print("[INFO] Compressing timeline via Semantic Chunking...")
        chunked_events = []
        
        if raw_events:
            # Initialize the first chunk
            current_chunk = {
                "start_time": raw_events[0]["timestamp"],
                "end_time": raw_events[0]["timestamp"],
                "objects": raw_events[0]["objects"],
                "action": raw_events[0]["action"]
            }

            for i in range(1, len(raw_events)):
                event = raw_events[i]
                
                # If the scene is the exact same, just extend the time!
                if event["action"] == current_chunk["action"] and event["objects"] == current_chunk["objects"]:
                    current_chunk["end_time"] = event["timestamp"]
                else:
                    # The scene changed! Save the old chunk.
                    scene_graph = f"Duration: [{current_chunk['start_time']}s - {current_chunk['end_time']}s] | Subjects: {current_chunk['objects']} | Action State: {current_chunk['action']}"
                    chunked_events.append({
                        "timestamp": current_chunk["start_time"], 
                        "label": scene_graph
                    })
                    
                    # Start a new chunk
                    current_chunk = {
                        "start_time": event["timestamp"],
                        "end_time": event["timestamp"],
                        "objects": event["objects"],
                        "action": event["action"]
                    }

            # Append the final chunk when the video ends
            scene_graph = f"Duration: [{current_chunk['start_time']}s - {current_chunk['end_time']}s] | Subjects: {current_chunk['objects']} | Action State: {current_chunk['action']}"
            chunked_events.append({
                "timestamp": current_chunk["start_time"],
                "label": scene_graph
            })

        return chunked_events, audio_segments, peak_volume