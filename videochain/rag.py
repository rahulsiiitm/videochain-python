import requests
import json

class RAGEngine:
    def __init__(self, model="llama3", mode="Security"):
        """
        Initializes the Video-RAG Brain.
        :param model: The Ollama model name (llama3.2:1b is recommended for RTX 3050).
        :param mode: The deployment environment (Security, Healthcare, Retail).
        """
        self.url = "http://localhost:11434/api/generate"
        self.model = model
        self.mode = mode
        
        # This stores the "Memory" of the video once processed
        self.video_memory = {
            "visual_events": [], # List of detected actions (e.g., ["walk", "fall"])
            "transcript": "",    # The text from Whisper audio extraction
            "metadata": {}       # Camera ID, Time, etc.
        }

    def update_memory(self, visual_events=None, transcript=None, metadata=None):
        """Updates the RAG's internal knowledge of the current video."""
        if visual_events:
            # We use set() to keep unique events for the summary
            self.video_memory["visual_events"] = list(set(visual_events))
        if transcript:
            self.video_memory["transcript"] = transcript
        if metadata:
            self.video_memory["metadata"].update(metadata)

    def query(self, user_question):
        """
        The core RAG function: Answers user questions based ONLY on video data.
        """
        # 1. Construct the Knowledge Context
        events_str = ", ".join(self.video_memory["visual_events"]) if self.video_memory["visual_events"] else "No specific actions detected."
        transcript_str = self.video_memory["transcript"] if self.video_memory["transcript"] else "No audio detected."
        
        # 2. Build the System Prompt (The 'True RAG' instruction)
        system_prompt = f"""
        You are the VideoChain AI assistant specialized in {self.mode}. 
        You have analyzed a video and extracted the following data:
        
        - VISUAL EVENTS DETECTED: {events_str}
        - AUDIO TRANSCRIPT: "{transcript_str}"
        
        Your task is to answer the user's question using ONLY the information provided above. 
        If the information is not in the video data, say "I cannot find evidence of that in the video."
        Be precise, professional, and brief.
        """

        # 3. Prepare the Payload
        payload = {
            "model": self.model,
            "prompt": user_query,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.2, # Keep it factual, not creative
                "num_predict": 150
            }
        }

        # 4. Request from Ollama
        try:
            print(f"🧠 RAG is searching video memory for: '{user_question}'...")
            response = requests.post(self.url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', "The AI brain returned an empty response.").strip()
            
        except requests.exceptions.RequestException as e:
            return f"⚠️ RAG Connection Error: Ensure Ollama is running and '{self.model}' is pulled. (Error: {e})"

    def generate_instant_alert(self, label):
        """
        Short-circuit function for real-time alerts without a user question.
        """
        prompt = f"Vision just detected a {label} event. Generate a 1-sentence {self.mode} alert."
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        
        try:
            res = requests.post(self.url, json=payload, timeout=5)
            return res.json().get('response', f"Alert: {label} detected.").strip()
        except:
            return f"REAL-TIME ALERT: {label.upper()} detected (LLM Offline)."