import torch
from ultralytics import YOLO  # type: ignore


class VisionEngine:
    def __init__(self, model_path="yolov8n.pt", confidence_threshold=0.3):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Ultralytics auto-handles the device mapping, so we remove .to(self.device)
        self.model = YOLO(model_path)
        
        # 🛑 THE FIX: Force the underlying PyTorch model into strict FP32
        # This prevents the layer-fusion crash on RTX 30-series laptops
        if self.device == "cuda":
            self.model.model.float()  # type: ignore
            
        self.threshold = confidence_threshold

    def predict(self, frame):
        """Returns (summary_string, avg_confidence, raw_detections)."""
        
        # 🛑 THE FIX: Pass half=False to stop AutoBackend from triggering the FP16 crash
        results = self.model(frame, conf=self.threshold, verbose=False, half=False)[0]

        names  = results.names
        counts = {}
        raw_detections = []  # (label, x1, y1, x2, y2)

        for i, box in enumerate(results.boxes):
            label = names[int(box.cls)]
            counts[label] = counts.get(label, 0) + 1
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            raw_detections.append((label, int(x1), int(y1), int(x2), int(y2)))

        if not counts:
            return "no significant objects", 0.0, []

        summary  = ", ".join([f"{c} {l}" for l, c in counts.items()])
        avg_conf = results.boxes.conf.mean().item() * 100 if len(results.boxes) > 0 else 0.0
        return summary, avg_conf, raw_detections