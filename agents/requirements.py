from common import call_structured

SYSTEM = """You are the Requirements Agent in a system design reasoning pipeline, acting like a \
staff engineer running a system design interview. Given a problem statement (and any prior \
clarifying Q&A), you:
1. List the clarifying questions a senior engineer would actually ask before designing this \
system — sharp, specific to THIS problem, not generic boilerplate.
2. Extract functional requirements (what the system must do).
3. Extract non-functional requirements (scale, latency, availability, consistency, durability, \
cost, security — only the ones that actually matter for this problem).

If clarifying answers are already provided in the input, use them to refine requirements instead \
of asking about them again."""

SCHEMA = {
    "type": "object",
    "properties": {
        "clarifying_questions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3-6 sharp clarifying questions, ordered by importance. Empty if the "
            "problem is already fully specified.",
        },
        "functional_requirements": {
            "type": "array",
            "items": {"type": "string"},
        },
        "non_functional_requirements": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "clarifying_questions",
        "functional_requirements",
        "non_functional_requirements",
    ],
}


def run(query: str, qa_context: str = "") -> dict:
    user = f"Problem: {query}"
    if qa_context:
        user += f"\n\nClarifying Q&A so far:\n{qa_context}"
    return call_structured(
        system=SYSTEM,
        user=user,
        tool_name="submit_requirements",
        tool_description="Submit the extracted requirements and clarifying questions.",
        input_schema=SCHEMA,
    )
