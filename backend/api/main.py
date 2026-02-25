from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import networkx as nx
import os
import sys
from typing import Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.graph.code_graph import build_dependency_graph
from backend.git.smart_git import (
    get_git_blame,
    get_expertise_heatmap,
    get_bus_factor_analysis,
    get_knowledge_gaps,
    get_developer_expertise
)
from backend.governance import (
    ArchitectureValidator,
    DriftDetector,
    print_validation_report,
)
# Import AI components
from backend.ai.rag import RAGPipeline

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "..", "..", "repo_graph.json")
REPO_PATH = os.path.join(BASE_DIR, "..", "..", "dummy_repo") # Point back to root

app = FastAPI(
    title="Synapse Backend Engine",
    description="GraphRAG platform for code intelligence with Smart Blame expertise identification",
    version="1.0.0"
)

# Enable CORS (so your future VS Code extension can talk to this)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GLOBAL STATE ---
# We keep the graph in memory for speed
# --- GLOBAL STATE ---
# We keep the graph in memory for speed
graph_db = {
    "nx_graph": nx.DiGraph(),
    "raw_data": []
}
startup_error = None

# Initialize AI Pipeline (lazy load or global?)
# We'll initialize it globally but it handles its own key checks
rag_pipeline = RAGPipeline()

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
        for call_str in func.get('calls', []):
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
    global startup_error
    try:
        with open(INPUT_FILE, "r") as f:
            data = json.load(f)
            graph_db["raw_data"] = data
            graph_db["nx_graph"] = build_graph(data)
            print(f"Loaded Graph: {graph_db['nx_graph'].number_of_nodes()} nodes")
    except Exception as e:
        import traceback
        traceback.print_exc()
        startup_error = str(e)
        print(f"Error loading graph: {e}")

# --- CORE ENDPOINTS ---

@app.get("/")
def health_check():
    return {
        "status": "active", 
        "system": "Node Zero Synapse",
        "startup_error": startup_error
    }

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


# --- SMART BLAME ENDPOINTS ---

@app.get("/blame/expert/{file_path:path}")
async def get_expert_for_file(
    file_path: str,
    repo_path: Optional[str] = Query(None, description="Path to the git repository")
):
    """
    Get the recommended expert for a file.
    
    Returns expert recommendation with confidence score and reasoning.
    Output format example: "Ask Sarah, she architected this"
    
    **Acceptance Criteria (from requirements):**
    - System analyzes commit history beyond simple git blame
    - Algorithm considers refactor depth, architectural decisions, and code ownership patterns
    - System identifies primary expert with confidence score
    - System distinguishes between code authors and domain experts
    """
    try:
        result = await get_git_blame(file_path, repo_path)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze file: {str(e)}")


@app.get("/blame/heatmap")
async def get_heatmap(
    module: Optional[str] = Query(None, description="Filter to specific module/directory"),
    repo_path: Optional[str] = Query(None, description="Path to the git repository")
):
    """
    Get expertise heatmap for the codebase or a specific module.
    
    **Acceptance Criteria (from requirements):**
    - System generates expertise heatmaps for different modules
    - Identifies single points of failure ("Bus Factor" analysis)
    - Shows expertise gaps and recommends knowledge transfer
    """
    try:
        result = await get_expertise_heatmap(module, repo_path)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate heatmap: {str(e)}")


