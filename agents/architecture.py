from common import call_structured

SYSTEM = """You are the Architecture Agent in a system design reasoning pipeline. Given \
requirements, a scale estimate, and domain analysis, propose a concrete component-level \
architecture like a staff engineer sketching a design on a whiteboard. Name real components \
(e.g. "API Gateway", "Write-path service", "Metadata DB", "CDN"), not vague boxes. Explain how \
data flows through the system for the main use cases. Your job is the SHAPE of the system \
(components, responsibilities, connections) — do NOT pick specific vendor technologies yet, that \
happens in a later stage; describe components by role/type (e.g. "relational datastore", \
"in-memory cache", "message queue") instead. Keep it to the components that actually matter at \
this scale — aim for 6-10 components, the way a staff engineer would draw it on a whiteboard in \
an interview, not an exhaustive microservices decomposition."""

SCHEMA = {
    "type": "object",
    "properties": {
        "components": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {
                        "type": "string",
                        "description": "role/category, e.g. 'service', 'relational datastore', "
                        "'cache', 'queue', 'object storage', 'cdn', 'load balancer'",
                    },
                    "responsibility": {"type": "string"},
                },
                "required": ["name", "type", "responsibility"],
            },
        },
        "connections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "purpose": {"type": "string"},
                },
                "required": ["from", "to", "purpose"],
            },
        },
        "primary_data_flows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "use_case": {"type": "string"},
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ordered steps data/requests take through the components",
                    },
                },
                "required": ["use_case", "steps"],
            },
        },
    },
    "required": ["components", "connections", "primary_data_flows"],
}


def run(
    query: str,
    requirements: dict,
    scale: dict,
    domain: dict,
    previous_architecture: dict | None = None,
    revision_notes: str = "",
) -> dict:
    user = (
        f"Problem: {query}\n\n"
        f"Functional requirements: {requirements.get('functional_requirements')}\n"
        f"Non-functional requirements: {requirements.get('non_functional_requirements')}\n\n"
        f"Scale estimate: {scale.get('estimates')}\n"
        f"Peak/average: {scale.get('peak_to_average_ratio')}\n\n"
        f"Domain type: {domain.get('domain_type')}\n"
        f"Domain constraints: {domain.get('domain_constraints')}\n"
        f"Key tradeoffs: {domain.get('key_tradeoffs')}"
    )
    if previous_architecture and revision_notes:
        user += (
            f"\n\nHere is the CURRENT architecture (your previous round's output):\n"
            f"{previous_architecture}\n\n"
            f"It has these specific problems — revise the architecture to fix them. Keep every "
            f"component and connection that isn't implicated in an issue below; do not redesign "
            f"parts that aren't broken. Prefer adjusting an existing component's responsibility "
            f"over adding a new one; add at most 1-2 new components only if genuinely necessary:"
            f"\n{revision_notes}"
        )
    # Output size scales with component count (each with connections + data-flow steps), so size
    # the budget off the previous round's component count instead of a fixed guess.
    num_components = len(previous_architecture.get("components", [])) if previous_architecture else 8
    max_tokens = min(8192, 2048 + 500 * num_components)
    return call_structured(
        system=SYSTEM,
        user=user,
        tool_name="submit_architecture",
        tool_description="Submit the proposed component-level architecture.",
        input_schema=SCHEMA,
        max_tokens=max_tokens,
    )
