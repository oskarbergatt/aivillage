"""Extracted methods for Agent."""
from __future__ import annotations

from .brain_shared import (
    TASKS,
    TOOLS,
    _tool_sprite,
    job_for,
    sprites,
)


class AgentSocialMixin:
    def _work(self, dt: float, ctx) -> None:
        if not self.task_name:
            self._pick_task()
        self.task_progress += dt
        self.work_activity_timer -= dt
        if self.work_activity_timer <= 0 and self.task_progress < self.task_time:
            activities = [task for task in TASKS.get(self.persona.job, ())
                          if task != self.task_name]
            if activities:
                self.task_name = self.rng.choice(activities)
                self.facing = self.rng.randrange(4)
            self.work_activity_timer = self.rng.uniform(25, 50)
        if self.task_progress >= self.task_time:
            self._complete_task(ctx)
            self._pick_task()

    def _complete_task(self, ctx) -> None:
        job = job_for(self.persona.job)
        if self.persona.is_child or job.key == "child":
            return
        if job.key == "farmer":
            ctx.tend_plot(self)
        if job.resource == "progress":
            ctx.build(job.amount, self)
        elif job.resource:
            ctx.gain(job.resource, job.amount, self)
        # Tasks complete every few simulation minutes; a full energy point
        # per task emptied the entire roster before the afternoon shift.
        self.needs.energy = max(0.0, self.needs.energy - 0.1)
        self.needs.fun += 1.0

    def available_for_chat(self) -> bool:
        return (self.state in ("free", "meal", "break", "idle")
                and self.talk_timer <= 0 and not self.path
                and self.bubble is None)

    def begin_talk(self, other: "Agent", seconds: float) -> None:
        self.partner = other.key
        self.talk_timer = seconds
        self.state = "talk"
        self.face_toward(other.x, other.y)
        self.needs.socialise(6)

    def end_talk(self) -> None:
        self.talk_timer = 0
        self.partner = None
        self.state = "free"
        self.action_timer = 5

    def attend_assembly(self, speaker_x: float, speaker_y: float, seconds: float) -> None:
        self.state = "assembly"
        self.action_timer = seconds
        self.talk_timer = 0
        self.face_toward(speaker_x, speaker_y)
        self.path = []

    def sprite(self) -> "sprites.pygame.Surface":
        look = self.persona.look
        tool = TOOLS.get(self.persona.job) if self.state == "work" else None
        if tool:
            return _tool_sprite(look.skin, look.hair, look.cloth, look.hair_style,
                                look.hat, look.version, self.facing,
                                self.animator.frame, look.apron, look.beard, tool)
        return sprites.villager(
            look.skin, look.hair, look.cloth, look.hair_style, look.hat,
            look.version, self.facing, self.animator.frame,
            look.apron, look.beard)

