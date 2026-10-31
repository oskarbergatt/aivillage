"""Prompt construction. Persona first, world state second, strict JSON out."""
from __future__ import annotations

import json

from ..agents.persona import Persona

LANG_NAME = {"en": "English", "de": "German"}

STYLE = (
    "You are a villager in a small pixel village. Speak naturally, in character, "
    "in 1-2 short sentences (max 240 characters). Never mention AI, models, prompts, "
    "or the modern world unless the news you are retelling requires it. No stage "
    "directions, no markdown, no quotation marks around the whole reply."
)

RETOLD = (
    "You retell real-world news as village gossip from a pre-industrial world. "
    "Keep the spirit and the subject of the headline, but translate it into the "
    "village's frame of reference (councils, harvests, ships, distant cities, "
    "workshops). Never invent a different event; never change who did what."
)


def lang(language: str) -> str:
    return LANG_NAME.get(language, "English")


def persona_card(p: Persona, language: str) -> str:
    traits = ", ".join(f"{k}={v:.2f}" for k, v in p.traits.items())
    if p.is_child:
        role = f"a child of {p.age}" if p.age else "a child"
    else:
        role = f"the village {p.job}"
    ambition = f" Your ambition: {p.ambition}." if p.ambition else ""
    return (
        f"You are {p.name}, {role}. "
        f"Personality: {traits}. "
        f"Background: {p.bio} "
        f"Quirk: {p.quirk}.{ambition} "
        f"Always answer in {lang(language)}."
    )


def self_system(p: Persona, language: str) -> str:
    if p.is_child:
        role = (f"You are {p.name}, a {p.age}-year-old child in a small pixel "
                "village. You may choose what you dream of becoming, and sharpen "
                "who you are.")
    else:
        role = (f"You are {p.name}, the village {p.job}. You may choose a new "
                "trade and reshape your own life.")
    return (
        f"{role} Decide for yourself, not for the player. Write in "
        f"{lang(language)}. Keep to the offered trades; give a one-sentence "
        "ambition, a short bio and quirk, and a hat and outfit you would "
        "actually choose. Never mention AI or the modern world. Return JSON only."
    )


def self_user(p: Persona, ctx: dict, choices: list[dict],
              child: bool = False) -> str:
    options = ", ".join(c["key"] for c in choices)
    field = "dream_job" if child else "job"
    return (
        f"{world_line(ctx)}\n"
        f"Your current background: {p.bio}\n"
        f"Your quirk: {p.quirk}\n"
        f"Your ambition so far: {p.ambition or 'none yet'}\n"
        f"Offered trades: {options}\n"
        'Return JSON only: {"ambition": "one sentence", "bio": "2 short sentences", '
        '"quirk": "one small habit", '
        f'"{field}": "one of the offered keys", '
        '"hat": "" or "straw" or "cap" or "hood", "outfit": 0-7}'
    )


def world_line(ctx: dict) -> str:
    return (
        f"Village time: {ctx.get('time', '')}. Weather: {ctx.get('weather', '')}, "
        f"{ctx.get('temp', '')}C. Season: {ctx.get('season', '')}. "
        f"Village stores: {ctx.get('stock', '')}."
    )


def chat_system(p: Persona, language: str) -> str:
    return f"{persona_card(p, language)} {STYLE}"


def chat_user(p: Persona, message: str, ctx: dict) -> str:
    memories = "; ".join(ctx.get("memories", [])[-5:]) or "nothing notable yet"
    neighbours = ctx.get("relations", "")
    thread = ctx.get("thread", []) or []
    history = "\n".join(f"- {line}" for line in thread[-8:]) or "- this is the first time you speak"
    return (
        f"{world_line(ctx)}\n"
        f"Your recent memories: {memories}\n"
        f"Your conversation so far:\n{history}\n"
        f"How you feel right now: {ctx.get('mood', 'steady')}. "
        f"You are currently {ctx.get('activity', 'standing around')}.\n"
        f"{neighbours}\n"
        f"The traveller/player says to you: \"{message}\"\n"
        "Reply in character, and remember what was said earlier. Return JSON only: "
        '{"line": "...", "emotion": "one of: cheerful|calm|gruff|sad|curious|angry|wistful"}'
    )


def exchange_system(language: str) -> str:
    return (
        "You write short, natural village conversations between two characters. "
        f"Write in {lang(language)}. 3 to 6 lines total, each 1-2 short sentences. "
        "Characters interrupt, misunderstand, tease and drift off topic like real people. "
        "Never mention AI or the modern world."
    )


