"""Automatic villager conversations should be brief and have quiet gaps."""
import time


def test_pair_exchange_is_slow_and_allows_three_lanes(app, monkeypatch):
    pairs = [app.agents[i:i + 2] for i in (0, 2, 4)]
    app.agents = [agent for pair in pairs for agent in pair]
    for pair_index, pair in enumerate(pairs):
        for index, agent in enumerate(pair):
            agent.x, agent.y = 100 + pair_index * 150 + index * 12, 100
            agent.state = agent.block = "free"
            agent.path = []
            agent.bubble = None
            agent.talk_timer = 0
    a, b = pairs[0]
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

    for expected_jobs in (2, 3):
        app.social_timer = 0
        app._maybe_social(0)
        assert len(jobs) == expected_jobs
    app.social_timer = 0
    app._maybe_social(0)
    assert len(jobs) == 3  # cap active + pending ambient lanes at three


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
