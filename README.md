# System Design Reasoning Agent

A multi-agent pipeline that takes a one-line system design prompt (e.g. "design a URL shortener")
and reasons through it the way a staff engineer would in an interview: extracting requirements,
estimating scale, proposing an architecture, picking real technologies, critiquing its own design,
and revising before producing a final write-up.

Built as a learning project while preparing for software engineering roles — specifically to get
hands-on with agentic pipeline design (structured multi-step LLM orchestration, not just a single
prompt) rather than just reading about it.

## How it works

```
User query
    |
    v
Requirements Agent -----> clarifying questions (asked interactively), functional/non-functional reqs
    |
    v
Scale Agent -------------> back-of-the-envelope QPS/storage/bandwidth estimates
    |
    v
Domain Agent -------------> domain-specific constraints (ordering, consistency, geospatial, etc.)
    |
    v
+-----------------------------------------------+
| Architecture Agent -> Tech Selection -> Critic |  <- loops up to 3x, critic decides
+-----------------------------------------------+     revise or approve
    |
    v
Explanation Agent -------> final write-up + Mermaid diagram (design_output.md)
```

Each agent is a single Claude API call, forced to respond via a tool call so the output is
structured JSON rather than free text (`common.py`). The orchestrator (`orchestrator.py`) holds
all shared state and drives the sequence — there's no agent framework in between; the orchestration
logic is plain Python.

On each revision round, the Architecture Agent is shown its own previous output plus the critic's
specific issues, and told to fix only what's broken — not regenerate the whole design from
scratch — so earlier fixes don't get silently lost in later rounds.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file with your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```bash
python orchestrator.py "Design a URL shortener like bit.ly"
```

It will ask a few clarifying questions interactively, then run the full pipeline and print its
reasoning at each stage. The final design (summary, full write-up, and architecture diagram) is
saved to `design_output.md`.

## Notes

- Uses `claude-haiku-4-5` by default to keep costs low during iteration — cheap enough to run
  many designs for a few cents each.
- The critic is capped at 3 issues per round and instructed to stay at "whiteboard" severity
  (architecturally significant problems only, not implementation-level nitpicks like exact retry
  counts or SQL injection prevention) — otherwise it never converges to "approve" within the
  revision budget.
