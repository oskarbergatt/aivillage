"""Personality data model."""
from __future__ import annotations

from dataclasses import dataclass, field

TRAIT_KEYS = ("curiosity", "sociability", "diligence", "grumpiness", "creativity")


@dataclass
class Look:
    skin: int = 0
    hair: int = 0
    cloth: int = 0
    hair_style: str = "short"      # short | long | bun | wild | bald
    hat: str = ""                  # "" | straw | cap | hood
    version: int = 0
    apron: bool = False
    beard: bool = False


@dataclass
class Voice:
    rate: int = 170
    volume: float = 0.9
    hint: str = ""                 # substring matched against installed SAPI voices
    lang: str = "en"


@dataclass
class Persona:
    key: str
    name: str
    job: str
    home: str
    work: str
    look: Look
    traits: dict[str, float]
    bio: str
    quirk: str
    voice: Voice
    schedule: list[tuple[float, float, str]] = field(default_factory=list)
    nocturnal: bool = False
    age: int = 0                       # 0 = adult / unspecified
    child: bool = False
    parent: str = ""                   # persona key of the grown-up they live with
    ambition: str = ""                 # self-authored, LLM-written
    dream_job: str = ""                # children only
    authored: bool = False             # has the model chosen a calling yet?

    @property
    def is_child(self) -> bool:
        return self.child or self.age in range(1, 16)

    def trait(self, name: str) -> float:
        return float(self.traits.get(name, 0.5))
