from common import call_structured, SONNET
from company import Company

ROLE = "Tech Lead"

SYSTEM = """You are the Tech Lead in a system design reasoning company. Given a \
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
                "additionalProperties": False,
            },
        },
    },
    "required": ["choices"],
    "additionalProperties": False,
}


def run(company: Company) -> dict:
    architecture = company.read("architecture")
    scale = company.read("scale")
    domain = company.read("domain")
    user = (
        f"Problem: {company.query}\n\n"
        f"Architecture components: {architecture.get('components')}\n\n"
        f"Scale estimate: {scale.get('estimates')}\n"
        f"Domain type: {domain.get('domain_type')}\n"
        f"Domain constraints: {domain.get('domain_constraints')}"
    )
    # Output scales with component count (one full justified choice per component). The real
    # ceiling is 64000 (claude-haiku-4-5) — sized generously rather than against an arbitrary cap.
    num_components = len(architecture.get("components", [])) or 8
    max_tokens = min(16000, 2048 + 600 * num_components)
    # Bumped to Sonnet: the eval harness scored "tech_justification" 3/5 on Haiku across every
    # problem tested — genuine tradeoff reasoning ("why not the alternative") is exactly where
    # a stronger model should help most.
    result, meta = call_structured(
        system=SYSTEM,
        user=user,
        tool_name="submit_tech_choices",
        tool_description="Submit the concrete technology choices with justification.",
        input_schema=SCHEMA,
        model=SONNET,
        max_tokens=max_tokens,
    )
    company.publish(ROLE, "tech", result)
    company.record_call(ROLE, meta)
    return result
