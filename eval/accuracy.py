"""Deterministic correctness checks — no LLM call, no judgment call, just referential integrity
and self-consistency the pipeline's own agents are supposed to guarantee. These catch a real class
of bug an LLM judge tends to miss (it reads the design as prose and doesn't cross-reference IDs):
an agent naming a component in one document that was never actually proposed in another.

Each check returns (valid_count, total_count) so results can be pooled across problems and rounds
without losing the denominator.
"""

import re


def _core_name(name: str) -> str:
    """Strip a trailing parenthetical annotation, e.g. "Messaging Service (Ordering & Fan-out)"
    -> "Messaging Service". The Reviewer writes about components in free prose and routinely drops
    these annotations, so matching against the bare name avoids penalizing a legitimate citation."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()


def check_connections_valid(architecture: dict) -> tuple[int, int]:
    """Every connection's `from`/`to` must name a component the Architect actually proposed."""
    names = {c.get("name") for c in architecture.get("components", [])}
    connections = architecture.get("connections", [])
    if not connections:
        return 0, 0
    valid = sum(1 for c in connections if c.get("from") in names and c.get("to") in names)
    return valid, len(connections)


def check_tech_choices_grounded(architecture: dict, tech: dict) -> tuple[int, int]:
    """Every tech choice's `component` must name a component that exists in the architecture —
    catches the Tech Lead inventing or misnaming a component it's supposedly assigning tech to."""
    names = {c.get("name") for c in architecture.get("components", [])}
    choices = tech.get("choices", [])
    if not choices:
        return 0, 0
    valid = sum(1 for ch in choices if ch.get("component") in names)
    return valid, len(choices)


def check_critique_grounded(architecture: dict, critique_history: list) -> tuple[int, int]:
    """Every critique issue's `component` must name a real component — catches the Reviewer
    citing a component that doesn't exist in the design it's supposedly reviewing.

    The Reviewer routinely annotates the component field with extra context (e.g. "Metadata Store
    consistency / DynamoDB Global Tables + custom alias uniqueness" rather than a bare "Metadata
    Store"), so this checks whether an architecture component name appears verbatim inside the
    issue's component string rather than requiring an exact match.
    """
    core_names = [_core_name(c.get("name", "")) for c in architecture.get("components", [])]
    total = valid = 0
    for round_ in critique_history:
        for issue in round_.get("issues", []):
            total += 1
            component = issue.get("component", "")
            if any(name and name in component for name in core_names):
                valid += 1
    return valid, total


def check_verdict_consistency(critique_history: list) -> tuple[int, int]:
    """The Reviewer's own system prompt states its policy: 'revise' if there is any critical or
    major issue, 'approve' otherwise. Check it actually followed that rule every round."""
    total = valid = 0
    for round_ in critique_history:
        total += 1
        issues = round_.get("issues", [])
        has_blocking = any(i.get("severity") in ("critical", "major") for i in issues)
        expected = "revise" if has_blocking else "approve"
        if round_.get("verdict") == expected:
            valid += 1
    return valid, total


CHECKS = {
    "connections_valid": lambda d: check_connections_valid(d["architecture"]),
    "tech_choices_grounded": lambda d: check_tech_choices_grounded(d["architecture"], d["tech"]),
    "critique_grounded": lambda d: check_critique_grounded(d["architecture"], d["critique_history"]),
    "verdict_consistent": lambda d: check_verdict_consistency(d["critique_history"]),
}


def run(design: dict) -> dict:
    results = {}
    total_valid = total_checks = 0
    for name, check in CHECKS.items():
        valid, total = check(design)
        results[name] = {"valid": valid, "total": total, "rate": (valid / total) if total else None}
        total_valid += valid
        total_checks += total
    return {
        "checks": results,
        "overall_rate": (total_valid / total_checks) if total_checks else None,
        "overall_valid": total_valid,
        "overall_total": total_checks,
    }
