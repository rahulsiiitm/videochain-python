import json
import os

class FusionEngine:
    def __init__(self, output_file="knowledge_base.json"):
        self.output_file = output_file

    def generate_knowledge_base(self, vision_data, audio_data):
        """
        Fuses vision and audio streams into a single chronological timeline.
        vision_data: List of dicts {'timestamp': float, 'label': str}
        audio_data: List of dicts {'start': float, 'end': float, 'text': str}
        """
        print("[VideoChain] Fusing multimodal data streams...")
        
        knowledge_base = {
            "metadata": {
                "total_frames_analyzed": len(vision_data),
                "audio_segments": len(audio_data)
            },
            "timeline": []
        }

        # Combine and Sort by timestamp
        # We create a unified "event" list
        full_timeline = []

        # Add Vision Events
        for v in vision_data:
            full_timeline.append({
                "time": v['timestamp'],
                "type": "visual",
                "content": v['label']
            })

        # Add Audio Events
        for a in audio_data:
            full_timeline.append({
                "time": a['start'],
                "type": "acoustic",
                "content": a['text']
            })

        # Sort everything chronologically so the LLM sees the story unfold
        full_timeline.sort(key=lambda x: x['time'])
        
        knowledge_base["timeline"] = full_timeline

        # Save to disk
        with open(self.output_file, 'w') as f:
            json.dump(knowledge_base, f, indent=4)
            
        print(f"[VideoChain] ✅ Knowledge Base fused and saved to {self.output_file}")
        return knowledge_base