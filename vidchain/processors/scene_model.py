"""
vidchain/processors/scene_model.py
------------------------------------
CLIP-based Scene Understanding Engine.
Classifies the environment/setting of each keyframe using zero-shot
image-text matching — no training required.

Rate-limited by processor.py (default: once per 10 seconds) since
CLIP inference is heavier than YOLO on 4GB VRAM.
"""

import torch
import numpy as np
from PIL import Image
from typing import Optional, List

DEFAULT_CATEGORIES = [
    "a computer workstation or office desk",
    "a bedroom or living room",
    "a kitchen or dining area",
    "a hallway or corridor",
    "an outdoor area or street",
    "a retail store or shop",
    "a laboratory or workshop",
    "a lecture room or classroom",
]


class SceneEngine:
    """
    Zero-shot scene classifier using OpenAI CLIP.
    Answers: "What kind of environment is this frame from?"
    """

    def __init__(
        self,
        model_name: str = "openai/clip-vit-base-patch32",
        categories: Optional[List[str]] = None,
    ):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.categories = categories or DEFAULT_CATEGORIES

        try:
            from transformers import CLIPProcessor, CLIPModel
            print(f"[VidChain] Scene Engine (CLIP) loading on {self.device.upper()}...")
            self.model     = CLIPModel.from_pretrained(model_name).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(model_name)
            self._available = True
            print("[VidChain] Scene Engine ready.")
        except Exception as e:
            print(f"[VidChain] Scene Engine unavailable: {e}")
            print("[VidChain] Install with: pip install transformers")
            self._available = False
            self.model     = None
            self.processor = None

    def predict(self, frame: np.ndarray) -> Optional[str]:
        """
        Classifies a BGR frame into one of the scene categories.
        Returns the best-matching category string, or None if unavailable.
        """
        if not self._available:
            return None

        try:
            image = Image.fromarray(frame[:, :, ::-1])  # BGR -> RGB

            inputs = self.processor(
                text=self.categories,
                images=image,
                return_tensors="pt",
                padding=True
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)
                probs   = outputs.logits_per_image.softmax(dim=1)[0]

            best_idx   = int(probs.argmax().item())
            best_score = float(probs[best_idx].item())

            # Skip low-confidence results — CLIP is guessing below 15%
            if best_score < 0.15:
                return None

            return self.categories[best_idx]

        except Exception as e:
            print(f"[Scene WARNING] Frame skipped: {e}")
            return None

    def add_category(self, category: str):
        """Dynamically add a new scene category without reloading the model."""
        if category not in self.categories:
            self.categories.append(category)

    def set_categories(self, categories: List[str]):
        """Replace the full category list."""
        self.categories = categories