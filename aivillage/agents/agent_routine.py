"""Extracted methods for Agent."""
from __future__ import annotations

from .brain_shared import (
    TASKS,
    TILE,
    job_for,
)


class AgentRoutineMixin:
    def _choose_intent(self, block: str, ctx) -> None:
        self.intent = block
        self.task_progress = 0.0
        weather = ctx.weather
        job = job_for(self.persona.job)
        stormy = ((weather.condition in ("storm", "snow") or weather.wet)
                  and not job.indoor and self.persona.job != "builder")

        if block == "sleep":
            self.state = "walk"
            self.go_to_point(self.home_point, jitter=1)
            self.task_name = "heading home to sleep"
            return
        if block == "meal":
            self.state = "walk"
            self.meal_plan = self._plan_meal(ctx)
            arrived = self.go_to_point(self.meal_plan.target, jitter=1)
            if not arrived:
                # A blocked door is no reason to starve: try home instead.
                self.meal_plan = self._fallback_meal_plan()
                arrived = self.go_to_point(self.home_point, jitter=1)
            self.task_name = "going to eat"
            if arrived and not self.path:
                self._arrived(ctx)
            return
        if block == "school":
            self.state = "walk"
            if stormy:
                self.go_to_point("tavern_door", jitter=2)
            else:
                self.go_to_point("school", jitter=1)
            self.task_name = "going to lessons"
            return
        if block == "play":
            self.state = "walk"
            r = self.rng.random()
            if r < 0.5:
                self.go_to_point("plaza", jitter=3)
            elif r < 0.75:
                self.go_to_point("pond", jitter=2)
            else:
                self.go_to_point("woods_west", jitter=2)
            self.task_name = "running wild"
            return
        if block == "market":
            self.state = "walk"
            arrived = self.go_to_point("market_front", jitter=3)
            if not arrived:
                arrived = self.go_to_point("plaza", jitter=3)
            self.task_name = "keeping the Saturday market"
            if arrived and not self.path:
                self._arrived(ctx)
            return
        if block == "repair":
            self.state = "walk"
            self.go_to_point("buildsite", jitter=2)
            self.task_name = "inspecting the repairs"
            return
        if block == "work":
            if stormy and self.persona.job != "builder":
                self._choose_intent("break", ctx)
                return
            work = job.work
            self.state = "walk"
            ok = self.go_to_point(work, jitter=1)
            if not ok:
                self.go_to_point("plaza", jitter=3)
            self.task_name = "heading to work"
            return
        if block == "break":
            self.state = "walk"
            self.go_to_point("tavern_door" if stormy else job.work, jitter=2)
            self.task_name = "taking shelter"
            return
        # free time
        self.state = "walk"
        self._new_wander_target(ctx)
        self.task_name = "looking for company"

    def _new_wander_target(self, ctx) -> None:
        r = self.rng.random()
        if r < 0.45:
            self.go_to_point("plaza", jitter=3)
        elif r < 0.65:
            friends = [a for a in ctx.agents if a is not self]
            if friends:
                other = self.rng.choice(friends)
                self.go_to_point(other.home_point, jitter=2)
        elif r < 0.8:
            self.go_to_point("market_front", jitter=2)
        else:
            town = self.world.points.get("plaza", (500, 360))
            tx, ty = self.world.random_walkable(self.rng, town[0] // TILE, town[1] // TILE, 6)
            self.go_to_tile(tx, ty)

    def update(self, dt: float, ctx) -> None:
        """dt is already scaled by the time multiplier."""
        if dt <= 0:
            return
        if self.bubble:
            self.bubble.timer -= dt
            if self.bubble.timer <= 0:
                self.bubble = None

        if self.talk_timer > 0:
            # Ambient conversations must not keep villagers from their next
            # scheduled job, meal or bedtime while a model is still replying.
            if self.partner and self._scheduled_block(ctx.clock) != "free":
                self.end_talk()
                self.block = ""
            else:
                self.talk_timer -= dt
                self.animator.update(dt, False, False)
                partner = ctx.agent_by_key.get(self.partner or "")
                if partner:
                    self.face_toward(partner.x, partner.y)
                if self.talk_timer <= 0:
                    self.partner = None
                    self.state = "free"
                    self.action_timer = 6
                return

        self.needs.decay(dt / 60.0, self.state if self.state not in ("walk",) else "walk",
                         self.persona.trait("diligence"))

        if self.state == "assembly":
            self.action_timer -= dt
            self.animator.update(dt, False, False)
            if self.action_timer <= 0:
                self.state = "free"
                self.action_timer = 2
            return

        block = self._scheduled_block(ctx.clock)
        if block != self.block:
            self.block = block
            self._choose_intent(block, ctx)

        if self.path:
            self.state = "walk" if self.state in ("walk", "idle", "free") else self.state
            self._walk(dt)
            self.animator.update(dt, True, False)
            if not self.path:
                self._arrived(ctx)
            return

        # arrived / stationary behaviour
        self.animator.update(dt, False,
                             self.state in ("work", "school", "play", "cook"))
        if self.state == "work":
            self._work(dt, ctx)
        elif self.state == "sleep":
            pass
        elif self.state == "school":
            self.action_timer -= dt
            if self.action_timer <= 0:
                self.action_timer = self.rng.uniform(20, 45) * 60
        elif self.state == "play":
            self.action_timer -= dt
            if self.action_timer <= 0:
                self.state = "walk"
                self._new_wander_target(ctx)
        elif self.state in ("cook", "buy"):
            self.action_timer -= dt
            if self.action_timer <= 0:
                self._begin_eating()
        elif self.state == "meal":
            self._eat(dt)
        elif self.state == "shop":
            self.action_timer -= dt
            if self.action_timer <= 0:
                self.state = "free"
                self.action_timer = self.rng.uniform(15, 35)
        elif self.state in ("free", "break", "idle"):
            self.action_timer -= dt
            if self.action_timer <= 0:
                if self.block in ("free", "play"):
                    self.state = "walk"
                    self._new_wander_target(ctx)
                else:
                    self.action_timer = self.rng.uniform(10, 25)
        # if we are supposed to be elsewhere, re-choose
        elif self.state == "walk":
            self._arrived(ctx)

    def _arrived(self, ctx) -> None:
        if self.intent == "sleep":
            self.state = "sleep"
            return
        if self.intent == "meal":
            self._start_meal(ctx)
            if self.bubble is None and self.rng.random() < 0.35:
                line = ctx.flavour_meal(self)
                if line:
                    self.say(line, 4.0, color=(240, 224, 190))
            return
        if self.intent == "market":
            trade = ctx.market_trade(self) if hasattr(ctx, "market_trade") else ""
            if trade:
                self.state = "shop"
                self.task_name = ("selling at the market" if trade == "sell"
                                  else "buying at the market")
                self.action_timer = self.rng.uniform(15, 35)
            else:
                self.state = "free"
                self.action_timer = self.rng.uniform(20, 50)
            return
        if self.intent == "school":
            self.state = "school"
            self.task_name = self.rng.choice(
                ("at lessons", "copying letters", "listening to a story"))
            self.action_timer = ctx.rng.uniform(12, 30) * 60
            return
        if self.intent == "play":
            self.state = "play"
            self.task_name = self.rng.choice(TASKS["child"])
            self.action_timer = ctx.rng.uniform(20, 45)
            return
        if self.intent == "work":
            self.state = "work"
            self._pick_task()
            return
        if self.intent == "break":
            self.state = "break"
            self.action_timer = 30
            return
        self.state = "free"
        self.action_timer = ctx.rng.uniform(20, 50)

    def _pick_task(self) -> None:
        options = TASKS.get(self.persona.job, ["working"])
        self.task_name = self.rng.choice(options)
        self.task_progress = 0.0
        self.task_time = self.rng.uniform(2.0, 4.5) * 60
        self.work_activity_timer = self.rng.uniform(20, 40)

