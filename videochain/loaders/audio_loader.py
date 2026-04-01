from moviepy import VideoFileClip  # Direct import for v2.x
import os

class AudioLoader:
    def __init__(self, output_dir="temp_audio"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_audio(self, video_path):
        print(f"[VideoChain] Extracting audio from {video_path}...")
        
        # Load the video file
        with VideoFileClip(video_path) as video:
            audio_path = os.path.join(self.output_dir, "extracted_audio.mp3")
            # In v2.x, we use write_audiofile directly on the audio attribute
            video.audio.write_audiofile(audio_path, logger=None) # type: ignore
            
        return audio_path