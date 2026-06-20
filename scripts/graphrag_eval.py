"""
GraphRAG benchmark runner + baseline compare gate.

Usage:
  python scripts/graphrag_eval.py run --benchmark scripts/graphrag_benchmark_v1.json
  python scripts/graphrag_eval.py snapshot --run-file uploads/latest.json
  python scripts/graphrag_eval.py compare --baseline scripts/graphrag_baseline_v1.json --current uploads/latest.json
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ai.rag import RAGPipeline  # noqa: E402
from backend.graph.code_graph import build_dependency_graph  # noqa: E402
from backend.ai.retrieval_orchestrator import p95  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_git_sha() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT)
            .decode("utf-8")
            .strip()
        )
    except Exception:
        return "unknown"


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _entity_hit_score(expected_entities: Sequence[str], evidence: Sequence[Dict[str, Any]], answer: str) -> Tuple[float, bool]:
    if not expected_entities:
        return 1.0, False
    bucket = " ".join(
        [answer]
        + [str(e.get("unique_id", "")) for e in evidence]
        + [str(e.get("snippet", "")) for e in evidence]
    ).lower()
    hits = 0
    for e in expected_entities:
        if str(e).lower() in bucket:
            hits += 1
    recall = hits / max(len(expected_entities), 1)
    missing = hits < len(expected_entities)
    return recall, missing


def _heuristic_answer_relevancy(question: str, answer: str) -> float:
    q_tokens = {t.lower() for t in question.split() if len(t) > 2}
    a_tokens = {t.lower() for t in answer.split() if len(t) > 2}
    if not q_tokens:
        return 0.0
    overlap = len(q_tokens.intersection(a_tokens)) / len(q_tokens)
    return min(1.0, max(0.0, overlap))


def _run_ragas_if_available(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Best-effort RAGAS scoring.
    Falls back silently if dependencies/models are unavailable.
    """
    try:
        from datasets import Dataset  # type: ignore
        from ragas import evaluate  # type: ignore
        from ragas.metrics import (  # type: ignore
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )
    except Exception:
        return {}

    samples = {
        "question": [r["question"] for r in rows],
        "answer": [r["answer"] for r in rows],
        "contexts": [r["contexts"] for r in rows],
        # RAGAS expects references/ground truths for some metrics.
        "ground_truth": [r.get("ground_truth", "") for r in rows],
    }
    ds = Dataset.from_dict(samples)
    try:
        scored = evaluate(
            ds,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )
        return {
            "faithfulness": float(scored["faithfulness"]),
            "answer_relevancy": float(scored["answer_relevancy"]),
            "context_precision": float(scored["context_precision"]),
            "context_recall": float(scored["context_recall"]),
        }
    except Exception:
        return {}


def _format_report_md(run: Dict[str, Any]) -> str:
    m = run["aggregate"]
    lines = [
        f"# GraphRAG Benchmark Report ({run['benchmark_version']})",
        "",
        f"- Timestamp: `{run['timestamp']}`",
        f"- Commit: `{run['commit_sha']}`",
        f"- Questions: `{run['question_count']}`",
        f"- Model provider: `{run['config']['provider']}`",
        f"- LLM model: `{run['config']['llm_model']}`",
        f"- Embedding model: `{run['config']['embedding_model']}`",
        "",
        "## Aggregate Metrics",
        "",
        f"- Faithfulness: `{m['faithfulness']:.4f}`",
        f"- Answer Relevancy: `{m['answer_relevancy']:.4f}`",
        f"- Context Precision: `{m['context_precision']:.4f}`",
        f"- Context Recall: `{m['context_recall']:.4f}`",
        f"- p95 Latency (ms): `{m['p95_latency_ms']:.2f}`",
        f"- Cost / query (USD): `{m['avg_cost_query_usd']:.8f}`",
        "",
        "## Quality Flags",
        "",
        f"- Hallucination flags: `{m['hallucination_flags']}`",
        f"- Missing-entity flags: `{m['missing_entity_flags']}`",
        "",
    ]
    return "\n".join(lines)


