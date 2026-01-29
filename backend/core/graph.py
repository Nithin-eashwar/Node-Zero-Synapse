import json
import networkx as nx

# --- CONFIGURATION ---
INPUT_FILE = "repo_graph.json"

def build_dependency_graph(data):
    G = nx.DiGraph()  # Directed Graph
    
    # 1. Add all nodes first
    for func in data:
        # We use "file:function" as the unique ID to avoid name collisions
        node_id = f"{func['name']}" 
        G.add_node(node_id, file=func['file'], line=func['range'][0])
    
    # 2. Add edges (The tricky part)
    
    print("--- Building Links ---")
    all_node_ids = list(G.nodes())
    
    for func in data:
        caller_id = func['name']
        
        for call_str in func['calls']:
            # Call string might be "helper.fetch_data"
            # We need to find if "fetch_data" exists in our nodes
            
            # Simple heuristic: Does a known function name end with this call?
            # e.g. "fetch_data" is inside "helper.fetch_data"
            target = None
            for candidate in all_node_ids:
                if call_str.endswith(candidate) or candidate == call_str:
                    target = candidate
                    break
            
            if target:
                print(f"🔗 Linking {caller_id} -> {target}")
                # Edge goes FROM caller TO target
                G.add_edge(caller_id, target)
            else:
                # Optional: Add external nodes (like library calls)
                pass
                
    return G

def calculate_blast_radius(G, target_function):
    print(f"\n💥 Calculating Blast Radius for: '{target_function}'")
    
    if target_function not in G:
        print(f"❌ Error: Function '{target_function}' not found in graph.")
        return

    # In Blast Radius, we want to know: "Who calls me?"
    # So we look at the PREDECESSORS (parents) in the graph.
    
    # Get all upstream dependencies
    affected_nodes = list(nx.ancestors(G, target_function))
    
    if not affected_nodes:
        print("✅ Safe! No other functions depend on this.")
    else:
        print(f"⚠️  WARNING: Changing this breaks {len(affected_nodes)} functions!")
        for node in affected_nodes:
            print(f"   - {node} (depends on it)")

    # Optional: Draw the path
    try:
        path = nx.shortest_path(G, source="app_start", target=target_function)
        print(f"\nExample Failure Chain: {' -> '.join(path)}")
    except:
        pass

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # 1. Load Data
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)
        
    # 2. Build Graph
    graph = build_dependency_graph(data)
    print(f"\nGraph Stats: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges.")
    
    # 3. Simulate a User Query
    # Let's say we edit "process_data" in utils.py
    # We expect "app_start" to be affected.
    target = "process_data" 
    
    calculate_blast_radius(graph, target)