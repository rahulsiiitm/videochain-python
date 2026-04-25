import torch
import sys

def main():
    print("\n" + "="*40)
    print(" 🚀 vidchain HARDWARE DIAGNOSTIC 🚀 ")
    print("="*40)

    print(f"Python Version:  {sys.version.split()[0]}")
    print(f"PyTorch Version: {torch.__version__}")

    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available:  {cuda_available}")

    # ── Ollama & Neural Model Diagnostic ───────────────────────────
    print("\n" + "🧠 NEURAL MODEL CHECK")
    print("-" * 40)
    import requests
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            required = ["llama3:latest", "moondream:latest"]
            
            for req in required:
                clean_name = req.split(":")[0]
                found = any(clean_name in m.lower() for m in models)
                status = "✅" if found else "❌"
                print(f"{status} {req.upper():<16} : {'Ready' if found else 'MISSING'}")
            
            if not all(any(r.split(":")[0] in m.lower() for m in models) for r in required):
                print("\n⚠️  ACTION REQUIRED: Missing models detected.")
                print("Please run: ollama pull llama3 && ollama pull moondream")
        else:
            print("❌ OLLAMA SERVICE: Unreachable (Status Code != 200)")
    except Exception:
        print("❌ OLLAMA SERVICE: Offline (Check if Ollama is running)")

    # ── Master Intelligence Audit ─────────────────────────────────
    print("\n🕸️  MASTER INTELLIGENCE HUB")
    print("-" * 40)
    import os, pickle
    graph_p = os.path.join("vidchain_storage", "knowledge_graphs", "global_graph.pkl")
    
    if os.path.exists(graph_p):
        try:
            with open(graph_p, "rb") as f:
                data = pickle.load(f)
                G = data.get("G")
                if G:
                    print(f"✅ STATUS         : ONLINE")
                    print(f"📊 REGISTERED FACTS: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
                else:
                    print("⚠️  STATUS         : EMPTY (Ready but no memory yet)")
        except Exception as e:
            print(f"❌ STATUS         : CORRUPTED ({e})")
    else:
        print("📁 STATUS         : INITIAL (First ingestion pending)")

    print("="*40)
    if cuda_available:
        print("\033[92mVidChain v1.0.0-Stable is Production-Ready!\033[0m")
    else:
        print("\033[93mHardware warning: CPU-Only mode active.\033[0m")

if __name__ == "__main__":
    main()
