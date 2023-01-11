from dataclasses import dataclass, field


@dataclass
class StrContract:
    assumptions: list[str] = field(default_factory=list)
    guarantees: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
