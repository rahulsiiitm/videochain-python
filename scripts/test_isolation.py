from vidchain.vectorstores.graph import TemporalKnowledgeGraph

def test_graph_isolation():
    kg = TemporalKnowledgeGraph()
    
    # ── Video A ──
    kg.build_from_timeline([
        {"time": 0.0, "objects": "1 person", "tracking": ["person #1"]},
        {"time": 5.0, "ocr": "Alice's Laptop"}
    ], video_id="alpha")
    
    # ── Video B ──
    kg.build_from_timeline([
        {"time": 10.0, "objects": "A suspicious man in a hoodie.", "action": "SUSPICIOUS"},
        {"time": 15.0, "ocr": "System Error"}
    ], video_id="beta")
    
    # ── Test Queries ──
    
    # 1. Query with isolation for Alpha
    print("\n--- Context for Video Alpha ---")
    ctx_alpha = kg.get_graph_context("search", video_id="alpha")
    print(ctx_alpha)
    assert "alpha" in ctx_alpha
    assert "Alice's Laptop" in ctx_alpha
    assert "beta" not in ctx_alpha
    assert "suspicious man" not in ctx_alpha
    
    # 2. Query with isolation for Beta
    print("\n--- Context for Video Beta ---")
    ctx_beta = kg.get_graph_context("search", video_id="beta")
    print(ctx_beta)
    assert "beta" in ctx_beta
    assert "suspicious man" in ctx_beta
    assert "Alice's Laptop" not in ctx_beta
    
    # 3. Global Query (No isolation)
    print("\n--- Global Context ---")
    ctx_global = kg.get_graph_context("search")
    print(ctx_global)
    assert "alpha" in ctx_global
    assert "beta" in ctx_global
    
    print("\n[SUCCESS] GraphRAG Isolation verified. Content is strictly separated when a video_id is provided.")

if __name__ == "__main__":
    test_graph_isolation()
