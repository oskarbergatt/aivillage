"""Walk / work animation state."""
from __future__ import annotations


class Animator:
    def __init__(self) -> None:
        self.t = 0.0
        self.frame = 0

    def update(self, dt: float, moving: bool, working: bool = False) -> None:
        if not (moving or working):
            self.t = 0.0
            self.frame = 0
            return
        speed = 8.0 if moving else 5.0
        self.t += dt * speed
        if self.t >= 1.0:
            self.t -= 1.0
            self.frame = (self.frame + 1) % 4
