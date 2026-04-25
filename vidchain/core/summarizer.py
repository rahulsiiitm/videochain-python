"""
vidchain/core/summarizer.py
--------------------------
Advanced Map-Reduce Narrative Engine.
Features: Recursive Summarization, Contextual Bridging, and Provider Abstraction.
"""

import math
from typing import List, Dict, Any, Optional, Callable
from litellm import completion

class VideoSummarizer:
    def __init__(self, model_name: str = "ollama/llama3", max_words_per_chunk: int = 1500):
        """
        max_words_per_chunk: Controls the density of the 'Map' phase to fit LLM context windows.
        """
        self.model_name = model_name
        self.max_words = max_words_per_chunk

    def _serialize_for_summary(self, event: Dict[str, Any]) -> str:
        """Converts a raw event into a dense string for the LLM to read."""
        ts = event.get('time') or event.get('current_time') or event.get('timestamp', 0)
        parts = [f"[{ts}s]"]
        if event.get('action'): parts.append(f"Action: {event['action']}")
        if event.get('objects'): parts.append(f"Visuals: {event['objects']}")
        if event.get('ocr'): parts.append(f"Text: {event['ocr']}")
        if event.get('audio'): parts.append(f"Speech: {event['audio']}")
        return " | ".join(parts)

    def _chunk_by_token_limit(self, timeline: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        chunks = []
        current_chunk = []
        current_word_count = 0

        for event in timeline:
            event_text = self._serialize_for_summary(event)
            word_count = len(event_text.split())
            
            if current_word_count + word_count > self.max_words:
                chunks.append(current_chunk)
                current_chunk = [event]
                current_word_count = word_count
            else:
                current_chunk.append(event)
                current_word_count += word_count
        
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    def generate(self, timeline: List[Dict[str, Any]], mode: str = "concise", status_callback: Optional[Callable[[str], None]] = None) -> str:
        if not timeline:
            return "No data available to summarize."

        print(f"[Summarizer] Processing {len(timeline)} events in '{mode}' mode...")
        
        chunks = self._chunk_by_token_limit(timeline)
        chapter_summaries = self._map_phase(chunks, status_callback)
        final_narrative = self._recursive_reduce(chapter_summaries, mode, status_callback)
        
        return final_narrative

    def _map_phase(self, chunks: List[List[Dict[str, Any]]], status_callback: Optional[Callable[[str], None]] = None) -> List[str]:
        summaries = []
        api_base = "http://localhost:11434" if "ollama" in self.model_name.lower() else None
        
        for i, chunk in enumerate(chunks):
            status_msg = f"Neural HUD: Mapping Chapter {i+1}/{len(chunks)}..."
            print(f"  -> {status_msg}")
            if status_callback: status_callback(status_msg)
            chunk_text = "\n".join([self._serialize_for_summary(e) for e in chunk])
            
            prompt = f"""Summarize this video segment logs into a dense narrative.
            Focus on escalating actions, key subjects, and any spoken dialogue.
            
            DATA:
            {chunk_text}
            """
            
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                api_base=api_base,
                timeout=300
            )
            summaries.append(response.choices[0].message.content)
        return summaries

    def _recursive_reduce(self, summaries: List[str], mode: str, status_callback: Optional[Callable[[str], None]] = None) -> str:
        if len(summaries) == 1:
            return self._final_polish(summaries[0], mode, status_callback)

        status_msg = f"Neural HUD: Reducing {len(summaries)} chapter summaries..."
        print(f"  -> {status_msg}")
        if status_callback: status_callback(status_msg)
        grouped_summaries = []
        api_base = "http://localhost:11434" if "ollama" in self.model_name.lower() else None
        
        for i in range(0, len(summaries), 10):
            batch = "\n\n".join(summaries[i:i+10])
            prompt = f"Combine these sequential video summaries into one flowing narrative:\n\n{batch}"
            
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                api_base=api_base,
                timeout=900
            )
            grouped_summaries.append(response.choices[0].message.content)

        return self._recursive_reduce(grouped_summaries, mode, status_callback)

    def _final_polish(self, raw_summary: str, mode: str, status_callback: Optional[Callable[[str], None]] = None) -> str:
        status_msg = "Neural HUD: Finalizing high-fidelity report..."
        if status_callback: status_callback(status_msg)
        system_prompt = """
        You are IRIS (Intelligent Retrieval & Insight System).
        You are a smart video summarization assistant. 
        Your task is to take raw video summaries and polish them into a clean, direct, and helpful narrative.

        STYLE GUIDELINES:
        - Professional, friendly, and helpful tone.
        - Avoid boilerplate headers like "Video Summary:" or "Additional Insights:".
        - A brief friendly intro is fine, but focus on getting to the facts quickly.
        - If 'concise', provide a punchy, one-paragraph narrative.
        - If 'detailed', provide a flowing chronological account with timestamps.
        - TEMPORAL PERSISTENCE: Assume that the actions and visuals from one timestamp persist throughout any gap until the next event is logged.
        """
        
        user_prompt = f"Polish this preliminary intelligence scan into a final report (Mode: {mode}):\n\n{raw_summary}"
        api_base = "http://localhost:11434" if "ollama" in self.model_name.lower() else None
        
        try:
            response = completion(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                api_base=api_base,
                timeout=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[Summarizer] Polish failed: {e}")
            return raw_summary