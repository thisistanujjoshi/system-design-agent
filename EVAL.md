# Evaluation results

This is the output of `python -m eval.run_eval` against the fixed 4-problem set in
`eval/problems.py` (URL shortener, WhatsApp-scale chat, ride-sharing dispatch, payments ledger),
run against the live Anthropic API on 2026-09-17. It replaces "it works, I tried it on a couple of
prompts" with numbers, and documents three real bugs the harness surfaced while building it —
including one in the pipeline itself, not just in the eval code.

## Headline numbers (n=4)

| Metric | Result |
|---|---|
| Pipeline reliability | **4/4 runs completed (100%)** |
| Judge quality score | **4.08/5** mean across 6 dimensions |
| Would pass a real interview (judge verdict) | **50%** (2/4) |
| Structural accuracy (deterministic checks) | **98.6%** (146/148 checks passed) |
| Hallucination rate (technology-grounding proxy) | **50%** (2/4) — both flags are protocol names, not fabricated vendor choices; see caveat below |
| Latency (wall-clock, full pipeline) | mean **422s**, median **426s**, p95 **465s**, range 379–458s |
| Cost per request | mean **$0.42**, median **$0.43**, range $0.36–$0.45 |
| Eval overhead (LLM judge, not part of production cost) | mean **$0.044**/problem |

Total cost to run the 4-problem eval once: **$1.67**. Full per-call breakdown (every agent call's
model/tokens/latency/cost) is in `eval/results/<timestamp>.json`, gitignored to keep the repo small
— reproduce with `python -m eval.run_eval`.

A caveat up front: n=4 is enough to catch real bugs and get a directional read, not enough for
tight statistical confidence — one problem flipping changes these percentages by 25 points. Treat
the numbers as "the pipeline is in this ballpark," not as a precise SLA.

## What each metric actually measures, and why

**Reliability** — did `run_design()` return without raising. Sounds trivial; it wasn't (see below).

**Quality** — the existing LLM-judge harness (`eval/judge.py`, Sonnet grading Haiku/Sonnet output)
scores 6 dimensions 1-5 and gives a holistic "would this pass a real interview" verdict. Unchanged
by this work except for the strict-schema fix below.

**Accuracy** — deliberately *not* another LLM call. `eval/accuracy.py` runs 4 deterministic
referential-integrity checks against the pipeline's own structured output: every architecture
connection's endpoints must name a real component; every tech choice's component must exist;
every critique issue's component must exist; the Reviewer's verdict must match the policy stated
in its own system prompt ("revise" iff there's a critical/major issue). An LLM judge reads the
design as prose and won't notice a connection pointing at a component that was never declared —
this catches that class of bug for free, no API call.

**Hallucination** — also deterministic. `eval/hallucination.py` extracts real-world technology
names from the final narrative and checks each one traces back to something the Tech Lead actually
selected or considered (`technology` or `alternative_considered` in its structured output). If the
write-up names a technology stack element that was never decided anywhere upstream, it was invented
at the write-up stage. This is a proxy, not a general hallucination detector — it only catches
fabricated *technology choices*, not fabricated numbers or unsupported claims elsewhere in the
prose. I validated the check has real detection power (not a rubber stamp) with a hand-built
synthetic design containing a deliberately fabricated "Kafka" mention before trusting it on real
runs.

**Latency & cost** — `common.py`'s `call_structured()` now returns per-call metadata (model, input/
output tokens, latency, cost) alongside its parsed result; `company.py` logs every call a role
makes; `orchestrator.py` aggregates it into wall-clock pipeline latency (what a caller actually
waits — lower than the sum of individual call latencies since the Systems Analyst and Domain
Expert run concurrently) and total cost, using published per-token pricing for Haiku 4.5 ($1/$5 per
1M in/out) and Sonnet 5 ($2/$10 per 1M in/out).

## Bugs this harness found

### 1. The pipeline crashed on ~1 in 4 runs — from an API call, not a code bug

Building the harness meant running the pipeline far more times than manual spot-checks ever had,
and it started crashing: `KeyError: 'verdict'` in the revision loop, and separately a `string
indices must be integers, not 'str'` error that didn't reproduce on retry. Root cause: every agent
forces a tool call via `tool_choice`, which strongly biases the model toward schema-shaped output
but — without `strict: true` — doesn't *guarantee* every required field is present. Rarely, the
Reviewer's tool call would come back missing `verdict`, and the orchestrator had no defense against
that.

