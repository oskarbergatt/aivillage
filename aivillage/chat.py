"""Player chat state and orchestration for the village controller."""
from __future__ import annotations

from dataclasses import dataclass, field

from .agents.brain import Agent
from .llm import prompts


@dataclass
class ChatState:
    active: bool = False
    target: str | None = None
    input: str = ""
    lines: list[tuple[str, str]] = field(default_factory=list)
    pending: bool = False


class ChatMixin:
    """Chat-related controller methods; the host supplies services and agents."""

    def selected_agent(self) -> Agent | None:
        return self.selected if isinstance(self.selected, Agent) else None

    def open_chat(self, agent: Agent | None = None) -> None:
        agent = agent or self.selected_agent()
        if agent is None:
            return
        if not self.llm.available:
            self.toast(self.i18n.t("ui.no_llm"))
            return
        self.chat.active = True
        self.chat.target = agent.key
        self.chat.lines = [("you" if line.speaker == "you" else "them", line.text)
                           for line in agent.memory.thread_recent()]
        self.chat.input = ""
        self.chat.pending = False
        agent.path = []
        agent.state = "talk"
        agent.talk_timer = 600.0
        agent.say("", 600.0, pending=True)
        self.sfx.play("select")

    def close_chat(self) -> None:
        agent = self.agent_by_key.get(self.chat.target or "")
        if agent:
            agent.talk_timer = 0.0
            agent.bubble = None
            agent.state = "free"
            agent.action_timer = 2
        self.chat = ChatState()

    def submit_chat(self) -> None:
        text = self.chat.input.strip()
        agent = self.agent_by_key.get(self.chat.target or "")
        if not text or agent is None or self.chat.pending:
            return
        if not self.llm.available:
            self.toast(self.i18n.t("ui.no_llm"))
            return
        self.chat.input = ""
        self.chat.lines.append(("you", text))
        self.chat.pending = True
        agent.say("", 600.0, pending=True)
        ctx = self._prompt_ctx(agent)
        key = agent.key
        message = text

        def done(data: dict | None, error: str) -> None:
            if self.chat.target == key:
                self.chat.pending = False
            if error or not data:
                if self.chat.target == key and self.chat.active:
                    self.toast(self.i18n.t("ui.no_reply"))
                return
            line = str(data.get("line") or data.get("reply") or "").strip()
            if not line:
                if self.chat.target == key and self.chat.active:
                    self.toast(self.i18n.t("ui.no_reply"))
                return
            agent.say(line, 9.0)
            agent.state = "talk"
            agent.talk_timer = 600.0
            agent.memory.add(f"You said: {message[:90]}", self.clock.date_text(),
                             "chat")
            agent.memory.add(f"You answered: {line[:120]}", self.clock.date_text(),
                             "chat")
            agent.memory.add_thread("you", message, self.clock.date_text())
            agent.memory.add_thread("them", line, self.clock.date_text())
            if self.chat.target == key:
                self.chat.lines.append(("them", line))
                if len(self.chat.lines) > 60:
                    self.chat.lines = self.chat.lines[-60:]
            self.voice.speak(line, key, self.i18n.language)

        self.llm.submit("chat", prompts.chat_system(agent.persona, self.i18n.language),
                        prompts.chat_user(agent.persona, message, ctx), done,
                        max_tokens=220, temperature=0.95)
