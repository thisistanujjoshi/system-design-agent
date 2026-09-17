from dataclasses import dataclass, field


@dataclass
class Company:
    """The shared board every role publishes to and reads from — the one channel roles use to
    hand off work to each other, instead of the orchestrator wiring return values through call
    arguments."""

    query: str
    docs: dict = field(default_factory=dict)
    log: list = field(default_factory=list)
    calls: list = field(default_factory=list)

    def publish(self, role: str, doc_type: str, content: dict) -> None:
        self.docs[doc_type] = content
        self.log.append((role, doc_type))

    def read(self, doc_type: str) -> dict:
        return self.docs[doc_type]

    def record_call(self, role: str, meta: dict) -> None:
        """Log one Claude API call's latency/token/cost metadata, keyed by the role that made it —
        this is what the eval harness aggregates into per-request cost and latency figures."""
        self.calls.append({"role": role, **meta})