Fix: `common.py` now sets `"strict": True` on every tool definition, and every `SCHEMA` in
`agents/*.py` and `eval/judge.py` has `"additionalProperties": false` at every object level (root
and nested) as required for strict mode. This surfaced two more findings in the process — strict
schemas reject `maxItems` and integer `minimum`/`maximum` outright (400 `invalid_request_error`),
so the Reviewer's 3-issue cap and the judge's 1-5 score bounds now rely on prompt instructions
(`enum: [1,2,3,4,5]` for the score) instead of schema constraints. Confirmed fixed: 100% pipeline
reliability across the final eval run, up from crashing on the first two attempts at a clean run.

### 2. The Architect names components inconsistently, silently breaking the rendered diagram

The accuracy check's `connections_valid` rate came back oddly low (42% on the chat-system problem)
even after the strict-schema fix. Investigating showed the Architect would declare a component as
`"Client Gateway (Connection/Edge Service)"` but then reference it in a connection as plain
`"Client Gateway"` — or reference an external actor (`"Rider/Driver Mobile Clients"`) in a
connection without ever declaring it as a component. Since `diagram.py`'s `node_id()` derives node
IDs straight from these strings, a mismatch means Mermaid silently draws a disconnected, unstyled
node instead of linking to the real one — a rendering bug that would only show up by actually
looking at the diagram, not by reading the JSON.

Fix: added an explicit instruction to the Architect's system prompt requiring every connection
endpoint to match a declared component name character-for-character, and requiring external actors
to be declared as components too. Verified with a targeted re-run: `chat_system`'s
`connections_valid` went from 42% (11/26) to 100% (22/22), and overall accuracy for that problem
from 69% to 100%.

### 3. Three bugs in the eval-scoring code itself, caught by spot-checking before trusting the numbers

Building a new metric is easy to get subtly wrong, and I don't want to publish numbers I haven't
sanity-checked:

- **Hallucination check, first version:** compared the narrative's plain `"CockroachDB"` against
  the Tech Lead's full hedged answer `"cockroachdb (or google cloud spanner if on gcp)"` with exact
  set membership — a mismatch every time, producing a 100% false-positive hallucination rate on
  the first real run. Fixed by switching to substring containment.
- **`critique_grounded` accuracy check:** same shape of bug in reverse — the Reviewer writes prose
  like `"Metadata Store consistency / DynamoDB Global Tables..."` for a component literally named
  `"Metadata Store"`, and exact matching flagged every one of these as an invented component.
  Fixed the same way, plus stripping trailing parenthetical annotations before matching.
- **Postgres vs. PostgreSQL:** word-boundary matching correctly refused to treat `"postgres"` as a
  substring of `"postgresql"` (there's no word boundary between them), so a narrative saying
  "Postgres" when the Tech Lead chose "PostgreSQL" registered as ungrounded. Fixed with a small
  alias table (`postgres` → `postgresql`, etc.).

After all three fixes, the two hallucination flags that remain (`WebSocket` in the chat-system
write-up, `gRPC` in the payments-ledger write-up) are real and defensible: both are protocol names
that appear in the final narrative without ever being named in the Tech Lead's structured output —
reasonable domain knowledge, but not something the pipeline actually decided anywhere upstream.
I'm reporting that as a genuine (if minor) finding rather than tuning the check further to make it
disappear.

## Known limitations

- n=4 problems, one run each — no repeated-run variance data, so latency/cost ranges reflect
  problem-to-problem difference, not measurement noise on a single problem.
- The hallucination check only catches fabricated *technology names* against a fixed vocabulary
  (`eval/hallucination.py:TECH_VOCAB`) — it says nothing about fabricated numbers, requirements, or
  claims in the prose.
- `critique_grounded` can't catch semantic paraphrases (the Reviewer inventing its own label for a
  real component's concept rather than reusing its name) — only exact-name-family mismatches. This
  is a real precision ceiling of a deterministic check, documented rather than hidden.
