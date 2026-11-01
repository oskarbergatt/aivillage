"""End-to-end behaviour of the running village (headless)."""
from __future__ import annotations

import time
from datetime import datetime

import pygame
import pytest

from aivillage.agents.visitor import Dispatch, Visitor
from aivillage.render.camera import Camera
from aivillage.reality.weather import WeatherState
from aivillage.save import load_village, save_village


def pump(app, seconds: float, step: float = 0.1, sleep: float = 0.0) -> None:
    frames = max(1, int(seconds / step))
    for _ in range(frames):
        app._update(step)
        if sleep:
            time.sleep(sleep)


def test_villagers_work_and_produce(app):
    app.social_timer = 1e9
    before = dict(app.stats)
    pump(app, 900, step=0.2)
    assert app.stats["food"] > before["food"], app.stats
    assert app.stats["coin"] > before["coin"], app.stats
    for agent in app.agents:
        assert 0 <= agent.x < app.world.W * 16
        assert 0 <= agent.y < app.world.H * 16
        tx, ty = agent.tile()
        assert app.world.is_walkable(tx, ty), (agent.name, tx, ty, agent.state)


def test_agents_leave_home_and_follow_the_schedule(app):
    app.social_timer = 1e9
    pump(app, 60, step=0.2)
    pip = app.agent_by_key["pip"]
    assert pip.block in ("work", "meal", "free")
    assert pip.state in ("work", "walk", "meal", "free", "idle")


def test_builder_advances_the_town_hall(app):
    app.social_timer = 1e9
    before = app.world.build_site.progress
    pump(app, 1200, step=0.2)
    assert app.world.build_site.progress > before


def test_news_traveller_arrives_and_speaks(app):
    app.social_timer = 1e9
    dispatch = Dispatch(headline="A cart of salt arrived from the coast.",
                        tone="good", topic="trade",
                        original="Salt shipment reaches port", source="Test Feed",
                        item_id="test-item", day="30 Oct")
    visitor = Visitor(app.rng, app.world, dispatch)
    app._admit_visitor(visitor)
    assert visitor in app.visitors
    pump(app, 120, step=0.2)
    assert app.dispatch_card is visitor
    assert visitor.state in ("speaking", "visiting")
    assert visitor.bubble_text
    assert any(e["kind"] == "news" for e in app.chronicle)
    assert app.visitors_today == 1


def test_chat_gets_a_model_reply(app):
    app.social_timer = 1e9
    agent = app.agent_by_key["pip"]
    app.selected = agent
    app.open_chat()
    assert app.chat.active and app.chat.target == "pip"
    app.chat.input = "How are the turnips?"
    app.submit_chat()
    assert app.chat.pending
    pump(app, 2.0, step=0.05, sleep=0.01)
    assert not app.chat.pending
    assert app.chat.lines and app.chat.lines[-1][0] == "them"
    assert app.chat.lines[-1][1]
    assert agent.bubble is not None
    assert agent.memory.recent(2, "chat")
    app.close_chat()
    assert not app.chat.active


def test_chat_keyboard_typing_and_enter(app):
    app.social_timer = 1e9
    app.selected = app.agent_by_key["orin"]
    app.open_chat()
    for ch in "hi":
        app._key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_h,
                                    unicode=ch, mod=0))
    assert app.chat.input == "hi"
    app._key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE,
                                unicode="", mod=0))
    assert app.chat.input == "h"
    app.chat.input = "hello"
    app._key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN,
                                unicode="\r", mod=0))
    pump(app, 2.0, step=0.05, sleep=0.01)
    assert app.chat.lines[-1][0] == "them"
    app._key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE,
                                unicode="", mod=0))
    assert not app.chat.active


def test_language_switch_is_live(app):
    assert app.i18n.language == "en"
    app._action("lang")
    assert app.i18n.language == "de"
    app._draw(0.016)
    app.show_chronicle = True
    app._draw(0.016)
    app._action("lang")
    assert app.i18n.language == "en"


def test_clock_controls(app):
    start = app.clock.now
    app._action("speed:4")
    assert app.clock.sim_speed == 4 and not app.clock.live
    app._update(1.0)
    moved = (app.clock.now - start).total_seconds()
    assert moved >= 3.9
    app._action("pause")
    assert app.clock.paused
    frozen = app.clock.now
    app._update(5.0)
    assert app.clock.now == frozen
    app._action("pause")
    app._action("live")
    assert app.clock.is_live


def test_picking_a_villager_by_click(app):
    agent = app.agent_by_key["sable"]
    px, py = app.camera.world_to_screen(agent.x, agent.y - 8)
    picked = app._pick((px, py))
    assert picked is agent


