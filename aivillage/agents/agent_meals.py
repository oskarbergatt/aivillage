"""Meal planning, cooking, buying and gradual eating."""
from __future__ import annotations

from ..economy import (
    NUTRITION,
    TAVERN_MEAL_PRICE,
    MealPlan,
    choose_meal,
)


class AgentMealsMixin:
    def _plan_meal(self, ctx) -> MealPlan:
        pantry = float(getattr(ctx, "stats", {}).get("food", 0.0))
        market = bool(ctx.market_open()) if hasattr(ctx, "market_open") else False
        return choose_meal(self.persona, self.needs, self.wallet, pantry,
                           market, self.rng)

    def _fallback_meal_plan(self) -> MealPlan:
        return MealPlan("cook", self.home_point, 0.0, NUTRITION["cook"])

    def _start_meal(self, ctx) -> None:
        """Cook, buy or scrounge, depending on what the villager can afford."""
        plan = self.meal_plan or self._plan_meal(ctx)
        if plan.kind in ("buy", "market"):
            if self._begin_buying(ctx, plan):
                return
            if self._begin_cooking(ctx):
                return
        elif plan.kind == "cook":
            if self._begin_cooking(ctx):
                return
            fallback = MealPlan("buy", "tavern_door", TAVERN_MEAL_PRICE,
                                NUTRITION["buy"])
            if self._begin_buying(ctx, fallback):
                return
        self._scrounge_meal()

    def _begin_cooking(self, ctx) -> bool:
        if not ctx.take_ingredient(self):
            return False
        self.meal_kind = "cook"
        self.meal_nutrition = NUTRITION["cook"]
        self.meal_served = 0.0
        self.state = "cook"
        self.action_timer = self.rng.uniform(18, 40)
        self.task_name = "cooking a meal"
        return True

    def _begin_buying(self, ctx, plan: MealPlan) -> bool:
        if not ctx.buy_meal(self, plan.kind):
            return False
        self.meal_kind = plan.kind
        self.meal_nutrition = plan.nutrition
        self.meal_served = 0.0
        self.state = "buy"
        self.action_timer = self.rng.uniform(6, 14)
        self.task_name = ("buying a market meal" if plan.kind == "market"
                          else "buying a meal at the tavern")
        return True

    def _scrounge_meal(self) -> None:
        self.meal_kind = "scrounge"
        self.meal_nutrition = NUTRITION["scrounge"]
        self.meal_served = 0.0
        self.state = "meal"
        self.action_timer = self.rng.uniform(12, 24)
        self.meal_total = self.action_timer
        self.task_name = "scrounging a cold meal"

    def _begin_eating(self) -> None:
        self.state = "meal"
        self.action_timer = self.rng.uniform(20, 45)
        self.meal_total = self.action_timer
        self.meal_served = 0.0
        self.task_name = "eating a meal"

    def _eat(self, dt: float) -> None:
        if self.meal_nutrition <= 0:
            # A save or a hand-built test agent from before cooking existed.
            self.needs.eat(58)
            self.meal_nutrition = 58.0
            self.meal_served = 58.0
            self.meal_total = max(self.action_timer, 1.0)
        else:
            total = max(self.meal_total, 0.001)
            if dt >= self.action_timer:
                portion = max(0.0, self.meal_nutrition - self.meal_served)
            else:
                portion = self.meal_nutrition * max(0.0, dt) / total
            portion = min(portion,
                          max(0.0, self.meal_nutrition - self.meal_served))
            if portion > 0:
                self.needs.eat(portion)
                self.meal_served += portion
        self.action_timer -= dt
        if self.action_timer <= 0:
            self.state = "idle"
            self.action_timer = 5
            self.meal_kind = ""
            self.meal_nutrition = 0.0
            self.meal_served = 0.0
            self.meal_total = 0.0
            self.eating = False
