from dataclasses import dataclass


@dataclass
class StrContract:
    assumptions: list[str]
    guarantees: list[str]
    inputs: list[str]
    outputs: list[str]