def exchange_user(a: Persona, b: Persona, ctx: dict, topic: str = "") -> str:
    return (
        f"{world_line(ctx)}\n"
        f"Character A: {a.name}, the {a.job}. {a.bio} Quirk: {a.quirk} "
        f"Mood: {ctx.get('mood_a', 'steady')}. Currently: {ctx.get('activity_a', 'idle')}.\n"
        f"Character B: {b.name}, the {b.job}. {b.bio} Quirk: {b.quirk} "
        f"Mood: {ctx.get('mood_b', 'steady')}. Currently: {ctx.get('activity_b', 'idle')}.\n"
        f"They feel about each other: {ctx.get('relation', 'acquainted')}.\n"
        f"Things they recently said: {'; '.join(ctx.get('social_history', [])[-4:]) or 'nothing yet'}.\n"
        f"Shared news on their minds: {topic or 'nothing in particular'}.\n"
        'Return JSON only: {"lines": [{"speaker": "a", "text": "..."}, '
        '{"speaker": "b", "text": "..."}]}'
    )


def group_system(language: str) -> str:
    return (
        "You write a short, lively village conversation between three or four "
        f"characters gathered in the square. Write in {lang(language)}. 4 to 8 lines "
        "total, each 1-2 short sentences. They interrupt, joke, disagree and drift "
        "off topic. Never mention AI or the modern world."
    )


def group_user(members: list[Persona], ctx: dict, topic: str = "",
               moods: dict[str, str] | None = None) -> str:
    moods = moods or {}
    card = "\n".join(
        f"- {p.name}, the {p.job}: {p.bio} Quirk: {p.quirk} "
        f"Mood: {moods.get(p.key, 'steady')}."
        for p in members
    )
    names = ", ".join(p.name for p in members)
    return (
        f"{world_line(ctx)}\n"
        f"Gathered here: {names}.\n{card}\n"
        f"What is on their minds: {topic or 'the day, the weather, the village'}.\n"
        'Return JSON only: {"lines": [{"speaker": "exact name", "text": "..."}]}'
    )


def alert_system(language: str) -> str:
    return (
        "You are a courier carrying an official weather warning into a small "
        "pre-industrial village. Keep the real hazard, severity and timing, but "
        "translate the wording into the village's frame of reference (roofs, boats, "
        f"livestock, the harvest, the road). Write in {lang(language)}, under 200 "
        "characters, urgent but not sensational. No modern agencies or technology."
    )


def alert_user(headline: str, description: str, instruction: str,
               severity: str, language: str) -> str:
    return (
        f"Official warning: {headline}\n"
        f"Severity: {severity}\n"
        f"Details: {description[:600]}\n"
        f"Advice: {instruction[:300]}\n"
        'Return JSON only: {"headline": "the courier\'s warning", '
        '"tone": "bad", "topic": "weather"}'
    )


def dispatch_system(language: str) -> str:
    return (
        f"{RETOLD} Write in {lang(language)}. "
        "Keep it under 200 characters. Add no commentary."
    )


def dispatch_user(title: str, summary: str, source: str, language: str) -> str:
    return (
        f"Real headline: {title}\n"
        f"Real summary: {summary[:500]}\n"
        f"Source: {source}\n"
        'Return JSON only: {"headline": "the village version", '
        '"tone": "good|bad|strange|neutral", '
        '"topic": "harvest|weather|trade|discovery|politics|festival|people|sport"}'
    )


def rumour_system(language: str) -> str:
    return (
        "You are a traveller arriving in a village with no news of the wider world. "
        "Invent a small, plausible rumour, omen or observation from the road: weather, "
        "a strange animal, a broken bridge, a rumour about a distant town. "
        f"Write in {lang(language)} under 200 characters. No modern technology."
    )


def rumour_user(visitor_name: str, trade: str, origin: str, ctx: dict) -> str:
    return (
        f"You are {visitor_name}, a {trade} from {origin}. "
        f"{world_line(ctx)}\n"
        'Return JSON only: {"headline": "...", "tone": "good|bad|strange|neutral", '
        '"topic": "weather|trade|people|discovery"}'
    )


def chronicle_system(language: str) -> str:
    return (
        "You keep the village diary. Write 2-3 sentences, warm and specific, in "
        f"{lang(language)}. Mention real villagers by name and what actually happened. "
        "No bullet points, no headings."
    )


def chronicle_user(day: str, events: list[str], ctx: dict) -> str:
    body = "\n".join(f"- {e}" for e in events[-18:]) or "- a quiet day"
    return (f"Date: {day}. Weather: {ctx.get('weather', '')}.\n"
            f"Events today:\n{body}\n"
            'Return JSON only: {"diary": "..."}')


def parse_json(text: str) -> dict | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(cleaned[start:end + 1])
        return data if isinstance(data, dict) else None
    except Exception:
        return None
