"""Villager meal plans, purses and market trades."""
from __future__ import annotations

import random
from datetime import datetime
from types import SimpleNamespace

from aivillage.economy import (MEAL_KEYS, TAVERN_MEAL_PRICE, MealPlan,
                               choose_meal)


class FixedRandom:
    def __init__(self, value: float):
        self.value = value

    def random(self) -> float:
        return self.value


def persona(traits=None, home="pip", child=False):
    return SimpleNamespace(home=home, is_child=child, traits=traits or {})


def need(hunger: float):
    return SimpleNamespace(hunger=hunger)


def test_meal_plan_uses_wallet_pantry_and_hunger():
    p = persona({"sociability": 0.2, "creativity": 0.9})
    plan = choose_meal(p, need(50), 0, 3, False, random.Random(1))
    assert plan.kind == "cook"
    assert plan.target == "home_pip"
    assert plan.price == 0

    plan = choose_meal(p, need(50), TAVERN_MEAL_PRICE, 0, False,
                       random.Random(1))
    assert plan.kind == "buy"
    assert plan.target == "tavern_door"

    plan = choose_meal(p, need(10), 0, 0, False, random.Random(1))
    assert plan.kind == "scrounge"
    assert plan.nutrition < 30


def test_market_plan_only_on_market_days_and_with_coin():
    p = persona({"sociability": 0.95, "creativity": 0.1})
    plan = choose_meal(p, need(60), 5, 3, True, FixedRandom(0.0))
    assert plan.kind == "market"
    assert plan.target == "market_front"

    plan = choose_meal(p, need(60), 5, 3, False, FixedRandom(0.0))
    assert plan.kind != "market"


def test_every_meal_kind_has_a_plan():
    assert set(MEAL_KEYS) == {"cook", "buy", "market", "scrounge"}


def test_wages_fill_the_workers_purse(app):
    agent = app.agent_by_key["marrow"]
    before = agent.wallet
    app.gain("coin", 10.0, agent)
    assert agent.wallet == round(before + 6.0, 2)


def test_buying_a_meal_moves_coins_and_food(app):
    agent = app.agent_by_key["pip"]
    agent.wallet = 5.0
    app.stats["food"] = 5.0
    app.stats["coin"] = 7.0
    assert app.buy_meal(agent, "buy")
    assert agent.wallet == 3.0
    assert app.stats["coin"] == 9.0
    assert app.stats["food"] == 4.0

    agent.wallet = 0.0
    assert not app.buy_meal(agent, "buy")


def test_cooking_uses_food_and_restores_hunger_gradually(app):
    app.clock._sim = datetime(2026, 10, 29, 6, 35)
    agent = app.agent_by_key["pip"]
    agent.needs.hunger = 40.0
    agent.block = agent.intent = "meal"
    agent.path = []
    app.stats["food"] = 4.0
    agent.meal_plan = MealPlan("cook", agent.home_point, 0.0, 58.0)

    agent._arrived(app)
    assert agent.state == "cook"
    assert app.stats["food"] == 3.0
    assert agent.needs.hunger == 40.0

    for _ in range(200):
        agent.update(0.5, app)
        if agent.state == "meal":
            break
    assert agent.state == "meal"
    for _ in range(10):
        agent.update(1.0, app)
    assert 40.0 < agent.needs.hunger < 98.0

    for _ in range(200):
        agent.update(1.0, app)
        if agent.state != "meal":
            break
    assert agent.state != "meal"
    assert agent.needs.hunger >= 97.0


def test_buying_takes_time_before_the_meal_is_eaten(app):
    app.clock._sim = datetime(2026, 10, 29, 12, 10)
    agent = app.agent_by_key["orin"]
    agent.needs.hunger = 35.0
    agent.block = agent.intent = "meal"
    agent.path = []
    agent.wallet = 5.0
    app.stats["food"] = 5.0
    agent.meal_plan = MealPlan("buy", "tavern_door", TAVERN_MEAL_PRICE, 62.0)

    agent._arrived(app)
    assert agent.state == "buy"
    assert agent.needs.hunger == 35.0
    assert agent.wallet == 3.0

    for _ in range(300):
        agent.update(0.5, app)
        if agent.state not in ("buy", "meal"):
            break
    assert agent.needs.hunger > 90.0


def test_meal_intent_plans_and_eats_market_food(app, monkeypatch):
    app.clock._sim = datetime(2026, 11, 7, 12, 40)
    agent = app.agent_by_key["nettle"]
    agent.needs.hunger = 50.0
    agent.wallet = 5.0
    app.stats["food"] = 3.0
    monkeypatch.setattr(agent.rng, "random", lambda: 0.0)

    agent._choose_intent("meal", app)
    assert agent.state == "walk"
    assert agent.meal_plan.kind == "market"
    assert agent.meal_plan.target == "market_front"

    agent.path = []
    agent._arrived(app)
    assert agent.state == "buy"
    assert agent.wallet == 4.0
    assert app.stats["food"] == 2.0

    agent.block = "meal"
    for _ in range(400):
        agent.update(0.5, app)
        if agent.state not in ("buy", "meal"):
            break
    assert agent.needs.hunger > 90.0


def test_market_trade_moves_coins_between_purse_and_till(app, monkeypatch):
    app.clock._sim = datetime(2026, 11, 7, 10, 0)
    assert app.market_open()
    agent = app.agent_by_key["pip"]
    agent.wallet = 3.0
    app.stats["food"] = 4.0
    app.stats["coin"] = 6.0
    monkeypatch.setattr(agent.rng, "random", lambda: 0.0)
    assert app.market_trade(agent) == "buy"
    assert agent.wallet == 2.0
    assert app.stats["coin"] == 7.0
    assert app.stats["food"] == 3.0

    app.stats["food"] = 0.0
    agent.wallet = 0.0
    app.stats["coin"] = 5.0
    assert app.market_trade(agent) == "sell"
    assert agent.wallet == 1.0
    assert app.stats["coin"] == 4.0


def test_wallet_survives_a_snapshot_roundtrip(app):
    agent = app.agent_by_key["pip"]
    agent.wallet = 12.5
    saved = app.snapshot()
    agent.wallet = 1.0
    app._apply_save(saved)
    assert agent.wallet == 12.5

    old = app.snapshot()
    old["agents"]["pip"].pop("wallet")
    agent.wallet = 7.5
    app._apply_save(old)
    assert agent.wallet == 7.5
