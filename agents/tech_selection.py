from common import call_structured

SYSTEM = """You are the Technology Selection Agent in a system design reasoning pipeline. Given a \
proposed architecture (component roles), a scale estimate, and domain constraints, pick concrete, \
real-world technologies for each component (e.g. "PostgreSQL", "Redis", "Kafka", "S3", "DynamoDB", \
"Cloudflare CDN"). For each choice, justify it against the actual scale/domain requirements — not \
generic "it's popular" reasoning — and name the main alternative you considered and why you didn't \
pick it. Prefer boring, proven technology unless the scale or domain genuinely demands something \
more specialized."""

SCHEMA = {
    "type": "object",
    "properties": {
        "choices": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "component": {"type": "string", "description": "Component name from the architecture"},
                    "technology": {"type": "string"},
                    "justification": {"type": "string", "description": "1-2 sentences"},
                    "alternative_considered": {"type": "string"},
                    "why_not_alternative": {"type": "string", "description": "1 sentence"},
                },
                "required": [
                    "component",
                    "technology",
                    "justification",
                    "alternative_considered",
                    "why_not_alternative",
                ],
            },
        },
    },
    "required": ["choices"],
}


def run(query: str, architecture: dict, scale: dict, domain: dict) -> dict:
    user = (
        f"Problem: {query}\n\n"
        f"Architecture components: {architecture.get('components')}\n\n"
        f"Scale estimate: {scale.get('estimates')}\n"
        f"Domain type: {domain.get('domain_type')}\n"
        f"Domain constraints: {domain.get('domain_constraints')}"
    )
    # Output scales with component count (one full justified choice per component), so size the
    # budget off that instead of a fixed guess that breaks on more elaborate architectures.
    num_components = len(architecture.get("components", [])) or 8
    max_tokens = min(8192, 1024 + 400 * num_components)
    return call_structured(
        system=SYSTEM,
        user=user,
        tool_name="submit_tech_choices",
        tool_description="Submit the concrete technology choices with justification.",
        input_schema=SCHEMA,
        max_tokens=max_tokens,
    )
