"""Integration checks for conversations, settings, slots and alert couriers."""
from aivillage.news.alerts import Alert
from aivillage.news.pipeline import Dispatch


def test_chat_history_survives_snapshot(app):
    agent = app.agent_by_key["pip"]
    agent.memory.add_thread("you", "Hello", "today")
    agent.memory.add_thread("them", "Good day", "today")
    snapshot = app.snapshot()
    agent.memory.thread.clear()
    app._apply_save(snapshot)
    assert agent.memory.thread_prompt() == ["you: Hello", "them: Good day"]
    assert app._prompt_ctx(agent)["thread"] == agent.memory.thread_prompt()
    app.open_chat(agent)
    assert app.chat.lines == [("you", "Hello"), ("them", "Good day")]


def test_group_conversation_maps_only_known_speakers(app, monkeypatch):
    members = app.agents[:3]
    def submit(kind, system, user, callback, **kwargs):
        assert kind == "group"
        callback({"lines": [{"speaker": members[0].name, "text": "Hello"},
                            {"speaker": "stranger", "text": "Ignored"}]}, "")
    monkeypatch.setattr(app.llm, "submit", submit)
    app._start_group(members)
    assert [(a.name, text) for a, text, _ in app.script] == [(members[0].name, "Hello")]
    assert not app.ambient_pending
    assert members[0].memory.about(members[1].key) > 0


def test_alert_waits_for_courier_and_bypasses_news_limit(app, monkeypatch):
    alert = Alert("test", "Storm", "High winds", "severe", "storm")
    app.alerts._new.append(alert)
    app.visitors_today = 99
    monkeypatch.setattr(app.llm, "provider", "openai")
    def request(alert, lang, callback):
        callback(Dispatch(headline="Storm warning", source="DWD"))
        return True
    monkeypatch.setattr(app.news, "request_alert", request)
    app._check_alerts()
    assert len(app.visitors) == 1
    assert app.visitors[0].dispatch.headline == "Storm warning"
    assert not app.visitor_pending


def test_settings_draw_and_slot_selection_do_not_change_autosave(app):
    app._action("settings")
    app._draw(0.016)
    assert "slot:2" in app.ui.hits and "load_slot" in app.ui.hits
    app._action("slot:2")
    assert app.selected_slot == 2 and app.save_slot == 1
    app._action("toggle:social.group_chats")
    assert not app.config.get("social.group_chats")
