import torch
from ultralytics import YOLO

class VisionEngine:
    def __init__(self, model_path="yolov8n.pt", confidence_threshold=0.3):
        """
        Entity-aware Vision Engine.
        Replaces simple classification with object detection.
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Let YOLO handle its own memory and device mapping
        self.model = YOLO(model_path)
        self.model.to(self.device)
        
        self.threshold = confidence_threshold

    def predict(self, frame):
        """Detects objects and returns a count summary."""
        # Clean, native Ultralytics prediction call
        results = self.model(frame, conf=self.threshold, verbose=False)[0]
        
        # Get labels and counts (e.g., "2 persons, 1 backpack")
        names = results.names
        counts = {}
        for box in results.boxes.cls:
            label = names[int(box)]
            counts[label] = counts.get(label, 0) + 1
            
        if not counts:
            return "no significant objects", 0.0
            
        summary = ", ".join([f"{c} {l}" for l, c in counts.items()])
        avg_conf = results.boxes.conf.mean().item() * 100 if len(results.boxes) > 0 else 0
        return summary, avg_conf