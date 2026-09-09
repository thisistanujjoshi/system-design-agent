"""Eval harness: runs the pipeline over a fixed problem set and scores each design with an
LLM judge, so pipeline/prompt changes can be checked against a repeatable baseline instead of
eyeballing one or two example runs.

Usage: python -m eval.run_eval
"""

import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from orchestrator import run_design
from eval.problems import PROBLEMS
from eval.judge import run as judge_run

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
    print(
        f"    pipeline done ({len(design['critique_history'])} revision round(s), "
        f"hit_max_revisions={design['hit_max_revisions']})"
    )
    judgment = judge_run(problem["query"], design)
    overall = statistics.mean(judgment["scores"].values())
    print(f"    judged: overall {overall:.1f}/5, would_pass_interview={judgment['would_pass_interview']}")
    return {
        "id": problem["id"],
        "query": problem["query"],
        "design": design,
        "judgment": judgment,
        "overall_score": overall,
    }


def print_summary(results: list[dict]) -> None:
    scored = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]

    header = f"{'Problem':<24}{'Overall':>8}" + "".join(f"{d[:6]:>8}" for d in DIMENSIONS) + f"{'Pass?':>7}"
    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))
    for r in scored:
        s = r["judgment"]["scores"]
        row = f"{r['id']:<24}{r['overall_score']:>8.1f}"
        row += "".join(f"{s[d]:>8}" for d in DIMENSIONS)
        row += f"{'yes' if r['judgment']['would_pass_interview'] else 'no':>7}"
        print(row)
    for r in failed:
        print(f"{r['id']:<24}{'ERROR':>8}  {r['error']}")

    if scored:
        avg = statistics.mean(r["overall_score"] for r in scored)
        print("-" * len(header))
        print(f"Average overall score: {avg:.2f}/5 across {len(scored)}/{len(results)} problems")


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
                print(f"    FAILED [{problem['id']}]: {e}")
                results.append({"id": problem["id"], "query": problem["query"], "error": str(e)})

    results.sort(key=lambda r: [p["id"] for p in PROBLEMS].index(r["id"]))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"{timestamp}.json"
    out_path.write_text(json.dumps(results, indent=2))

    print_summary(results)
    print(f"\nFull results saved to {out_path}")


if __name__ == "__main__":
    main()
