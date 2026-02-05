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

### ✅ Phase 4: Architectural Governance (Complete)
- Boundary rules engine with YAML configuration
- Clean Architecture defaults with import validation
- Real-time violation detection
- Drift metrics and tracking over time

### ✅ Phase 4.5: Enhanced Risk Assessment (Complete)
- 6-factor weighted risk scoring (complexity, centrality, coverage, etc.)
- Betweenness centrality for hub node detection
- Actionable recommendations based on risk factors
- Risk levels: LOW/MEDIUM/HIGH/CRITICAL

### 🔲 Phase 5: Semantic/Vector Layer (Planned)

## 📁 Project Structure

```
Node-Zero-Synapse/
├── backend/
│   ├── api/                     # API Layer
│   │   ├── main.py              # FastAPI application
│   │   └── routes/              # Route handlers
│   ├── parsing/                 # Code Parsing Domain
│   │   ├── parser.py            # tree-sitter AST parsing
│   │   ├── entities.py          # FunctionEntity, ClassEntity, etc.
│   │   └── complexity.py        # Cyclomatic & cognitive metrics
│   ├── graph/                   # Graph Analysis Domain
│   │   ├── relationships.py     # RelationType enum, Relationship model
│   │   ├── resolver.py          # Smart call resolution
│   │   ├── extractor.py         # Relationship extraction
│   │   └── code_graph.py        # CodeGraph, blast radius, RiskFactors
│   ├── git/                     # Git Analysis Domain
│   │   ├── smart_git.py         # High-level Smart Blame API
│   │   └── blame/               # Smart Blame module
│   │       ├── models.py        # DeveloperProfile, ExpertiseScore
│   │       ├── analyzer.py      # SmartBlameAnalyzer orchestrator
│   │       ├── providers/       # Git providers (local, AWS)
│   │       ├── scoring/         # 7 weighted scoring factors
│   │       └── stores/          # Expert stores (memory, Neptune)
│   ├── governance/              # Architectural Governance
│   │   ├── models.py            # Layer, BoundaryRule, Violation, DriftMetrics
│   │   ├── rules.py             # RuleEngine with YAML config
│   │   ├── validator.py         # ArchitectureValidator
│   │   └── drift.py             # DriftDetector
│   └── data/                    # Data files
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
python -m backend.parsing.parser <path_to_repo>

# 4. Analyze the graph
python -m backend.graph.code_graph

# 5. Run the API server
uvicorn backend.api.main:app --reload
```

## 📊 Example Output

```
[*] Building dependency graph...
[INFO] Graph Stats: 17 nodes, 11 edges
[INFO] Edge types: {'CALLS': 9, 'INHERITS': 2}

[*] Calculating Blast Radius for: 'process_data'
[!] WARNING: Changing this affects 1 functions!
    Direct callers: 1
    Risk score: 0.27 (MEDIUM)
    
Risk Factors:
    complexity_risk: 0.0
    centrality_risk: 0.5
    test_coverage_risk: 1.0
    dependency_risk: 0.1
    
Recommendations:
    - Add unit tests before modifying this code
```

## 🔧 API Endpoints

### Core Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/graph` | GET | Get full dependency graph |
| `/blast-radius/{function}` | GET | Calculate blast radius with risk factors |

### Governance Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/governance/validate` | GET | Validate architecture against rules |
| `/governance/violations` | GET | List boundary violations |
| `/governance/drift` | GET | Get architectural drift report |
| `/governance/layers` | GET | View configured layers and rules |

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

## ✅ Phase 4: Architectural Governance (Complete)

Enforce layered architecture boundaries and detect drift over time.

### Features

| Feature | Description |
|---------|-------------|
| **Boundary Rules Engine** | Define allowed/blocked imports between layers |
| **YAML Configuration** | Customizable layer definitions via `.synapse/architecture.yaml` |
| **Clean Architecture Defaults** | Built-in rules for API → Service → Data patterns |
| **Violation Detection** | Real-time import validation |
| **Drift Metrics** | Track coupling, cohesion, and violations over time |

### Usage

```bash
# Validate architecture
python -m backend.governance.validator <repo_path>

# Save baseline metrics
python -m backend.governance.drift --save-baseline <repo_path> baseline.json

# Detect drift
python -m backend.governance.drift <repo_path> baseline.json
```

### Example Config (`.synapse/architecture.yaml`)

```yaml
layers:
  api:
    patterns: ["**/api/**", "**/routes/**"]
  service:
    patterns: ["**/services/**", "**/core/**"]
  data:
    patterns: ["**/data/**", "**/models/**"]

rules:
  - name: "API cannot access Data directly"
    from: api
    to: data
    action: block
```

---

## ✅ Phase 4.5: Enhanced Risk Assessment (Complete)

Multi-factor risk scoring for blast radius analysis.

### Risk Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| `complexity_risk` | 25% | Cyclomatic/cognitive complexity |
| `centrality_risk` | 20% | Betweenness centrality (hub nodes) |
| `test_coverage_risk` | 20% | 0.0 = well tested, 1.0 = no tests |
| `dependency_risk` | 15% | Number of things depending on this |
| `change_frequency_risk` | 10% | How often the code changes |
| `bus_factor_risk` | 10% | Single expert = higher risk |

### Risk Levels

| Score | Level | Action |
|-------|-------|--------|
| 0.0 - 0.2 | LOW | Standard workflow |
| 0.2 - 0.5 | MEDIUM | Extra review recommended |
| 0.5 - 0.8 | HIGH | Pair programming suggested |
| 0.8 - 1.0 | CRITICAL | Refactor before changes |

### Recommendations Generated

The system automatically generates actionable advice:
- "Add unit tests before modifying this code"
- "This is a critical path node - changes will have wide impact"
- "Consider refactoring to reduce complexity before changes"

---

## 📝 License

MIT License - See LICENSE file for details.

---

*Part of the Node-Zero project suite.*
