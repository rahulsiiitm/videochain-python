import json


class FusionEngine:
    def __init__(self, output_file="knowledge_base.json"):
        self.output_file = output_file

    def generate_knowledge_base(self, vision_data, audio_data, ocr_data=None):
        """
        Fuses all modalities into unified per-timestamp entries.

        Each entry contains everything observed at that moment:
        objects, action, ocr text, and any overlapping audio.
        """
        print("[VideoChain] Fusing multimodal data streams...")
        ocr_data = ocr_data or []

        # Index OCR and audio by timestamp for O(1) lookup during merge
        # OCR: exact timestamp match
        ocr_map = {o["timestamp"]: o["text"] for o in ocr_data}

        # Audio: map each audio segment to any visual timestamp that falls within it
        # (audio segments span a duration, visuals are point-in-time)
        def get_audio_at(ts):
            for a in audio_data:
                start = a.get("start", a.get("time", 0))
                end = a.get("end", start + 3.0)  # default 3s window if no end
                if start <= ts <= end:
                    return a["text"]
            return None

        timeline = []

        for v in vision_data:
            ts = v["timestamp"]

            # Parse objects and action out of the scene graph label
            # Label format: "Duration: [Xs - Ys] | Subjects: ... | Action State: ..."
            label = v["label"]
            objects = _extract(label, "Subjects:", "| Action")
            action = _extract(label, "Action State:", None)
            duration = _extract(label, "Duration:", "| Subjects")

            entry = {
                "time": ts,
                "duration": duration.strip() if duration else None,
                "objects": objects.strip() if objects else "no significant objects",
                "action": action.strip() if action else "UNKNOWN",
                "ocr": ocr_map.get(ts),          # text seen on screen at this frame
                "audio": get_audio_at(ts),        # speech overlapping this moment
            }

            timeline.append(entry)

        # Also append any audio segments that didn't overlap any visual timestamp
        visual_times = {v["timestamp"] for v in vision_data}
        for a in audio_data:
            start = a.get("start", a.get("time", 0))
            if not any(abs(start - vt) < 1.0 for vt in visual_times):
                timeline.append({
                    "time": start,
                    "duration": None,
                    "objects": None,
                    "action": None,
                    "ocr": None,
                    "audio": a["text"],
                })

        timeline.sort(key=lambda x: x["time"])

        knowledge_base = {
            "metadata": {
                "total_frames_analyzed": len(vision_data),
                "audio_segments": len(audio_data),
                "ocr_events": len(ocr_data),
                "total_timeline_entries": len(timeline),
            },
            "timeline": timeline
        }

        with open(self.output_file, "w") as f:
            json.dump(knowledge_base, f, indent=4)

        print(f"[VideoChain] ✅ Knowledge Base saved to {self.output_file}")
        print(f"             Frames: {len(vision_data)} | Audio: {len(audio_data)} | OCR: {len(ocr_data)}")
        return knowledge_base


def _extract(text: str, start_marker: str, end_marker: str | None) -> str:
    """Extract substring between two markers."""
    try:
        start = text.index(start_marker) + len(start_marker)
        if end_marker and end_marker in text[start:]:
            end = text.index(end_marker, start)
            return text[start:end]
        return text[start:]
    except ValueError:
        return ""