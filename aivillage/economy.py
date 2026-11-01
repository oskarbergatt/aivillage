"""Small village economy: meal choices, prices and wages.

The simulation owns the decisions here.  Villagers weigh their purse, the
village pantry and their own traits before deciding whether to cook, buy a
meal or trade at the Saturday market.  Keeping the arithmetic in one module
makes those choices testable without spinning up a whole village.
"""
from __future__ import annotations

from dataclasses import dataclass

TAVERN_MEAL_PRICE = 2.0
MARKET_MEAL_PRICE = 1.0
MARKET_TRADE_PRICE = 1.0
WAGE_SHARE = 0.6

NUTRITION = {
    "cook": 58.0,
    "buy": 62.0,
    "market": 48.0,
    "scrounge": 22.0,
}

MEAL_KEYS = tuple(NUTRITION)


@dataclass(frozen=True)
class MealPlan:
    kind: str
    target: str
    price: float
    nutrition: float


def home_point(persona) -> str:
    return f"home_{persona.home}"


def choose_meal(persona, needs, wallet: float, pantry: float,
                market_open: bool, rng) -> MealPlan:
    """Pick a meal the villager can actually afford and prepare."""
    traits = persona.traits
    home = home_point(persona)
    can_cook = pantry >= 1.0
    can_buy = wallet >= TAVERN_MEAL_PRICE
    can_market = (market_open and pantry >= 1.0
                  and wallet >= MARKET_MEAL_PRICE)

    # A market day is a social occasion, but hunger still comes first.
    if can_market and needs.hunger >= 30:
        sociability = traits.get("sociability", 0.5)
        if rng.random() < 0.12 + sociability * 0.28:
            return MealPlan("market", "market_front", MARKET_MEAL_PRICE,
                            NUTRITION["market"])

    if needs.hunger < 30:
        if can_buy:
            return MealPlan("buy", "tavern_door", TAVERN_MEAL_PRICE,
                            NUTRITION["buy"])
        if can_cook:
            return MealPlan("cook", home, 0.0, NUTRITION["cook"])
        return MealPlan("scrounge", home, 0.0, NUTRITION["scrounge"])

    if can_cook and not can_buy:
        return MealPlan("cook", home, 0.0, NUTRITION["cook"])
    if can_buy and not can_cook:
        return MealPlan("buy", "tavern_door", TAVERN_MEAL_PRICE,
                        NUTRITION["buy"])

    if can_cook:
        # Creative villagers experiment in their own kitchens; sociable ones
        # prefer the tavern table.
        cook_chance = (0.45 + traits.get("creativity", 0.5) * 0.25
                       - traits.get("sociability", 0.5) * 0.20)
        if not can_buy or rng.random() < cook_chance:
            return MealPlan("cook", home, 0.0, NUTRITION["cook"])
        return MealPlan("buy", "tavern_door", TAVERN_MEAL_PRICE,
                        NUTRITION["buy"])

    if can_buy:
        return MealPlan("buy", "tavern_door", TAVERN_MEAL_PRICE,
                        NUTRITION["buy"])
    return MealPlan("scrounge", home, 0.0, NUTRITION["scrounge"])
