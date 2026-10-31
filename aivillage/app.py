"""aivillage — the running village.

One process, one window. The simulation ticks on real elapsed time; the clock
inside the village is the player's clock unless they fast-forward.
"""
from __future__ import annotations

import math
import os
import random
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime

import pygame

from .agents.brain import Agent
from .agents.jobs import JOBS, ADULT_JOBS, job_choices
from .agents.roster import ROSTER
from .agents.visitor import Visitor
from .assets import sprites
from .assets.palette import P
from .assets.sfx import Sfx
from .i18n import I18N
from .llm import prompts
from .llm.client import client as make_llm
from .news.pipeline import NewsService
from .reality.clock import SimClock
from .reality.geo import LocationService
from .reality.weather import WeatherService
from .render.camera import Camera
from .render.renderer import Renderer
from .render.ui import UI
from .save import load_village, save_village
from .voice.tts import VoiceService
from .world.mapgen import H, W, World

TILE = 16


@dataclass
class ChatState:
    active: bool = False
    target: str | None = None
    input: str = ""
    lines: list[tuple[str, str]] = field(default_factory=list)
    pending: bool = False


class VillageApp:
    def __init__(self, config, new_game: bool = False, seed: int | None = None):
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass
        pygame.font.init()

        self.config = config
        self.i18n = I18N
        self.i18n.set_language(config.language)
        self.seed = int(seed if seed is not None else config.seed)
        self.new_game = new_game

        info = pygame.display.Info()
        width = int(config.get("general.window_width", 1440))
        height = int(config.get("general.window_height", 810))
        width = max(960, min(width, max(960, info.current_w - 80)))
        height = max(600, min(height, max(600, info.current_h - 100)))
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("aivillage")
        self._set_icon()

        self.pyclock = pygame.time.Clock()
        self.running = True
        self.sfx = Sfx(True, 0.8)
        self.voice = VoiceService(config, self.i18n,
                                  {p.key: p.voice for p in ROSTER})
        self.llm = make_llm(config)
        self.uiclock = pygame.time.Clock()

        self.world = World(self.seed)
        self.locations = LocationService(config)
        self.weather_service = WeatherService(config, self.locations)
        self.weather = self.weather_service.current()
        self.clock = SimClock(config, self.weather_service)

        self.rng = random.Random(self.seed * 977 + 13)
        self.agents: list[Agent] = []
        for i, persona in enumerate(ROSTER):
            self.agents.append(Agent(persona, self.world,
                                     random.Random(self.seed + i * 131)))
        self.agent_by_key = {a.key: a for a in self.agents}

        self.camera = Camera(W * TILE, H * TILE,
                             int(config.get("general.zoom", 3)),
                             (width, height))
        self.camera.center_on(*self.world.points.get("plaza", (500, 360)))
        self.renderer = Renderer(self.world, self.camera, self.i18n)
        self.ui = UI(self.i18n)

        self.selected = None
        self.follow_selected = False
        self.chat = ChatState()
        self.show_chronicle = False
        self.show_jobs = False
        self.setup_dismissed = False
        self.self_pending: str | None = None
        self._self_timer = 40.0

        self.stats = {"wood": 14, "stone": 6, "food": 22, "coin": 7}
        self.chronicle: list[dict] = []
        self.diaries: dict[str, str] = {}
        self.day_number = 1
        self.current_day_key = self.clock.now.strftime("%Y-%m-%d")
        self.visitors: list[Visitor] = []
        self.dispatch_card: Visitor | None = None
        self.toasts: list[list] = []
        self.ambient_pending = False
        self.script: list[tuple[Agent, str, float]] = []
        self.social_timer = 12.0
        self.visitor_pending = False
        self.visitors_today = 0
        self.visitor_slots: list[int] = []
        self.visitor_slot_idx = 0
        self.night_demo_at = 0.0
        self._last_build_pct = -1
        self._last_condition = self.weather.condition
        self._autosave = 0.0
        self._diary_requested: set[str] = set()
        self._drag_last = (0, 0)
        self._dragging = False
        self._press_world = False
        self._was_live = self.clock.live

        self.news = NewsService(config, self.llm, self.i18n)

        self._autoquit = float(os.environ.get("AIVILLAGE_AUTOQUIT", "0") or 0)
        self._autoshot = os.environ.get("AIVILLAGE_AUTOSHOT", "")
        self._shot_at = float(os.environ.get("AIVILLAGE_SHOT_AT", "2.0") or 2.0)
        self._shot_done = False
        self._started_at = time.time()

        self._plan_visitors()
        if not new_game:
            data = load_village()
            if data:
                self._apply_save(data)
                self.toast(self._saved_banner(data))
        if self.clock.now.hour >= 19:
            self.night_demo_at = time.time() + 90.0

    # -- setup -----------------------------------------------------------
    def _set_icon(self) -> None:
        try:
            icon = pygame.Surface((32, 32), pygame.SRCALPHA)
            icon.fill((26, 32, 30))
            pygame.draw.rect(icon, P["roof_red"], (4, 10, 24, 8))
            pygame.draw.rect(icon, P["cream"], (7, 18, 18, 10))
            pygame.draw.rect(icon, P["window"], (14, 21, 4, 4))
            pygame.display.set_icon(icon)
        except Exception:
            pass

    def _saved_banner(self, data: dict) -> str:
        stamp = data.get("saved_at")
        if not stamp:
            return self.i18n.t("ui.saved")
        try:
            when = datetime.fromtimestamp(float(stamp)).strftime("%d %b %H:%M")
        except Exception:
            when = ""
        return self.i18n.t("ui.loaded", when=when)

    def _plan_visitors(self) -> None:
        key = self.clock.now.strftime("%Y-%m-%d")
        rng = random.Random(f"{key}-{self.seed}")
        arrivals = int(self.config.get("visitors.arrivals_per_day", 3))
        cap = int(self.config.get("news.max_dispatches_per_day", 2))
        count = max(0, min(arrivals, cap))
        pool = list(range(9 * 60, 19 * 60))
        self.visitor_slots = sorted(rng.sample(pool, count)) if count else []
        self.visitor_slot_idx = 0
        self.visitors_today = 0

    # -- services --------------------------------------------------------
    def _start_services(self) -> None:
        self.locations.resolve_async()
        self.weather_service.start()
        threading.Thread(target=self._after_location, daemon=True,
                         name="reality").start()
        self.news.start()

    def _after_location(self) -> None:
        loc_thread = self.locations._thread
        if loc_thread:
            loc_thread.join(20)
        self.weather_service.fetch()

    # -- toasts / chronicle ---------------------------------------------
    def toast(self, text: str, ttl: float = 4.5) -> None:
        if not text:
            return
        self.toasts.append([text, ttl])
        if len(self.toasts) > 6:
            self.toasts = self.toasts[-6:]

    def add_chronicle(self, text: str, kind: str = "event") -> None:
        if not text:
            return
        now = self.clock.now
        self.chronicle.append({
            "key": now.strftime("%Y-%m-%d"),
            "day": now.strftime("%d %b"),
            "time": now.strftime("%H:%M"),
            "text": text,
            "kind": kind,
        })
        if len(self.chronicle) > 260:
            self.chronicle = self.chronicle[-260:]

    # -- context methods used by agents ----------------------------------
    def gain(self, resource: str, amount: float, agent: Agent) -> None:
        if resource in self.stats:
            self.stats[resource] += amount

    def build(self, amount: float, agent: Agent) -> None:
        site = self.world.build_site
        if site is None:
            return
        finished = site.contribute(amount)
        pct = int(site.progress * 10)
        if pct != self._last_build_pct:
            self._last_build_pct = pct
            for obj in self.world.objects:
                if obj.kind == "buildsite":
                    obj.sprite = sprites.scaffold(site.progress)
                    break
            self.renderer.invalidate()
        if finished:
            self.toast(self.i18n.t("event.townhall"))
            self.add_chronicle(self.i18n.t("event.townhall_long"), "build")
            self.sfx.play("hammer")
            self.gain("stone", 4, agent)

    def tend_plot(self, agent: Agent) -> None:
        site = (agent.x // TILE, agent.y // TILE)
        best = None
        best_d = 1e9
        for plot in self.world.plots:
            if plot.ripe:
                continue
            d = abs(plot.tx - site[0]) + abs(plot.ty - site[1])
            if d < best_d:
                best, best_d = plot, d
        if best is None:
            self.gain("food", 1, agent)
            return
        best.watered = max(best.watered, 1.5)
        best.advance(2.0, self.weather.wet)
        if best.ripe:
            self.gain("food", 4, agent)

    def flavour_meal(self, agent: Agent) -> str:
        # Dialogue is LLM-only; the simulation never invents lines itself.
        return ""

    def on_visitor_arrived(self, visitor: Visitor) -> None:
        self.toast(self.i18n.t("event.arrived", name=visitor.name))
        self.sfx.chime()

    def speak_visitor(self, visitor: Visitor) -> None:
        dispatch = visitor.dispatch
        if dispatch is None:
            return
        self.dispatch_card = visitor
        line = dispatch.headline
        self.add_chronicle(
            self.i18n.t("event.news", name=visitor.name, line=line,
                        source=dispatch.source), "news")
        self.news.record_visit(dispatch, line, self.clock.date_text())
        for agent in self.agents:
            agent.memory.add(line, self.clock.date_text(), "news", dispatch.item_id)
        near = sorted(self.agents, key=lambda a: math.hypot(a.x - visitor.x,
                                                            a.y - visitor.y))[:4]
        for agent in near:
            agent.attend_assembly(visitor.x, visitor.y, 18.0)
        self.voice.speak(line, "__visitor__", self.i18n.language)
        self.sfx.chime()

    def rumour_for(self, visitor: Visitor) -> str:
        return ""

    # -- chat ------------------------------------------------------------
    def selected_agent(self) -> Agent | None:
        return self.selected if isinstance(self.selected, Agent) else None

    def open_chat(self, agent: Agent | None = None) -> None:
        agent = agent or self.selected_agent()
        if agent is None:
            return
        if not self.llm.available:
            self.toast(self.i18n.t("ui.no_llm"))
            return
        self.chat.active = True
        self.chat.target = agent.key
        self.chat.lines = []
        self.chat.input = ""
        self.chat.pending = False
        agent.path = []
        agent.state = "talk"
        agent.talk_timer = 600.0
        agent.say("", 600.0, pending=True)
        self.sfx.play("select")

    def close_chat(self) -> None:
        agent = self.agent_by_key.get(self.chat.target or "")
        if agent:
            agent.talk_timer = 0.0
            agent.bubble = None
            agent.state = "free"
            agent.action_timer = 2
        self.chat = ChatState()

    def submit_chat(self) -> None:
        text = self.chat.input.strip()
        agent = self.agent_by_key.get(self.chat.target or "")
        if not text or agent is None or self.chat.pending:
            return
        if not self.llm.available:
            self.toast(self.i18n.t("ui.no_llm"))
            return
        self.chat.input = ""
        self.chat.lines.append(("you", text))
        self.chat.pending = True
        agent.say("", 600.0, pending=True)
        ctx = self._prompt_ctx(agent)
        key = agent.key
        message = text

        def done(data: dict | None, error: str) -> None:
            if self.chat.target == key:
                self.chat.pending = False
            if error or not data:
                if self.chat.target == key and self.chat.active:
                    self.toast(self.i18n.t("ui.no_reply"))
                return
            line = str(data.get("line") or data.get("reply") or "").strip()
            if not line:
                if self.chat.target == key and self.chat.active:
                    self.toast(self.i18n.t("ui.no_reply"))
                return
            agent.say(line, 9.0)
            agent.state = "talk"
            agent.talk_timer = 600.0
            agent.memory.add(f"You said: {message[:90]}", self.clock.date_text(),
                             "chat")
            agent.memory.add(f"You answered: {line[:120]}", self.clock.date_text(),
                             "chat")
            if self.chat.target == key:
                self.chat.lines.append(("them", line))
                if len(self.chat.lines) > 60:
                    self.chat.lines = self.chat.lines[-60:]
            self.voice.speak(line, key, self.i18n.language)

        self.llm.submit("chat", prompts.chat_system(agent.persona, self.i18n.language),
                        prompts.chat_user(agent.persona, message, ctx), done,
                        max_tokens=220, temperature=0.95)

    def _prompt_ctx(self, agent: Agent | None) -> dict:
        t = self.i18n
        loc = self.locations.location
        ctx = {
            "time": self.clock.now.strftime("%H:%M"),
            "weather": t.weather(self.weather.condition),
            "temp": f"{self.weather.temp_c:.0f}",
            "season": t.t(f"season.{self.clock.season()}"),
            "stock": (f"wood {int(self.stats['wood'])}, stone "
                      f"{int(self.stats['stone'])}, food {int(self.stats['food'])}"),
            "place": loc.label,
        }
        if agent is not None:
            rels = []
            for key, value in sorted(agent.memory.affinity.items(),
                                     key=lambda kv: -abs(kv[1]))[:3]:
                other = self.agent_by_key.get(key)
                if other:
                    rels.append(f"{other.name}: {agent.memory.relation_word(key)}")
            ctx.update({
                "memories": agent.memory.recent(5),
                "mood": agent.needs.mood_word(),
                "activity": agent.state,
                "relations": ("How you feel about your neighbours: " +
                              "; ".join(rels)) if rels else "",
            })
        return ctx

    # -- self-authored identities ---------------------------------------
    def request_self(self, agent: Agent | None = None) -> bool:
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
                self.toast(self.i18n.t("ui.no_reply"))
                return
            changed = agent.apply_self(data)
            if not changed:
                self.toast(self.i18n.t("ui.self_none", name=agent.name))
                return
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
        self.request_self(self.rng.choice(candidates))

    # -- visitors --------------------------------------------------------
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

    # -- ambient conversation -------------------------------------------
    def _maybe_social(self, dt: float) -> None:
        self.social_timer -= dt
        if (self.social_timer > 0 or self.ambient_pending or self.chat.active
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
        a.begin_talk(b, 12.0)
        b.begin_talk(a, 12.0)
        self.ambient_pending = True
        topic = ""
        recent = a.memory.recent(1, "news") or b.memory.recent(1, "news")
        if recent:
            topic = recent[-1]

        def done(data: dict | None, error: str) -> None:
            self.ambient_pending = False
            lines = (data or {}).get("lines") if isinstance(data, dict) else None
            if not isinstance(lines, list) or not lines:
                a.end_talk()
                b.end_talk()
                self.social_timer = 25.0
                return
            now = time.time() + 0.4
            script: list[tuple[Agent, str, float]] = []
            for i, item in enumerate(lines[:5]):
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text", "")).strip()
                if not text:
                    continue
                speaker = str(item.get("speaker", "a")).lower()
                who = a if speaker in ("a", "you") else b
                script.append((who, text[:240], now))
                now += max(2.6, min(6.0, len(text) * 0.05 + 2.2))
            self.script.extend(script)
            a.talk_timer = max(a.talk_timer, now - time.time() + 3)
            b.talk_timer = max(b.talk_timer, now - time.time() + 3)
            a.memory.adjust(b.key, 0.04)
            b.memory.adjust(a.key, 0.04)
            self.social_timer = max(90.0, float(
                self.config.get("social.ambient_budget_s", 150)))

        self.llm.submit(
            "exchange",
            prompts.exchange_system(self.i18n.language),
            prompts.exchange_user(a.persona, b.persona,
                                  {**self._prompt_ctx(None),
                                   "mood_a": a.needs.mood_word(),
                                   "mood_b": b.needs.mood_word(),
                                   "activity_a": a.state,
                                   "activity_b": b.state,
                                   "relation": a.memory.relation_word(b.key)},
                                  topic),
            done, max_tokens=380, temperature=0.95)

    def _tick_script(self) -> None:
        if not self.script:
            return
        now = time.time()
        due = [s for s in self.script if s[2] <= now]
        if not due:
            return
        self.script = [s for s in self.script if s[2] > now]
        for agent, text, _ in due:
            if agent.talk_timer <= 0:
                continue
            agent.say(text, 5.6)
            self.voice.speak(text, agent.key, self.i18n.language, ambient=True)
            agent.needs.socialise(2)

    # -- day / save ------------------------------------------------------
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
        self.ambient_pending = False
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
                if "x" in adata and "y" in adata:
                    agent.x, agent.y = float(adata["x"]), float(adata["y"])
                    agent.state = "idle"
                    agent.block = ""
                    agent.path = []
                self._apply_persona_save(agent, adata.get("persona") or {})
            self.chronicle = list(data.get("chronicle", self.chronicle))[-260:]
            self.diaries = dict(data.get("diaries", {}))
            lang = data.get("language")
            if lang in ("en", "de"):
                self.i18n.set_language(lang)
                self.config.set("general.language", lang)
            self._last_build_pct = -1
            self.renderer.invalidate()
        except Exception:
            traceback.print_exc()

    def autosave(self) -> None:
        save_village(self.snapshot())

    # -- simulation ------------------------------------------------------
    def _update(self, frame_dt: float) -> None:
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
            self._check_visitor_schedule()
            self._maybe_social(frame_dt)
            self._maybe_self_direction(frame_dt)
            self._tick_script()
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

    # -- drawing ---------------------------------------------------------
    def _draw(self, frame_dt: float) -> None:
        self.renderer.draw(self.screen, self.clock, self.weather, self.agents,
                           self.visitors, self.selected, frame_dt)
        self.ui.draw(self.screen, self, frame_dt)
        pygame.display.flip()

    # -- input -----------------------------------------------------------
    def _action(self, action: str) -> None:
        t = self.i18n.t
        if action == "pause":
            self.clock.toggle_pause()
            self.sfx.play("click")
        elif action.startswith("speed:"):
            self.clock.set_speed(int(action.split(":")[1]))
            self.sfx.play("click")
        elif action == "live":
            self.clock.return_to_live()
            self.sfx.play("click")
        elif action == "mute":
            muted = self.voice.toggle_mute()
            self.toast(t("ui.mute") if muted else t("ui.unmute"))
        elif action == "lang":
            lang = self.i18n.toggle()
            self.config.set("general.language", lang)
            self.toast(t("ui.language") + ": " + lang.upper())
        elif action == "chronicle":
            self.show_chronicle = not self.show_chronicle
            self.ui.chronicle_scroll = 0
        elif action == "save":
            if save_village(self.snapshot()):
                self.toast(t("ui.saved"))
                self.sfx.play("coin")
            else:
                self.toast(t("ui.save_failed"))
        elif action == "visitor":
            if not self.spawn_visitor(force=True):
                pass
        elif action == "talk":
            self.open_chat()
        elif action == "self":
            self.request_self()
        elif action == "jobs":
            self.show_jobs = not self.show_jobs
        elif action == "close_jobs":
            self.show_jobs = False
        elif action == "send":
            self.submit_chat()
        elif action == "close_chat":
            self.close_chat()
        elif action == "close_chronicle":
            self.show_chronicle = False
        elif action == "close_setup":
            self.setup_dismissed = True
        elif action == "close_dispatch":
            self.dispatch_card = None
        elif action == "llm_retry":
            self.llm.retry_resolve()
            self.toast(self.llm.label)

    def _paste(self) -> str:
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            raw = pygame.scrap.get(pygame.SCRAP_TEXT)
            if not raw:
                return ""
            text = raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else str(raw)
            return " ".join(text.replace("\x00", "").split())
        except Exception:
            return ""

    def _key(self, e) -> None:
        if self.chat.active:
            if e.key == pygame.K_ESCAPE:
                self.close_chat()
            elif e.key == pygame.K_RETURN or e.key == pygame.K_KP_ENTER:
                self.submit_chat()
            elif e.key == pygame.K_BACKSPACE:
                self.chat.input = self.chat.input[:-1]
            elif e.key == pygame.K_v and (e.mod & pygame.KMOD_CTRL):
                pasted = self._paste()
                if pasted:
                    self.chat.input = (self.chat.input + " " + pasted).strip()[:220]
            elif e.unicode and e.unicode.isprintable() and len(self.chat.input) < 220:
                self.chat.input += e.unicode
            return

        if self.show_jobs:
            if e.key in (pygame.K_ESCAPE, pygame.K_j):
                self.show_jobs = False
            return

        if self.show_chronicle:
            if e.key in (pygame.K_ESCAPE, pygame.K_c):
                self.show_chronicle = False
            elif e.key == pygame.K_DOWN:
                self.ui.scroll(-1)
            elif e.key == pygame.K_UP:
                self.ui.scroll(1)
            return

        if e.key == pygame.K_ESCAPE:
            if self.selected is not None:
                self.selected = None
                self.follow_selected = False
            elif not self.setup_dismissed and not self.llm.available:
                self.setup_dismissed = True
        elif e.key == pygame.K_t:
            self.open_chat()
        elif e.key == pygame.K_r:
            self._action("self")
        elif e.key == pygame.K_j:
            self._action("jobs")
        elif e.key == pygame.K_c:
            self.show_chronicle = True
            self.ui.chronicle_scroll = 0
        elif e.key == pygame.K_m:
            self._action("mute")
        elif e.key == pygame.K_s:
            self._action("save")
        elif e.key == pygame.K_v:
            self._action("visitor")
        elif e.key == pygame.K_F2:
            self._action("lang")
        elif e.key == pygame.K_SPACE:
            self._action("pause")
        elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            speeds = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 4, pygame.K_4: 8}
            self.clock.set_speed(speeds[e.key])
        elif e.key == pygame.K_l:
            self.clock.return_to_live()
        elif e.key == pygame.K_n:
            self.clock.sleep_until_dawn()
            self.toast(self.i18n.t("ui.sleep_until_dawn"))
        elif e.key == pygame.K_F12:
            self._screenshot()

    def _screenshot(self) -> None:
        try:
            from .config import DATA_DIR
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            path = DATA_DIR / f"aivillage-{stamp}.png"
            pygame.image.save(self.screen, str(path))
            self.toast(f"screenshot: {path.name}")
        except Exception:
            pass

    def _pick(self, pos):
        wx, wy = self.camera.screen_to_world(*pos)
        best = None
        best_d = 1e9
        for agent in self.agents:
            d = math.hypot(agent.x - wx, (agent.y - 8) - wy)
            if d < 15 and d < best_d:
                best, best_d = agent, d
        for visitor in self.visitors:
            if visitor.state == "gone":
                continue
            d = math.hypot(visitor.x - wx, (visitor.y - 8) - wy)
            if d < 15 and d < best_d:
                best, best_d = visitor, d
        return best

    def _mouse_down(self, e) -> None:
        if e.button == 1:
            action = self.ui.action_at(e.pos)
            if action:
                self._action(action)
                self._press_world = False
                return
            if self.show_jobs:
                self.show_jobs = False
                return
            if self.show_chronicle:
                self.show_chronicle = False
                return
            self._press_world = True
            self._dragging = False
            self._drag_last = e.pos
        elif e.button == 3:
            if self.chat.active:
                self.close_chat()
            elif self.show_jobs:
                self.show_jobs = False
            elif self.show_chronicle:
                self.show_chronicle = False
            else:
                self.selected = None
                self.follow_selected = False

    def _mouse_up(self, e) -> None:
        if e.button != 1 or not self._press_world:
            return
        self._press_world = False
        if self._dragging:
            self._dragging = False
            return
        picked = self._pick(e.pos)
        self.selected = picked
        self.follow_selected = picked is not None
        if picked is not None:
            self.sfx.play("select")

    def _events(self) -> None:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.VIDEORESIZE:
                w = max(960, e.w)
                h = max(600, e.h)
                self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
                self.camera.set_view(w, h)
                self.renderer.invalidate()
            elif e.type == pygame.KEYDOWN:
                self._key(e)
            elif e.type == pygame.MOUSEWHEEL:
                if self.show_chronicle:
                    self.ui.scroll(e.y)
                else:
                    self.camera.zoom_at(*pygame.mouse.get_pos(), e.y)
                    self.renderer.invalidate()
                    self.follow_selected = False
            elif e.type == pygame.MOUSEBUTTONDOWN:
                self._mouse_down(e)
            elif e.type == pygame.MOUSEBUTTONUP:
                self._mouse_up(e)
            elif e.type == pygame.MOUSEMOTION:
                if self._press_world and e.buttons[0]:
                    dx = e.pos[0] - self._drag_last[0]
                    dy = e.pos[1] - self._drag_last[1]
                    if abs(dx) + abs(dy) > 3:
                        self._dragging = True
                        self.follow_selected = False
                        self.camera.pan_screen(dx, dy)
                    self._drag_last = e.pos

        keys = pygame.key.get_pressed()
        if not self.chat.active and not self.show_chronicle and not self.show_jobs:
            step = 260.0 * (1 / 60.0)
            dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - \
                 (keys[pygame.K_a] or keys[pygame.K_LEFT])
            dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - \
                 (keys[pygame.K_w] or keys[pygame.K_UP])
            if dx or dy:
                self.follow_selected = False
                self.camera.nudge(dx * step, dy * step)

    # -- main loop -------------------------------------------------------
    def run(self) -> None:
        self._start_services()
        last = time.perf_counter()
        while self.running:
            now = time.perf_counter()
            frame_dt = min(0.12, max(0.0001, now - last))
            last = now
            self._events()
            self._update(frame_dt)
            self._draw(frame_dt)
            self.pyclock.tick(60)

            elapsed = time.time() - self._started_at
            if self._autoshot and not self._shot_done and elapsed >= self._shot_at:
                self._shot_done = True
                try:
                    pygame.image.save(self.screen, self._autoshot)
                except Exception:
                    traceback.print_exc()
            if self._autoquit and elapsed >= self._autoquit:
                self.running = False
        self.shutdown()

    def shutdown(self) -> None:
        try:
            self.autosave()
        except Exception:
            pass
        try:
            self.news.stop()
        except Exception:
            pass
        try:
            self.weather_service.stop()
        except Exception:
            pass
        try:
            self.voice.shutdown()
        except Exception:
            pass
        try:
            self.llm.stop()
        except Exception:
            pass
        pygame.quit()
