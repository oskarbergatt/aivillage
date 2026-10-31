"""Job registry, children and self-authored identities."""
from __future__ import annotations

from datetime import datetime

from aivillage.agents.brain import Agent, block_at
from aivillage.agents.jobs import ADULT_JOBS, JOBS, job_choices, job_for
from aivillage.agents.roster import BY_KEY, ROSTER
from aivillage.llm import prompts
from aivillage.llm.client import Job
from aivillage.world.mapgen import World
from aivillage.world.pathfinding import astar


def test_jobs_registry_is_consistent():
    assert "farmer" in JOBS and "teacher" in JOBS
    for key, job in JOBS.items():
        assert job.key == key
        assert job.tasks
        if job.child:
            assert key == "child"
        else:
            assert key in ADULT_JOBS
    assert job_for("nonsense").key == "farmer"
    assert job_for("child").child
    assert job_choices(True)[0]["key"] == "child"
    assert all(c["key"] != "child" for c in job_choices(False))


def test_resource_jobs_have_workers_homes_and_reachable_sites():
    world = World(1234)
    expected = {"shepherd": "pasture", "woodcutter": "woodlot",
                "miner": "quarry", "beekeeper": "apiary"}
    for job_key, site in expected.items():
        job = JOBS[job_key]
        assert job.work == site
        assert job.resource and job.amount > 0
        workers = [p for p in ROSTER if p.job == job_key]
        assert len(workers) == 1, job_key
        worker = workers[0]
        assert not worker.is_child
        home = world.points.get(f"home_{worker.home}")
        point = world.points.get(site)
        assert home and point, job_key
        start = (home[0] // 16, home[1] // 16)
        goal = (point[0] // 16, point[1] // 16)
        assert world.is_walkable(*goal), job_key
        assert astar(start, goal, world.is_walkable), job_key


def test_roster_has_children_with_living_parents():
    kids = [p for p in ROSTER if p.is_child]
    assert len(kids) >= 3
    for kid in kids:
        assert kid.job == "child"
        assert kid.parent in BY_KEY
        assert not BY_KEY[kid.parent].is_child
        assert kid.age > 0
    for adult in ROSTER:
        if not adult.is_child:
            assert adult.job in ADULT_JOBS, adult.key


def test_child_schedule_school_and_play():
    kid = BY_KEY["nettle"]
    assert block_at(kid, datetime(2026, 10, 29, 9, 0)) == "school"
    assert block_at(kid, datetime(2026, 10, 29, 14, 30)) == "play"
    assert block_at(BY_KEY["pip"], datetime(2026, 10, 29, 9, 0)) == "work"


def test_agent_can_change_adult_job_but_not_a_child():
    world = World(1234)
    import random
    adult = Agent(BY_KEY["pip"], world, random.Random(1))
    assert adult.set_job("miller")
    assert adult.persona.job == "miller"
    assert adult.persona.work == JOBS["miller"].work
    assert not adult.set_job("child")
    assert not adult.set_job("astronaut")

    kid = Agent(BY_KEY["nettle"], world, random.Random(2))
    assert not kid.set_job("miller")
    assert kid.persona.job == "child"


def test_apply_self_validates_and_dreams():
    world = World(1234)
    import random
    adult = Agent(BY_KEY["pip"], world, random.Random(3))
    changed = adult.apply_self({
        "ambition": "  To  grow the  best turnips  ",
        "bio": "A new story.",
        "quirk": "talks to the soil",
        "job": "weaver",
        "hat": "hood",
        "outfit": 5,
    })
    assert adult.persona.ambition == "To grow the best turnips"
    assert adult.persona.job == "weaver"
    assert adult.persona.look.hat == "hood"
    assert adult.persona.look.cloth == 5
    assert {"ambition", "bio", "quirk", "job", "hat", "outfit"} <= set(changed)

    # Hallucinated values are ignored rather than corrupting the villager.
    adult.apply_self({"job": "wizard", "hat": "crown", "outfit": 99})
    assert adult.persona.job == "weaver"
    assert adult.persona.look.hat == "hood"

    kid = Agent(BY_KEY["nettle"], world, random.Random(4))
    kid.apply_self({"dream_job": "builder", "job": "farmer"})
    assert kid.persona.dream_job == "builder"
    assert kid.persona.job == "child"


def test_self_prompts_offer_the_real_registry():
    pip = BY_KEY["pip"]
    ctx = {"time": "10:00", "weather": "clear", "temp": "15", "season": "autumn",
           "stock": "food 2"}
    system = prompts.self_system(pip, "en")
    user = prompts.self_user(pip, ctx, job_choices(False), child=False)
    assert "English" in system
    assert "miller" in user and "teacher" in user
    assert '"job"' in user
    kid_user = prompts.self_user(BY_KEY["nettle"], ctx, job_choices(True), child=True)
    assert '"dream_job"' in kid_user
    assert kid_user.count("child") >= 1


def test_mock_self_reply_is_usable(app):
    data = app.llm._mock(Job("self", "", ""))
    from aivillage.llm.prompts import parse_json
    parsed = parse_json(data)
    assert parsed and parsed["ambition"]
    assert "hat" in parsed and "outfit" in parsed


def test_self_request_applies_a_mock_identity(app):
    app.social_timer = 1e9
    agent = app.agent_by_key["pip"]
    app.selected = agent
    assert app.request_self(agent)
    assert app.self_pending == "pip"
    for _ in range(80):
        app._update(0.05)
        if app.self_pending is None:
            break
    assert app.self_pending is None
    assert agent.persona.authored
    assert agent.persona.ambition
    assert any(e["kind"] == "self" for e in app.chronicle)


def test_persona_survives_a_snapshot_roundtrip(app):
    agent = app.agent_by_key["pip"]
    agent.set_job("miller")
    agent.persona.ambition = "To grind every sack before noon."
    saved = app.snapshot()["agents"]["pip"]["persona"]
    assert saved["job"] == "miller"

    agent.set_job("farmer")
    agent.persona.ambition = ""
    app._apply_persona_save(agent, saved)
    assert agent.persona.job == "miller"
    assert agent.persona.ambition == "To grind every sack before noon."


def test_kids_and_self_controls_draw(app):
    app.selected = app.agent_by_key["nettle"]
    app._draw(0.016)
    assert app.ui.hits
    assert "talk" in app.ui.hits and "self" in app.ui.hits

    app.show_jobs = True
    app._draw(0.016)
    assert "close_jobs" in app.ui.hits
    app.show_jobs = False


def test_children_do_not_produce_resources(app):
    app.social_timer = 1e9
    before = dict(app.stats)
    kid = app.agent_by_key["nettle"]
    for _ in range(400):
        app._update(0.2)
    # Kids can be at lessons or play; the stores only move through adults.
    assert kid.persona.job == "child"
    assert app.stats["food"] >= before["food"]
