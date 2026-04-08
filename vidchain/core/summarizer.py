"""
vidchain/core/summarizer.py
--------------------------
Advanced Map-Reduce Narrative Engine.
Features: Recursive Summarization, Contextual Bridging, and Provider Abstraction.
"""

import math
from typing import List, Dict, Any, Optional
from litellm import completion

class VideoSummarizer:
    def __init__(self, model_name: str = "ollama/phi3", max_words_per_chunk: int = 1500):
        """
        max_words_per_chunk: Controls the density of the 'Map' phase to fit LLM context windows.
        """
        self.model_name = model_name
        self.max_words = max_words_per_chunk

    def _serialize_for_summary(self, event: Dict[str, Any]) -> str:
        """Converts a raw event into a dense string for the LLM to read."""
        # We prioritize Action, OCR, and Audio as they drive the narrative
        parts = [f"[{event.get('timestamp', 0)}s]"]
        if event.get('action'): parts.append(f"Action: {event['action']}")
        if event.get('objects'): parts.append(f"Visuals: {event['objects']}")
        if event.get('ocr'): parts.append(f"Text: {event['ocr']}")
        if event.get('audio'): parts.append(f"Speech: {event['audio']}")
        return " | ".join(parts)

    def _chunk_by_token_limit(self, timeline: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Smarter Chunking: Instead of fixed time, we chunk by data density.
        A busy 1-minute scene is more important than 1 hour of an empty room.
        """
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

    def generate(self, timeline: List[Dict[str, Any]], mode: str = "concise") -> str:
        """
        The Main Entry Point. Handles recursive reduction if the video is massive.
        """
        if not timeline:
            return "No data available to summarize."

        print(f"[Summarizer] Processing {len(timeline)} events in '{mode}' mode...")
        
        # 1. Map Phase: Summarize individual chapters
        chunks = self._chunk_by_token_limit(timeline)
        chapter_summaries = self._map_phase(chunks)

        # 2. Recursive Reduce: If we have too many chapters, reduce them in groups
        # This allows summarizing 24-hour feeds without crashing
        final_narrative = self._recursive_reduce(chapter_summaries, mode)
        
        return final_narrative

    def _map_phase(self, chunks: List[List[Dict[str, Any]]]) -> List[str]:
        summaries = []
        for i, chunk in enumerate(chunks):
            print(f"  -> Mapping Chapter {i+1}/{len(chunks)}...")
            chunk_text = "\n".join([self._serialize_for_summary(e) for e in chunk])
            
            prompt = f"""Summarize this video segment logs into a dense narrative.
            Focus on escalating actions, key subjects, and any spoken dialogue.
            
            DATA:
            {chunk_text}
            """
            
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3 # Low temperature for factual accuracy
            )
            summaries.append(response.choices[0].message.content)
        return summaries

    def _recursive_reduce(self, summaries: List[str], mode: str) -> str:
        """
        Fuses summaries together. If there are > 5 summaries, it reduces them 
        into sub-summaries first to prevent context loss.
        """
        if len(summaries) == 1:
            return self._final_polish(summaries[0], mode)

        # Group summaries into sets of 5 to maintain high detail
        print(f"  -> Reducing {len(summaries)} chapters...")
        grouped_summaries = []
        for i in range(0, len(summaries), 5):
            batch = "\n\n".join(summaries[i:i+5])
            prompt = f"Combine these sequential video summaries into one flowing narrative:\n\n{batch}"
            
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            grouped_summaries.append(response.choices[0].message.content)

        # Recurse until we have one final summary
        return self._recursive_reduce(grouped_summaries, mode)

    def _final_polish(self, raw_summary: str, mode: str) -> str:
        """Applies the B.A.B.U.R.A.O. persona and requested formatting."""
        persona = "You are B.A.B.U.R.A.O., an elite forensic AI."
        style = "Write a cohesive, engaging story." if mode == "concise" else "Provide a detailed chronological breakdown."
        
        prompt = f"{persona} {style} Polish this summary:\n\n{raw_summary}"
        
        response = completion(
            model=self.model_name,
            messages=[{"role": "system", "content": prompt}]
        )
        return response.choices[0].message.content.strip()