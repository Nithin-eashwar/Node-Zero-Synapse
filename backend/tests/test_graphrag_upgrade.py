import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ai.retrieval_orchestrator import (  # noqa: E402
    RetrievalOrchestrator,
    RetrievalCandidate,
    EntityResolver,
    ContextBudgetManager,
    evaluate_grounding,
)


class FakeVectorStore:
    def build_unique_id(self, node):
        return node.get("unique_id")

    def build_document(self, node):
        return node.get("document", "")

    def build_metadata(self, node, unique_id):
        out = dict(node.get("metadata", {}))
        out["unique_id"] = unique_id
        out.setdefault("name", node.get("name", ""))
        out.setdefault("file", node.get("file", ""))
        out.setdefault("type", node.get("type", "function"))
        return out

    def search(self, query_embedding, n_results=5):
        docs = [
            "Function parse_data handles parsing and schema mapping.",
            "Class ParserConfig stores parsing options and defaults.",
            "Function validate_payload checks request payload fields.",
        ]
        metas = [
            {"unique_id": "a.py:parse_data:10", "name": "parse_data", "file": "a.py", "type": "function"},
            {"unique_id": "a.py:ParserConfig:3", "name": "ParserConfig", "file": "a.py", "type": "class"},
            {"unique_id": "b.py:validate_payload:18", "name": "validate_payload", "file": "b.py", "type": "function"},
        ]
        dists = [0.12, 0.32, 0.48]
        return {
            "documents": [docs[:n_results]],
            "metadatas": [metas[:n_results]],
            "distances": [dists[:n_results]],
        }


def _index_docs(orchestrator: RetrievalOrchestrator):
    nodes = [
        {
            "unique_id": "a.py:parse_data:10",
            "name": "parse_data",
            "file": "a.py",
            "type": "function",
            "document": "Function parse_data handles parsing and schema mapping.",
            "metadata": {"module": "parser"},
        },
        {
            "unique_id": "a.py:ParserConfig:3",
            "name": "ParserConfig",
            "file": "a.py",
            "type": "class",
            "document": "Class ParserConfig stores parsing options and defaults.",
            "metadata": {"module": "parser"},
        },
        {
            "unique_id": "b.py:validate_payload:18",
            "name": "validate_payload",
            "file": "b.py",
            "type": "function",
            "document": "Function validate_payload checks request payload fields.",
            "metadata": {"module": "validator"},
        },
    ]
    orchestrator.index_nodes(nodes)


def test_dynamic_top_k_policy():
    orch = RetrievalOrchestrator(FakeVectorStore())
    assert orch.dynamic_top_k(intent="general", confidence=0.9) == 4
    assert orch.dynamic_top_k(intent="governance", confidence=0.8) == 6
    assert orch.dynamic_top_k(intent="general", confidence=0.2) == 8


def test_hybrid_search_and_filters():
    orch = RetrievalOrchestrator(FakeVectorStore())
    _index_docs(orch)
    out, trace = orch.search(
        query="find class config in file:a.py",
        query_embedding=[0.1, 0.2],
        intent="architecture",
        use_hybrid=True,
        use_reranker=True,
        score_threshold=0.0,
    )
    assert len(out) >= 1
    assert trace["dynamic_top_k"] >= 6
    for c in out:
        assert c.file == "a.py"


def test_rrf_dedup_by_unique_id():
    sem = [
        RetrievalCandidate(
            id="u1",
            unique_id="u1",
            name="foo",
            file="a.py",
            source_type="semantic",
            document="foo",
            metadata={},
            semantic_rank=1,
            semantic_score=0.9,
        )
    ]
    lex = [
        RetrievalCandidate(
            id="u1",
            unique_id="u1",
            name="foo",
            file="a.py",
            source_type="lexical",
            document="foo",
            metadata={},
            lexical_rank=1,
            lexical_score=3.0,
        ),
        RetrievalCandidate(
            id="u2",
            unique_id="u2",
            name="bar",
            file="b.py",
            source_type="lexical",
            document="bar",
            metadata={},
            lexical_rank=2,
            lexical_score=2.0,
        ),
    ]
    fused = RetrievalOrchestrator._fuse_rrf(sem, lex)
    ids = [f.unique_id for f in fused]
    assert ids.count("u1") == 1
    assert "u2" in ids


def test_entity_resolution_with_file_hint():
    raw = [
        {"unique_id": "pkg/a.py:parse:10", "name": "parse"},
        {"unique_id": "pkg/b.py:parse:22", "name": "parse"},
    ]
    resolver = EntityResolver(raw)
    candidates = [
        RetrievalCandidate(
            id="1",
            unique_id="pkg/a.py:parse:10",
            name="parse",
            file="pkg/a.py",
            source_type="semantic",
            document="parse function",
            metadata={},
            rerank_score=0.5,
        ),
        RetrievalCandidate(
            id="2",
            unique_id="pkg/b.py:parse:22",
            name="parse",
            file="pkg/b.py",
            source_type="semantic",
            document="parse function",
            metadata={},
            rerank_score=0.49,
        ),
    ]
    resolved = resolver.resolve("explain parse file:pkg/b.py", candidates)
    assert resolved[0] == "pkg/b.py:parse:22"


def test_context_budget_pack_and_dedupe():
    manager = ContextBudgetManager(token_budget=40)
    c1 = RetrievalCandidate("1", "u1", "a", "a.py", "semantic", "alpha beta gamma", {}, rerank_score=0.8)
    c2 = RetrievalCandidate("2", "u1", "a", "a.py", "semantic", "alpha beta gamma", {}, rerank_score=0.7)
    packed, evidence, trace = manager.pack(
        intent="general",
        candidates=[c1, c2],
        graph_context="graph context",
        feature_data="",
    )
    assert "[INTENT:" in packed
    assert len(evidence) == 1
    assert trace["packed_evidence_count"] == 1


def test_grounding_overlap_check():
    evidence = [{"snippet": "parse_data validates schema and returns payload"}]
    good = evaluate_grounding("parse_data validates schema.", evidence)
    bad = evaluate_grounding("deploy kubernetes cluster now.", evidence)
    assert good["unsupported_claim_count"] <= bad["unsupported_claim_count"]
    assert bad["grounded"] is False

