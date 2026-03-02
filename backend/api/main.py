from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

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
# Import AI components (may fail on some Python versions due to pyo3 panics)
_ai_available = False
rag_pipeline = None

if os.environ.get("SYNAPSE_DISABLE_AI", "").lower() not in ("1", "true", "yes"):
    try:
        from backend.ai.rag import RAGPipeline
        _ai_available = True
    except Exception as e:
        print(f"Warning: AI module failed to load: {e}")
        print("Non-AI endpoints will still work.")
else:
    print("AI module disabled via SYNAPSE_DISABLE_AI env var.")
    RAGPipeline = None  # type: ignore

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


RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _normalise_file_path(file_path: str) -> str:
    if not file_path:
        return ""
    return file_path.replace("\\", "/").lstrip("./")


def _directory_key(file_path: str) -> str:
    path = _normalise_file_path(file_path)
    parts = [part for part in path.split("/") if part]
    if len(parts) == 0:
        return ""
    if len(parts) == 1:
        return "root"
    if len(parts) == 2:
        return parts[0]
    return "/".join(parts[:2])


def _risk_level_from_degree(total_degree: int) -> str:
    if total_degree >= 8:
        return "CRITICAL"
    if total_degree >= 5:
        return "HIGH"
    if total_degree >= 2:
        return "MEDIUM"
    return "LOW"


def _highest_risk_level(levels: List[str]) -> str:
    if not levels:
        return "LOW"
    return max(levels, key=lambda risk: RISK_ORDER.get(risk, 0))


def _build_raw_entity_map() -> Dict[str, Dict[str, Any]]:
    raw_entity_map: Dict[str, Dict[str, Any]] = {}
    for entity in graph_db["raw_data"]:
        entity_id = entity.get("unique_id") or entity.get("name")
        if entity_id:
            raw_entity_map[entity_id] = entity
    return raw_entity_map


def _collect_graph_nodes_and_edges() -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    cg = graph_db["code_graph"]
    store = cg.store
    raw_entity_map = _build_raw_entity_map()

    nodes: List[Dict[str, Any]] = []
    all_node_ids = store.get_all_nodes()
    for node_id in all_node_ids:
        store_data = store.get_node_data(node_id) or {}
        raw_data = raw_entity_map.get(node_id, {})
        merged = {**raw_data, **store_data}
        nodes.append({"id": node_id, **merged})

    edges: List[Dict[str, str]] = []
    for node_id in all_node_ids:
        for succ in store.successors(node_id):
            edges.append({"source": node_id, "target": succ})

    return nodes, edges


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
    nodes, edges = _collect_graph_nodes_and_edges()
    return {"nodes": nodes, "edges": edges}


