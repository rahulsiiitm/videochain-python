import requests
import json

def generate_vidchain_alert(detected_action, mode="Security"):
    print(f"🚨 Vision Engine detected: [{detected_action.upper()}]")
    print(f"🧠 RAG Engine processing in [{mode}] mode...\n")

    # 1. The RAG Knowledge Base (Dynamic Context)
    if mode == "Healthcare":
        system_rules = "You are a hospital monitoring AI. If you see 'emergency', dispatch a nurse immediately. Keep responses under 2 sentences."
    elif mode == "Retail":
        system_rules = "You are a store security AI. If you see 'suspicious', ask floor staff to offer customer service. Keep responses under 2 sentences."
    else: # Default Security Mode
        system_rules = "You are a high-security AI. 'Violence' requires police. 'Suspicious' requires guards. Keep responses under 2 sentences."

    # 2. The Prompt Construction
    user_prompt = f"The CCTV vision model just detected the following action: '{detected_action}'. Based on your protocols, what is the exact alert message you should broadcast to the staff?"

    # 3. Sending it to your Local Llama (Ollama API)
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3",  # Make sure this matches the nano model you pulled!
        "prompt": user_prompt,
        "system": system_rules,
        "stream": False # We want the whole response at once, not word-by-word
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        # Parse the JSON response from Llama
        result = response.json()
        print("-" * 40)
        print("🗣️ LLM ALERT GENERATED:")
        print(f"\n{result['response'].strip()}")
        print("-" * 40)
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to Ollama. Make sure the Ollama app is running in the background!")

if __name__ == "__main__":
    # Let's test the Multi-Purpose functionality!
    
    # Test 1: Healthcare mode reacting to a Fall (Emergency)
    generate_vidchain_alert(detected_action="emergency", mode="Healthcare")
    
    # Test 2: Retail mode reacting to a Sneak (Suspicious)
    generate_vidchain_alert(detected_action="suspicious", mode="Retail")
    
    # Test 3: Security mode reacting to a Hit (Violence)
    generate_vidchain_alert(detected_action="violence", mode="Security")