# System Design Reasoning Agent

A small virtual company of Claude agents, each with a real engineering-org role, that takes a
one-line system design prompt (e.g. "design a URL shortener") and reasons through it the way a
staff engineer would in an interview: extracting requirements, estimating scale, proposing an
architecture, picking real technologies, critiquing its own design, and revising before producing
a final write-up.

Built as a learning project while preparing for software engineering roles — specifically to get
hands-on with agentic pipeline design (structured multi-step LLM orchestration, not just a single
prompt) rather than just reading about it.

## How it works

```
User query
    |
    v
Product Manager -----> clarifying questions (asked interactively), functional/non-functional reqs
    |
    v
Systems Analyst ------> back-of-the-envelope QPS/storage/bandwidth estimates
    |
    v
Domain Expert --------> domain-specific constraints (ordering, consistency, geospatial, etc.)
    |
    v
+-----------------------------------------+
| Architect -> Tech Lead -> Staff Reviewer |  <- loops up to 3x, reviewer decides
+-----------------------------------------+     revise or approve
    |
    v
Presenter -------------> final write-up + Mermaid diagram (design_output.md)
```

Each role is a single Claude API call, forced to respond via a tool call so the output is
structured JSON rather than free text (`common.py`). Roles don't call each other directly or
receive their inputs as function arguments — they all read from and publish to one shared
`Company` object (`company.py`), a plain dict-backed message board keyed by document type
("requirements", "scale", "architecture", ...). The orchestrator (`orchestrator.py`) just tells
each role when it's their turn; it never wires one role's output into the next role's input
itself. That's the mechanism, not an agent framework — `Company` is ~15 lines.

On each revision round, the Architect is shown its own previous output (read straight off the
board) plus the reviewer's specific issues, and told to fix only what's broken — not regenerate
the whole design from scratch — so earlier fixes don't get silently lost in later rounds.

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

- Mixed-tier model selection: the Product Manager, Domain Expert, and Presenter run on
  `claude-haiku-4-5` (cheap, and already scored well on these in the eval harness — see below).
  The Systems Analyst, Architect, Tech Lead, and Staff Reviewer run on `claude-sonnet-5` — these
  are the reasoning-heavy roles, and the harness showed Haiku underperforming specifically on
  scale soundness and tech-choice justification.
- The Staff Reviewer is capped at 3 issues per round and instructed to stay at "whiteboard"
  severity (architecturally significant problems only, not implementation-level nitpicks like
  exact retry counts or SQL injection prevention) — otherwise it never converges to "approve"
  within the revision budget.
- The Systems Analyst and Domain Expert run concurrently (both only need Requirements off the
  board, not each other's output); the Architect → Tech Lead → Staff Reviewer loop stays
  sequential since each round depends on the previous one's output.
- Every tool call uses `strict: true` (Claude API structured-output validation) — forcing a tool
  call with `tool_choice` alone doesn't guarantee every required field is present, and running the
  eval harness enough times surfaced exactly that: a `KeyError` from a Reviewer response that
  skipped its required `verdict` field. See [EVAL.md](EVAL.md) for the full story.

## Eval harness

`python -m eval.run_eval` runs the pipeline over a fixed, non-interactive problem set (see
`eval/problems.py`) and measures it on five axes instead of "it works":

- **Reliability** — did the pipeline complete without crashing.
- **Quality** — an LLM judge (`eval/judge.py`, a stronger model than the pipeline it grades) scores
  six dimensions 1-5 (requirements coverage, scale soundness, domain awareness, tech justification,
  critique quality, narrative clarity) plus a holistic "would this pass a real interview" verdict.
- **Accuracy** — `eval/accuracy.py` runs deterministic referential-integrity checks (no LLM call)
  against the pipeline's own structured output: do connections/tech choices/critique issues
  actually reference components that exist, and does the Reviewer's verdict match its own stated
  policy.
- **Hallucination rate** — `eval/hallucination.py` checks whether the final write-up names a
  technology that was never actually selected or considered anywhere upstream (also no LLM call).
- **Latency & cost per request** — every agent call now returns token/latency/cost metadata
  (`common.py`), aggregated per pipeline run (`orchestrator.py`) into wall-clock latency and $ cost
  using published Haiku 4.5 / Sonnet 5 pricing.

Results are saved to `eval/results/<timestamp>.json` so pipeline or prompt changes can be checked
against a repeatable baseline instead of eyeballing one or two example runs. See **[EVAL.md](EVAL.md)**
for the actual numbers from the latest run and three real bugs (one in the pipeline, two in the
eval code itself) this harness surfaced while being built.
