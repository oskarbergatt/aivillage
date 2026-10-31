"""LLM-authored story developments persist and advance at day boundaries."""


def test_story_arc_uses_previous_development_and_survives_save(app, monkeypatch):
    app.llm.provider = "codex_cli"
    app.story_arc = {"day": "2026-10-28", "title": "The bridge", "summary": "A bridge needs repair.",
                     "open_question": "Who will help?"}
    jobs = []
    monkeypatch.setattr(app.llm, "submit", lambda *args, **kwargs: jobs.append((args, kwargs)))
    app._request_story_arc("2026-10-29", ["Bram visited the bridge"])
    assert len(jobs) == 1
    args, options = jobs[0]
    assert args[0] == "story" and "A bridge needs repair." in args[2]
    assert "Bram visited the bridge" in args[2] and options["use_cache"] is False
    args[3]({"title": "The bridge", "summary": "Bram asks neighbours for help.",
             "open_question": "Will the rain hold off?"}, "")
    assert app.story_arc["day"] == "2026-10-29"
    assert app._prompt_ctx(None)["story_arc"] == "Bram asks neighbours for help."
    saved = app.snapshot()
    app.story_arc = {}
    app._apply_save(saved)
    assert app.story_arc["open_question"] == "Will the rain hold off?"
    app._request_story_arc("2026-10-29", [])
    assert len(jobs) == 1


def test_story_errors_do_not_invent_fallback_or_overwrite_previous(app, monkeypatch):
    app.llm.provider = "codex_cli"
    app.story_arc = {"day": "old", "title": "Prior", "summary": "Existing"}
    callbacks = []
    monkeypatch.setattr(app.llm, "submit", lambda *args, **kwargs: callbacks.append(args[3]))
    app._request_story_arc("2026-10-29", [])
    callbacks[0](None, "network error")
    assert app.story_arc["title"] == "Prior" and not app._story_pending
    assert not any(e.get("kind") == "story" for e in app.chronicle)


def test_mock_provider_does_not_create_stories(app, monkeypatch):
    monkeypatch.setattr(app.llm, "submit", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    app._request_story_arc("2026-10-29", [])
    assert not app.story_arc


def test_stale_callback_cannot_overwrite_loaded_game(app, monkeypatch):
    app.llm.provider = "codex_cli"
    callbacks = []
    monkeypatch.setattr(app.llm, "submit", lambda *args, **kwargs: callbacks.append(args[3]))
    saved = app.snapshot()
    app._request_story_arc("2026-10-29", [])
    app._apply_save(saved)
    callbacks[0]({"title": "old", "summary": "stale"}, "")
    assert not app.story_arc
