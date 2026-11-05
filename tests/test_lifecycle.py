from __future__ import annotations

import logging


def test_shutdown_continues_after_service_failures(app, monkeypatch, caplog):
    stopped = []

    def failing(name):
        def stop():
            stopped.append(name)
            raise RuntimeError(name)
        return stop

    with monkeypatch.context() as patch:
        patch.setattr(app, "autosave", failing("autosave"))
        patch.setattr(app.news, "stop", failing("news"))
        patch.setattr(app.alerts, "stop", failing("alerts"))
        patch.setattr(app.weather_service, "stop", failing("weather"))
        patch.setattr(app, "_close_social_tracks", failing("social_tracks"))
        patch.setattr(app.voice, "shutdown", lambda: stopped.append("voice"))
        patch.setattr(app.llm, "stop", lambda: stopped.append("llm"))
        patch.setattr("aivillage.app_loop.pygame.quit", lambda: stopped.append("pygame"))

        with caplog.at_level(logging.ERROR, logger="aivillage.lifecycle"):
            app.shutdown()

    assert stopped == ["autosave", "news", "alerts", "weather", "social_tracks",
                       "voice", "llm", "pygame"]
    failed_services = {getattr(record, "service", "") for record in caplog.records}
    assert {"autosave", "news", "alerts", "weather", "social_tracks"} <= failed_services


def test_llm_stop_waits_for_all_workers(app):
    workers = [app.llm._worker, *app.llm._ambient_workers]
    assert all(worker is not None and worker.is_alive() for worker in workers)

    app.llm.stop()

    assert all(not worker.is_alive() for worker in workers if worker is not None)
