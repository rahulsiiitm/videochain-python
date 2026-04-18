import cv2
import base64
from typing import Dict, Any
from .base import BaseNode

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

class LlavaNode(BaseNode):
    """
    Vision Language Model (VLM) Node using Ollama's LLaVA or Moondream.
    Extracts deep, contextual scene descriptions that YOLO cannot perceive.
    """
    def __init__(self, model_name: str = "llava:7b", prompt: str = "Describe everything happening in this scene in dense detail. Identify software, interfaces, text, actions, and objects."):
        if not OLLAMA_AVAILABLE:
            raise ImportError("The 'ollama' python package is required for the LlavaNode. Run: pip install ollama")
            
        print(f"[LlavaNode] Initializing VLM Node locally via Ollama ({model_name})...")
        self.model_name = model_name
        self.prompt = prompt
        
        # Verify the model exists on the user's Ollama instance, or try pulling it
        try:
            ollama.show(self.model_name)
        except Exception:
            print(f"[LlavaNode] Warning: {self.model_name} might not be pulled yet. Try running 'ollama run {self.model_name}' first.")

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        frame = context.get("current_frame")
        if frame is None:
            return context

        # Encode OpenCV frame to JPG bytes
        _, buffer = cv2.imencode('.jpg', frame)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        
        try:
            print(f"   👁️ [VLM] Analyzing frame via {self.model_name}...")
            response = ollama.chat(
                model=self.model_name,
                messages=[{
                    'role': 'user',
                    'content': self.prompt,
                    'images': [jpg_as_text]
                }]
            )
            vlm_description = response.get('message', {}).get('content', "").strip()
            
            # Write this ultra-rich description to the objects or scene context
            context["objects"] = vlm_description
            
        except Exception as e:
            print(f"   ⚠️ [VLM Error]: {e}")
            context["objects"] = "VLM Error"

        return context
