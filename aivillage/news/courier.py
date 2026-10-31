"""Queue official alerts for delivery by a village traveller."""
from __future__ import annotations

import time
from datetime import datetime

from ..agents.visitor import Visitor


class AlertCourierMixin:
    """Controller methods that bridge the alert service and visitor system."""

    def _check_alerts(self) -> None:
        while True:
            alert = self.alerts.poll()
            if alert is None:
                break
            self._alert_queue.append(alert)
        if (not self._alert_queue or time.monotonic() < self._alert_retry_at
                or self.visitor_pending or self._active_visitor()
                or not self.llm.available or self.llm.provider == "mock"):
            return
        alert = self._alert_queue.pop(0)
        if alert.expires:
            try:
                if datetime.fromisoformat(alert.expires.replace("Z", "+00:00")).timestamp() < time.time():
                    return
            except ValueError:
                pass
        self.visitor_pending = True

        def done(dispatch):
            self.visitor_pending = False
            if dispatch is None:
                self._alert_queue.append(alert)
                self._alert_retry_at = time.monotonic() + 60
                return
            self._admit_visitor(Visitor(self.rng, self.world, dispatch))

        if not self.news.request_alert(alert, self.i18n.language, done):
            self.visitor_pending = False
            self._alert_queue.insert(0, alert)
