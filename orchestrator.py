import sys
import json

from agents import requirements, scale, domain, architecture, tech_selection, critic, explain
from diagram import to_mermaid
from models import DesignState

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


def run_pipeline(query: str) -> DesignState:
    state = DesignState(query=query)

    print(f"\n=== Requirements ===")
    req = requirements.run(query)
    if req["clarifying_questions"]:
        qa_context = ask_clarifying_questions(req["clarifying_questions"])
        req = requirements.run(query, qa_context=qa_context)
    state.functional_requirements = req["functional_requirements"]
    state.non_functional_requirements = req["non_functional_requirements"]
    print(json.dumps(req, indent=2))

    print(f"\n=== Scale Estimate ===")
    sc = scale.run(query, req)
    state.scale_estimate = sc
    print(json.dumps(sc, indent=2))

    print(f"\n=== Domain Analysis ===")
    dm = domain.run(query, req)
    state.domain_notes = dm
    print(json.dumps(dm, indent=2))

    critique_history = []
    revision_notes = ""
    arch, tech, crit = None, None, None

    for round_num in range(1, MAX_REVISIONS + 1):
        print(f"\n=== Architecture (round {round_num}) ===")
        arch = architecture.run(
            query, req, sc, dm, previous_architecture=arch, revision_notes=revision_notes
        )
        print(json.dumps(arch, indent=2))

        print(f"\n=== Technology Selection (round {round_num}) ===")
        tech = tech_selection.run(query, arch, sc, dm)
        print(json.dumps(tech, indent=2))

        print(f"\n=== Design Critique (round {round_num}) ===")
        crit = critic.run(query, req, sc, dm, arch, tech)
        print(json.dumps(crit, indent=2))
        critique_history.append({"round": round_num, **crit})

        if crit["verdict"] == "approve":
            print("\nCritic approved the design.")
            break

        revision_notes = format_issues(crit["issues"])
        print(f"\nCritic requested revisions. Revising (round {round_num + 1})...")
    else:
        print(f"\nHit max revisions ({MAX_REVISIONS}) — proceeding with the last design.")

    state.architecture = arch
    state.tech_choices = tech
    state.critiques = critique_history
    state.revision_count = len(critique_history) - 1

    print(f"\n=== Final Explanation ===")
    result = explain.run(query, req, sc, dm, arch, tech, critique_history)

    print("\n" + "=" * 70)
    print("FINAL DESIGN")
    print("=" * 70)
    print(f"\n{result['summary']}\n")
    print(result["narrative"])
    print("\n--- Architecture Diagram (Mermaid) ---\n")
    mermaid = to_mermaid(arch)
    print(mermaid)

    with open("design_output.md", "w") as f:
        f.write(f"# System Design: {query}\n\n")
        f.write(f"{result['summary']}\n\n")
        f.write(result["narrative"])
        f.write("\n\n## Architecture Diagram\n\n```mermaid\n")
        f.write(mermaid)
        f.write("\n```\n")
    print("\n(Full write-up saved to design_output.md)")

    return state


if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
    else:
        user_query = input("What system do you want to design? ")
    run_pipeline(user_query)
