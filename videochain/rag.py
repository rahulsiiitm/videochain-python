import requests
import json

class RAGEngine:
    def __init__(self, model="llama3", mode="Security"):
        # We use llama3.2:1b as it's much faster for your 4GB VRAM
        self.url = "http://localhost:11434/api/generate"
        self.model = model
        self.mode = mode
        self.video_memory = {"timeline": []}

    def load_knowledge(self, file_path="knowledge_base.json"):
        """Loads the fused timeline created by the FusionEngine."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                self.video_memory["timeline"] = data.get("timeline", [])
            print(f"✅ Knowledge Base loaded from {file_path}")
        except FileNotFoundError:
            print("⚠️ No Knowledge Base found. Run analysis first.")

    def query(self, user_question):
        """Answers questions based ONLY on the loaded timeline context."""
        # Convert the fused timeline into a text summary for the AI
        context_str = "\n".join([f"[{e['time']}s] {e['type'].upper()}: {e['content']}" 
                                for e in self.video_memory["timeline"]])

        system_prompt = f"""
        You are the VideoChain AI assistant specialized in {self.mode}. 
        Below is the data extracted from a video:
        {context_str}
        
        TASK: Answer the user's question using ONLY the data above. 
        If the information is missing, say "I cannot find evidence of that in the video."
        """

        payload = {
            "model": self.model,
            "prompt": user_question, # FIXED: Matched the function argument
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": 0.1}
        }

        try:
            print(f"🧠 AI is analyzing video memory for: '{user_question}'...")
            response = requests.post(self.url, json=payload, timeout=15)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', "The AI processed the request but returned no text.").strip()
            
        except Exception as e:
            return f"⚠️ RAG Error: Ensure Ollama is running. (Error: {e})"