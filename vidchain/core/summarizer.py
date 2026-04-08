# """
# VidChain Core: Map-Reduce Video Summarizer
# ------------------------------------------
# Bypasses vector retrieval to perform global temporal summarization.
# Chunks heavy video timelines into digestible blocks to prevent LLM 
# context-window overflow and VRAM crashes.
# """

# import json
# from litellm import completion

# class VideoSummarizer:
#     def __init__(self, model_name="ollama/llama3", chunk_duration_sec=600):
#         """
#         chunk_duration_sec: Defines the size of the "Map" blocks. Default is 600s (10 minutes).
#         """
#         self.model_name = model_name
#         self.chunk_duration = chunk_duration_sec

#     def _chunk_timeline(self, timeline_data: list) -> list:
#         """Slices the JSON timeline into sequential blocks based on timestamps."""
#         chunks = []
#         current_chunk = []
#         current_limit = self.chunk_duration

#         for event in timeline_data:
#             if event["timestamp"] <= current_limit:
#                 current_chunk.append(event)
#             else:
#                 chunks.append(current_chunk)
#                 current_chunk = [event]
#                 current_limit += self.chunk_duration
                
#         if current_chunk:
#             chunks.append(current_chunk)
            
#         return chunks

#     def _map_phase(self, chunks: list) -> list:
#         """Processes each video chunk individually (The 'Map' step)."""
#         print(f"\n[INFO] Starting Map Phase: Processing {len(chunks)} temporal chunks...")
#         chapter_summaries = []

#         for i, chunk in enumerate(chunks):
#             print(f"  -> Summarizing Chapter {i + 1}/{len(chunks)}...")
            
#             # Format the chunk into raw text for the LLM
#             chunk_text = "\n".join([
#                 f"[{evt['timestamp']}s] Camera: {evt.get('camera', 'static')} | Subjects: {evt['subjects']} | Action: {evt['action']}"
#                 for evt in chunk
#             ])

#             prompt = f"""You are a forensic analyst. Read this chronological log of a video segment and write a concise, 3-sentence summary of what happened. Do not mention that you are reading a log.
            
#             LOG DATA:
#             {chunk_text}
#             """

#             response = completion(
#                 model=self.model_name,
#                 messages=[{"role": "user", "content": prompt}]
#             )
#             chapter_summaries.append(f"Chapter {i + 1}: {response.choices[0].message.content}")

#         return chapter_summaries

#     def _reduce_phase(self, chapter_summaries: list) -> str:
#         """Fuses all chapter summaries into a final master narrative (The 'Reduce' step)."""
#         print("\n[INFO] Starting Reduce Phase: Synthesizing final narrative...")
        
#         combined_text = "\n\n".join(chapter_summaries)
        
#         prompt = f"""You are B.A.B.U.R.A.O., an elite forensic video AI copilot.
#         You have been provided with sequential chapter summaries of a long video feed.
#         Write a cohesive, engaging master summary of the entire video. 
#         Ensure chronological flow and highlight any escalating situations or key actions.
#         Do not use robotic phrases.
        
#         CHAPTER SUMMARIES:
#         {combined_text}
#         """

#         response = completion(
#             model=self.model_name,
#             messages=[{"role": "system", "content": prompt}]
#         )
#         return response.choices[0].message.content

#     def generate_master_summary(self, kb_path: str = "knowledge_base.json") -> str:
#         """Executes the full Map-Reduce pipeline."""
#         try:
#             with open(kb_path, 'r') as f:
#                 data = json.load(f)
#         except FileNotFoundError:
#             return "[ERROR] Knowledge base not found. Please ingest a video first."

#         if not data.get("timeline"):
#             return "[ERROR] Timeline is empty."

#         # 1. Chunking
#         chunks = _chunk_timeline(self, data["timeline"])
        
#         # 2. Map (Analyze Chapters)
#         chapter_summaries = self._map_phase(chunks)
        
#         # 3. Reduce (Final Polish)
#         final_summary = self._reduce_phase(chapter_summaries)
        
#         return final_summary