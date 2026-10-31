"""Extracted methods for VillageApp."""
from __future__ import annotations

from .app_shared import (
    Agent,
    datetime,
    prompts,
    time,
)


class VillageSocialMixin:
    def _social_speed(self) -> float:
        return 1.0 if self.clock.live else max(1.0, self.clock.sim_speed)

    def _social_wait(self) -> float:
        key = "llm.cli_timeout_s" if self.llm.provider in ("claude_cli", "codex_cli") else "llm.timeout_s"
        timeout = max(12.0, min(180.0, float(self.config.get(key, 60) or 60)))
        return (timeout + 5.0) * self._social_speed()

    def _social_retry_delay(self) -> float:
        """Back off failed background calls, without slowing player chat."""
        self._social_failures = min(self._social_failures + 1, 20)
        if self._social_failures == 1:
            self.toast(self.i18n.t("ui.ambient_unavailable"))
        base = max(1.0, float(self.config.get("social.failure_backoff_s", 120)))
        cap = max(base, float(self.config.get("social.failure_backoff_max_s", 900)))
        return min(cap, base * 2 ** (self._social_failures - 1))

    def _maybe_social(self, dt: float) -> None:
        self.social_timer -= dt
        if (self.social_timer > 0 or self.ambient_pending >= 2
                or self._social_track_count() + self.ambient_pending >= 3 or self.chat.active
                or self.show_chronicle):
            return
        if not self.config.get("llm.ambient_dialogue", True) or not self.llm.available:
            return
        free = [a for a in self.agents
                if a.block == "free" and a.available_for_chat()
                and self.selected is not a]
        best = None
        best_d = 1e9
        for i, a in enumerate(free):
            for b in free[i + 1:]:
                d = a.distance_to(b)
                if d < 78 and d < best_d:
                    best, best_d = (a, b), d
        if best is None:
            self.social_timer = 4.0
            return
        a, b = best
        others = [p for p in free if p not in best and
                  max(p.distance_to(a), p.distance_to(b)) < 78]
        if (others and self.config.get("social.group_chats", True)
                and self.rng.random() < float(self.config.get("social.group_chance", 0.35))):
            members = [a, b] + sorted(others, key=lambda p: p.distance_to(a))[:2]
            self._start_group(members)
            return
        a.begin_talk(b, self._social_wait())
        b.begin_talk(a, self._social_wait())
        self.ambient_pending += 1
        self.social_timer = 2.0
        generation = self._social_generation
        topic = ""
        recent = a.memory.recent(1, "news") or b.memory.recent(1, "news")
        if recent:
            topic = recent[-1]
        history = [entry.text for entry in a.memory.entries
                   if entry.kind == "social" and entry.dispatch_id == b.key][-4:]

        def done(data: dict | None, error: str) -> None:
            if generation != self._social_generation:
                return
            self.ambient_pending = max(0, self.ambient_pending - 1)
            if (a.state != "talk" or b.state != "talk"
                    or a.partner != b.key or b.partner != a.key):
                for agent, other in ((a, b), (b, a)):
                    if agent.state == "talk" and agent.partner == other.key:
                        agent.end_talk()
                self.social_timer = 4.0
                return
            lines = (data or {}).get("lines") if isinstance(data, dict) else None
            if error or not isinstance(lines, list) or not lines:
                a.end_talk()
                b.end_talk()
                self.social_timer = self._social_retry_delay()
                return
            now = time.time() + 0.4
            script: list[tuple[Agent, str, float]] = []
            speakers = {"a": a, "b": b, "you": a, a.key.casefold(): a, b.key.casefold(): b,
                        a.name.casefold(): a, b.name.casefold(): b}
            for i, item in enumerate(lines[:5]):
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text", "")).strip()
                if not text:
                    continue
                speaker = str(item.get("speaker", "")).strip().casefold()
                who = speakers.get(speaker)
                if who is None:
                    continue
                script.append((who, text[:240], now))
                now += max(2.6, min(6.0, len(text) * 0.05 + 2.2))
            if not script:
                a.end_talk()
                b.end_talk()
                self.social_timer = self._social_retry_delay()
                return
            self._social_failures = 0
            self._add_social_script(script)
            a.talk_timer = (now - time.time() + 3) * self._social_speed()
            b.talk_timer = (now - time.time() + 3) * self._social_speed()
            a.memory.adjust(b.key, 0.04)
            b.memory.adjust(a.key, 0.04)
            self.social_timer = min(8.0, max(1.0, float(
                self.config.get("social.ambient_budget_s", 45))))

        self.llm.submit(
            "exchange",
            prompts.exchange_system(self.i18n.language),
            prompts.exchange_user(a.persona, b.persona,
                                  {**self._prompt_ctx(None),
                                   "mood_a": a.needs.mood_word(),
                                   "mood_b": b.needs.mood_word(),
                                    "activity_a": a.state,
                                    "activity_b": b.state,
                                    "relation": a.memory.relation_word(b.key),
                                    "social_history": history},
                                  topic),
            done, max_tokens=380, temperature=0.95)

    def _start_group(self, members: list[Agent]) -> None:
        for i, agent in enumerate(members):
            agent.begin_talk(members[(i + 1) % len(members)], self._social_wait())
        self.ambient_pending += 1
        self.social_timer = 2.0
        generation = self._social_generation

        def done(data: dict | None, error: str) -> None:
            if generation != self._social_generation:
                return
            self.ambient_pending = max(0, self.ambient_pending - 1)
            if any(agent.state != "talk" or agent.partner != members[(i + 1) % len(members)].key
                   for i, agent in enumerate(members)):
                for i, agent in enumerate(members):
                    if agent.state == "talk" and agent.partner == members[(i + 1) % len(members)].key:
                        agent.end_talk()
                self.social_timer = 4.0
                return
            lines = data.get("lines") if isinstance(data, dict) and not error else None
            by_name = {agent.name.casefold(): agent for agent in members}
            for index, agent in enumerate(members):
                by_name.setdefault(agent.key.casefold(), agent)
                by_name.setdefault(chr(ord("a") + index), agent)
            script = []
            at = time.time() + 0.4
            for item in (lines if isinstance(lines, list) else [])[:8]:
                if not isinstance(item, dict):
                    continue
                who = by_name.get(str(item.get("speaker", "")).strip().casefold())
                text = str(item.get("text", "")).strip()[:240]
                if who and text:
                    script.append((who, text, at))
                    at += max(2.6, min(6.0, len(text) * 0.05 + 2.2))
            if not script:
                for agent in members:
                    agent.end_talk()
                self.social_timer = self._social_retry_delay()
                return
            self._social_failures = 0
            self._add_social_script(script)
            for agent in members:
                agent.talk_timer = (at - time.time() + 3) * self._social_speed()
                for other in members:
                    if other is not agent:
                        agent.memory.adjust(other.key, 0.04)
            self.social_timer = min(8.0, max(1.0, float(self.config.get("social.ambient_budget_s", 45))))

        self.llm.submit("group", prompts.group_system(self.i18n.language),
                        prompts.group_user([a.persona for a in members], self._prompt_ctx(None),
                                           moods={a.key: a.needs.mood_word() for a in members}),
                        done, max_tokens=500, temperature=0.95)

    def _tick_script(self) -> None:
        self._tick_social_tracks()

    def _tick_one_script(self, script, voice) -> None:
        if not script:
            return
        now = time.time()
        agent, text, due = script[0]
        if due > now:
            return
        if agent.talk_timer <= 0 or agent.state != "talk":
            script.pop(0)
            return
        if voice.speak_ambient and voice.is_busy():
            return
        script.pop(0)
        agent.say(text, 5.6 * self._social_speed())
        voice.speak(text, agent.key, self.i18n.language, ambient=True)
        agent.needs.socialise(2)
        other = self.agent_by_key.get(agent.partner or "")
        if other:
            memory = f"{agent.name}: {text[:180]}"
            date = self.clock.date_text()
            agent.memory.add(memory, date, "social", other.key)
            other.memory.add(memory, date, "social", agent.key)

    def _hold_social_speech(self, dt: float) -> None:
        """Keep active bubbles and scheduled speakers alive while SAPI reads."""
        tracks = [(self.script, self.voice), *self._social_tracks]
        for script, voice in tracks:
            busy = voice.speak_ambient and voice.is_busy()
            if not busy:
                continue
            for speaker, _, _ in script:
                for agent in (speaker, self.agent_by_key.get(speaker.partner or "")):
                    if agent and agent.state == "talk" and agent.partner:
                        agent.talk_timer = max(agent.talk_timer, dt + 1.0)
        for agent in self.agents:
            if (agent.bubble and agent.state == "talk"
                    and any(voice.is_speaking(agent.key) for _, voice in tracks)):
                if agent.partner:
                    agent.talk_timer = max(agent.talk_timer, dt + 1.0)
                agent.bubble.timer = max(agent.bubble.timer, dt + 0.5)

    def _check_day(self) -> None:
        key = self.clock.now.strftime("%Y-%m-%d")
        if key == self.current_day_key:
            self._maybe_diary()
            return
        previous = self.current_day_key
        self.current_day_key = key
        self.day_number += 1
        self._plan_visitors()
        self.script.clear()
        self._close_social_tracks()
        self._social_generation += 1
        self.ambient_pending = 0
        self.social_timer = 8.0
        self.dispatch_card = None
        self.add_chronicle(self.i18n.t("event.newday", day=self.day_number), "day")
        self._request_diary(previous)
        self.toast(self.i18n.t("event.newday", day=self.day_number))
        self.autosave()

    def _maybe_diary(self) -> None:
        now = self.clock.now
        if now.hour == 21 and now.minute >= 30:
            self._request_diary(self.current_day_key)

    def _request_diary(self, day_key: str) -> None:
        if day_key in self._diary_requested or not self.llm.available:
            return
        events = [e["text"] for e in self.chronicle if e.get("key") == day_key]
        if len(events) < 2:
            return
        self._diary_requested.add(day_key)
        stamp = day_key
        try:
            stamp = datetime.strptime(day_key, "%Y-%m-%d").strftime("%d %b")
        except Exception:
            pass

        def done(data: dict | None, error: str) -> None:
            if error or not data:
                return
            diary = str(data.get("diary", "")).strip()
            if diary:
                self.diaries[day_key] = diary

        self.llm.submit(
            "chronicle", prompts.chronicle_system(self.i18n.language),
            prompts.chronicle_user(stamp, events, self._prompt_ctx(None)),
            done, max_tokens=320, temperature=0.85)

