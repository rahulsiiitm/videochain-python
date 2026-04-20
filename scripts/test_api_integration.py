from fastapi.testclient import TestClient
from vidchain.serve import app
import vidchain.serve as serve
from unittest.mock import MagicMock
import pytest

client = TestClient(app)

def test_graph_entities_endpoint():
    # 1. Mock the VidChain client that serve uses
    mock_vc = MagicMock()
    mock_vc.knowledge_graph._is_built = True
    mock_vc.knowledge_graph.get_all_entities.return_value = [
        {"entity": "person #1", "video_id": "alpha", "first_seen": 0.0},
        {"entity": "laptop", "video_id": "beta", "first_seen": 10.0}
    ]
    mock_vc.knowledge_graph.describe.return_value = "Mocked Graph with 2 entities"
    mock_vc.list_indexed_videos.return_value = ["alpha", "beta"]
    
    # Inject mock into serve module
    serve.vc = mock_vc
    
    # 2. Test /api/health
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "alpha" in response.json()["indexed_videos"]
    
    # 3. Test /api/graph/entities (The new endpoint)
    print("\nTesting /api/graph/entities...")
    response = client.get("/api/graph/entities")
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]) == 2
    assert "person #1" in str(data["entities"])
    assert "Mocked Graph" in data["summary"]
    
    print("[SUCCESS] API Integration Test for GraphRAG passed.")

if __name__ == "__main__":
    test_graph_entities_endpoint()
