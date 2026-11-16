from dataclasses import dataclass, field

from ..container import AppArea


@dataclass(frozen=True)
class Context:
    area: AppArea
    config: dict
    layout: dict
    symbols: dict


@dataclass(frozen=True)
class Edit:
    offset: int
    data: bytes
    name: str


@dataclass
class Patch:
    payload: bytes = b""
    assembly: str = ""
    edits: list[Edit] = field(default_factory=list)
