"""Extracted methods for VillageApp."""
from __future__ import annotations

from .app_shared import (
    Agent,
    P,
    TILE,
    Visitor,
    datetime,
    math,
    pygame,
    random,
    sprites,
    threading,
)
from .agents.jobs import job_for
from .reality.calendar import routine_key
from .economy import (
    MARKET_MEAL_PRICE,
    MARKET_TRADE_PRICE,
    TAVERN_MEAL_PRICE,
    WAGE_SHARE,
)


class VillageServicesMixin:
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

    def _start_services(self) -> None:
        self.locations.resolve_async()
        self.weather_service.start()
        threading.Thread(target=self._after_location, daemon=True,
                         name="reality").start()
        self.news.start()
        self.alerts.start()

    def _after_location(self) -> None:
        loc_thread = self.locations._thread
        if loc_thread:
            loc_thread.join(20)
        self.weather_service.fetch()

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

    def market_open(self) -> bool:
        now = self.clock.now
        minute = now.hour * 60 + now.minute
        return routine_key(now) == "market" and 9 * 60 <= minute < 14 * 60

    def gain(self, resource: str, amount: float, agent: Agent) -> None:
        if resource not in self.stats:
            return
        self.stats[resource] += amount
        if resource == "coin" and agent is not None:
            # Paid trades also put a wage share into the worker's own purse.
            agent.wallet = round(agent.wallet + float(amount) * WAGE_SHARE, 2)

    def take_ingredient(self, agent: Agent) -> bool:
        """Take one meal's worth of food from the village pantry."""
        if float(self.stats.get("food", 0)) < 1.0:
            return False
        self.stats["food"] -= 1.0
        return True

    def buy_meal(self, agent: Agent, kind: str) -> bool:
        """Pay for a prepared meal at the tavern or the Saturday market."""
        if kind == "market" and not self.market_open():
            return False
        price = MARKET_MEAL_PRICE if kind == "market" else TAVERN_MEAL_PRICE
        if agent.wallet + 1e-9 < price:
            return False
        if float(self.stats.get("food", 0)) < 1.0:
            return False
        agent.wallet = round(max(0.0, agent.wallet - price), 2)
        self.stats["coin"] += price
        self.stats["food"] -= 1.0
        return True

    def market_trade(self, agent: Agent) -> str:
        """Let a villager buy provisions or sell wares on market day.

        Buying moves coins from the purse into the village till and food out of
        the pantry.  Selling moves coins the other way.  Both sides therefore
        use the same small stock, instead of inventing money from nowhere.
        """
        if not self.market_open():
            return ""
        price = MARKET_TRADE_PRICE
        can_buy = (float(self.stats.get("food", 0)) >= 1.0
                   and agent.wallet + 1e-9 >= price)
        job = job_for(agent.persona.job)
        can_sell = (not agent.persona.is_child and bool(job.resource)
                    and float(self.stats.get("coin", 0)) >= price)
        if can_buy and (not can_sell or agent.rng.random() < 0.6):
            agent.wallet = round(max(0.0, agent.wallet - price), 2)
            self.stats["coin"] += price
            self.stats["food"] -= 1.0
            agent.needs.fun = min(100.0, agent.needs.fun + 4.0)
            agent.needs.socialise(4.0)
            return "buy"
        if can_sell:
            agent.wallet = round(agent.wallet + price, 2)
            self.stats["coin"] -= price
            return "sell"
        return ""

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

    def _prompt_ctx(self, agent: Agent | None) -> dict:
        t = self.i18n
        loc = self.locations.location
        ctx = {
            "time": self.clock.now.strftime("%H:%M"),
            "weather": t.weather(self.weather.condition),
            "temp": f"{self.weather.temp_c:.0f}",
            "season": t.t(f"season.{self.clock.season()}"),
            "stock": (f"wood {int(self.stats['wood'])}, stone "
                      f"{int(self.stats['stone'])}, food {int(self.stats['food'])}, "
                      f"coin {int(self.stats['coin'])}"),
            "place": loc.label,
        }
        if self.config.get("social.story_arcs", True) and self.story_arc:
            ctx["story_arc"] = self.story_arc.get("summary", "")
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
                "purse": f"{agent.wallet:.0f} coin",
                "activity": agent.state,
                "thread": agent.memory.thread_prompt() if self.config.get("social.threads", True) else [],
                "relations": ("How you feel about your neighbours: " +
                              "; ".join(rels)) if rels else "",
            })
        return ctx

