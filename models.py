from dataclasses import dataclass, field


@dataclass
class DesignState:
    query: str
    clarifying_questions: list[str] = field(default_factory=list)
    clarifying_answers: dict[str, str] = field(default_factory=dict)
    functional_requirements: list[str] = field(default_factory=list)
    non_functional_requirements: list[str] = field(default_factory=list)
    scale_estimate: dict = field(default_factory=dict)
    domain_notes: list[str] = field(default_factory=list)
    architecture: dict = field(default_factory=dict)
    tech_choices: dict = field(default_factory=dict)
    critiques: list[dict] = field(default_factory=list)
    revision_count: int = 0
