from common import call_structured, SONNET
from company import Company

ROLE = "Staff Reviewer"

SYSTEM = """You are the Staff Reviewer in a system design reasoning company — a skeptical \
staff engineer reviewing a design at INTERVIEW-WHITEBOARD level, not doing a production code \
review. Find real, architecturally significant problems: single points of failure, bottlenecks \
under the stated scale, consistency/availability tradeoffs that weren't justified, a missing \
major component (e.g. no caching layer despite very high read QPS, no queue for an async \
workload), or a technology choice that plainly doesn't fit the scale or domain. Be specific — \
cite the component and the actual numbers from the scale estimate, don't hand-wave.

Do NOT flag implementation-level details that wouldn't change the whiteboard architecture: exact \
timeout values, specific retry/backoff counts, SQL injection prevention, exact cache-key schemes, \
idempotency token wiring, or test plans. Those are execution details, not design flaws.

Report at most the 3 most important issues, ranked by severity — fewer, sharper issues beat an \
exhaustive list. If the design is genuinely solid at this level, say so and approve it rather than \
inventing problems for the sake of criticism."""

SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            # strict=True tool schemas don't support maxItems (400 invalid_request_error) — the
            # 3-issue cap is enforced by the system prompt instruction instead.
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["critical", "major", "minor"]},
                    "component": {"type": "string"},
                    "problem": {"type": "string", "description": "1-2 sentences"},
                    "suggested_fix": {
                        "type": "string",
                        "description": "1-2 sentences, a whiteboard-level fix, not an "
                        "implementation plan",
                    },
                },
                "required": ["severity", "component", "problem", "suggested_fix"],
                "additionalProperties": False,
            },
        },
        "verdict": {
            "type": "string",
            "enum": ["approve", "revise"],
            "description": "'revise' if there is any critical or major issue, 'approve' otherwise",
        },
    },
    "required": ["issues", "verdict"],
    "additionalProperties": False,
}


def run(company: Company) -> dict:
    requirements = company.read("requirements")
    scale = company.read("scale")
    domain = company.read("domain")
    architecture = company.read("architecture")
    tech = company.read("tech")
    user = (
        f"Problem: {company.query}\n\n"
        f"Non-functional requirements: {requirements.get('non_functional_requirements')}\n\n"
        f"Scale estimate: {scale.get('estimates')}\n"
        f"Peak/average: {scale.get('peak_to_average_ratio')}\n\n"
        f"Domain constraints: {domain.get('domain_constraints')}\n\n"
        f"Architecture components: {architecture.get('components')}\n"
        f"Connections: {architecture.get('connections')}\n\n"
        f"Technology choices: {tech.get('choices')}"
    )
    # Bumped to Sonnet: a critic is only as useful as its ability to catch real issues — grading
    # the pipeline's own output with the same tier that produced it is a weaker check than
    # grading it with a stronger one.
    result, meta = call_structured(
        system=SYSTEM,
        user=user,
        tool_name="submit_critique",
        tool_description="Submit the design critique and verdict.",
        input_schema=SCHEMA,
        model=SONNET,
        max_tokens=4096,
    )
    company.publish(ROLE, "critique", result)
    company.record_call(ROLE, meta)
    return result
