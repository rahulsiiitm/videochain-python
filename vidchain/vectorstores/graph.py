"""
vidchain/vectorstores/graph.py
------------------------------
GraphRAG: Temporal Knowledge Graph for entity-level reasoning.
Uses NetworkX to map objects, actions and co-occurrences across time,
enabling multi-hop detective queries that flat ChromaDB cannot answer.
"""

import re
import pickle
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

import networkx as nx


class TemporalKnowledgeGraph:
    """
    Builds a directed temporal knowledge graph from a VidChain timeline.

    Graph structure:
    - Entity nodes  : "person #1", "laptop #2", "ASUS Vivobook" (OCR), etc.
    - Action nodes  : "SUSPICIOUS", "NORMAL" at specific timestamps
    - Edges         : co-occurrence, interaction, temporal sequence

    Enables queries like:
    - "When did person #1 first appear?"
    - "When did person #1 interact with the laptop?"
    - "What was happening when the screen showed 'ASUS Vivobook'?"
    """

    def __init__(self):
        self.G = nx.DiGraph()
        self.entity_timestamps: Dict[str, List[float]] = defaultdict(list)
        self.video_segments: Dict[str, Tuple[float, float]] = {} # video_id -> (start, end)
        self.timeline_length: float = 0.0
        self._is_built = False

    # ──────────────────────────────────────────────────────
    # Builder
    # ──────────────────────────────────────────────────────

    def build_from_timeline(self, timeline: List[Dict[str, Any]], video_id: Optional[str] = None):
        """Parse VidChain timeline and construct the knowledge graph."""
        # Note: We don't clear the graph if adding a new video_id to support multi-video graphs
        if not video_id:
            self.G.clear()
            self.entity_timestamps.clear()
        
        start_ts = float('inf')
        end_ts = 0.0

        for event in timeline:
            ts = float(event.get("time") or event.get("current_time") or 0.0)
            self.timeline_length = max(self.timeline_length, ts)

            # Add timestamp node
            prefix = f"v:{video_id}_" if video_id else ""
            t_node = f"{prefix}t:{ts}"
            self.G.add_node(t_node, type="timestamp", time=ts, video_id=video_id)
            
            start_ts = min(start_ts, ts)
            end_ts = max(end_ts, ts)

            # ── Parse tracking field (legacy pipeline) ────
            entities_this_frame = []
            for track_str in event.get("tracking") or []:
                entity = self._extract_entity_id(track_str)
                if entity:
                    entities_this_frame.append(entity)
                    self._add_entity(entity, ts, t_node, video_id=video_id, action=event.get("action"))

            # ── Parse objects field ───────────────────────
            objects_str = event.get("objects", "") or ""
            # Only parse if it's a short YOLO-style string, not a VLM paragraph
            if len(objects_str) < 120:
                yolo_entities = self._parse_yolo_objects(objects_str)
                if yolo_entities:
                    for obj in yolo_entities:
                        if obj not in entities_this_frame:
                            entities_this_frame.append(obj)
                            self._add_entity(obj, ts, t_node, video_id=video_id, action=event.get("action"))
                else:
                    # Treat as a descriptive scene entity
                    clean_obj = objects_str.strip().rstrip(".")
                    if clean_obj and clean_obj not in entities_this_frame:
                        entities_this_frame.append(clean_obj)
                        self._add_entity(clean_obj, ts, t_node, video_id=video_id, action=event.get("action"))

            # ── Parse OCR field ───────────────────────────
            ocr_text = event.get("ocr")
            if ocr_text:
                ocr_node = f"ocr:{ocr_text.strip()}"
                self.G.add_node(ocr_node, type="ocr_text", text=ocr_text, video_id=video_id)
                self.G.add_edge(t_node, ocr_node, relation="screen_shows")
                self.entity_timestamps[ocr_node].append(ts)

            # ── Co-occurrence edges ───────────────────────
            for i, e1 in enumerate(entities_this_frame):
                for e2 in entities_this_frame[i + 1:]:
                    if not self.G.has_edge(e1, e2):
                        self.G.add_edge(e1, e2, relation="co-occurs", timestamps=[ts])
                    else:
                        self.G[e1][e2].setdefault("timestamps", []).append(ts)

                audio_node = f"{prefix}audio:{ts}"
                self.G.add_node(audio_node, type="audio", time=ts, video_id=video_id)
                self.G.add_edge(t_node, audio_node, relation="audio_at")

            # ── Camera Motion ─────────────────────────────
            motion = event.get("camera_motion")
            if motion and motion != "static":
                motion_node = f"motion:{motion}"
                if not self.G.has_node(motion_node):
                    self.G.add_node(motion_node, type="camera_behavior", movement=motion)
                self.G.add_edge(t_node, motion_node, relation="camera_behavior_is")

        if video_id:
            self.video_segments[video_id] = (start_ts, end_ts)

        self._is_built = True
        print(f"[GraphRAG] Graph updated: {self.G.number_of_nodes()} nodes, {self.G.number_of_edges()} edges.")

    def _add_entity(self, entity: str, ts: float, t_node: str, video_id: Optional[str] = None, action: Optional[str] = None):
        """Add an entity node and link it to the timestamp."""
        if not self.G.has_node(entity):
            self.G.add_node(entity, type="entity", first_seen=ts, last_seen=ts, video_id=video_id)
        else:
            self.G.nodes[entity]["last_seen"] = max(self.G.nodes[entity].get("last_seen", ts), ts)

        self.entity_timestamps[entity].append(ts)
        self.G.add_edge(t_node, entity, relation="detects", action=action or "NORMAL")

    # ──────────────────────────────────────────────────────
    # Query API
    # ──────────────────────────────────────────────────────

    def get_entity_timeline(self, entity_name: str) -> List[float]:
        """Return all timestamps where the given entity was detected."""
        # Fuzzy match against graph nodes
        matches = [n for n in self.entity_timestamps if entity_name.lower() in n.lower()]
        timestamps = []
        for m in matches:
            timestamps.extend(self.entity_timestamps[m])
        return sorted(set(timestamps))

    def get_cooccurrences(self, entity1: str, entity2: str) -> List[float]:
        """Return timestamps where both entities appeared in the same frame."""
        ts1 = set(self.get_entity_timeline(entity1))
        ts2 = set(self.get_entity_timeline(entity2))
        return sorted(ts1 & ts2)

    def get_all_entities(self) -> List[Dict[str, Any]]:
        """Return a list of all tracked entities with their first/last seen timestamps."""
        entities = []
        for node, data in self.G.nodes(data=True):
            if data.get("type") == "entity":
                entities.append({
                    "entity": node,
                    "first_seen": data.get("first_seen"),
                    "last_seen": data.get("last_seen"),
                    "total_appearances": len(self.entity_timestamps.get(node, []))
                })
        return sorted(entities, key=lambda x: x["first_seen"] or 0)

    def link_entities(self, entity_a: str, entity_b: str, relation: str = "same_as"):
        """Creates a manual link between two entities or an entity and a description."""
        if not self.G.has_node(entity_a):
            self.G.add_node(entity_a, type="entity")
        if not self.G.has_node(entity_b):
            self.G.add_node(entity_b, type="entity")
        
        self.G.add_edge(entity_a, entity_b, relation=relation)
        print(f"[GraphRAG] Manual Link: {entity_a} --({relation})--\u003e {entity_b}")

    def get_graph_context(self, query: str, video_id: Optional[str] = None) -> str:
        """
        Extracts relevant graph facts in natural language for RAG prompt injection.
        IRIS uses this as additional factual context before answering.
        """
        if not self._is_built:
            return ""

        lines = ["[GraphRAG Temporal Facts]"]
        if video_id:
            lines.append(f"Source Video: {video_id}")

        # Entity timeline summary
        entities = self.get_all_entities()
        if video_id:
            entities = [e for e in entities if self.G.nodes[e["entity"]].get("video_id") == video_id or e["entity"] in self.entity_timestamps]

        if entities:
            lines.append("\nHigh-Fidelity VLM Observations:")
            for e in entities:
                node_data = self.G.nodes[e["entity"]]
                vid = node_data.get("video_id", "unknown")
                ts_list = self.entity_timestamps.get(e["entity"], [])
                
                if video_id:
                    ts_list = [
                        self.G.nodes[t]["time"] 
                        for t in self.G.predecessors(e["entity"]) 
                        if self.G.nodes[t].get("type") == "timestamp" and self.G.nodes[t].get("video_id") == video_id
                    ]
                
                if not ts_list and video_id: continue

                lines.append(
                    f"  • {e['entity']} (in {vid}): first seen at {min(ts_list) if ts_list else e['first_seen']}s, "
                    f"last seen at {max(ts_list) if ts_list else e['last_seen']}s, "
                    f"appeared {len(ts_list)} time(s)"
                )

        # Identity Resolutions (Manual Links)
        links = [
            (u, v, d) for u, v, d in self.G.edges(data=True)
            if d.get("relation") in ["same_as", "potentially_same_as", "potentially_same_as"]
        ]
        if links:
            lines.append("\nEntity Identity Resolutions:")
            for u, v, d in links:
                lines.append(f"  • {u} is identified as {v} (Relation: {d['relation']})")

        # Camera Motion Summary
        motions = [n for n, d in self.G.nodes(data=True) if d.get("type") == "camera_behavior"]
        if video_id:
            motions = [m for m in motions if any(self.G.nodes[t].get("video_id") == video_id for t in self.G.predecessors(m))]

        if motions:
            lines.append("\nSignificant camera movements detected:")
            for m in motions:
                # Find timestamps for this motion
                ts_list = [
                    self.G.nodes[t]["time"] 
                    for t in self.G.predecessors(m) 
                    if self.G.nodes[t].get("type") == "timestamp" and (not video_id or self.G.nodes[t].get("video_id") == video_id)
                ]
                if ts_list:
                    movement = self.G.nodes[m]["movement"]
                    lines.append(f"  • {movement}: detected at {sorted(ts_list)}")

        # Co-occurrence relationships
        cooccur_edges = [
            (u, v, d) for u, v, d in self.G.edges(data=True)
            if d.get("relation") == "co-occurs"
        ]
        if video_id:
            # Filter co-occurrences that happen in this video
            # A co-occurrence (u,v) happens in video_id at ts if v:{video_id}_t:{ts} exists
            prefix = f"v:{video_id}_"
            cooccur_edges = [
                (u, v, d) for u, v, d in cooccur_edges
                if any(self.G.has_node(f"{prefix}t:{ts}") for ts in d.get("timestamps", []))
            ]
        
        if cooccur_edges:
            lines.append("\nEntity co-occurrences (shared frames):")
            for u, v, d in cooccur_edges[:8]:
                ts = sorted(set(d.get("timestamps", [])))
                if video_id:
                    # Filter timestamps to only those in the current video
                    # This is complex because we only stored numbers.
                    # But we can check self.entity_timestamps intersections.
                    pass 
                lines.append(f"  • {u} + {v} together at: {ts[:3]}")

        # OCR facts
        ocr_nodes = [(n, d) for n, d in self.G.nodes(data=True) if d.get("type") == "ocr_text"]
        if video_id:
            ocr_nodes = [o for o in ocr_nodes if o[1].get("video_id") == video_id]

        if ocr_nodes:
            lines.append("\nText visible on screen:")
            for n, d in ocr_nodes:
                ts_list = self.entity_timestamps.get(n, [])
                if video_id:
                    # Filter timestamps
                    ts_list = [
                        self.G.nodes[t]["time"] 
                        for t in self.G.predecessors(n) 
                        if self.G.nodes[t].get("type") == "timestamp" and self.G.nodes[t].get("video_id") == video_id
                    ]
                if not ts_list: continue
                lines.append(f"  • \"{d.get('text')}\" first seen at {ts_list[0]}s")

        return "\n".join(lines)

    def describe(self) -> str:
        """Human-readable graph summary."""
        if not self._is_built:
            return "Graph not yet built."
        entities = self.get_all_entities()
        return (
            f"Knowledge Graph: {self.G.number_of_nodes()} nodes, "
            f"{self.G.number_of_edges()} edges, "
            f"{len(entities)} distinct entities tracked over {self.timeline_length:.1f}s"
        )

    # ──────────────────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────────────────

    def save_to_disk(self, file_path: str):
        """Pickles the graph and metadata to disk."""
        data = {
            "G": self.G,
            "entity_timestamps": dict(self.entity_timestamps),
            "timeline_length": self.timeline_length
        }
        with open(file_path, "wb") as f:
            pickle.dump(data, f)
        print(f"[GraphRAG] Persistent index saved -> {file_path}")

    def load_from_disk(self, file_path: str) -> bool:
        """Loads a pickled graph from disk. Returns True on success."""
        try:
            with open(file_path, "rb") as f:
                data = pickle.load(f)
                self.G = data["G"]
                self.entity_timestamps = defaultdict(list, data["entity_timestamps"])
                self.timeline_length = data["timeline_length"]
                self._is_built = True
            print(f"[GraphRAG] Persistent index loaded from -> {file_path}")
            return True
        except Exception as e:
            print(f"[GraphRAG] Load failed (normal if first run): {e}")
            return False

    # ──────────────────────────────────────────────────────
    # Parsers
    # ──────────────────────────────────────────────────────

    @staticmethod
    def _extract_entity_id(track_str: str) -> Optional[str]:
        """Extract entity ID like 'person #1' or 'laptop #2' from tracking string."""
        match = re.match(r"(\w[\w\s]*#\d+)", track_str.strip())
        return match.group(1).strip() if match else None

    @staticmethod
    def _parse_yolo_objects(objects_str: str) -> List[str]:
        """Parse YOLO-style '2 persons, 1 laptop' into generic entity tokens."""
        entities = []
        # Match patterns like "1 laptop", "2 persons", "1 person"
        for match in re.finditer(r"(\d+)\s+([\w]+)", objects_str.lower()):
            count, obj = int(match.group(1)), match.group(2).rstrip("s")
            for i in range(1, count + 1):
                entities.append(f"{obj}")
        return entities
