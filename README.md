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

### ✅ Phase 3: Git Integration (Complete)
- Smart Blame expert identification
- 7 weighted scoring factors for expertise calculation
- Expertise heatmap and bus factor analysis
- AWS cloud-ready architecture (Neptune/CodeCommit ready)

### 🔲 Phase 4: Advanced Complexity (Planned)
### 🔲 Phase 5: Semantic/Vector Layer (Planned)

## 📁 Project Structure

```
Node-Zero-Synapse/
├── backend/
│   ├── app/
│   │   └── main.py              # FastAPI application
│   ├── core/
│   │   ├── entities.py          # Data models (FunctionEntity, ClassEntity, etc.)
│   │   ├── complexity.py        # Cyclomatic & cognitive complexity
│   │   ├── parser.py            # tree-sitter AST parsing
│   │   ├── relationships.py     # RelationType enum, Relationship model
│   │   ├── resolver.py          # Smart call resolution
│   │   ├── relationship_extractor.py  # Edge extraction
│   │   ├── graph.py             # CodeGraph, blast radius analysis
│   │   ├── smart_git.py         # High-level Smart Blame API
│   │   └── blame/               # Smart Blame module
│   │       ├── models.py        # DeveloperProfile, ExpertiseScore, etc.
│   │       ├── analyzer.py      # SmartBlameAnalyzer orchestrator
│   │       ├── providers/       # Git providers (local, AWS)
│   │       ├── scoring/         # 7 weighted scoring factors
│   │       └── stores/          # Expert stores (memory, Neptune)
│   └── tests/
│       └── test_smart_blame.py  # Smart Blame test suite
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

---

## ✅ Phase 3: Smart Blame - Git Integration (Complete)

The **Smart Blame** feature identifies true code experts beyond simple `git blame` by analyzing commit patterns, refactoring depth, architectural contributions, and recency.

### Features

| Feature | Description |
|---------|-------------|
| **Expert Identification** | "Ask Sarah, she architected this" - finds true experts, not just last committers |
| **7 Weighted Scoring Factors** | Commit frequency, lines changed, refactor depth, architectural changes, bug fixes, recency, code review |
| **Expertise Heatmap** | Visualize expertise distribution across modules |
| **Bus Factor Analysis** | Identify single points of failure (modules with only 1-2 experts) |
| **Knowledge Gap Detection** | Find areas with insufficient expertise coverage |
| **AWS Cloud-Ready** | Abstract interfaces for future Neptune/CodeCommit integration |

### Smart Blame Module Structure

```
backend/core/blame/
├── __init__.py              # Main module exports
├── models.py                # Data models (DeveloperProfile, ExpertiseScore, etc.)
├── analyzer.py              # SmartBlameAnalyzer orchestrator
├── providers/
│   ├── base.py              # Abstract GitProvider interface (AWS-ready)
│   └── local_git.py         # GitPython implementation
├── scoring/
│   ├── factors.py           # 7 weighted scoring factors
│   └── calculator.py        # ExpertiseScoreCalculator
└── stores/
    ├── base.py              # Abstract ExpertStore interface (Neptune-ready)
    └── memory.py            # InMemoryStore implementation
```

### Scoring Algorithm

| Factor | Weight | Description |
|--------|--------|-------------|
| `commit_frequency` | 0.15 | How often the developer commits to this file |
| `lines_changed` | 0.10 | Total lines modified by the developer |
| `refactor_depth` | 0.25 | Complexity and depth of refactoring commits |
| `architectural_changes` | 0.20 | Contributions to structural changes |
| `bug_fixes` | 0.15 | Bug fixes demonstrate deep understanding |
| `recency` | 0.10 | Recent activity weighted higher (exponential decay) |
| `code_review_participation` | 0.05 | Participation in code reviews |

### Usage

**Analyze any git repository:**

```bash
cd /path/to/Node-Zero-Synapse && python -c "
import sys, os; sys.path.insert(0, 'backend/core')
import asyncio
from blame.analyzer import create_analyzer

async def main():
    repo_path = '/path/to/your/repo'  # Use absolute path
    analyzer = await create_analyzer(repo_path)
    
    # Get expert recommendation for a file
    result = await analyzer.identify_expert('src/main.py')
    print(result.recommendation_text)  # 'Ask Sarah, she architected this'
    print(f'Score: {result.score.total_score:.2f}')
    print(f'Bus Factor: {result.bus_factor}')

asyncio.run(main())
"
```

**Analyze entire repository:**

```python
# Get expertise for all Python files
results = await analyzer.analyze_repository(file_patterns=['.py'])

# Generate expertise heatmap
heatmap = await analyzer.generate_heatmap()
print(f'Risk areas: {heatmap.risk_areas}')
print(f'Knowledge gaps: {heatmap.knowledge_gaps}')

# Get bus factor analysis
bus_factors = await analyzer.get_bus_factor_analysis()
```

### Smart Blame API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/blame/expert/{file_path}` | GET | Get recommended expert for a file |
| `/blame/heatmap` | GET | Get expertise heatmap for codebase |
| `/blame/bus-factor` | GET | Get bus factor analysis |
| `/blame/gaps` | GET | Identify knowledge gaps |
| `/blame/developer/{email}` | GET | Get developer's expertise areas |

### Requirements

```bash
pip install gitpython
```

### Example Output

```
*** EXPERT RECOMMENDATION ***
Target: src/main.py
Recommendation: Ask Sarah, she architected this module
Bus Factor: 3
Primary Expert: Sarah Chen <sarah@example.com>
Score: 0.85
Confidence: 0.92

Factors:
  - commit_frequency: 0.75
  - lines_changed: 0.80
  - refactor_depth: 0.95
  - architectural_changes: 0.90
  - bug_fixes: 0.60
  - recency: 0.85
  - code_review_participation: 0.70
```

---

## 📝 License

MIT License - See LICENSE file for details.

---

*Part of the Node-Zero project suite.*
