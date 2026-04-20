from vidchain.vectorstores.graph import TemporalKnowledgeGraph
import json

def test_graph_logic():
    # Initialize Graph directly (no heavy AI engines)
    kg = TemporalKnowledgeGraph()
    
    # ── Video 1 ──
    v1_id = "alpha"
    v1_timeline = [
        {"time": 0.0, "objects": "1 person", "tracking": ["person #1"], "action": "NORMAL"},
        {"time": 5.0, "objects": "1 person, 1 laptop", "tracking": ["person #1", "laptop #1"], "ocr": "Alice"},
    ]
    print(f"Ingesting {v1_id}...")
    kg.build_from_timeline(v1_timeline, video_id=v1_id)
    
    # ── Video 2 ──
    v2_id = "beta"
    v2_timeline = [
        {"time": 10.0, "objects": "A woman is typing on a Macbook. She wears a red shirt.", "action": "NORMAL"},
        {"time": 15.0, "objects": "1 person", "tracking": ["person #1"], "ocr": "Error 404"},
    ]
    print(f"Ingesting {v2_id}...")
    kg.build_from_timeline(v2_timeline, video_id=v2_id)
    
    # ── Link Entities ──
    kg.link_entities("person #1", "v:beta_desc:10.0", relation="same_as")
    
    # ── Verify Context ──
    context = kg.get_graph_context("search")
    print("\n--- Graph Context ---")
    print(context)
    
    # Validation
    assert "alpha" in context
    assert "beta" in context
    assert "High-Fidelity VLM Observations" in context
    assert "Entity Identity Resolutions" in context
    assert "person #1 is identified as v:beta_desc:10.0" in context
    
    print("\n[SUCCESS] GraphRAG Refinement Logic Verified.")

if __name__ == "__main__":
    test_graph_logic()
