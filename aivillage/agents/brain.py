"""Public facade and controller composition."""
from __future__ import annotations

from copy import deepcopy

from .brain_shared import (
    Animator,
    Bubble,
    JOBS,
    MemoryBook,
    Needs,
    Persona,
    TASKS,
    TILE,
    TOOLS,
    YIELD,
    _tool_sprite,
    astar,
    block_at,
    dataclass,
    field,
    is_rest_day,
    job_for,
    lru_cache,
    math,
    random,
    routine_key,
    sprites,
)

from .agent_identity import AgentIdentityMixin
from .agent_routine import AgentRoutineMixin
from .agent_social import AgentSocialMixin


class Agent(AgentIdentityMixin, AgentRoutineMixin, AgentSocialMixin):
    def __init__(self, persona: Persona, world, rng: random.Random):
        # Each simulation owns its identity; self-direction must not mutate
        # the shared founder roster or leak into a new village.
        self.persona = deepcopy(persona)
        self.key = persona.key
        self.world = world
        self.rng = rng
        home = world.points.get(f"home_{persona.home}", world.points.get("plaza", (500, 360)))
        self.x = float(home[0])
        self.y = float(home[1])
        self.facing = 0
        self.path: list[tuple[float, float]] = []
        self.state = "idle"          # action state
        self.intent = "idle"         # schedule block
        self.block = ""
        self.target: str | None = None
        self.action_timer = 0.0
        self.needs = Needs(
            hunger=rng.uniform(55, 90),
            energy=rng.uniform(65, 95),
            social=rng.uniform(35, 70),
            fun=rng.uniform(35, 70),
        )
        self.memory = MemoryBook()
        self.animator = Animator()
        self.bubble: Bubble | None = None
        self.task_name = ""
        self.task_progress = 0.0
        self.task_time = rng.uniform(0, 90)
        self.work_activity_timer = rng.uniform(20, 40)
        self.partner: str | None = None
        self.talk_timer = 0.0
        self.napping = False
        self.eating = False
        self.selected = False
        self.home_point = f"home_{persona.home}"
