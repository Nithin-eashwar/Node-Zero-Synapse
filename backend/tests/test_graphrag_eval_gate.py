import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.graphrag_eval import compare_runs  # noqa: E402


def _write(path: Path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def _run_payload(faith, relevancy, precision=0.5, recall=0.5, p95_ms=1000.0, cost=0.001):
    return {
        "aggregate": {
            "faithfulness": faith,
            "answer_relevancy": relevancy,
            "context_precision": precision,
            "context_recall": recall,
            "p95_latency_ms": p95_ms,
            "avg_cost_query_usd": cost,
        }
    }


def test_compare_gate_blocks_faithfulness_drop(tmp_path):
    base = tmp_path / "baseline.json"
    cur = tmp_path / "current.json"
    _write(base, _run_payload(0.80, 0.81))
    _write(cur, _run_payload(0.77, 0.81))
    rc = compare_runs(SimpleNamespace(baseline=str(base), current=str(cur)))
    assert rc == 2


def test_compare_gate_allows_small_changes(tmp_path):
    base = tmp_path / "baseline.json"
    cur = tmp_path / "current.json"
    _write(base, _run_payload(0.80, 0.81))
    _write(cur, _run_payload(0.79, 0.80))
    rc = compare_runs(SimpleNamespace(baseline=str(base), current=str(cur)))
    assert rc == 0
