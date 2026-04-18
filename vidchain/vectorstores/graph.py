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
        self.timeline_length: float = 0.0
        self._is_built = False

    # ──────────────────────────────────────────────────────
    # Builder
    # ──────────────────────────────────────────────────────

    def build_from_timeline(self, timeline: List[Dict[str, Any]]):
        """Parse VidChain timeline and construct the knowledge graph."""
        self.G.clear()
        self.entity_timestamps.clear()

        for event in timeline:
            ts = float(event.get("time") or event.get("current_time") or 0.0)
            self.timeline_length = max(self.timeline_length, ts)

            # Add timestamp node
            t_node = f"t:{ts}"
            self.G.add_node(t_node, type="timestamp", time=ts)

            # ── Parse tracking field (legacy pipeline) ────
            entities_this_frame = []
            for track_str in event.get("tracking") or []:
                entity = self._extract_entity_id(track_str)
                if entity:
                    entities_this_frame.append(entity)
                    self._add_entity(entity, ts, t_node, action=event.get("action"))

            # ── Parse objects field ───────────────────────
            objects_str = event.get("objects", "") or ""
            # Only parse if it's a short YOLO-style string, not a VLM paragraph
            if len(objects_str) < 120:
                for obj in self._parse_yolo_objects(objects_str):
                    if obj not in entities_this_frame:
                        entities_this_frame.append(obj)
                        self._add_entity(obj, ts, t_node, action=event.get("action"))

            # ── Parse OCR field ───────────────────────────
            ocr_text = event.get("ocr")
            if ocr_text:
                ocr_node = f"ocr:{ocr_text.strip()}"
                self.G.add_node(ocr_node, type="ocr_text", text=ocr_text)
                self.G.add_edge(t_node, ocr_node, relation="screen_shows")
                self.entity_timestamps[ocr_node].append(ts)

            # ── Co-occurrence edges ───────────────────────
            for i, e1 in enumerate(entities_this_frame):
                for e2 in entities_this_frame[i + 1:]:
                    if not self.G.has_edge(e1, e2):
                        self.G.add_edge(e1, e2, relation="co-occurs", timestamps=[ts])
                    else:
                        self.G[e1][e2].setdefault("timestamps", []).append(ts)

            # ── Audio node ────────────────────────────────
            audio = event.get("audio")
            if audio:
                audio_node = f"audio:{ts}"
                self.G.add_node(audio_node, type="audio", text=audio, time=ts)
                self.G.add_edge(t_node, audio_node, relation="audio_at")

        self._is_built = True
        print(f"[GraphRAG] Graph built: {self.G.number_of_nodes()} nodes, {self.G.number_of_edges()} edges.")

    def _add_entity(self, entity: str, ts: float, t_node: str, action: Optional[str] = None):
        """Add an entity node and link it to the timestamp."""
        if not self.G.has_node(entity):
            self.G.add_node(entity, type="entity", first_seen=ts, last_seen=ts)
        else:
            self.G.nodes[entity]["last_seen"] = ts

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

    def get_graph_context(self, query: str) -> str:
        """
        Extracts relevant graph facts in natural language for RAG prompt injection.
        B.A.B.U.R.A.O. uses this as additional factual context before answering.
        """
        if not self._is_built:
            return ""

        lines = ["[GraphRAG Temporal Facts]"]

        # Entity timeline summary
        entities = self.get_all_entities()
        if entities:
            lines.append("\nDetected entities and their presence:")
            for e in entities:
                ts_list = self.entity_timestamps.get(e["entity"], [])
                lines.append(
                    f"  • {e['entity']}: first seen at {e['first_seen']}s, "
                    f"last seen at {e['last_seen']}s, "
                    f"appeared {e['total_appearances']} time(s)"
                )

        # Co-occurrence relationships
        cooccur_edges = [
            (u, v, d) for u, v, d in self.G.edges(data=True)
            if d.get("relation") == "co-occurs"
        ]
        if cooccur_edges:
            lines.append("\nEntity co-occurrences (shared frames):")
            for u, v, d in cooccur_edges[:8]:  # Limit for token budget
                ts = sorted(set(d.get("timestamps", [])))[:3]
                lines.append(f"  • {u} + {v} together at: {ts}")

        # OCR facts
        ocr_nodes = [(n, d) for n, d in self.G.nodes(data=True) if d.get("type") == "ocr_text"]
        if ocr_nodes:
            lines.append("\nText visible on screen:")
            for n, d in ocr_nodes:
                ts_list = self.entity_timestamps.get(n, [])
                lines.append(f"  • \"{d.get('text')}\" first seen at {ts_list[0] if ts_list else '?'}s")

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
