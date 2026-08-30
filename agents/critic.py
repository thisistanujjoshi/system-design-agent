from common import call_structured

SYSTEM = """You are the Design Critic Agent in a system design reasoning pipeline — a skeptical \
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
            "maxItems": 3,
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
            },
        },
        "verdict": {
            "type": "string",
            "enum": ["approve", "revise"],
            "description": "'revise' if there is any critical or major issue, 'approve' otherwise",
        },
    },
    "required": ["issues", "verdict"],
}


def run(query: str, requirements: dict, scale: dict, domain: dict, architecture: dict, tech: dict) -> dict:
    user = (
        f"Problem: {query}\n\n"
        f"Non-functional requirements: {requirements.get('non_functional_requirements')}\n\n"
        f"Scale estimate: {scale.get('estimates')}\n"
        f"Peak/average: {scale.get('peak_to_average_ratio')}\n\n"
        f"Domain constraints: {domain.get('domain_constraints')}\n\n"
        f"Architecture components: {architecture.get('components')}\n"
        f"Connections: {architecture.get('connections')}\n\n"
        f"Technology choices: {tech.get('choices')}"
    )
    return call_structured(
        system=SYSTEM,
        user=user,
        tool_name="submit_critique",
        tool_description="Submit the design critique and verdict.",
        input_schema=SCHEMA,
        max_tokens=4096,
    )