async def run_benchmark(args) -> int:
    benchmark_path = Path(args.benchmark).resolve()
    benchmark = _load_json(benchmark_path)
    questions = benchmark.get("questions", [])
    if args.limit:
        questions = questions[: args.limit]

    graph_path = Path(args.graph_file).resolve()
    graph_data = _load_json(graph_path)
    code_graph = build_dependency_graph(graph_data)

    pipeline = RAGPipeline()
    pipeline.set_graph_context(code_graph.store, graph_data, repo_path=str(ROOT))
    pipeline.ensure_indexed(graph_data, force_reindex=False)

    rows: List[Dict[str, Any]] = []
    latencies: List[float] = []
    costs: List[float] = []
    faithfulness_scores: List[float] = []
    relevancy_scores: List[float] = []
    context_precisions: List[float] = []
    context_recalls: List[float] = []
    hallucination_flags = 0
    missing_entity_flags = 0

    for q in questions:
        question = str(q.get("query", ""))
        expected_entities = q.get("expected_entities", [])
        start = time.perf_counter()
        result = await pipeline.ask(question)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        answer = str(result.get("answer", ""))
        evidence = result.get("evidence", []) or []
        contexts = result.get("context", []) or []
        grounding = result.get("grounding", {}) or {}
        metrics = result.get("metrics", {}) or {}
        cost = float(metrics.get("cost_query_usd_estimate", 0.0) or 0.0)

        entity_recall, missing_flag = _entity_hit_score(expected_entities, evidence, answer)
        relevancy = _heuristic_answer_relevancy(question, answer)
        unsupported = int(grounding.get("unsupported_claim_count", 0) or 0)
        grounded = bool(grounding.get("grounded", False))
        faith = max(0.0, 1.0 - min(1.0, unsupported * 0.34))
        if grounded:
            faith = max(faith, 0.8)
        context_precision = entity_recall if evidence else 0.0
        context_recall = entity_recall

        if not grounded:
            hallucination_flags += 1
        if missing_flag:
            missing_entity_flags += 1

        latencies.append(elapsed_ms)
        costs.append(cost)
        faithfulness_scores.append(faith)
        relevancy_scores.append(relevancy)
        context_precisions.append(context_precision)
        context_recalls.append(context_recall)

        rows.append(
            {
                "id": q.get("id"),
                "category": q.get("category"),
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "expected_entities": expected_entities,
                "latency_ms": round(elapsed_ms, 3),
                "cost_query_usd": cost,
                "grounded": grounded,
                "unsupported_claim_count": unsupported,
                "missing_entity_flag": missing_flag,
                "scores": {
                    "faithfulness": faith,
                    "answer_relevancy": relevancy,
                    "context_precision": context_precision,
                    "context_recall": context_recall,
                },
                "retrieval_trace": result.get("retrieval_trace", {}),
            }
        )

    ragas_scores = _run_ragas_if_available(rows)
    faithfulness = ragas_scores.get("faithfulness", statistics.fmean(faithfulness_scores) if faithfulness_scores else 0.0)
    answer_relevancy = ragas_scores.get("answer_relevancy", statistics.fmean(relevancy_scores) if relevancy_scores else 0.0)
    context_precision = ragas_scores.get("context_precision", statistics.fmean(context_precisions) if context_precisions else 0.0)
    context_recall = ragas_scores.get("context_recall", statistics.fmean(context_recalls) if context_recalls else 0.0)

    run = {
        "benchmark_version": benchmark.get("benchmark_version", "unknown"),
        "timestamp": _now_iso(),
        "commit_sha": _safe_git_sha(),
        "question_count": len(rows),
        "config": {
            "provider": os.getenv("LLM_PROVIDER", "gemini"),
            "llm_model": os.getenv("GEMINI_MODEL", os.getenv("BEDROCK_MODEL_ID", "")),
            "embedding_model": os.getenv("EMBEDDING_MODEL", "all-mpnet-base-v2"),
            "retrieval_flags": {
                "SYNAPSE_RAG_HYBRID": os.getenv("SYNAPSE_RAG_HYBRID", "1"),
                "SYNAPSE_RAG_RERANKER": os.getenv("SYNAPSE_RAG_RERANKER", "1"),
                "SYNAPSE_RAG_INTENT_EXPANSION": os.getenv("SYNAPSE_RAG_INTENT_EXPANSION", "1"),
                "SYNAPSE_RAG_GROUNDED_ONLY": os.getenv("SYNAPSE_RAG_GROUNDED_ONLY", "0"),
            },
            "prompt_version": os.getenv("SYNAPSE_PROMPT_VERSION", "v1"),
        },
        "aggregate": {
            "faithfulness": float(faithfulness),
            "answer_relevancy": float(answer_relevancy),
            "context_precision": float(context_precision),
            "context_recall": float(context_recall),
            "p95_latency_ms": float(p95(latencies)),
            "avg_cost_query_usd": float(statistics.fmean(costs) if costs else 0.0),
            "hallucination_flags": hallucination_flags,
            "missing_entity_flags": missing_entity_flags,
        },
        "rows": rows,
    }

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_json = out_dir / f"run_{tag}.json"
    run_md = out_dir / f"run_{tag}.md"
    latest_json = out_dir / "latest.json"
    latest_md = out_dir / "latest.md"
    with open(run_json, "w", encoding="utf-8") as f:
        json.dump(run, f, indent=2)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(run, f, indent=2)
    report_md = _format_report_md(run)
    run_md.write_text(report_md, encoding="utf-8")
    latest_md.write_text(report_md, encoding="utf-8")
    print(f"[OK] Run saved: {run_json}")
    print(f"[OK] Report saved: {run_md}")
    return 0


