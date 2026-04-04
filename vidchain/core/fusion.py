import json
import os


class FusionEngine:
    def __init__(self, output_file="knowledge_base.json"):
        self.output_file = output_file

    def generate_knowledge_base(self, vision_data, audio_data, ocr_data=None):
        """
        Fuses vision, audio, and OCR streams into a single chronological timeline.

        Args:
            vision_data:  List of dicts — {'timestamp': float, 'label': str}
            audio_data:   List of dicts — {'start': float, 'text': str}
            ocr_data:     List of dicts — {'timestamp': float, 'text': str}  (optional)
        """
        print("[vidchain] Fusing multimodal data streams...")

        ocr_data = ocr_data or []

        knowledge_base = {
            "metadata": {
                "total_frames_analyzed": len(vision_data),
                "audio_segments": len(audio_data),
                "ocr_events": len(ocr_data)
            },
            "timeline": []
        }

        timeline = []

        for v in vision_data:
            timeline.append({
                "time": v["timestamp"],
                "type": "visual",
                "content": v["label"]
            })

        for a in audio_data:
            timeline.append({
                "time": a["start"],
                "type": "acoustic",
                "content": a["text"]
            })

        for o in ocr_data:
            timeline.append({
                "time": o["timestamp"],
                "type": "ocr",
                "content": o["text"]
            })

        timeline.sort(key=lambda x: x["time"])
        knowledge_base["timeline"] = timeline

        with open(self.output_file, "w") as f:
            json.dump(knowledge_base, f, indent=4)

        print(f"[vidchain] ✅ Knowledge Base saved to {self.output_file}")
        print(f"             Visual: {len(vision_data)} | Audio: {len(audio_data)} | OCR: {len(ocr_data)}")
        return knowledge_base