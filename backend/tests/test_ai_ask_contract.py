import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("SYNAPSE_DISABLE_AI", "1")

from backend.api.main import app  # noqa: E402
import backend.api.main as api_main  # noqa: E402


class _FakePipeline:
    def ensure_indexed(self, _nodes, force_reindex: bool = False):
        return 1

    async def ask(self, _query):
        return {
            "answer": "Mock answer",
            "context": ["ctx-a", "ctx-b"],
            "evidence": [
                {
                    "id": "ev1",
                    "unique_id": "x.py:foo:1",
                    "file": "x.py",
                    "snippet": "def foo()",
                    "score": 0.8,
                    "source_type": "semantic",
                    "rank": 1,
                }
            ],
            "retrieval_trace": {"semantic_count": 2, "final_count": 1},
            "grounding": {
                "grounded": True,
                "unsupported_claim_count": 0,
                "uncertainty_reason": "",
            },
            "metrics": {
                "stage_ms": {"retrieve_rerank": 1.5, "generate": 10.0},
                "total_latency_ms": 12.0,
                "cost_query_usd_estimate": 0.0001,
            },
            "intent": "general",
            "mode": "multi_source",
        }


def test_ai_ask_backwards_compatible_additive_fields(monkeypatch):
    api_main._ai_available = True
    api_main._rag_pipeline = _FakePipeline()
    monkeypatch.setattr(api_main, "get_rag_pipeline", lambda: api_main._rag_pipeline)
    api_main.graph_db["raw_data"] = [{"name": "foo"}]

    with TestClient(app) as client:
        response = client.get("/ai/ask", params={"query": "what does foo do?"})

    assert response.status_code == 200
    payload = response.json()

    # Backward-compat fields still present.
    assert "answer" in payload
    assert "context" in payload

    # New additive contract.
    assert "evidence" in payload
    assert "retrieval_trace" in payload
    assert "grounding" in payload
    assert "metrics" in payload
