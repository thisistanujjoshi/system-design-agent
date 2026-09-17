from common import call_structured
from company import Company

ROLE = "Presenter"

SYSTEM = """You are the Presenter in a system design reasoning company. Given the full \
design (requirements, scale, domain, final architecture, tech choices, and a summary of what was \
revised during critique), write it up the way a staff engineer would present a final design in an \
interview: crisp, confident, and honest about tradeoffs made. Cover: the problem restated in one \
line, the key requirements that shaped the design, the architecture and why it's shaped that way, \
the technology choices and their tradeoffs, and — briefly — what was revised during critique and \
why, since that shows real design iteration rather than a first draft.

Be concise: hit the most important points once, don't restate the same tradeoff in multiple \
sections, and don't try to cover every minor detail from the inputs — a staff engineer's verbal \
walkthrough is tight, not exhaustive."""

SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "One paragraph, the elevator pitch of the design"},
        "narrative": {
            "type": "string",
            "description": "The full write-up in markdown, roughly 500-900 words across a few "
            "clear sections, as a staff engineer would present it verbally — not an exhaustive "
            "dump of every input detail",
        },
    },
    "required": ["summary", "narrative"],
    "additionalProperties": False,
}


def run(company: Company, critique_history: list) -> dict:
    requirements = company.read("requirements")
    scale = company.read("scale")
    domain = company.read("domain")
    architecture = company.read("architecture")
    tech = company.read("tech")
    # Only the final round's issues matter for "what's still a known tradeoff"; earlier rounds are
    # summarized to one line each so the input doesn't balloon the model into an exhaustive output.
    if critique_history:
        earlier = critique_history[:-1]
        final_round = critique_history[-1]
        earlier_summary = [
            f"Round {r['round']}: fixed {len(r['issues'])} issue(s) — "
            + "; ".join(i["component"] for i in r["issues"])
            for r in earlier
        ]
    else:
        earlier_summary, final_round = [], {}

    user = (
        f"Problem: {company.query}\n\n"
        f"Requirements: {requirements}\n\n"
        f"Scale: {scale}\n\n"
        f"Domain: {domain}\n\n"
        f"Final architecture: {architecture}\n\n"
        f"Final tech choices: {tech}\n\n"
        f"Earlier revision rounds (one line each): {earlier_summary}\n"
        f"Final round's outstanding/just-fixed issues: {final_round}"
    )
    result, meta = call_structured(
        system=SYSTEM,
        user=user,
        tool_name="submit_explanation",
        tool_description="Submit the final design write-up.",
        input_schema=SCHEMA,
        max_tokens=8192,
    )
    company.publish(ROLE, "explanation", result)
    company.record_call(ROLE, meta)
    return result
