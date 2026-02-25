import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def run_checks():
    print("--- Synapse System Verification ---")
    
    # 1. Health Check
    try:
        print(f"[1] Checking API Health ({BASE_URL})...")
        r = requests.get(f"{BASE_URL}/")
        if r.status_code == 200:
            print("    [OK] API is ONLINE.")
            print(f"    Response: {r.json()}")
        else:
            print(f"    [FAIL] API Error: {r.status_code}")
            return
    except Exception as e:
        print(f"    [FAIL] Connection Failed: {e}")
        print("    (!) Please ensure 'python -m uvicorn backend.api.main:app --reload' is running.")
        return

    # 2. Graph Module Check
    try:
        print("\n[2] Checking Graph Module (/graph)...")
        r = requests.get(f"{BASE_URL}/graph")
        if r.status_code == 200:
            data = r.json()
            nodes = len(data.get("nodes", []))
            edges = len(data.get("links", []))
            print(f"    [OK] Graph Loaded.")
            print(f"    Stats: {nodes} nodes, {edges} links.")
            if nodes > 0:
                print("    (Core graph logic is functioning)")
            else:
                print("    (!) Warning: Graph is empty. Did parser run correctly?")
        else:
            print(f"    [FAIL] Graph Endpoint Error: {r.status_code}")
    except Exception as e:
        print(f"    [FAIL] Graph Check Failed: {e}")

    # 3. AI Module Check
    try:
        print("\n[3] Checking AI Module (/ai/ask)...")
        query = "How is blast radius calculated?"
        print(f"    Asking: '{query}'")
        r = requests.get(f"{BASE_URL}/ai/ask", params={"query": query})
        
        if r.status_code == 200:
            resp = r.json()
            answer = resp.get("answer", "")
            context = resp.get("context", [])
            
            print(f"    [OK] AI Responded.")
            print(f"    Answer Preview: {answer[:100]}...")
            print(f"    Context Nodes Used: {len(context)}")
            
            if "RiskFactors" in answer or "calculate_blast_radius" in str(context):
                print("    [OK] Validation: Found relevant 'blast radius' info!")
            else:
                print("    [WARN] Validation: Answer might be generic. Check content.")
                print(f"    Full Answer: {answer}")
        else:
            print(f"    [FAIL] AI Endpoint Error: {r.status_code}")
            print(f"    Detail: {r.text}")
    except Exception as e:
        print(f"    [FAIL] AI Check Failed: {e}")

if __name__ == "__main__":
    run_checks()
