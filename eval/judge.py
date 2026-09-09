from common import call_structured

# Deliberately a stronger model than the pipeline it's grading (which runs on Haiku) — a judge
# shouldn't be the same tier as the thing it's judging.
JUDGE_MODEL = "claude-sonnet-5"

SYSTEM = """You are a rigorous system design interviewer evaluating a candidate's design against \
the original problem statement. Score it the way a demanding staff engineer would when deciding \
whether this design would pass a real system design interview loop — not against a generic \
checklist. Be skeptical: if the architecture is generic boilerplate that ignores the stated scale \
or domain, or if the critique/revision rounds didn't catch real problems, say so and score \
accordingly. Do not be lenient just because the write-up sounds confident."""

SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "object",
            "description": "1 (poor) to 5 (excellent) on each dimension.",
            "properties": {
                "requirements_coverage": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Does the architecture and tech selection actually address "
                    "the stated functional and non-functional requirements?",
                },
                "scale_soundness": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Are the capacity estimates reasonable, and is the "
                    "architecture appropriately sized for that scale (not over- or "
                    "under-engineered)?",
                },
                "domain_awareness": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Does the design actually address the domain-specific "
                    "constraints identified (ordering, consistency, geospatial, idempotency, "
                    "etc.), or are they just listed and then ignored?",
                },
                "tech_justification": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Are technology choices justified with genuine, "
                    "scale/domain-specific reasoning and a real alternative considered, or "
                    "generic 'it's popular' reasoning?",
                },
                "critique_quality": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Did the critic find real, architecturally significant "
                    "issues (if any existed), and did the revision genuinely fix them without "
                    "breaking other parts of the design?",
                },
                "narrative_clarity": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Is the final write-up clear, well-organized, and honest "
                    "about tradeoffs, the way a strong staff engineer would present it?",
                },
            },
            "required": [
                "requirements_coverage",
                "scale_soundness",
                "domain_awareness",
                "tech_justification",
                "critique_quality",
                "narrative_clarity",
            ],
        },
        "biggest_strength": {
            "type": "string",
            "description": "1-2 sentences: the single most notable thing this design got right.",
        },
        "biggest_weakness": {
            "type": "string",
            "description": "1-2 sentences: the single most important thing that's wrong or "
            "missing, even if minor.",
        },
        "would_pass_interview": {
            "type": "boolean",
            "description": "Would this design, presented as-is, pass a real system design "
            "interview at a solid engineering org?",
        },
    },
    "required": ["scores", "biggest_strength", "biggest_weakness", "would_pass_interview"],
}


def run(query: str, design: dict) -> dict:
    user = (
        f"Original problem: {query}\n\n"
        f"Requirements: {design['requirements']}\n\n"
        f"Scale estimate: {design['scale']}\n\n"
        f"Domain analysis: {design['domain']}\n\n"
        f"Final architecture: {design['architecture']}\n\n"
        f"Technology choices: {design['tech']}\n\n"
        f"Critique/revision history ({len(design['critique_history'])} round(s), "
        f"hit_max_revisions={design['hit_max_revisions']}): {design['critique_history']}\n\n"
        f"Final write-up: {design['explanation']['narrative']}"
    )
    return call_structured(
        system=SYSTEM,
        user=user,
        tool_name="submit_judgment",
        tool_description="Submit the scored evaluation of this system design.",
        input_schema=SCHEMA,
        model=JUDGE_MODEL,
        max_tokens=2048,
    )
