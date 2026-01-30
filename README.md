# Synapse - The Organizational Brain for Software Teams

A Graph-Augmented Generation (GraphRAG) platform that creates a "Living Knowledge Graph" of entire codebases. Synapse moves beyond "writing code faster" to "understanding code deeper" by solving the "Context Gap" in large software teams.

## 🎯 What Synapse Solves

| Problem | Solution |
|---------|----------|
| **Blast Radius Blindness** | Visualize all downstream impacts before merging |
| **Imposter Syndrome** | Private AI mentor for judgment-free learning |
| **Knowledge Silos** | Smart Blame identifies true experts, not just last committers |
| **Architectural Drift** | Automated boundary enforcement |

## 🏗️ Current Implementation Status

### ✅ Phase 1: Rich Node Model (Complete)
- Comprehensive entity extraction (functions, classes, imports)
- Complexity metrics (cyclomatic, cognitive)
- Parameter/type/decorator parsing

### ✅ Phase 2: Complete Relationship Graph (Complete)
- 15+ relationship types (CALLS, INHERITS, IMPORTS, DECORATES, etc.)
- Smart call resolution with import alias tracking
- Blast radius calculation with risk scoring

### 🔲 Phase 3: Git Integration (Planned)
### 🔲 Phase 4: Advanced Complexity (Planned)
### 🔲 Phase 5: Semantic/Vector Layer (Planned)

## 📁 Project Structure

```
Node-Zero-Synapse/
├── backend/
│   ├── app/
│   │   └── main.py              # FastAPI application
│   └── core/
│       ├── entities.py          # Data models (FunctionEntity, ClassEntity, etc.)
│       ├── complexity.py        # Cyclomatic & cognitive complexity
│       ├── parser.py            # tree-sitter AST parsing
│       ├── relationships.py     # RelationType enum, Relationship model
│       ├── resolver.py          # Smart call resolution
│       ├── relationship_extractor.py  # Edge extraction
│       └── graph.py             # CodeGraph, blast radius analysis
├── dummy_repo/                  # Test codebase
├── design.md                    # System architecture
└── requirements.md              # Business requirements
```

## 🚀 Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Parse a repository
python -m backend.core.parser <path_to_repo>

# 4. Analyze the graph
python -m backend.core.graph

# 5. Run the API server
uvicorn backend.app.main:app --reload
```

## 📊 Example Output

```
[*] Building dependency graph...
[INFO] Graph Stats: 17 nodes, 11 edges
[INFO] Edge types: {'CALLS': 9, 'INHERITS': 2}

[*] Calculating Blast Radius for: 'process_data'
[!] WARNING: Changing this affects 1 functions!
    Direct callers: 1
    Risk score: 0.20
```

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/graph` | GET | Get full dependency graph |
| `/blast-radius/{function}` | GET | Calculate blast radius |

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Parsing | tree-sitter (Python grammar) |
| Graph (Local) | NetworkX |
| Graph (Production) | Amazon Neptune / Neo4j (planned) |
| Vector Store | Amazon OpenSearch (planned) |
| LLM | Amazon Bedrock (planned) |
| API | FastAPI |
| Frontend | VS Code Extension (planned) |

## 📈 Architecture

The codebase is modular with single-responsibility modules:

- **entities.py** - Pure data classes, no logic
- **complexity.py** - Metrics calculation only
- **parser.py** - AST parsing only
- **graph.py** - Graph operations only

Each module can be independently tested and swapped (e.g., NetworkX → Neo4j).

## 📝 License

MIT License - See LICENSE file for details.

---

*Part of the Node-Zero project suite.*
