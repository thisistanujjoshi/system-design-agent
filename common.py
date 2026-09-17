import time

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-5"

# $ per 1M tokens (Anthropic first-party API rates, checked 2026-09-16). Dated snapshot IDs
# (e.g. HAIKU above) bill at their family's rate, so this keys on model family, not the exact ID.
PRICING = {
    HAIKU: {"input": 1.00, "output": 5.00},
    SONNET: {"input": 2.00, "output": 10.00},
}


def _cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = PRICING[model]
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


def call_structured(
    system: str,
    user: str,
    tool_name: str,
    tool_description: str,
    input_schema: dict,
    model: str = HAIKU,
    max_tokens: int = 3072,
) -> tuple[dict, dict]:
    """Call Claude and force a single tool call. Returns (parsed tool input, call metadata) —
    metadata carries latency/token/cost figures so callers can build real eval metrics instead of
    just checking the output looks right."""
    start = time.perf_counter()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        tools=[
            {
                "name": tool_name,
                "description": tool_description,
                "input_schema": input_schema,
                # Forced tool_choice alone doesn't guarantee schema compliance — the eval harness
                # surfaced two crashes (a missing "verdict", an unexplained downstream indexing
                # error) from tool calls that skipped a required field. strict=True makes the API
                # itself reject a non-conforming call instead of us discovering it as a KeyError
                # three functions away. Every SCHEMA in agents/ and eval/judge.py must therefore
                # set "additionalProperties": false at every object level (root and nested).
                "strict": True,
            }
        ],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": user}],
    )
    latency_ms = (time.perf_counter() - start) * 1000
    if response.stop_reason == "max_tokens":
        raise RuntimeError(
            f"Response truncated at max_tokens={max_tokens} before completing the tool call "
            f"for '{tool_name}'. Raise max_tokens or shrink the expected output."
        )
    for block in response.content:
        if block.type == "tool_use":
            usage = response.usage
            meta = {
                "model": model,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "latency_ms": round(latency_ms, 1),
                "cost_usd": round(_cost_usd(model, usage.input_tokens, usage.output_tokens), 6),
            }
            return block.input, meta
    raise RuntimeError("Model did not return a tool_use block")
