"""Offline check for the Company message-board plumbing — no API calls.

Stubs common.call_structured so the pipeline runs on canned responses, and asserts each role
read/published to the right board slots (including that the Architect sees its own previous
round's output on revision).
"""

from unittest.mock import patch

from agents import product_manager, systems_analyst, domain_expert, architect, tech_lead, reviewer, presenter

CANNED = {
    "submit_requirements": {
        "clarifying_questions": [],
        "functional_requirements": ["do the thing"],
        "non_functional_requirements": ["be fast"],
    },
    "submit_scale_estimate": {
        "assumptions": ["1M users"],
        "estimates": [{"metric": "QPS", "value": "100", "reasoning": "math"}],
        "peak_to_average_ratio": "2x",
    },
    "submit_domain_analysis": {
        "domain_type": "test domain",
        "domain_constraints": ["must be testable"],
        "key_tradeoffs": ["speed vs correctness"],
    },
    "submit_tech_choices": {
        "choices": [
            {
                "component": "DB",
                "technology": "Postgres",
                "justification": "boring and proven",
                "alternative_considered": "DynamoDB",
                "why_not_alternative": "no need for that scale",
            }
        ]
    },
    "submit_explanation": {"summary": "a design", "narrative": "it works"},
}

# First critic call requests a revision, second approves — checks the revise-then-approve loop.
CRITIQUES = [
    {
        "issues": [
            {
                "severity": "major",
                "component": "DB",
                "problem": "single point of failure",
                "suggested_fix": "add a replica",
            }
        ],
        "verdict": "revise",
    },
    {"issues": [], "verdict": "approve"},
]

architecture_calls = []


def fake_call_structured(system, user, tool_name, tool_description, input_schema, **kwargs):
    if tool_name == "submit_architecture":
        architecture_calls.append(user)
        return {
            "components": [{"name": "DB", "type": "relational datastore", "responsibility": "store data"}],
            "connections": [],
            "primary_data_flows": [],
        }
    if tool_name == "submit_critique":
        return CRITIQUES.pop(0)
    return CANNED[tool_name]


ROLE_MODULES = [product_manager, systems_analyst, domain_expert, architect, tech_lead, reviewer, presenter]


def main() -> None:
    import orchestrator

    # Each role module did `from common import call_structured`, so it holds its own reference —
    # patch it on every role module, not on `common`.
    patches = [patch.object(m, "call_structured", side_effect=fake_call_structured) for m in ROLE_MODULES]
    for p in patches:
        p.start()
    try:
        design = orchestrator.run_design("a test system")
    finally:
        for p in patches:
            p.stop()

    assert design["requirements"]["functional_requirements"] == ["do the thing"]
    assert design["scale"]["assumptions"] == ["1M users"]
    assert design["domain"]["domain_type"] == "test domain"
    assert design["tech"]["choices"][0]["technology"] == "Postgres"
    assert design["explanation"]["summary"] == "a design"
    assert len(design["critique_history"]) == 2, "should revise once then approve"
    assert design["hit_max_revisions"] is False
    assert "DB" in design["mermaid"]

    # Round 2's architecture call must have been shown round 1's own output (the shared-board
    # read), not regenerated from a blank slate.
    assert len(architecture_calls) == 2
    assert "CURRENT architecture" in architecture_calls[1]
    assert "single point of failure" not in architecture_calls[0]

    print("OK: Company board plumbing, revision loop, and result shape all check out.")


if __name__ == "__main__":
    main()
