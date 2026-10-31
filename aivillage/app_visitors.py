"""Extracted methods for VillageApp."""
from __future__ import annotations

from .app_shared import (
    Agent,
    Visitor,
    job_choices,
    prompts,
    time,
)


class VisitorsMixin:
    def _backoff_self_direction(self) -> None:
        self._self_failures = min(self._self_failures + 1, 20)
        base = max(1.0, float(self.config.get("llm.self_interval_s", 180)))
        cap = max(base, float(self.config.get("llm.self_failure_backoff_max_s", 1800)))
        self._self_timer = min(cap, base * 2 ** self._self_failures)

    def request_self(self, agent: Agent | None = None, *, automatic: bool = False) -> bool:
        """Ask the model to let a villager choose who they are."""
        agent = agent or self.selected_agent()
        if agent is None:
            return False
        if not self.llm.available:
            self.toast(self.i18n.t("ui.no_llm"))
            return False
        if not self.config.get("llm.self_directed", True):
            self.toast(self.i18n.t("ui.self_off"))
            return False
        if self.self_pending or self.chat.active:
            return False
        child = agent.persona.is_child
        choices = job_choices(child)
        if not choices:
            return False
        self.self_pending = agent.key
        agent.say("", 600.0, pending=True)
        agent.path = []

        def done(data: dict | None, error: str) -> None:
            if self.self_pending == agent.key:
                self.self_pending = None
            agent.bubble = None
            if error or not data:
                if automatic:
                    self._backoff_self_direction()
                self.toast(self.i18n.t("ui.no_reply"))
                return
            changed = agent.apply_self(data)
            if not changed:
                if automatic:
                    self._backoff_self_direction()
                self.toast(self.i18n.t("ui.self_none", name=agent.name))
                return
            if automatic:
                self._self_failures = 0
            fields = ", ".join(self.i18n.t(f"field.{name}")
                               for name in changed
                               if self.i18n.t(f"field.{name}") != f"field.{name}")
            self.toast(self.i18n.t("event.self", name=agent.name))
            self.add_chronicle(
                self.i18n.t("event.self_long", name=agent.name,
                            fields=fields or agent.persona.job),
                "self")
            line = agent.persona.ambition
            if line:
                agent.say(line, 9.0)
                self.voice.speak(line, agent.key, self.i18n.language)
            self.autosave()

        self.llm.submit(
            "self", prompts.self_system(agent.persona, self.i18n.language),
            prompts.self_user(agent.persona, self._prompt_ctx(agent), choices,
                              child),
            done, max_tokens=340, temperature=0.95, use_cache=False)
        return True

    def _maybe_self_direction(self, dt: float) -> None:
        """Villagers occasionally decide for themselves who to become."""
        if not self.config.get("llm.self_directed", True):
            return
        if not self.llm.available or self.llm.provider == "mock":
            return
        if self.self_pending or self.chat.active or self.show_chronicle:
            return
        self._self_timer -= dt
        if self._self_timer > 0:
            return
        self._self_timer = float(self.config.get("llm.self_interval_s", 180) or 180)
        candidates = [a for a in self.agents if not a.persona.authored]
        if not candidates:
            return
        self.request_self(self.rng.choice(candidates), automatic=True)

    def _active_visitor(self) -> Visitor | None:
        for v in self.visitors:
            if v.state not in ("leaving", "gone"):
                return v
        return None

    def spawn_visitor(self, force: bool = False) -> bool:
        if self.visitor_pending or self._active_visitor() is not None:
            return False
        cap = int(self.config.get("news.max_dispatches_per_day", 2))
        if not force and self.visitors_today >= cap:
            return False
        if not self.news.enabled:
            return False
        if not self.llm.available:
            self.toast(self.i18n.t("ui.no_llm"))
            return False
        if force and not self.news.status()["unused"]:
            self.news.wake()

        self.visitor_pending = True
        started = self.news.request_dispatch(self.i18n.language,
                                             self._on_dispatch)
        if not started:
            # No fresh headline (yet): a traveller still carries a rumour.
            temp = Visitor(self.rng, self.world, None)
            self._pending_rumour_visitor = temp
            ok = self.news.request_rumour(
                self.i18n.language, temp.name, temp.trade, temp.origin,
                self._prompt_ctx(None),
                lambda d: self._on_rumour(d, temp))
            if not ok:
                self.visitor_pending = False
                self.toast(self.i18n.t("ui.no_news"))
                return False
        return True

    def _on_dispatch(self, dispatch) -> None:
        self.visitor_pending = False
        if dispatch is None:
            self.toast(self.i18n.t("ui.no_reply"))
            return
        self._admit_visitor(Visitor(self.rng, self.world, dispatch))

    def _on_rumour(self, dispatch, visitor: Visitor) -> None:
        self.visitor_pending = False
        if dispatch is None:
            self.toast(self.i18n.t("ui.no_reply"))
            return
        visitor.dispatch = dispatch
        self._admit_visitor(visitor)

    def _admit_visitor(self, visitor: Visitor) -> None:
        if self._active_visitor() is not None:
            return
        cap = int(self.config.get("news.max_dispatches_per_day", 2))
        if self.visitors_today >= cap and visitor.dispatch and visitor.dispatch.item_id:
            return
        self.visitors.append(visitor)
        self.visitors_today += 1
        self.toast(self.i18n.t("event.incoming", name=visitor.name))
        self.sfx.play("step")

    def _check_visitor_schedule(self) -> None:
        if not self.news.enabled:
            return
        minutes = self.clock.now.hour * 60 + self.clock.now.minute
        if (self.visitor_slot_idx < len(self.visitor_slots)
                and minutes >= self.visitor_slots[self.visitor_slot_idx]
                and self._active_visitor() is None
                and not self.visitor_pending):
            self.visitor_slot_idx += 1
            if self.visitors_today < int(self.config.get("news.max_dispatches_per_day", 2)):
                self.spawn_visitor()
        if (self.night_demo_at and time.time() >= self.night_demo_at
                and self.visitors_today == 0 and not self.visitor_pending
                and self._active_visitor() is None):
            self.night_demo_at = 0.0
            self.spawn_visitor()