def test_camera_zoom_and_pan(app):
    cam = app.camera
    z = cam.zoom
    cam.zoom_at(400, 300, 1)
    assert cam.zoom > z
    cam.zoom_at(400, 300, -1)
    assert cam.zoom == z
    x = cam.x
    cam.pan_screen(100, 0)
    assert cam.x != x
    cam.nudge(10_000, 10_000)
    assert 0 <= cam.x <= app.world.W * 16
    assert 0 <= cam.y <= app.world.H * 16


def test_day_and_night_render_differently(app):
    day = pygame.Surface((640, 400))
    night = pygame.Surface((640, 400))
    app.renderer.draw(day, app.clock, app.weather, app.agents, [], None, 0.016,
                      night_override=False)
    app.renderer.draw(night, app.clock, app.weather, app.agents, [], None, 0.016,
                      night_override=True)

    def mean_luma(surf):
        total = 0
        count = 0
        for x in range(0, surf.get_width(), 13):
            for y in range(0, surf.get_height(), 13):
                r, g, b = surf.get_at((x, y))[:3]
                total += r * 0.3 + g * 0.59 + b * 0.11
                count += 1
        return total / count

    assert mean_luma(night) < mean_luma(day) * 0.85


def test_hud_buttons_are_clickable(app):
    app._draw(0.016)
    hits = app.ui.hits
    for action in ("pause", "live", "lang", "mute", "chronicle", "save",
                   "visitor"):
        assert action in hits, action
        assert hits[action].w > 0


def test_secret_dev_mode_pins_resources_and_refills_needs(app):
    from types import SimpleNamespace

    assert not app.dev_mode
    app._key(SimpleNamespace(key=pygame.K_F9,
                             mod=pygame.KMOD_RCTRL | pygame.KMOD_RSHIFT,
                             unicode="",))
    assert app.dev_mode
    assert all(app.stats[key] == 999_999
               for key in ("wood", "stone", "food", "coin"))

    app.stats["wood"] = 0
    app._update(0.0)
    assert app.stats["wood"] == 999_999

    agent = app.agents[0]
    agent.needs.hunger = agent.needs.energy = 1.0
    app._key(SimpleNamespace(key=pygame.K_F5, mod=0, unicode=""))
    assert agent.needs.hunger == agent.needs.energy == 100.0

    app._key(SimpleNamespace(key=pygame.K_F9,
                             mod=pygame.KMOD_LCTRL | pygame.KMOD_LSHIFT,
                             unicode="",))
    assert not app.dev_mode
    app.stats["wood"] = 3
    app._update(0.0)
    assert app.stats["wood"] == 3


def test_chronicle_and_toasts_draw(app):
    app.add_chronicle("The well was repaired by Bram.", "build")
    app.toast("A test toast")
    app.show_chronicle = True
    app._draw(0.016)
    app.show_chronicle = False
    app._draw(0.016)


def test_help_window_toggles_and_draws(app):
    app._draw(0.016)
    assert "help" in app.ui.hits
    app._key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1,
                                unicode="", mod=0))
    assert app.show_help
    app._draw(0.016)
    assert "close_help" in app.ui.hits
    assert "help" not in app.ui.hits
    app._key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE,
                                unicode="", mod=0))
    assert not app.show_help
    app._action("help")
    assert app.show_help
    app._action("close_help")
    assert not app.show_help


def test_help_text_explains_update_and_work_times(app):
    for lang in ("en", "de"):
        app.i18n.set_language(lang)
        assert "0.4.16" in app.i18n.t("help.update_title")
        assert app.i18n.t("help.update_body") != "help.update_body"
        assert "07:30" in app.i18n.t("help.work_day")
        assert "19:00" in app.i18n.t("help.work_night")
        for key in ("help.controls_pan", "help.work_kid", "help.work_market",
                    "help.work_note"):
            assert app.i18n.t(key) != key
    app.i18n.set_language("en")


def test_save_and_load_roundtrip(app, tmp_path):
    app.add_chronicle("A remembered day", "event")
    data = app.snapshot()
    path = tmp_path / "village.json"
    assert save_village(data, path)
    loaded = load_village(path)
    assert loaded is not None
    assert loaded["seed"] == data["seed"]
    assert loaded["day_number"] == data["day_number"]
    assert loaded["chronicle"][-1]["text"] == "A remembered day"
    path.write_text("{not json", encoding="utf-8")
    assert load_village(path) is None


def test_new_game_snapshot_has_all_villagers(app):
    from aivillage.agents.roster import ROSTER
    data = app.snapshot()
    assert set(data["agents"]) == {a.key for a in app.agents}
    assert len(data["agents"]) == len(ROSTER)
    assert "plots" in data and data["plots"]
