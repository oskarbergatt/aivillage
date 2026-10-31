"""Villager threads are recorded on delivery and survive save/load."""
import time


def test_pair_thread_persists_and_reaches_next_prompt(app, monkeypatch):
    a, b = app.agent_by_key["pip"], app.agent_by_key["orin"]
    a.begin_talk(b, 30)
    b.begin_talk(a, 30)
    app.script = [(a, "The bridge needs repair.", time.time() - 1)]
    app._tick_script()
    assert b.memory.social_prompt(a.key) == ["pip: The bridge needs repair."]
    snapshot = app.snapshot()
    a.memory.social_threads.clear()
    b.memory.social_threads.clear()
    app._apply_save(snapshot)
    assert a.memory.social_prompt(b.key) == ["pip: The bridge needs repair."]
    from aivillage.llm.prompts import exchange_user
    history = [f"{app.agent_by_key[line.speaker].name}: {line.text}"
               for line in a.memory.social_threads[b.key]]
    assert "The bridge needs repair" in exchange_user(a.persona, b.persona, {"social_history": history})


def test_group_lines_reach_every_pair_and_can_be_disabled(app):
    members = app.agents[:3]
    for i, agent in enumerate(members):
        agent.begin_talk(members[(i + 1) % len(members)], 30)
    app.script = [(members[0], "A shared thought", time.time() - 1)]
    app._tick_script()
    for member in members:
        for other in members:
            if member is not other:
                assert member.memory.social_prompt(other.key) == [f"{members[0].key}: A shared thought"]
    app.config.set("social.threads", False)
    app.script = [(members[1], "Not remembered", time.time() - 1)]
    app._tick_script()
    assert "Not remembered" not in str(members[0].memory.social_threads)


def test_scheduler_uses_saved_thread_in_next_request(app, monkeypatch):
    a, b = app.agent_by_key["pip"], app.agent_by_key["orin"]
    a.memory.add_social_thread(b.key, a.key, "The bridge needs repair.", "yesterday")
    app.agents = [a, b]
    for agent in app.agents:
        agent.block = agent.state = "free"
        agent.path = []
        agent.bubble = None
        agent.talk_timer = 0
    a.x, a.y = b.x, b.y
    app.social_timer = 0
    prompts = []
    monkeypatch.setattr(app.llm, "submit", lambda kind, system, user, callback, **kw: prompts.append(user))
    app._maybe_social(1)
    assert len(prompts) == 1 and "The bridge needs repair." in prompts[0]
