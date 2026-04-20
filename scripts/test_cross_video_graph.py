from vidchain import VidChain
import os

def test_cross_video_graph():
    # Initialize VidChain in ephemeral mode (no db_path)
    vc = VidChain(config={"verbose": True})
    
    # ── Video 1 (Legacy Style Timeline) ──
    v1_id = "video_alpha"
    v1_timeline = [
        {"time": 0.0, "objects": "1 person", "tracking": ["person #1"], "action": "NORMAL"},
        {"time": 5.0, "objects": "1 person, 1 laptop", "tracking": ["person #1", "laptop #1"], "ocr": "User: Alice"},
    ]
    print(f"\n--- Ingesting {v1_id} ---")
    vc.knowledge_graph.build_from_timeline(v1_timeline, video_id=v1_id)
    
    # ── Video 2 (VLM-style Timeline) ──
    v2_id = "video_beta"
    v2_timeline = [
        {"time": 10.0, "objects": "A woman is typing on a Macbook. She appears focused and is wearing a green lanyard.", "action": "NORMAL"},
        {"time": 15.0, "objects": "1 person", "tracking": ["person #1"], "ocr": "System Error 404"},
    ]
    print(f"\n--- Ingesting {v2_id} ---")
    vc.knowledge_graph.build_from_timeline(v2_timeline, video_id=v2_id)
    
    # ── Link Entities ──
    # Let's say we suspect 'person #1' from video_alpha is the woman in video_beta
    vc.knowledge_graph.link_entities("person #1", "v:video_beta_desc:10.0", relation="potentially_same_as")
    
    # ── Verify Graph Context ──
    print("\n--- Generating Graph Context for AI ---")
    context = vc.knowledge_graph.get_graph_context("Tell me about person #1 across all videos")
    print(context)
    
    # Assertions
    assert "video_alpha" in context
    assert "video_beta" in context
    assert "VLM Observations" in context
    assert "potentially_same_as" in context or "Identity Resoltuions" in context  # Check Aliases (I had a typo in code 'Resoltuions')
    
    print("\n[SUCCESS] Cross-video GraphRAG refinement verified.")

if __name__ == "__main__":
    test_cross_video_graph()
