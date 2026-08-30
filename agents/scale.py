from common import call_structured

SYSTEM = """You are the Scale/Capacity Agent in a system design reasoning pipeline. Given a \
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
            },
        },
        "peak_to_average_ratio": {
            "type": "string",
            "description": "Estimated peak load multiplier and why (e.g. '3x for launch-day "
            "traffic spikes')",
        },
    },
    "required": ["assumptions", "estimates", "peak_to_average_ratio"],
}


def run(query: str, requirements: dict) -> dict:
    user = (
        f"Problem: {query}\n\n"
        f"Functional requirements: {requirements.get('functional_requirements')}\n"
        f"Non-functional requirements: {requirements.get('non_functional_requirements')}"
    )
    return call_structured(
        system=SYSTEM,
        user=user,
        tool_name="submit_scale_estimate",
        tool_description="Submit the capacity/scale estimate.",
        input_schema=SCHEMA,
        max_tokens=4096,
    )
