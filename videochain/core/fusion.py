import json

class FusionEngine:
    def fuse(self, audio_segments, vision_events):
        """
        Zips audio and vision into a single event log for the LLM.
        """
        print("[VideoChain] Fusing data into Temporal Knowledge Base...")
        final_context = []

        for segment in audio_segments:
            # Find any visual events that happened during this audio clip
            visuals = [v['label'] for v in vision_events 
                       if segment['start'] <= v['timestamp'] <= segment['end']]
            
            context_label = visuals[0] if visuals else "No visual change"
            
            final_context.append({
                "time": f"{segment['start']}s - {segment['end']}s",
                "visual": context_label,
                "transcript": segment['text']
            })
            
        return final_context