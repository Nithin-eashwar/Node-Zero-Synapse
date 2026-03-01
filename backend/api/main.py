from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import sys
from typing import Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.graph.code_graph import build_dependency_graph, CodeGraph
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
graph_db = {
    "code_graph": None,  # CodeGraph instance (uses pluggable store backend)
    "raw_data": [],
    "git_risk": None     # GitRiskAnalyzer instance (lazy, cached)
}
startup_error = None

# AI Pipeline - initialized lazily on first /ai/* request
# This avoids loading the embedding model at startup
_rag_pipeline = None

def get_rag_pipeline() -> RAGPipeline:
    """Lazy initialization of RAG pipeline on first AI request."""
    global _rag_pipeline
    if _rag_pipeline is None:
        print("Initializing RAG Pipeline (first AI request)...")
        _rag_pipeline = RAGPipeline()
        # Wire in graph context and repo path if graph is already loaded
        if graph_db["raw_data"] and graph_db["code_graph"]:
            _rag_pipeline.set_graph_context(
                graph_db["code_graph"].store, graph_db["raw_data"], REPO_PATH
            )
    return _rag_pipeline


# build_graph replaced by build_dependency_graph from CodeGraph module

@app.on_event("startup")
async def load_data():
    """Load the graph into memory on startup (AI pipeline loaded lazily on first request)"""
    global startup_error
    try:
        with open(INPUT_FILE, "r") as f:
            data = json.load(f)
            graph_db["raw_data"] = data
            graph_db["code_graph"] = build_dependency_graph(data)
            print(f"Loaded Graph: {graph_db['code_graph'].store.number_of_nodes()} nodes")
    except Exception as e:
        import traceback
        traceback.print_exc()
        startup_error = str(e)
        print(f"Error loading graph: {e}")
    
    # Initialize git risk analyzer (non-blocking, lightweight)
    try:
        from backend.git.git_risk_analyzer import get_git_risk_analyzer
        graph_db["git_risk"] = get_git_risk_analyzer(REPO_PATH)
        print(f"[Startup] Git risk analyzer ready")
    except Exception as e:
        print(f"[Startup] Git risk analysis unavailable: {e}")
        graph_db["git_risk"] = None

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
    cg = graph_db["code_graph"]
    store = cg.store
    nodes = []
    for node_id in store.get_all_nodes():
        node_data = store.get_node_data(node_id)
        nodes.append({"id": node_id, **node_data})
    edges = []
    for node_id in store.get_all_nodes():
        for succ in store.successors(node_id):
            edges.append({"source": node_id, "target": succ})
    return {"nodes": nodes, "edges": edges}

@app.get("/blast-radius/{function_name}")
def get_blast_radius(function_name: str):
    """Calculates dependencies for a specific function"""
    cg = graph_db["code_graph"]
    
    if not cg.store.has_node(function_name):
        raise HTTPException(status_code=404, detail=f"Function '{function_name}' not found")
    
    # Logic: Who depends on me? (Ancestors)
    affected_nodes = list(cg.store.ancestors(function_name))
    
    return {
        "target": function_name,
        "blast_radius_score": len(affected_nodes),
        "affected_functions": affected_nodes
    }


@app.get("/blast-radius/{function_name}/explain")
async def explain_blast_radius(function_name: str):
    """
    AI-Powered Blast Radius Explanation.
    
    Uses the preloaded CodeGraph for rich impact assessment and
    generates a natural language explanation.
    """
    cg = graph_db["code_graph"]
    raw_data = graph_db["raw_data"]
    
    if not cg.store.has_node(function_name):
        raise HTTPException(status_code=404, detail=f"Function '{function_name}' not found")
    
    # Build complexity data for risk calculation
    complexity_data = {}
    for node in raw_data:
        if node.get("complexity"):
            complexity_data[node["name"]] = node["complexity"]
    
    # Calculate full impact assessment using preloaded CodeGraph + git risk
    git_risk = graph_db.get("git_risk")
    impact = cg.calculate_blast_radius(function_name, complexity_data, git_risk_analyzer=git_risk)
    impact_dict = impact.to_dict()
    
    # Find the entity's raw node data
    entity_node = next((n for n in raw_data if n["name"] == function_name), None)
    
    # Generate AI explanation
    from backend.ai.blast_radius_explainer import BlastRadiusExplainer
    explainer = BlastRadiusExplainer()
    result = explainer.explain(
        impact_dict=impact_dict,
        entity_node=entity_node,
        graph_nodes=raw_data,
    )
    
    # Merge structured data with AI explanation
    result["impact_assessment"] = impact_dict
    return result


@app.get("/git-risk/{file_path:path}")
def get_git_risk(file_path: str):
    """
    Get git-backed risk metrics for a file.
    
    Returns change frequency, bus factor, unique authors,
    and commit history analysis.
    """
    git_risk = graph_db.get("git_risk")
    if not git_risk:
        raise HTTPException(
            status_code=503,
            detail="Git risk analysis not available (no git repo found)"
        )
    
    summary = git_risk.get_file_summary(file_path)
    if not summary:
        raise HTTPException(
            status_code=404,
            detail=f"No git history found for '{file_path}'"
        )
    
    return {
        "file": file_path,
        **summary
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
    
    pipeline = get_rag_pipeline()
    count = pipeline.index_codebase(graph_db["raw_data"])
    return {"status": "success", "indexed_nodes": count}

@app.get("/ai/ask")
async def ask_ai(query: str):
    """Asks the RAG pipeline a question"""
    pipeline = get_rag_pipeline()
    result = await pipeline.ask(query)
    return result