@app.get("/graph/condensed")
def get_condensed_graph():
    """
    Returns a 3-level hierarchical graph for cleaner visualization.
    
    Level 1: Directory/module nodes (~8-12)
    Level 2: File nodes (expand from directory)
    Level 3: Entity nodes (expand from file)
    """
    all_nodes, all_edges = _collect_graph_nodes_and_edges()

    in_degree: Dict[str, int] = {}
    out_degree: Dict[str, int] = {}
    for edge in all_edges:
        out_degree[edge["source"]] = out_degree.get(edge["source"], 0) + 1
        in_degree[edge["target"]] = in_degree.get(edge["target"], 0) + 1

    node_file_map: Dict[str, str] = {}
    node_dir_map: Dict[str, str] = {}
    hierarchy_node_ids = set()
    for node in all_nodes:
        node_id = node["id"]
        file_path = _normalise_file_path(str(node.get("file") or ""))
        if not file_path:
            continue
        node_file_map[node_id] = file_path
        node_dir_map[node_id] = _directory_key(file_path)
        hierarchy_node_ids.add(node_id)

    filtered_entity_edges = [
        edge for edge in all_edges
        if edge["source"] in hierarchy_node_ids and edge["target"] in hierarchy_node_ids
    ]

    entities_by_file: Dict[str, List[Dict[str, Any]]] = {}
    for node in all_nodes:
        node_id = node["id"]
        file_key = node_file_map.get(node_id)
        if not file_key:
            continue

        complexity = 0
        raw_complexity = node.get("complexity")
        if isinstance(raw_complexity, dict):
            complexity = raw_complexity.get("cyclomatic", 0) or 0
        elif isinstance(raw_complexity, (int, float)):
            complexity = raw_complexity

        line = 0
        line_range = node.get("range")
        if isinstance(line_range, list) and line_range:
            line = line_range[0]

        degree = out_degree.get(node_id, 0) + in_degree.get(node_id, 0)
        entities_by_file.setdefault(file_key, []).append({
            "id": node_id,
            "name": node.get("name", node_id),
            "type": node.get("type", "function"),
            "risk_level": _risk_level_from_degree(degree),
            "complexity": complexity,
            "degree": degree,
            "line": line,
        })

    for entities in entities_by_file.values():
        entities.sort(key=lambda entity: entity["name"])

    file_nodes: Dict[str, Dict[str, Any]] = {}
    for file_key, entities in entities_by_file.items():
        file_nodes[file_key] = {
            "id": file_key,
            "type": "file",
            "label": file_key.split("/")[-1],
            "full_path": file_key,
            "directory": _directory_key(file_key),
            "entity_count": len(entities),
            "risk_level": _highest_risk_level([entity["risk_level"] for entity in entities]),
            "total_complexity": sum(entity["complexity"] for entity in entities),
        }

    files_by_directory: Dict[str, List[Dict[str, Any]]] = {}
    for _, file_node in file_nodes.items():
        directory = file_node["directory"]
        files_by_directory.setdefault(directory, []).append(file_node)

    for directory_files in files_by_directory.values():
        directory_files.sort(key=lambda file_node: file_node["label"])

    file_edge_counts: Dict[Tuple[str, str], int] = {}
    dir_edge_counts: Dict[Tuple[str, str], int] = {}
    for edge in filtered_entity_edges:
        source_file = node_file_map[edge["source"]]
        target_file = node_file_map[edge["target"]]
        source_dir = node_dir_map[edge["source"]]
        target_dir = node_dir_map[edge["target"]]

        if source_file != target_file:
            file_pair = (source_file, target_file)
            file_edge_counts[file_pair] = file_edge_counts.get(file_pair, 0) + 1

        if source_dir != target_dir:
            dir_pair = (source_dir, target_dir)
            dir_edge_counts[dir_pair] = dir_edge_counts.get(dir_pair, 0) + 1

    file_edges = [
        {"source": source, "target": target, "weight": weight}
        for (source, target), weight in sorted(file_edge_counts.items())
    ]

    directory_edges = [
        {"source": source, "target": target, "weight": weight}
        for (source, target), weight in sorted(dir_edge_counts.items())
    ]

    directory_nodes = []
    for directory, directory_files in sorted(files_by_directory.items()):
        directory_nodes.append({
            "id": directory,
            "type": "directory",
            "label": directory,
            "file_count": len(directory_files),
            "entity_count": sum(file_node["entity_count"] for file_node in directory_files),
            "risk_level": _highest_risk_level([file_node["risk_level"] for file_node in directory_files]),
            "total_complexity": sum(file_node["total_complexity"] for file_node in directory_files),
        })

    return {
        "directory_nodes": directory_nodes,
        "directory_edges": directory_edges,
        "files_by_directory": files_by_directory,
        "file_edges": file_edges,
        "entities_by_file": entities_by_file,
        "entity_edges": filtered_entity_edges,
    }

    # Legacy implementation (kept unreachable for rollback safety).
    cg = graph_db["code_graph"]
    store = cg.store

    # ── Collect all nodes and edges ──────────────────────────────
    all_nodes = []
    for node_id in store.get_all_nodes():
        nd = store.get_node_data(node_id)
        all_nodes.append({"id": node_id, **(nd or {})})

    all_edges = []
    for node_id in store.get_all_nodes():
        for succ in store.successors(node_id):
            all_edges.append({"source": node_id, "target": succ})

    # ── Helper: normalise file path to forward-slash, strip leading ./ ──
    def _norm(file_path: str) -> str:
        p = file_path.replace("\\", "/").lstrip("./")
        return p

    # ── Helper: derive directory key (first 2 segments) ─────────
    def _dir_key(file_path: str) -> str:
        p = _norm(file_path)
        parts = p.split("/")
        if len(parts) <= 2:
            # e.g. "debug_chroma.py" → "root" or "backend/ai" stays as-is
            if len(parts) == 1:
                return "root"
            return parts[0] if parts[0] != "" else "root"
        return "/".join(parts[:2])

    def _file_key(file_path: str) -> str:
        return _norm(file_path)

    # ── Build node-id → file/dir mappings ───────────────────────
    node_file_map = {}       # node_id → normalised file path
    node_dir_map = {}        # node_id → directory key
    for n in all_nodes:
        fp = n.get("file", "") or ""
        nf = _file_key(fp)
        node_file_map[n["id"]] = nf
        node_dir_map[n["id"]] = _dir_key(fp)

    # ── Risk helpers ────────────────────────────────────────────
    def _degree(node_id):
        out = sum(1 for e in all_edges if e["source"] == node_id)
        inn = sum(1 for e in all_edges if e["target"] == node_id)
        return out + inn

    def _risk_level(total_degree):
        if total_degree >= 8:
            return "CRITICAL"
        if total_degree >= 5:
            return "HIGH"
        if total_degree >= 2:
            return "MEDIUM"
        return "LOW"

    RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

    def _highest_risk(levels):
        if not levels:
            return "LOW"
        return max(levels, key=lambda r: RISK_ORDER.get(r, 0))

    # ── Group entities by file ──────────────────────────────────
    entities_by_file: dict = {}   # file_key → [entity dicts]
    for n in all_nodes:
        fk = node_file_map[n["id"]]
        entities_by_file.setdefault(fk, [])
        deg = _degree(n["id"])
        complexity = 0
        if isinstance(n.get("complexity"), dict):
            complexity = n["complexity"].get("cyclomatic", 0)
        elif isinstance(n.get("complexity"), (int, float)):
            complexity = n["complexity"]
        entities_by_file[fk].append({
            "id": n["id"],
            "name": n.get("name", n["id"]),
            "type": n.get("type", "function"),
            "risk_level": _risk_level(deg),
            "complexity": complexity,
            "degree": deg,
            "line": n.get("range", [0])[0] if n.get("range") else 0,
        })

    # ── Build file nodes ────────────────────────────────────────
    file_nodes = {}  # file_key → file node dict
    for fk, entities in entities_by_file.items():
        risks = [e["risk_level"] for e in entities]
        total_cx = sum(e["complexity"] for e in entities)
        file_nodes[fk] = {
            "id": fk,
            "type": "file",
            "label": fk.split("/")[-1] if "/" in fk else fk,
            "full_path": fk,
            "directory": _dir_key(".\\" + fk.replace("/", "\\")),
            "entity_count": len(entities),
            "risk_level": _highest_risk(risks),
            "total_complexity": total_cx,
        }

    # ── Build file-to-file edges (deduplicated, weighted) ───────
    file_edge_counts: dict = {}   # (src_file, tgt_file) → count
    for e in all_edges:
        sf = node_file_map.get(e["source"], "")
        tf = node_file_map.get(e["target"], "")
        if sf and tf and sf != tf:
            key = (sf, tf)
            file_edge_counts[key] = file_edge_counts.get(key, 0) + 1

    file_edges = [
        {"source": k[0], "target": k[1], "weight": v}
        for k, v in file_edge_counts.items()
    ]

    # ── Group files by directory ────────────────────────────────
    files_by_directory: dict = {}
    for fk, fnode in file_nodes.items():
        dk = fnode["directory"]
        files_by_directory.setdefault(dk, [])
        files_by_directory[dk].append(fnode)

    # ── Build directory nodes ───────────────────────────────────
    directory_nodes = []
    for dk, fnodes in files_by_directory.items():
        risks = [fn["risk_level"] for fn in fnodes]
        total_entities = sum(fn["entity_count"] for fn in fnodes)
        total_cx = sum(fn["total_complexity"] for fn in fnodes)
        directory_nodes.append({
            "id": dk,
            "type": "directory",
            "label": dk,
            "file_count": len(fnodes),
            "entity_count": total_entities,
            "risk_level": _highest_risk(risks),
            "total_complexity": total_cx,
        })

    # ── Build directory-to-directory edges (deduplicated) ───────
    dir_edge_counts: dict = {}
    for e in all_edges:
        sd = node_dir_map.get(e["source"], "")
        td = node_dir_map.get(e["target"], "")
        if sd and td and sd != td:
            key = (sd, td)
            dir_edge_counts[key] = dir_edge_counts.get(key, 0) + 1

    directory_edges = [
        {"source": k[0], "target": k[1], "weight": v}
        for k, v in dir_edge_counts.items()
    ]

    # ── Entity-level edges (original) ───────────────────────────
    entity_edges = all_edges

    return {
        "directory_nodes": directory_nodes,
        "directory_edges": directory_edges,
        "files_by_directory": files_by_directory,
        "file_edges": file_edges,
        "entities_by_file": entities_by_file,
        "entity_edges": entity_edges,
    }


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
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="AI module not available (embedding library failed to load)")
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
