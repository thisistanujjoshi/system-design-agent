from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

HAIKU = "claude-haiku-4-5-20251001"


def call_structured(
    system: str,
    user: str,
    tool_name: str,
    tool_description: str,
    input_schema: dict,
    model: str = HAIKU,
    max_tokens: int = 3072,
) -> dict:
    """Call Claude and force a single tool call, returning its parsed arguments as a dict."""
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        tools=[
            {
                "name": tool_name,
                "description": tool_description,
                "input_schema": input_schema,
            }
        ],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": user}],
    )
    if response.stop_reason == "max_tokens":
        raise RuntimeError(
            f"Response truncated at max_tokens={max_tokens} before completing the tool call "
            f"for '{tool_name}'. Raise max_tokens or shrink the expected output."
        )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Model did not return a tool_use block")