@app.get("/blame/bus-factor")
async def get_bus_factor(
    repo_path: Optional[str] = Query(None, description="Path to the git repository")
):
    """
    Get bus factor analysis across the codebase.
    
    Bus factor = the number of developers who would need to leave
    before a module becomes orphaned (no one understands it).
    
    Returns dict mapping module paths to bus factor values.
    Low bus factor (1-2) indicates high risk areas.
    """
    try:
        result = await get_bus_factor_analysis(repo_path)
        return {
            "analysis": result,
            "warning_threshold": 2,
            "risk_areas": [k for k, v in result.items() if v <= 2]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze bus factor: {str(e)}")


@app.get("/blame/gaps")
async def get_gaps(
    repo_path: Optional[str] = Query(None, description="Path to the git repository")
):
    """
    Identify areas of the codebase with insufficient expertise coverage.
    
    Knowledge gaps are files/modules where no developer has a strong
    expertise score, indicating potential maintenance risks.
    """
    try:
        gaps = await get_knowledge_gaps(repo_path)
        return {
            "knowledge_gaps": gaps,
            "total_gaps": len(gaps),
            "recommendation": "Consider pairing junior developers with experts on these areas"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to identify gaps: {str(e)}")


@app.get("/blame/developer/{email}")
async def get_developer_areas(
    email: str,
    repo_path: Optional[str] = Query(None, description="Path to the git repository")
):
    """
    Get all expertise areas for a specific developer.
    
    Returns a list of files/modules the developer has expertise in,
    sorted by expertise score.
    """
    try:
        expertise = await get_developer_expertise(email, repo_path)
        return {
            "developer_email": email,
            "expertise_areas": expertise,
            "total_areas": len(expertise)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get developer expertise: {str(e)}")


# --- GOVERNANCE ENDPOINTS ---

@app.get("/governance/validate")
async def validate_architecture(
    repo_path: Optional[str] = Query(None, description="Path to the repository to validate")
):
    """
    Validate repository architecture against defined rules.
    
    Returns all violations and warnings found.
    """
    try:
        path = repo_path or REPO_PATH
        validator = ArchitectureValidator()
        result = validator.validate_repository(path)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@app.get("/governance/violations")
async def get_violations(
    repo_path: Optional[str] = Query(None, description="Path to the repository")
):
    """
    Get list of current architectural violations.
    
    Violations are imports that cross layer boundaries in prohibited ways.
    """
    try:
        path = repo_path or REPO_PATH
        validator = ArchitectureValidator()
        result = validator.validate_repository(path)
        return {
            "total_violations": result.total_violations,
            "total_warnings": result.total_warnings,
            "violations": [v.to_dict() for v in result.all_violations],
            "warnings": [w.to_dict() for w in result.all_warnings]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get violations: {str(e)}")


@app.get("/governance/drift")
async def get_drift(
    repo_path: Optional[str] = Query(None, description="Path to the repository"),
    baseline_path: Optional[str] = Query(None, description="Path to baseline metrics JSON")
):
    """
    Get architectural drift report.
    
    Compares current metrics to baseline to detect architectural drift.
    """
    try:
        path = repo_path or REPO_PATH
        detector = DriftDetector(baseline_path=baseline_path)
        report = detector.detect_drift(path)
        return report.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drift detection failed: {str(e)}")


@app.get("/governance/layers")
async def get_layers():
    """
    Get configured architectural layers.
    
    Returns the layer definitions used for validation.
    """
    try:
        validator = ArchitectureValidator()
        return {
            "layers": validator.rule_engine.get_layer_summary(),
            "rules": validator.rule_engine.get_rules_summary()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get layers: {str(e)}")


# --- API DOCUMENTATION ---

@app.get("/api/info")
def api_info():
    """Get information about available Smart Blame endpoints"""
    return {
        "smart_blame_endpoints": [
            {
                "path": "/blame/expert/{file_path}",
                "method": "GET",
                "description": "Get recommended expert for a file"
            },
            {
                "path": "/blame/heatmap",
                "method": "GET",
                "description": "Get expertise heatmap for codebase"
            },
            {
                "path": "/blame/bus-factor",
                "method": "GET",
                "description": "Get bus factor analysis"
            },
            {
                "path": "/blame/gaps",
                "method": "GET",
                "description": "Identify knowledge gaps"
            },
            {
                "path": "/blame/developer/{email}",
                "method": "GET",
                "description": "Get developer expertise areas"
            }
        ],
        "scoring_factors": [
            {"name": "commit_frequency", "weight": 0.15},
            {"name": "lines_changed", "weight": 0.10},
            {"name": "refactor_depth", "weight": 0.25},
            {"name": "architectural_changes", "weight": 0.20},
            {"name": "bug_fixes", "weight": 0.15},
            {"name": "recency", "weight": 0.10},
            {"name": "code_review_participation", "weight": 0.05}
        ]
    }

# --- AI ENDPOINTS ---

class QueryRequest(BaseModel):
    query: str

@app.post("/ai/index")
async def index_graph():
    """Triggers the embeddings generation for the current graph"""
    if not graph_db["raw_data"]:
        raise HTTPException(status_code=400, detail="Graph not loaded yet")
    
    count = rag_pipeline.index_codebase(graph_db["raw_data"])
    return {"status": "success", "indexed_nodes": count}

@app.get("/ai/ask")
async def ask_ai(query: str):
    """Asks the RAG pipeline a question"""
    result = rag_pipeline.ask(query)
    return result
