"""Independent conversations must not block each other's audio."""
import time
import threading


def test_two_conversations_progress_independently(app, monkeypatch):
    import aivillage.social_tracks as tracks

    class Voice:
        def __init__(self, config, i18n, profiles):
            self.enabled = True
            self.speak_ambient = True
            self.muted = False
            self.busy = False
            self.closed = False
            self.spoken = []
            self.status = "voice idle"
        def speak(self, text, key, *args, **kwargs):
            self.spoken.append((key, text))
            self.busy = True
        def is_busy(self):
            return self.busy and not self.muted
        def is_speaking(self, key):
            return self.is_busy() and self.spoken[-1][0] == key
        def shutdown(self):
            self.closed = True
        def toggle_mute(self):
            self.muted = not self.muted

    monkeypatch.setattr(tracks, "VoiceService", Voice)
    a, b, c, d = app.agents[:4]
    for x, y in ((a, b), (b, a), (c, d), (d, c)):
        x.begin_talk(y, 100)
    due = time.time() - 1
    primary_busy = [False]
    first_spoken = []
    monkeypatch.setattr(app.voice, "is_busy", lambda: primary_busy[0])
    def speak(text, key, *args, **kwargs):
        first_spoken.append((key, text))
        primary_busy[0] = True
    monkeypatch.setattr(app.voice, "speak", speak)
    app.voice.speak_ambient = True
    app._add_social_script([(a, "A1", due), (b, "B1", due)])
    app._add_social_script([(c, "C1", due), (d, "D1", due)])
    secondary = app._social_tracks[0][1]
    app._tick_script()
    assert first_spoken == [(a.key, "A1")]
    assert secondary.spoken == [(c.key, "C1")]
    app._tick_script()
    assert len(first_spoken) == len(secondary.spoken) == 1
    secondary.busy = False
    app._tick_script()
    assert secondary.spoken[-1] == (d.key, "D1")
    assert len(first_spoken) == 1
    secondary.busy = False
    app._tick_script()
    assert secondary.closed and not app._social_tracks
    primary_busy[0] = False
    app._tick_script()
    assert first_spoken[-1] == (b.key, "B1")


def test_secondary_tracks_close_and_clear_on_cleanup(app):
    from types import SimpleNamespace
    closed = []
    script = [(app.agents[0], "text", 0)]
    app._social_tracks.append((script, SimpleNamespace(shutdown=lambda: closed.append(True))))
    app._close_social_tracks()
    assert not script and not app._social_tracks and closed == [True]


def test_two_background_requests_can_run_at_once(app, monkeypatch):
    first = threading.Event()
    second = threading.Event()
    release = threading.Event()

    def call(job):
        (first if job.user == "one" else second).set()
        assert release.wait(3)
        return '{"lines": []}'

    monkeypatch.setattr(app.llm, "_call", call)
    try:
        app.llm.submit("exchange", "system", "one", use_cache=False)
        assert first.wait(3)
        app.llm.submit("exchange", "system", "two", use_cache=False)
        assert second.wait(3)
    finally:
        release.set()


def test_old_callback_cannot_change_new_day_conversations(app, monkeypatch):
    callbacks = []
    monkeypatch.setattr(app.llm, "submit", lambda kind, system, user, callback, **kw: callbacks.append(callback))
    members = app.agents[:2]
    app._start_group(members)
    app._social_generation += 1
    app.ambient_pending = 1
    callbacks[0]({"lines": [{"speaker": members[0].name, "text": "old"}]}, "")
    assert app.ambient_pending == 1
    assert not app.script and not app._social_tracks
