"""Ambient speech stays in order and does not outrun the visible dialogue."""
from types import SimpleNamespace
import threading
import time

from aivillage.agents.roster import ROSTER
from aivillage.voice.tts import VoiceService


def test_ambient_lines_wait_for_previous_speech(app, monkeypatch):
    a, b = app.agent_by_key["pip"], app.agent_by_key["orin"]
    a.begin_talk(b, 20)
    b.begin_talk(a, 20)
    app.voice.speak_ambient = True
    busy = [False]
    heard = []
    monkeypatch.setattr(app.voice, "is_busy", lambda: busy[0])
    def speak(text, key, *args, **kwargs):
        heard.append((key, text))
        busy[0] = True
    monkeypatch.setattr(app.voice, "speak", speak)
    app.script = [(a, "First line", time.time() - 1),
                  (b, "Second line", time.time() - 1)]
    app._tick_script()
    assert heard == [(a.key, "First line")]
    app._tick_script()
    assert len(heard) == 1 and len(app.script) == 1
    busy[0] = False
    app._tick_script()
    assert heard == [(a.key, "First line"), (b.key, "Second line")]


def test_waiting_for_audio_keeps_the_next_speaker_available(app, monkeypatch):
    a, b = app.agent_by_key["pip"], app.agent_by_key["orin"]
    a.begin_talk(b, 0.1)
    b.begin_talk(a, 0.1)
    app.script = [(b, "Next line", time.time() - 1)]
    app.voice.speak_ambient = True
    monkeypatch.setattr(app.voice, "is_busy", lambda: True)
    app._hold_social_speech(0.2)
    assert a.talk_timer > 0.2 and b.talk_timer > 0.2


def test_active_speaker_bubble_stays_visible_during_audio(app, monkeypatch):
    a, b = app.agent_by_key["pip"], app.agent_by_key["orin"]
    a.begin_talk(b, 10)
    a.say("A long sentence", 0.01)
    monkeypatch.setattr(app.voice, "is_speaking", lambda key: key == a.key)
    app._hold_social_speech(0.2)
    assert a.bubble.timer > 0.2


def test_last_speaker_is_held_but_schedule_still_takes_priority(app, monkeypatch):
    a, b = app.agent_by_key["pip"], app.agent_by_key["orin"]
    a.begin_talk(b, 0.1)
    a.say("Last line", 0.1)
    monkeypatch.setattr(app.voice, "is_speaking", lambda key: key == a.key)
    monkeypatch.setattr(a, "_scheduled_block", lambda clock: "sleep")
    app._hold_social_speech(0.2)
    assert a.talk_timer > 0.2
    a.update(0.2, app)
    assert a.state != "talk" and not a.partner


def test_muted_ambient_dialogue_does_not_wait_for_audio(app, monkeypatch):
    a, b = app.agent_by_key["pip"], app.agent_by_key["orin"]
    a.begin_talk(b, 20)
    app.voice.speak_ambient = False
    monkeypatch.setattr(app.voice, "is_busy", lambda: True)
    app.script = [(a, "A line", time.time() - 1)]
    app._tick_script()
    assert not app.script and a.bubble.text == "A line"


def test_next_answer_is_prepared_in_the_final_second(app, monkeypatch):
    a, b = app.agent_by_key["pip"], app.agent_by_key["orin"]
    a.begin_talk(b, 20)
    b.begin_talk(a, 20)
    app.voice.speak_ambient = True
    state = {"busy": True, "remaining": 2.0}
    heard = []
    monkeypatch.setattr(app.voice, "is_busy", lambda: state["busy"])
    monkeypatch.setattr(app.voice, "ending_within",
                        lambda seconds=1.0: state["remaining"] <= seconds)
    monkeypatch.setattr(app.voice, "speak",
                        lambda text, key, *args, **kwargs: heard.append((key, text)))
    app.script = [(b, "Second line", time.time() - 1)]

    app._tick_script()
    assert heard == [] and len(app.script) == 1
    state["remaining"] = 0.9
    app._tick_script()
    assert heard == [(b.key, "Second line")] and not app.script
    app._tick_script()
    assert heard == [(b.key, "Second line")]  # one request per turn


def test_voice_reports_the_last_second_before_speech_ends(config):
    config.set("voice.enabled", True)
    service = VoiceService(config, SimpleNamespace(language="de"))
    service._speaking_started = time.monotonic() - 2.0
    service._speaking_seconds = 2.75
    assert service.ending_within(1.0)
    service._speaking_seconds = 4.0
    assert not service.ending_within(1.0)
    service._speaking_seconds = 2.75
    service.muted = True
    assert not service.ending_within(1.0)
    assert (service._estimate_seconds("one two three four", 120)
            > service._estimate_seconds("one two three four", 240))


def test_voice_queue_tracks_each_speaker_until_playback_finishes(config, monkeypatch):
    import ctypes
    import sys

    first_started = threading.Event()
    release_first = threading.Event()
    both_played = threading.Event()
    spoken = []
    engines = []
    voice = SimpleNamespace(id="de", name="German", languages=["de-DE"])

    class Engine:
        def __init__(self):
            engines.append(self)
        def getProperty(self, name):
            return [voice]
        def setProperty(self, *args):
            pass
        def say(self, text):
            spoken.append(text)
        def runAndWait(self):
            if len(spoken) == 1:
                first_started.set()
                assert release_first.wait(3)
            else:
                both_played.set()
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
    service = VoiceService(config, SimpleNamespace(language="de"), {p.key: p.voice for p in ROSTER})
    try:
        service.speak("Erster Satz", "pip", ambient=True)
        assert first_started.wait(3)
        assert service.is_busy() and service.is_speaking("pip")
        service.speak("Zweiter Satz", "marrow", ambient=True)
        release_first.set()
        assert both_played.wait(3)
    finally:
        release_first.set()
        service.shutdown()
        if service._thread:
            service._thread.join(3)
    assert spoken == ["Erster Satz", "Zweiter Satz"]
    assert len(engines) == 2 and engines[0] is not engines[1]
    assert not service.is_busy()


def test_stalled_voice_does_not_hold_conversations_forever(config):
    config.set("voice.enabled", True)
    service = VoiceService(config, SimpleNamespace(language="de"))
    service._pending = 1
    service._pending_since = time.monotonic() - 100
    assert not service.is_busy()
    assert service.status == "voice playback stalled"


def test_driver_callback_errors_are_visible(config, monkeypatch):
    import ctypes
    import sys
    completed = threading.Event()

    class Engine:
        def getProperty(self, name):
            return []
        def connect(self, name, callback):
            self.on_error = callback
        def setProperty(self, *args):
            pass
        def say(self, text):
            pass
        def runAndWait(self):
            self.on_error(None, RuntimeError("device unavailable"))
            completed.set()
        def stop(self):
            pass

    ole = SimpleNamespace(CoInitializeEx=lambda *args: 0, CoUninitialize=lambda: None)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(ole32=ole), raising=False)
    monkeypatch.setitem(sys.modules, "pyttsx3", SimpleNamespace(engine=SimpleNamespace(Engine=lambda **kwargs: Engine())))
    config.set("voice.enabled", True)
    service = VoiceService(config, SimpleNamespace(language="de"))
    try:
        service.speak("Hallo", "pip", ambient=True)
        assert completed.wait(3)
    finally:
        service.shutdown()
        if service._thread:
            service._thread.join(3)
    assert "device unavailable" in service.label()
    assert not service.ok