def snapshot_baseline(args) -> int:
    run_file = Path(args.run_file).resolve()
    baseline_file = Path(args.baseline_file).resolve()
    run_data = _load_json(run_file)
    with open(baseline_file, "w", encoding="utf-8") as f:
        json.dump(run_data, f, indent=2)
    print(f"[OK] Baseline written: {baseline_file}")
    return 0


def compare_runs(args) -> int:
    baseline = _load_json(Path(args.baseline).resolve())
    current = _load_json(Path(args.current).resolve())

    b = baseline["aggregate"]
    c = current["aggregate"]
    deltas = {
        "faithfulness": float(c["faithfulness"] - b["faithfulness"]),
        "answer_relevancy": float(c["answer_relevancy"] - b["answer_relevancy"]),
        "context_precision": float(c["context_precision"] - b["context_precision"]),
        "context_recall": float(c["context_recall"] - b["context_recall"]),
        "p95_latency_ms": float(c["p95_latency_ms"] - b["p95_latency_ms"]),
        "avg_cost_query_usd": float(c["avg_cost_query_usd"] - b["avg_cost_query_usd"]),
    }

    drop_f = deltas["faithfulness"] < -0.02
    drop_r = deltas["answer_relevancy"] < -0.02
    warn_precision = deltas["context_precision"] < -0.03
    warn_recall = deltas["context_recall"] < -0.03
    latency_ratio = c["p95_latency_ms"] / max(1e-9, b["p95_latency_ms"])
    cost_ratio = c["avg_cost_query_usd"] / max(1e-12, b["avg_cost_query_usd"] or 1e-12)

    gate = {
        "pass": not (drop_f or drop_r),
        "hard_failures": {
            "faithfulness_regression": bool(drop_f),
            "answer_relevancy_regression": bool(drop_r),
        },
        "warnings": {
            "context_precision_regression": bool(warn_precision),
            "context_recall_regression": bool(warn_recall),
            "latency_target_exceeded": bool(latency_ratio > 1.0 and c["p95_latency_ms"] > 4000.0),
            "cost_target_exceeded": bool(cost_ratio > 1.25),
        },
        "deltas": deltas,
        "targets": {
            "faithfulness_hard_drop": -0.02,
            "answer_relevancy_hard_drop": -0.02,
            "context_warn_drop": -0.03,
            "p95_latency_ms_target": 4000.0,
            "cost_ratio_target": 1.25,
        },
    }
    print(json.dumps(gate, indent=2))
    return 0 if gate["pass"] else 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GraphRAG benchmark + baseline utilities.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run")
    run.add_argument("--benchmark", default="scripts/graphrag_benchmark_v1.json")
    run.add_argument("--graph-file", default="repo_graph.json")
    run.add_argument("--output-dir", default="uploads")
    run.add_argument("--limit", type=int, default=0)

    snap = sub.add_parser("snapshot")
    snap.add_argument("--run-file", default="uploads/latest.json")
    snap.add_argument("--baseline-file", default="scripts/graphrag_baseline_v1.json")

    cmp_cmd = sub.add_parser("compare")
    cmp_cmd.add_argument("--baseline", default="scripts/graphrag_baseline_v1.json")
    cmp_cmd.add_argument("--current", default="uploads/latest.json")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.cmd == "run":
        return __import__("asyncio").run(run_benchmark(args))
    if args.cmd == "snapshot":
        return snapshot_baseline(args)
    if args.cmd == "compare":
        return compare_runs(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
