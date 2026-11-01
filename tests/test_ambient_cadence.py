"""Automatic villager conversations should be brief and have quiet gaps."""
import time


def test_pair_exchange_is_short_slow_and_not_overlapped(app, monkeypatch):
    a, b = app.agents[:2]
    app.agents = [a, b]
    a.x, a.y = 100, 100
    b.x, b.y = 120, 100
    a.state = b.state = a.block = b.block = "free"
    a.path = b.path = []
    a.talk_timer = b.talk_timer = 0
    app.social_timer = 0
    jobs = []
    monkeypatch.setattr(app.llm, "submit", lambda *args, **kwargs: jobs.append(args[3]))

    app._maybe_social(0)
    assert len(jobs) == 1
    lines = [{"speaker": who, "text": f"A short thought from {who}."}
             for who in ("a", "b", "a", "b", "a", "b")]
    jobs[0]({"lines": lines}, "")
    assert len(app.script) == 4
    gaps = [app.script[i + 1][2] - app.script[i][2]
            for i in range(len(app.script) - 1)]
    assert all(gap >= 7 for gap in gaps)
    assert app.social_timer >= app._ambient_cooldown()

    app.social_timer = 0
    app._maybe_social(0)
    assert len(jobs) == 1  # no second request while the first exchange is playing


def test_group_exchange_is_bounded_and_uses_long_gaps(app, monkeypatch):
    members = app.agents[:3]
    callback = []
    monkeypatch.setattr(app.llm, "submit", lambda *args, **kwargs: callback.append(args[3]))
    app._start_group(members)
    callback[0]({"lines": [{"speaker": agent.name, "text": "A quiet village thought."}
                           for agent in members for _ in range(2)]}, "")
    assert len(app.script) == 5
    assert all(app.script[i + 1][2] - app.script[i][2] >= 7
               for i in range(len(app.script) - 1))
    assert app.social_timer >= app._ambient_cooldown()
