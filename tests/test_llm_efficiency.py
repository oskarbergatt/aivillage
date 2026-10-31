"""Tests for bounded response caching and automatic-dialogue backoff."""
from aivillage.llm.client import Job
import threading


def test_cache_uses_generation_settings_and_bounded_lru(app, monkeypatch):
    client = app.llm
    client.config.set("llm.cache_entries", 2)
    calls = []
    monkeypatch.setattr(client, "_call", lambda job: calls.append(job.user) or '{"line":"ok"}')
    first = Job("chat", "system", "first", max_tokens=100, temperature=0.5)
    second = Job("chat", "system", "second", max_tokens=100, temperature=0.5)
    third = Job("chat", "system", "third", max_tokens=100, temperature=0.5)
    client._execute(first)
    client._execute(second)
    client._execute(first)  # touch first, making second the least recent
    client._execute(third)
    client._execute(second)
    assert calls == ["first", "second", "third", "second"]
    assert len(client._cache) == 2
    changed = Job("chat", "system", "first", max_tokens=200, temperature=0.5)
    assert client._cache_key(changed) != client._cache_key(first)
    assert client._cache_key(Job("group", "system", "first", max_tokens=100,
                                 temperature=0.5)) != client._cache_key(first)


def test_invalid_response_not_cached_and_cache_can_be_disabled(app, monkeypatch):
    client = app.llm
    calls = []
    monkeypatch.setattr(client, "_call", lambda job: calls.append(job.user) or "not json")
    job = Job("chat", "system", "question")
    assert client._execute(job) == {"line": "not json"}
    client._execute(job)
    assert len(calls) == 2
    monkeypatch.setattr(client, "_call", lambda job: calls.append(job.user) or '{}')
    client._execute(job)
    client._execute(job)
    assert len(calls) == 4
    client.config.set("llm.cache_entries", 0)
    monkeypatch.setattr(client, "_call", lambda job: calls.append(job.user) or '{"line":"ok"}')
    client._execute(job)
    client._execute(job)
    assert len(calls) == 6
    assert not client._cache


def test_group_failures_back_off_and_success_resets(app, monkeypatch):
    app.config.set("social.failure_backoff_s", 10)
    app.config.set("social.failure_backoff_max_s", 25)
    members = app.agents[:3]
    monkeypatch.setattr(app.llm, "submit",
                        lambda kind, system, user, callback, **kw: callback(None, "failed"))
    for expected in (10, 20, 25):
        app._start_group(members)
        assert app.social_timer == expected
        assert not app.ambient_pending
    monkeypatch.setattr(app.llm, "submit", lambda kind, system, user, callback, **kw:
                        callback({"lines": [{"speaker": members[0].name, "text": "Hi"}]}, ""))
    app._start_group(members)
    assert app._social_failures == 0


def test_self_direction_backoff_does_not_block_manual_requests(app, monkeypatch):
    app.config.set("llm.self_interval_s", 10)
    app.config.set("llm.self_failure_backoff_max_s", 30)
    monkeypatch.setattr(app.llm, "submit",
                        lambda kind, system, user, callback, **kw: callback(None, "failed"))
    agent = app.agent_by_key["pip"]
    assert app.request_self(agent, automatic=True)
    assert app._self_timer == 20
    assert app.request_self(agent, automatic=True)
    assert app._self_timer == 30
    assert app.request_self(agent)
    assert app._self_failures == 2
    monkeypatch.setattr(app.llm, "submit", lambda kind, system, user, callback, **kw:
                        callback({"ambition": "Grow a better garden"}, ""))
    assert app.request_self(agent, automatic=True)
    assert app._self_failures == 0


def test_ambient_worker_is_not_blocked_by_slow_foreground(app, monkeypatch):
    client = app.llm
    entered = threading.Event()
    release = threading.Event()
    ambient_done = threading.Event()
    called_back = []

    def fake_call(job):
        if job.kind == "self":
            entered.set()
            assert release.wait(3)
        else:
            assert job.model == "small-model"
            ambient_done.set()
        return '{"line":"hello"}'

    client.config.set("llm.ambient_model", "small-model")
    monkeypatch.setattr(client, "_call", fake_call)
    try:
        client.submit("self", "system", "foreground", lambda data, error: called_back.append("self"))
        assert entered.wait(3)
        client.submit("exchange", "system", "ambient", lambda data, error: called_back.append("ambient"))
        assert ambient_done.wait(3), "ambient request was blocked behind foreground work"
        assert not called_back  # callbacks are still delivered only by poll()
    finally:
        release.set()
