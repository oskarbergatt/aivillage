"""LLM-authored village story continuity, advanced at most once per day."""
from __future__ import annotations


def story_prompts(language: str, day: str, events: list[str], previous: dict) -> tuple[str, str]:
    language = "German" if language == "de" else "English"
    system = ("You are a village chronicler. Create or continue one plausible multi-day village "
              f"story, grounded in the supplied events. Write in {language}. Do not invent "
              "dialogue or claim real-world news happened in the village. Return JSON only.")
    history = "\n".join(f"- {str(event)[:200]}" for event in events[-12:]) or "- no recorded events"
    user = (f"Day: {day}\nRecorded village events:\n{history}\n"
            f"Previous story title: {previous.get('title', '')}\n"
            f"Previous development: {previous.get('summary', '')}\n"
            "Continue the previous story when possible; otherwise start a new one. "
            'Return JSON: {"title":"short title", "summary":"one or two short sentences", '
            '"open_question":"what could happen next"}.')
    return system, user


class StoryArcsMixin:
    def _request_story_arc(self, day: str, events: list[str]) -> None:
        if (not self.config.get("social.story_arcs", True) or not self.llm.available
                or self.llm.provider in ("mock", "none") or self._story_pending
                or day == self.story_arc.get("day")):
            return
        self._story_pending = day
        generation = self._story_generation
        system, user = story_prompts(self.i18n.language, day, events, self.story_arc)

        def done(data, error):
            if generation != self._story_generation:
                return
            self._story_pending = ""
            if day != self.current_day_key or error or not isinstance(data, dict):
                return
            fields = {key: " ".join(str(data.get(key, "") or "").split())[:limit]
                      for key, limit in (("title", 100), ("summary", 320), ("open_question", 180))}
            if not fields["title"] or not fields["summary"]:
                return
            self.story_arc = {"day": day, **fields}
            self.add_chronicle(f"{fields['title']}: {fields['summary']}", "story")

        self.llm.submit("story", system, user, done, max_tokens=260, temperature=0.8,
                        use_cache=False)
