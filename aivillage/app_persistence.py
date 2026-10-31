"""Extracted methods for VillageApp."""
from __future__ import annotations

from .app_shared import (
    Agent,
    JOBS,
    pygame,
    slot_path,
    sprites,
    traceback,
)

import importlib


class VillagePersistenceMixin:
    def snapshot(self) -> dict:
        return {
            "seed": self.seed,
            "day_number": self.day_number,
            "day_key": self.current_day_key,
            "language": self.i18n.language,
            "stats": dict(self.stats),
            "build": self.world.build_site.progress if self.world.build_site else 1.0,
            "plots": [{"tx": p.tx, "ty": p.ty, "stage": p.stage,
                       "growth": round(p.growth, 3),
                       "watered": round(p.watered, 3)} for p in self.world.plots],
            "agents": {
                a.key: {
                    "needs": {"hunger": a.needs.hunger, "energy": a.needs.energy,
                              "social": a.needs.social, "fun": a.needs.fun},
                    "affinity": dict(a.memory.affinity),
                    "memory": [{"text": m.text, "day": m.day, "kind": m.kind,
                                "dispatch_id": m.dispatch_id}
                               for m in a.memory.entries[-20:]],
                    "thread": [{"speaker": line.speaker, "text": line.text, "day": line.day}
                               for line in a.memory.thread_recent(a.memory.MAX_THREAD)],
                    "social_threads": {key: [{"speaker": line.speaker, "text": line.text, "day": line.day}
                                             for line in lines[-a.memory.MAX_THREAD:]]
                                       for key, lines in a.memory.social_threads.items()},
                    "x": a.x, "y": a.y,
                    "persona": {
                        "job": a.persona.job,
                        "work": a.persona.work,
                        "ambition": a.persona.ambition,
                        "bio": a.persona.bio,
                        "quirk": a.persona.quirk,
                        "dream_job": a.persona.dream_job,
                        "authored": a.persona.authored,
                        "hat": a.persona.look.hat,
                        "outfit": a.persona.look.cloth,
                    },
                } for a in self.agents
            },
            "chronicle": self.chronicle[-180:],
            "diaries": dict(self.diaries),
            "story_arc": dict(self.story_arc),
            "visitors_today": self.visitors_today,
        }

    def _apply_persona_save(self, agent: Agent, data: dict) -> None:
        """Restore a self-authored identity without trusting the save blindly."""
        if not isinstance(data, dict) or not data:
            return
        p = agent.persona
        for field_name, limit in (("ambition", 120), ("bio", 240), ("quirk", 90)):
            value = " ".join(str(data.get(field_name, "")).split())[:limit]
            if value:
                setattr(p, field_name, value)
        if p.is_child:
            dream = str(data.get("dream_job", "")).strip().lower()
            if dream in JOBS and not JOBS[dream].child:
                p.dream_job = dream
        else:
            job = str(data.get("job", "")).strip().lower()
            if job in JOBS and not JOBS[job].child:
                agent.set_job(job)
            else:
                work = str(data.get("work", ""))
                if work in agent.world.points:
                    p.work = work
        hat = str(data.get("hat", "")).strip().lower()
        if hat in ("", "straw", "cap", "hood"):
            p.look.hat = hat
        try:
            outfit = int(data.get("outfit", p.look.cloth))
        except (TypeError, ValueError):
            outfit = p.look.cloth
        if 0 <= outfit <= 7:
            p.look.cloth = outfit
        p.authored = bool(data.get("authored", True))

    def _apply_save(self, data: dict) -> None:
        try:
            if int(data.get("seed", self.seed)) != self.seed:
                return
            self.day_number = int(data.get("day_number", 1))
            self.stats.update({k: v for k, v in data.get("stats", {}).items()
                               if k in self.stats})
            build = data.get("build")
            if build is not None and self.world.build_site:
                self.world.build_site.progress = max(0.0, min(1.0, float(build)))
                for obj in self.world.objects:
                    if obj.kind == "buildsite":
                        obj.sprite = sprites.scaffold(self.world.build_site.progress)
            plots = {(p["tx"], p["ty"]): p for p in data.get("plots", [])}
            for plot in self.world.plots:
                saved = plots.get((plot.tx, plot.ty))
                if saved:
                    plot.stage = int(saved.get("stage", plot.stage))
                    plot.growth = float(saved.get("growth", plot.growth))
                    plot.watered = float(saved.get("watered", plot.watered))
            for key, adata in data.get("agents", {}).items():
                agent = self.agent_by_key.get(key)
                if not agent:
                    continue
                needs = adata.get("needs", {})
                for field_name in ("hunger", "energy", "social", "fun"):
                    if field_name in needs:
                        setattr(agent.needs, field_name,
                                float(needs[field_name]))
                agent.memory.affinity = {k: float(v) for k, v in
                                         adata.get("affinity", {}).items()}
                from .agents.memory import Memory
                agent.memory.entries = [
                    Memory(text=m.get("text", ""), day=m.get("day", ""),
                           kind=m.get("kind", "event"),
                           dispatch_id=m.get("dispatch_id", ""))
                    for m in adata.get("memory", []) if m.get("text")
                ]
                agent.memory.thread = []
                for line in adata.get("thread", [])[-agent.memory.MAX_THREAD:]:
                    if isinstance(line, dict) and line.get("speaker") in ("you", "them"):
                        agent.memory.add_thread(line["speaker"], line.get("text", ""), line.get("day", ""))
                agent.memory.social_threads = {}
                social_threads = adata.get("social_threads", {})
                if isinstance(social_threads, dict):
                    for other_key, lines in social_threads.items():
                        if other_key not in self.agent_by_key or other_key == key or not isinstance(lines, list):
                            continue
                        for line in lines[-agent.memory.MAX_THREAD:]:
                            if isinstance(line, dict) and line.get("speaker") in self.agent_by_key:
                                agent.memory.add_social_thread(other_key, line["speaker"], line.get("text", ""), line.get("day", ""))
                if "x" in adata and "y" in adata:
                    agent.x, agent.y = float(adata["x"]), float(adata["y"])
                    agent.state = "idle"
                    agent.block = ""
                    agent.path = []
                self._apply_persona_save(agent, adata.get("persona") or {})
            self.chronicle = list(data.get("chronicle", self.chronicle))[-260:]
            self.diaries = dict(data.get("diaries", {}))
            arc = data.get("story_arc", {})
            self.story_arc = {key: str(arc.get(key, ""))[:limit]
                              for key, limit in (("day", 10), ("title", 100),
                                                 ("summary", 320), ("open_question", 180))} if isinstance(arc, dict) and arc else {}
            self._story_generation += 1
            self._story_pending = ""
            lang = data.get("language")
            if lang in ("en", "de"):
                self.i18n.set_language(lang)
                self.config.set("general.language", lang)
            self._last_build_pct = -1
            self.renderer.invalidate()
        except Exception:
            traceback.print_exc()

    def autosave(self) -> None:
        importlib.import_module("aivillage.app").save_village(self.snapshot(), slot_path(self.save_slot))

    def _update(self, frame_dt: float) -> None:
        self.setup_download.poll()
        self.llm.poll()
        self.clock.update(frame_dt)
        self.weather = self.weather_service.current(self.clock.now)
        if self.weather.condition != self._last_condition:
            self._last_condition = self.weather.condition
            self.add_chronicle(self.i18n.t("event.weather",
                                           weather=self.i18n.weather(
                                               self.weather.condition)),
                               "weather")

        paused = self.clock.paused
        speed = 1 if self.clock.live else self.clock.sim_speed
        dt = 0.0 if paused else frame_dt * speed

        if self.chat.active:
            agent = self.agent_by_key.get(self.chat.target or "")
            if agent:
                agent.talk_timer = 600.0
                if agent.bubble:
                    agent.bubble.timer = 600.0

        if dt > 0:
            self._hold_social_speech(dt)

        for agent in self.agents:
            try:
                agent.update(dt, self)
            except Exception:
                traceback.print_exc()

        for visitor in list(self.visitors):
            try:
                visitor.update(dt, self)
            except Exception:
                traceback.print_exc()
            if visitor.state == "gone":
                if self.selected is visitor:
                    self.selected = None
                if self.dispatch_card is visitor:
                    self.dispatch_card = None
                self.visitors.remove(visitor)

        if dt > 0:
            self._check_alerts()
            self._check_visitor_schedule()
            self._maybe_social(frame_dt)
            self._maybe_self_direction(frame_dt)
            self._tick_script()
        if self._update_result:
            version, url, current = self._update_result
            self._update_result = None
            from .update_check import newer_version
            if newer_version(version, current):
                self.update_version, self.update_url = version, url
                self.toast(f"Version {version} available · press U for release", 12.0)
        self._check_day()
        for toast in list(self.toasts):
            toast[1] -= frame_dt
            if toast[1] <= 0:
                self.toasts.remove(toast)
        if self.dispatch_card is not None:
            if self.dispatch_card.state in ("leaving", "gone"):
                self.dispatch_card = None
        if self.follow_selected and self.selected is not None:
            self.camera.soft_follow(self.selected.x, self.selected.y, frame_dt)
        self._autosave += frame_dt
        if self._autosave > 300:
            self._autosave = 0.0
            self.autosave()

    def _draw(self, frame_dt: float) -> None:
        if self.inside_house:
            self.renderer.draw_interior(self.screen, self.world.buildings.get(self.inside_house),
                                        self.agents, self.i18n)
        else:
            self.renderer.draw(self.screen, self.clock, self.weather, self.agents,
                               self.visitors, self.selected, frame_dt)
        if not self.photo_mode:
            self.ui.draw(self.screen, self, frame_dt)
        else:
            self.ui.hits = {}
        pygame.display.flip()

