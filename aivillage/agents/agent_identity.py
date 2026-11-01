"""Extracted methods for Agent."""
from __future__ import annotations

from .brain_shared import (
    Bubble,
    JOBS,
    TILE,
    astar,
    block_at,
    math,
)


class AgentIdentityMixin:
    @property
    def name(self) -> str:
        return self.persona.name

    @property
    def moving(self) -> bool:
        return bool(self.path)

    def tile(self) -> tuple[int, int]:
        return int(self.x // TILE), int(self.y // TILE)

    def distance_to(self, other: "Agent") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def face_toward(self, px: float, py: float) -> None:
        dx, dy = px - self.x, py - self.y
        if abs(dx) > abs(dy):
            self.facing = 2 if dx > 0 else 1
        elif abs(dy) > 2:
            self.facing = 0 if dy > 0 else 3

    def say(self, text: str, seconds: float = 5.0, pending: bool = False,
            kind: str = "speech", color=(240, 232, 210)) -> None:
        self.bubble = Bubble(text, seconds, pending, kind, color)

    def set_job(self, key: str) -> bool:
        """Change an adult's trade. Children keep their lessons."""
        if self.persona.is_child or key not in JOBS or JOBS[key].child:
            return False
        job = JOBS[key]
        changed = key != self.persona.job
        self.persona.job = key
        self.persona.work = job.work
        self.persona.authored = True
        if changed:
            self.task_name = ""
            self.state = "free"
            self.action_timer = 2
            self.target = None
        return changed

    def apply_self(self, data: dict) -> list[str]:
        """Apply a model-authored identity update. Returns the fields changed.

        Everything is validated here: a hallucinated job, hat or colour is
        ignored rather than corrupting the simulation.
        """
        if not isinstance(data, dict):
            return []
        changed: list[str] = []
        p = self.persona
        ambition = " ".join(str(data.get("ambition", "")).split())[:120]
        if ambition and ambition != p.ambition:
            p.ambition = ambition
            changed.append("ambition")
        for key, limit in (("bio", 240), ("quirk", 90)):
            value = " ".join(str(data.get(key, "")).split())[:limit]
            if value and value != getattr(p, key):
                setattr(p, key, value)
                changed.append(key)
        raw_job = ((data.get("dream_job") or data.get("job")) if p.is_child
                   else (data.get("job") or data.get("dream_job")))
        job_key = str(raw_job or "").strip().lower()
        if p.is_child:
            if job_key in JOBS and not JOBS[job_key].child and job_key != p.dream_job:
                p.dream_job = job_key
                changed.append("dream_job")
        elif job_key in JOBS and not JOBS[job_key].child and self.set_job(job_key):
            changed.append("job")
        hat = str(data.get("hat", "")).strip().lower()
        if hat in ("", "straw", "cap", "hood") and hat != p.look.hat:
            p.look.hat = hat
            changed.append("hat")
        try:
            cloth = int(data.get("outfit", -1))
        except Exception:
            cloth = -1
        if 0 <= cloth <= 7 and cloth != p.look.cloth:
            p.look.cloth = cloth
            changed.append("outfit")
        p.authored = True
        return changed

    def go_to_tile(self, tx: int, ty: int, exact: tuple[int, int] | None = None) -> bool:
        start = self.tile()
        path = astar(start, (tx, ty), self.world.is_walkable)
        if not path:
            self.path = []
            return False
        # A* retargets blocked goals to the nearest walkable tile; honour where
        # it actually arrived instead of teleporting into a wall or the pond.
        pts = [(p[0] * TILE + TILE // 2, p[1] * TILE + TILE // 2) for p in path[1:]]
        if exact and self.world.is_walkable(tx, ty):
            pts.append(exact)
        self.path = pts
        return True

    def go_to_point(self, name: str, jitter: int = 0) -> bool:
        pt = self.world.points.get(name)
        if pt is None:
            return False
        tx, ty = pt[0] // TILE, pt[1] // TILE
        if jitter:
            tx += self.rng.randint(-jitter, jitter)
            ty += self.rng.randint(-jitter, jitter)
        # A scattered destination must use its own tile center, not the
        # original landmark pixel, or everybody converges on the same spot.
        exact = self.world.tile_center(tx, ty) if jitter else pt
        if not self.go_to_tile(tx, ty, exact=exact):
            return False
        self.target = name
        return True

    def _walk(self, dt: float) -> None:
        if not self.path:
            return
        speed = 30.0 * (0.9 + self.persona.trait("diligence") * 0.25)
        budget = speed * dt
        while self.path and budget > 0:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            dist = math.hypot(dx, dy)
            if dist <= budget or dist < 0.5:
                self.x, self.y = tx, ty
                budget -= dist
                self.path.pop(0)
                continue
            self.x += dx / dist * budget
            self.y += dy / dist * budget
            self.face_toward(tx, ty)
            budget = 0
        if self.path:
            nx, ny = self.path[0]
            self.face_toward(nx, ny)

    def _scheduled_block(self, clock) -> str:
        block = block_at(self.persona, clock.now)
        # A scheduled shift is a hard hand-off.  Lunch may be interrupted at
        # the end of its hour, and a lingering emergency nap must not strand
        # workers at home for the rest of the afternoon.
        if block in ("work", "school", "market", "repair"):
            self.napping = False
            self.eating = False
            return block
        if self.napping:
            if self.needs.energy < 68:
                return "sleep"
            self.napping = False
        if self.eating and self.needs.hunger < 62:
            return "meal"
        self.eating = False
        if self.needs.energy < 9 and block != "sleep":
            self.napping = True
            return "sleep"
        if self.needs.hunger < 11 and block not in ("meal", "sleep"):
            self.eating = True
            return "meal"
        return block

