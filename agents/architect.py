from common import call_structured, SONNET
from company import Company

ROLE = "Architect"

SYSTEM = """You are the Architect in a system design reasoning company. Given \
requirements, a scale estimate, and domain analysis, propose a concrete component-level \
architecture like a staff engineer sketching a design on a whiteboard. Name real components \
(e.g. "API Gateway", "Write-path service", "Metadata DB", "CDN"), not vague boxes. Explain how \
data flows through the system for the main use cases. Your job is the SHAPE of the system \
(components, responsibilities, connections) — do NOT pick specific vendor technologies yet, that \
happens in a later stage; describe components by role/type (e.g. "relational datastore", \
"in-memory cache", "message queue") instead. Keep it to the components that actually matter at \
this scale — aim for 6-10 components, the way a staff engineer would draw it on a whiteboard in \
an interview, not an exhaustive microservices decomposition.

Every `from`/`to` value in `connections` must exactly match, character-for-character, a `name` \
in `components` — never a shortened or reworded version of it (e.g. if you name a component \
"Client Gateway (Connection/Edge Service)", every connection touching it must use that exact \
string, not "Client Gateway"). If a data flow involves an actor outside the system you're \
designing (a client app, an end user's device, a third-party service), add it as its own \
component too rather than referencing an undeclared name — every connection endpoint must \
resolve to something in your own `components` list."""

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
                "additionalProperties": False,
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
                "additionalProperties": False,
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
                "additionalProperties": False,
            },
        },
    },
    "required": ["components", "connections", "primary_data_flows"],
    "additionalProperties": False,
}


def run(company: Company, revision_notes: str = "") -> dict:
    requirements = company.read("requirements")
    scale = company.read("scale")
    domain = company.read("domain")
    previous_architecture = company.docs.get("architecture")
    user = (
        f"Problem: {company.query}\n\n"
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
    # Output size scales with component count, but connections and primary_data_flows (both
    # unbounded arrays) grow with it too, not just the component list itself — a straight
    # per-component multiplier undercounted them and caused truncation on larger architectures.
    # The real ceiling is 64000 (claude-haiku-4-5), so there's plenty of room to size generously.
    num_components = len(previous_architecture.get("components", [])) if previous_architecture else 8
    max_tokens = min(16000, 3072 + 700 * num_components)
    # Bumped to Sonnet: this is the core design-reasoning step in the pipeline, and the one most
    # worth paying for over Haiku.
    result, meta = call_structured(
        system=SYSTEM,
        user=user,
        tool_name="submit_architecture",
        tool_description="Submit the proposed component-level architecture.",
        input_schema=SCHEMA,
        model=SONNET,
        max_tokens=max_tokens,
    )
    company.publish(ROLE, "architecture", result)
    company.record_call(ROLE, meta)
    return result
