import os
import easyocr
import numpy as np
import torch
import re

OCR_TRIGGER_LABELS = {
    "laptop", "tv", "monitor", "cell phone", "book",
    "keyboard", "remote", "tablet", "screen", "whiteboard"
}

MIN_TEXT_LENGTH = 3
NOISE_PATTERN = re.compile(r"[^a-zA-Z0-9\s.,!?;:'\"-]")


class OCRProcessor:
    def __init__(self, languages=["en"], gpu=None):
        cuda_ok = torch.cuda.is_available()
        self.use_gpu = cuda_ok if gpu is None else gpu

        if self.use_gpu:
            # Windows: EasyOCR ignores torch CUDA context unless env var is set first
            os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
            torch.zeros(1).cuda()  # warm up CUDA before EasyOCR spawns its context

        print(f"[VideoChain] OCR Engine initializing on: {'CUDA' if self.use_gpu else 'CPU'}")
        self.reader = easyocr.Reader(languages, gpu=self.use_gpu, verbose=False)
        print("[VideoChain] OCR Engine ready.")

        # Deduplication: suppress repeated identical OCR text across consecutive frames
        self._last_text: str | None = None

    def should_run(self, detected_objects: str) -> bool:
        """Only trigger OCR when YOLO sees a surface that could contain text."""
        if not detected_objects or detected_objects == "no significant objects":
            return False
        lowered = detected_objects.lower()
        return any(trigger in lowered for trigger in OCR_TRIGGER_LABELS)

    def extract_text(self, frame: np.ndarray) -> str | None:
        """
        Runs OCR on a frame. Returns cleaned text only if it differs from the
        previous accepted result (deduplication), or None if nothing useful found.
        """
        try:
            rgb_frame = frame[:, :, ::-1]  # BGR -> RGB
            results = self.reader.readtext(rgb_frame, detail=1, paragraph=False)

            if not results:
                return None

            meaningful = [
                text.strip()
                for (_, text, conf) in results
                if conf >= 0.4 and len(text.strip()) >= MIN_TEXT_LENGTH
            ]

            if not meaningful:
                return None

            raw = " | ".join(meaningful)
            cleaned = NOISE_PATTERN.sub("", raw)
            cleaned = " ".join(cleaned.split())

            if len(cleaned) < MIN_TEXT_LENGTH:
                return None

            # Deduplication: skip if identical to last accepted text
            if cleaned == self._last_text:
                return None

            self._last_text = cleaned
            return cleaned

        except Exception as e:
            print(f"[OCR WARNING] Frame skipped: {e}")
            return None