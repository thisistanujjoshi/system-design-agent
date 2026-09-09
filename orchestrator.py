import sys
import json
from concurrent.futures import ThreadPoolExecutor

from agents import product_manager, systems_analyst, domain_expert, architect, tech_lead, reviewer, presenter
from company import Company
from diagram import to_mermaid

MAX_REVISIONS = 3


def ask_clarifying_questions(questions: list[str]) -> str:
    print("\nBefore I design this, a few clarifying questions:\n")
    qa_lines = []
    for q in questions:
        answer = input(f"  {q}\n  > ").strip()
        if answer:
            qa_lines.append(f"Q: {q}\nA: {answer}")
    return "\n".join(qa_lines)


def format_issues(issues: list[dict]) -> str:
    return "\n".join(
        f"- [{i['severity']}] {i['component']}: {i['problem']} (fix: {i['suggested_fix']})"
        for i in issues
    )


def run_design(query: str, qa_context: str = "", verbose: bool = False) -> dict:
    """Run the full company non-interactively and return every intermediate + final artifact.

    Each role reads what it needs off the shared `Company` board and publishes its own output
    back to it — the orchestrator just tells roles when it's their turn, it doesn't wire their
    inputs/outputs together itself. `qa_context` is passed straight through to the Product
    Manager; the caller is responsible for gathering it (interactively, or not at all) before
    calling this.
    """
    company = Company(query=query)

    def log(label: str, data: dict) -> None:
        if verbose:
            print(f"\n=== {label} ===")
            print(json.dumps(data, indent=2))

    req = product_manager.run(company, qa_context=qa_context)
    log(f"{product_manager.ROLE}: Requirements", req)

    # Scale and domain analysis both depend only on requirements, not on each other, so run them
    # concurrently instead of paying for two sequential API round-trips.
    with ThreadPoolExecutor(max_workers=2) as pool:
        sc_future = pool.submit(systems_analyst.run, company)
        dm_future = pool.submit(domain_expert.run, company)
        sc = sc_future.result()
        dm = dm_future.result()
    log(f"{systems_analyst.ROLE}: Scale Estimate", sc)
    log(f"{domain_expert.ROLE}: Domain Analysis", dm)

    critique_history = []
    revision_notes = ""
    crit = None

    for round_num in range(1, MAX_REVISIONS + 1):
        arch = architect.run(company, revision_notes=revision_notes)
        log(f"{architect.ROLE}: Architecture (round {round_num})", arch)

        tech = tech_lead.run(company)
        log(f"{tech_lead.ROLE}: Technology Selection (round {round_num})", tech)

        crit = reviewer.run(company)
        log(f"{reviewer.ROLE}: Design Critique (round {round_num})", crit)
        critique_history.append({"round": round_num, **crit})

        if crit["verdict"] == "approve":
            if verbose:
                print(f"\n{reviewer.ROLE} approved the design.")
            break

        revision_notes = format_issues(crit["issues"])
        if verbose:
            print(f"\n{reviewer.ROLE} requested revisions. Revising (round {round_num + 1})...")
    hit_max_revisions = crit["verdict"] != "approve"
    if verbose and hit_max_revisions:
        print(f"\nHit max revisions ({MAX_REVISIONS}) — proceeding with the last design.")

    result = presenter.run(company, critique_history)
    log(f"{presenter.ROLE}: Final Explanation", result)

    return {
        "query": query,
        "requirements": req,
        "scale": sc,
        "domain": dm,
        "architecture": company.read("architecture"),
        "tech": company.read("tech"),
        "critique_history": critique_history,
        "hit_max_revisions": hit_max_revisions,
        "explanation": result,
        "mermaid": to_mermaid(company.read("architecture")),
    }


def run_pipeline(query: str) -> None:
    company = Company(query=query)
    req = product_manager.run(company)
    qa_context = ""
    if req["clarifying_questions"]:
        qa_context = ask_clarifying_questions(req["clarifying_questions"])

    design = run_design(query, qa_context=qa_context, verbose=True)
    result = design["explanation"]

    print("\n" + "=" * 70)
    print("FINAL DESIGN")
    print("=" * 70)
    print(f"\n{result['summary']}\n")
    print(result["narrative"])
    print("\n--- Architecture Diagram (Mermaid) ---\n")
    print(design["mermaid"])

    with open("design_output.md", "w") as f:
        f.write(f"# System Design: {query}\n\n")
        f.write(f"{result['summary']}\n\n")
        f.write(result["narrative"])
        f.write("\n\n## Architecture Diagram\n\n```mermaid\n")
        f.write(design["mermaid"])
        f.write("\n```\n")
    print("\n(Full write-up saved to design_output.md)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = input("What system do you want to design? ")
    run_pipeline(user_query)
