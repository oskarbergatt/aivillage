"""Visible free-time behavior, schedule boundaries and offline voice."""
from datetime import datetime
from types import SimpleNamespace
import threading
import time

from aivillage.agents.roster import ROSTER
from aivillage.llm import prompts
from aivillage.voice.tts import VoiceService, _voice_lang


def test_scattered_destination_stays_on_scattered_tile(app, monkeypatch):
    agent = app.agent_by_key["pip"]
    monkeypatch.setattr(agent.rng, "randint", lambda a, b: 1)
    assert agent.go_to_point("plaza", jitter=1)
    assert agent.path[-1] == app.world.tile_center(32, 23)
    assert agent.path[-1] != app.world.points["plaza"]


def test_unreachable_walkable_goal_reports_failure(app, monkeypatch):
    agent = app.agent_by_key["pip"]
    monkeypatch.setattr(agent, "go_to_tile", lambda *args, **kwargs: False)
    assert not agent.go_to_point("plaza")


def test_self_changes_do_not_mutate_founder_roster(app):
    founder = next(persona for persona in ROSTER if persona.key == "pip")
    original_job = founder.job
    agent = app.agent_by_key["pip"]
    assert agent.set_job("miller")
    assert founder.job == original_job == "farmer"


def test_free_time_villager_moves_again_without_waiting_many_minutes(app, monkeypatch):
    app.clock._sim = datetime(2026, 10, 29, 17, 30)
    agent = app.agent_by_key["pip"]
    agent.intent = agent.block = "free"
    agent.path = []
    agent._arrived(app)
    assert 20 <= agent.action_timer <= 50
    moves = []
    monkeypatch.setattr(agent, "_new_wander_target", lambda ctx: moves.append(True))
    agent.update(51, app)
    assert moves


def test_outdoor_worker_goes_to_shelter_in_rain(app, monkeypatch):
    agent = app.agent_by_key["pip"]
    app.weather.condition = "rain"
    targets = []
    monkeypatch.setattr(agent, "go_to_point", lambda name, jitter=0: targets.append(name) or True)
    agent._choose_intent("work", app)
    assert targets == ["tavern_door"]
    assert agent.intent == "break"


def test_work_actions_change_without_extra_resource_yields(app):
    agent = app.agent_by_key["pip"]
    agent._pick_task()
    old_task = agent.task_name
    agent.task_time = 200
    agent.work_activity_timer = 1
    before = dict(app.stats)
    agent._work(2, app)
    assert agent.task_name != old_task
    assert agent.task_progress == 2
    assert app.stats == before


def test_ambient_talk_yields_to_work_schedule(app, monkeypatch):
    agent, other = app.agent_by_key["pip"], app.agent_by_key["orin"]
    app.clock._sim = datetime(2026, 10, 29, 10, 0)
    app.weather = app.weather_service.state
    agent.begin_talk(other, 100)
    monkeypatch.setattr(agent, "go_to_point", lambda *args, **kwargs: True)
    agent.update(0.1, app)
    assert agent.partner is None
    assert agent.block == "work"
    assert agent.intent == "work"


def test_spoken_conversation_is_remembered_and_offered_to_model(app):
    first, second = app.agent_by_key["pip"], app.agent_by_key["orin"]
    first.begin_talk(second, 20)
    second.begin_talk(first, 20)
    app.script = [(first, "The turnips are ready.", time.time() - 1)]
    app._tick_script()
    assert first.memory.entries[-1].dispatch_id == second.key
    assert second.memory.entries[-1].dispatch_id == first.key
    saved = app.snapshot()
    first.memory.entries.clear()
    app._apply_save(saved)
    remembered = first.memory.recent(1, "social")
    assert "turnips" in remembered[0]
    prompt = prompts.exchange_user(first.persona, second.persona, {"social_history": remembered})
    assert "turnips" in prompt


def test_late_group_reply_does_not_pull_workers_back_into_conversation(app, monkeypatch):
    members = app.agents[:3]
    pending = []
    monkeypatch.setattr(app.llm, "submit",
                        lambda kind, system, user, callback, **kw: pending.append(callback))
    app._start_group(members)
    members[0].state = "work"
    members[0].partner = None
    pending[0]({"lines": [{"speaker": members[0].name, "text": "Hello"}]}, "")
    assert members[0].state == "work"
    assert not app.script
    assert not app.ambient_pending


def test_voice_selection_handles_windows_language_codes(config):
    voice = VoiceService(config, SimpleNamespace(language="de"))
    german = SimpleNamespace(id="de", name="German Voice", languages=[b"\x05\x07\x04"])
    english = SimpleNamespace(id="en", name="English Voice", languages=[b"\x05\x09\x04"])
    unknown = SimpleNamespace(id="other", name="Other", languages=[])
    assert _voice_lang(german) == "de"
    assert _voice_lang(english) == "en"
    assert _voice_lang(unknown) == "unknown"
    voice._voices = [english, german]
    assert voice._pick_voice("david", "de") == "de"
    assert voice._pick_voice("", "en") == "en"


def test_all_villagers_have_voice_profiles_and_ambient_setting(app):
    assert all(agent.key in app.voice.profiles for agent in app.agents)
    assert len(app.voice.profiles) == len(ROSTER)
    app._action("settings")
    app._draw(0.016)
    assert "toggle:voice.speak_ambient" in app.ui.hits
    previous = app.voice.speak_ambient
    app._action("toggle:voice.speak_ambient")
    assert app.voice.speak_ambient is not previous


def test_sapi_worker_speaks_multiple_ambient_villagers(config, monkeypatch):
    import ctypes
    import sys

    spoken = []
    finished = threading.Event()
    calls = []
    voice = SimpleNamespace(id="german", name="German Voice", languages=["de-DE"])

    class Engine:
        def getProperty(self, name):
            return [voice]
        def setProperty(self, name, value):
            calls.append((name, value))
        def say(self, text):
            spoken.append(text)
        def runAndWait(self):
            if len(spoken) == 2:
                finished.set()
        def stop(self):
            pass

    class Ole:
        def CoInitializeEx(self, *args):
            return 0
        def CoUninitialize(self):
            pass

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(ole32=Ole()), raising=False)
    monkeypatch.setitem(sys.modules, "pyttsx3", SimpleNamespace(engine=SimpleNamespace(Engine=lambda **kwargs: Engine())))
    config.set("voice.enabled", True)
    config.set("voice.speak_ambient", True)
    profiles = {p.key: p.voice for p in ROSTER}
    service = VoiceService(config, SimpleNamespace(language="de"), profiles)
    try:
        service.speak("Erster Satz", "pip", ambient=True)
        service.speak("Zweiter Satz", "marrow", ambient=True)
        assert finished.wait(3), service.status
        assert spoken == ["Erster Satz", "Zweiter Satz"]
        assert ("voice", "german") in calls
        assert sum(1 for key, _ in calls if key == "rate") == 2
    finally:
        service.shutdown()
        if service._thread:
            service._thread.join(3)
