"""Eval harness: runs the pipeline over a fixed problem set and measures it on four axes —
quality (LLM judge), accuracy (deterministic referential-integrity checks), latency, and cost —
plus a hallucination proxy, so pipeline/prompt changes can be checked against a repeatable
baseline instead of eyeballing one or two example runs.

Usage: python -m eval.run_eval
"""

import json
import statistics
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from orchestrator import run_design
from eval.problems import PROBLEMS
from eval.judge import run as judge_run
from eval import accuracy, hallucination

RESULTS_DIR = Path(__file__).parent / "results"

DIMENSIONS = [
    "requirements_coverage",
    "scale_soundness",
    "domain_awareness",
    "tech_justification",
    "critique_quality",
    "narrative_clarity",
]


def eval_one(problem: dict) -> dict:
    print(f"\n>>> {problem['id']}")
    design = run_design(problem["query"])
    metrics = design["metrics"]
    print(
        f"    pipeline done ({len(design['critique_history'])} revision round(s), "
        f"hit_max_revisions={design['hit_max_revisions']}, "
        f"latency={metrics['wall_latency_ms']:.0f}ms, cost=${metrics['total_cost_usd']:.4f})"
    )

    judgment, judge_meta = judge_run(problem["query"], design)
    overall = statistics.mean(judgment["scores"].values())
    print(f"    judged: overall {overall:.1f}/5, would_pass_interview={judgment['would_pass_interview']}")

    acc = accuracy.run(design)
    halluc = hallucination.run(design)
    print(
        f"    accuracy={acc['overall_rate']:.0%} ({acc['overall_valid']}/{acc['overall_total']} checks), "
        f"hallucinated={halluc['hallucinated']}"
    )

    return {
        "id": problem["id"],
        "query": problem["query"],
        "design": design,
        "judgment": judgment,
        "judge_cost_usd": judge_meta["cost_usd"],
        "overall_score": overall,
        "accuracy": acc,
        "hallucination": halluc,
    }


def aggregate(scored: list[dict], total_attempted: int) -> dict:
    latencies = [r["design"]["metrics"]["wall_latency_ms"] for r in scored]
    costs = [r["design"]["metrics"]["total_cost_usd"] for r in scored]
    accuracies = [r["accuracy"]["overall_rate"] for r in scored if r["accuracy"]["overall_rate"] is not None]
    hallucinated = [r["hallucination"]["hallucinated"] for r in scored]

    def pct(data: list[float], p: float) -> float:
        return statistics.quantiles(data, n=100)[int(p) - 1] if len(data) > 1 else data[0]

    return {
        "n": len(scored),
        "reliability": {
            "attempted": total_attempted,
            "succeeded": len(scored),
            "success_rate": len(scored) / total_attempted if total_attempted else None,
        },
        "quality": {
            "mean_overall_score": statistics.mean(r["overall_score"] for r in scored),
            "would_pass_interview_rate": statistics.mean(
                1.0 if r["judgment"]["would_pass_interview"] else 0.0 for r in scored
            ),
        },
        "accuracy": {
            "mean_rate": statistics.mean(accuracies) if accuracies else None,
        },
        "hallucination": {
            "rate": statistics.mean(1.0 if h else 0.0 for h in hallucinated),
        },
        "latency_ms": {
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "p95": pct(latencies, 95),
            "min": min(latencies),
            "max": max(latencies),
        },
        "cost_usd": {
            "mean_per_request": statistics.mean(costs),
            "median_per_request": statistics.median(costs),
            "total_for_run": sum(costs),
            "mean_judge_overhead": statistics.mean(r["judge_cost_usd"] for r in scored),
        },
    }


def print_summary(results: list[dict]) -> None:
    scored = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]

    header = (
        f"{'Problem':<24}{'Overall':>8}{'Acc':>6}{'Halluc':>7}{'Latency':>9}{'Cost':>9}{'Pass?':>7}"
    )
    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))
    for r in scored:
        m = r["design"]["metrics"]
        acc_rate = r["accuracy"]["overall_rate"]
        row = (
            f"{r['id']:<24}{r['overall_score']:>8.1f}"
            f"{(f'{acc_rate:.0%}' if acc_rate is not None else 'n/a'):>6}"
            f"{('yes' if r['hallucination']['hallucinated'] else 'no'):>7}"
            f"{m['wall_latency_ms']:>8.0f}m"
            f"{r['design']['metrics']['total_cost_usd']:>9.4f}"
            f"{('yes' if r['judgment']['would_pass_interview'] else 'no'):>7}"
        )
        print(row)
    for r in failed:
        print(f"{r['id']:<24}{'ERROR':>8}  {r['error']}")

    if scored:
        agg = aggregate(scored, total_attempted=len(results))
        print("-" * len(header))
        print(f"reliability: {agg['reliability']['succeeded']}/{agg['reliability']['attempted']} "
              f"runs completed ({agg['reliability']['success_rate']:.0%})")
        print(f"n={agg['n']}  |  quality {agg['quality']['mean_overall_score']:.2f}/5  |  "
              f"would-pass-interview {agg['quality']['would_pass_interview_rate']:.0%}  |  "
              f"accuracy {agg['accuracy']['mean_rate']:.0%}  |  "
              f"hallucination rate {agg['hallucination']['rate']:.0%}")
        print(f"latency (ms): mean={agg['latency_ms']['mean']:.0f} "
              f"median={agg['latency_ms']['median']:.0f} p95={agg['latency_ms']['p95']:.0f} "
              f"min={agg['latency_ms']['min']:.0f} max={agg['latency_ms']['max']:.0f}")
        print(f"cost/request: mean=${agg['cost_usd']['mean_per_request']:.4f} "
              f"median=${agg['cost_usd']['median_per_request']:.4f}  |  "
              f"total run cost=${agg['cost_usd']['total_for_run']:.4f}  |  "
              f"judge overhead avg=${agg['cost_usd']['mean_judge_overhead']:.4f}/problem (not counted "
              f"in per-request cost — it's eval-time only, never runs in production)")
        return agg
    return None


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    results = []
    # Problems are independent (each is its own pipeline run) so run them concurrently — these
    # calls are network-bound, not CPU-bound, so threads are enough without needing async.
    with ThreadPoolExecutor(max_workers=len(PROBLEMS)) as pool:
        futures = {pool.submit(eval_one, p): p for p in PROBLEMS}
        for future in as_completed(futures):
            problem = futures[future]
            try:
                results.append(future.result())
            except Exception as e:
                tb = traceback.format_exc()
                print(f"    FAILED [{problem['id']}]: {e}\n{tb}")
                results.append(
                    {"id": problem["id"], "query": problem["query"], "error": str(e), "traceback": tb}
                )

    results.sort(key=lambda r: [p["id"] for p in PROBLEMS].index(r["id"]))

    agg = print_summary(results)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"{timestamp}.json"
    out_path.write_text(json.dumps({"results": results, "aggregate": agg}, indent=2))
    print(f"\nFull results saved to {out_path}")


if __name__ == "__main__":
    main()
