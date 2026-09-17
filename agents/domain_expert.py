from common import call_structured
from company import Company

ROLE = "Domain Expert"

SYSTEM = """You are the Domain Expert in a system design reasoning company. Given a problem \
statement and its requirements, you identify constraints and design implications that come \
specifically from the DOMAIN of this problem — not generic distributed-systems concerns (those \
are handled elsewhere). Examples of domain reasoning: a chat app needs message ordering and \
delivery guarantees; a payments system needs idempotency and exactly-once semantics; a ride-sharing \
app needs geospatial indexing and real-time matching; a social feed needs fan-out strategy \
(push vs pull) for follower graphs. Be concrete to THIS problem."""

SCHEMA = {
    "type": "object",
    "properties": {
        "domain_type": {
            "type": "string",
            "description": "Short label for the problem domain, e.g. 'real-time messaging', "
            "'geospatial matching', 'payments/ledger'",
        },
        "domain_constraints": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Concrete constraints or invariants this domain imposes on the design",
        },
        "key_tradeoffs": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Domain-specific tradeoffs the architecture will need to make "
            "(e.g. 'push vs pull fan-out', 'strong vs eventual consistency on X')",
        },
    },
    "required": ["domain_type", "domain_constraints", "key_tradeoffs"],
    "additionalProperties": False,
}


def run(company: Company) -> dict:
    requirements = company.read("requirements")
    user = (
        f"Problem: {company.query}\n\n"
        f"Functional requirements: {requirements.get('functional_requirements')}\n"
        f"Non-functional requirements: {requirements.get('non_functional_requirements')}"
    )
    result, meta = call_structured(
        system=SYSTEM,
        user=user,
        tool_name="submit_domain_analysis",
        tool_description="Submit the domain-specific constraints and tradeoffs.",
        input_schema=SCHEMA,
    )
    company.publish(ROLE, "domain", result)
    company.record_call(ROLE, meta)
    return result
