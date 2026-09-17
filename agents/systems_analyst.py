from common import call_structured, SONNET
from company import Company

ROLE = "Systems Analyst"

SYSTEM = """You are the Systems Analyst in a system design reasoning company. Given a \
problem statement and its requirements, you do back-of-the-envelope capacity estimation like a \
staff engineer: reads/writes per second, storage growth, bandwidth, and peak-vs-average load. \
Show your assumptions explicitly (e.g. "assume 100M DAU, 5% post daily") since the numbers matter \
less than showing the reasoning is sound. If the requirements already state hard numbers, use \
them instead of inventing your own."""

SCHEMA = {
    "type": "object",
    "properties": {
        "assumptions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The numeric assumptions used as inputs (user counts, request rates, "
            "object sizes, retention periods, etc.)",
        },
        "estimates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "description": "e.g. 'Write QPS', 'Storage/year'"},
                    "value": {"type": "string", "description": "e.g. '~2,000 QPS', '~50 TB/year'"},
                    "reasoning": {"type": "string", "description": "One-line derivation"},
                },
                "required": ["metric", "value", "reasoning"],
                "additionalProperties": False,
            },
        },
        "peak_to_average_ratio": {
            "type": "string",
            "description": "Estimated peak load multiplier and why (e.g. '3x for launch-day "
            "traffic spikes')",
        },
    },
    "required": ["assumptions", "estimates", "peak_to_average_ratio"],
    "additionalProperties": False,
}


def run(company: Company) -> dict:
    requirements = company.read("requirements")
    user = (
        f"Problem: {company.query}\n\n"
        f"Functional requirements: {requirements.get('functional_requirements')}\n"
        f"Non-functional requirements: {requirements.get('non_functional_requirements')}"
    )
    # Bumped to Sonnet: the eval harness scored this agent's estimates 3/5 ("scale_soundness")
    # on Haiku across every problem tested — this is the one step where numerical rigor matters
    # most and is worth the extra cost.
    result, meta = call_structured(
        system=SYSTEM,
        user=user,
        tool_name="submit_scale_estimate",
        tool_description="Submit the capacity/scale estimate.",
        input_schema=SCHEMA,
        model=SONNET,
        max_tokens=4096,
    )
    company.publish(ROLE, "scale", result)
    company.record_call(ROLE, meta)
    return result
