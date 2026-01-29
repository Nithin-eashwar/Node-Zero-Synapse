from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import networkx as nx
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.graph import build_dependency_graph
from core.git import get_git_blame

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "..", "data", "repo_graph.json")
REPO_PATH = os.path.join(BASE_DIR, "..", "..", "dummy_repo") # Point back to root

app = FastAPI(title="Synapse Backend Engine")

# Enable CORS (so your future VS Code extension can talk to this)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GLOBAL STATE ---
# We keep the graph in memory for speed
graph_db = {
    "nx_graph": None,
    "raw_data": []
}

def build_graph(data):
    """Rebuilds the NetworkX graph from JSON data"""
    G = nx.DiGraph()
    all_nodes = set()
    
    # 1. Add Nodes
    for func in data:
        node_id = func['name']
        G.add_node(node_id, file=func['file'], line=func['range'][0])
        all_nodes.add(node_id)
        
    # 2. Add Edges (Fuzzy Match)
    for func in data:
        caller = func['name']
        for call_str in func['calls']:
            # Find which node this call refers to
            target = None
            for candidate in all_nodes:
                if call_str == candidate or call_str.endswith("." + candidate):
                    target = candidate
                    break
            
            if target:
                G.add_edge(caller, target)
                
    return G

@app.on_event("startup")
async def load_data():
    """Load the graph into memory on startup"""
    try:
        with open(INPUT_FILE, "r") as f:
            data = json.load(f)
            graph_db["raw_data"] = data
            graph_db["nx_graph"] = build_graph(data)
            print(f"✅ Loaded Graph: {graph_db['nx_graph'].number_of_nodes()} nodes")
    except Exception as e:
        print(f"❌ Error loading graph: {e}")

# --- ENDPOINTS ---

@app.get("/")
def health_check():
    return {"status": "active", "system": "Node Zero Synapse"}

@app.get("/graph")
def get_full_graph():
    """Returns the raw nodes and edges for visualization"""
    G = graph_db["nx_graph"]
    return {
        "nodes": [{"id": n, **G.nodes[n]} for n in G.nodes()],
        "edges": [{"source": u, "target": v} for u, v in G.edges()]
    }

@app.get("/blast-radius/{function_name}")
def get_blast_radius(function_name: str):
    """Calculates dependencies for a specific function"""
    G = graph_db["nx_graph"]
    
    if function_name not in G:
        raise HTTPException(status_code=404, detail=f"Function '{function_name}' not found")
    
    # Logic: Who depends on me? (Ancestors)
    affected_nodes = list(nx.ancestors(G, function_name))
    
    return {
        "target": function_name,
        "blast_radius_score": len(affected_nodes),
        "affected_functions": affected_nodes
    }