import ollama
import json
import os

class OllamaRAGEngine:
    def __init__(self, model_name="llama3", kb_path="knowledge_base.json"):
        self.model_name = model_name
        
        if not os.path.exists(kb_path):
            raise FileNotFoundError(f"❌ Could not find {kb_path}. Run build_knowledge_base.py first.")
            
        with open(kb_path, 'r') as f:
            self.video_data = json.load(f)

    def ask(self, question):
        prompt = f"""
        You are a precise Video Analysis AI. I am providing a chronological log of a video.
        Use ONLY this data to answer the user's question. 
        Always include the exact timestamp in your answer.

        VIDEO KNOWLEDGE BASE:
        {json.dumps(self.video_data, indent=2)}

        USER QUESTION: 
        {question}
        """

        # Sending the prompt to your local GPU
        response = ollama.chat(model=self.model_name, messages=[
            {'role': 'system', 'content': 'You are a helpful security and video analysis assistant.'},
            {'role': 'user', 'content': prompt},
        ])
        
        return response['message']['content']