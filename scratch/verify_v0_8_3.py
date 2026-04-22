import requests
import time
import subprocess
import os

def test_server():
    print("[TEST] Starting VidChain Server Simulation...")
    
    # Start server as a background process
    # We use python -m vidchain.serve instead of the entry point to be sure we use the local source
    server_process = subprocess.Popen(
        ["python", "-m", "vidchain.serve"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to wake up
    time.sleep(5)
    
    try:
        # 1. Health Check
        print("[TEST] Checking Health Endpoint...")
        health = requests.get("http://localhost:8000/api/health").json()
        print(f"Health Response: {health}")
        
        # 2. Session List Check
        print("[TEST] Checking Session List...")
        sessions = requests.get("http://localhost:8000/api/sessions").json()
        print(f"Sessions Found: {len(sessions.get('sessions', []))}")
        
        if len(sessions.get('sessions', [])) > 0:
            sid = sessions['sessions'][0]['id']
            print(f"[TEST] Attempting auto-fetch for session: {sid}")
            detail = requests.get(f"http://localhost:8000/api/sessions/{sid}").json()
            print(f"Session '{detail.get('title')}' retrieved successfully.")
        
        print("\n[SUCCESS] v0.8.3-Stable API Verification PASSED.")
        
    except Exception as e:
        print(f"\n[FAIL] Simulation error: {e}")
    finally:
        server_process.terminate()
        print("[TEST] Simulation complete.")

if __name__ == "__main__":
    test_server()
