"""Offline Windows speech, on a dedicated worker thread.

pyttsx3/SAPI5 is not thread-safe and blocks while speaking, so every utterance
goes through a queue owned by one thread. Failure is always non-fatal: the
village simply becomes silent.
"""
from __future__ import annotations

import queue
import threading

from ..agents.persona import Voice as VoiceProfile

FALLBACK_VOICE_HINTS = {
    "en": ("zira", "david", "mark", "hazel", "george", "susan"),
    "de": ("hedda", "katja", "conrad", "stefan", "sabina", "georg"),
}


def _voice_lang(voice) -> str:
    try:
        langs = getattr(voice, "languages", None) or []
    except Exception:
        langs = []
    for lang in langs:
        try:
            text = lang.decode("ascii", "ignore") if isinstance(lang, (bytes, bytearray)) \
                else str(lang)
        except Exception:
            text = ""
        low = text.lower()
        if "de" in low:
            return "de"
        if "en" in low:
            return "en"
    name = f"{getattr(voice, 'id', '')} {getattr(voice, 'name', '')}".lower()
    if any(k in name for k in ("german", "deutsch", "hedda", "katja", "conrad")):
        return "de"
    return "en"


class VoiceService:
    def __init__(self, config, i18n, profiles: dict[str, VoiceProfile] | None = None):
        self.config = config
        self.i18n = i18n
        self.profiles = profiles or {}
        self.enabled = bool(config.get("voice.enabled", True))
        self.speak_ambient = bool(config.get("voice.speak_ambient", False))
        self.volume = float(config.get("voice.volume", 0.85))
        self.rate_scale = float(config.get("voice.rate_scale", 1.0))

        self.muted = False
        self.ok = False
        self.status = "voice idle"
        self.voice_count = 0
        self._q: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._voices = None

    # -- lifecycle -------------------------------------------------------
    def ensure(self) -> None:
        if not self.enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True, name="tts")
        self._thread.start()

    def shutdown(self) -> None:
        self._stop.set()
        self._q.put(None)

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        if self.muted:
            self._drain()
        return self.muted

    def _drain(self) -> None:
        while True:
            try:
                self._q.get_nowait()
            except queue.Empty:
                break

    # -- speaking --------------------------------------------------------
    def profile_for(self, key: str) -> tuple[int, float, str]:
        p = self.profiles.get(key)
        if p is None:
            return 175, 0.9, ""
        return p.rate, p.volume, p.hint

    def speak(self, text: str, key: str = "", lang: str | None = None,
              ambient: bool = False) -> None:
        if not self.enabled or self.muted:
            return
        if ambient and not self.speak_ambient:
            return
        text = " ".join(str(text or "").split())
        if len(text) < 2:
            return
        if len(text) > 420:
            text = text[:417].rsplit(" ", 1)[0] + "…"
        rate, volume, hint = self.profile_for(key)
        lang = lang or self.i18n.language
        self.ensure()
        self._q.put((text, max(80, int(rate * self.rate_scale)),
                     max(0.05, min(1.0, volume)), hint, lang))

    # -- worker ----------------------------------------------------------
    def _run(self) -> None:
        try:
            import pyttsx3
            engine = pyttsx3.init()
        except Exception as exc:
            self.ok = False
            self.status = f"voice unavailable ({str(exc)[:40]})"
            return
        try:
            self._voices = engine.getProperty("voices") or []
            self.voice_count = len(self._voices)
            self.ok = True
            self.status = f"{self.voice_count} voices"
        except Exception:
            self._voices = []
            self.ok = True
            self.status = "voice ready"

        while not self._stop.is_set():
            item = self._q.get()
            if item is None:
                break
            text, rate, volume, hint, lang = item
            try:
                engine.setProperty("rate", rate)
                engine.setProperty("volume", max(0.0, min(1.0, volume * self.volume)))
                vid = self._pick_voice(hint, lang)
                if vid:
                    engine.setProperty("voice", vid)
                engine.say(text)
                engine.runAndWait()
            except Exception as exc:
                # A dead SAPI voice should not take the village with it.
                self.status = f"voice error ({str(exc)[:40]})"
        try:
            engine.stop()
        except Exception:
            pass

    def _pick_voice(self, hint: str, lang: str) -> str | None:
        voices = self._voices or []
        if not voices:
            return None
        same_lang = [v for v in voices if _voice_lang(v) == lang]
        pool = same_lang or voices
        hint = (hint or "").lower()
        if hint:
            for v in pool:
                label = f"{getattr(v, 'id', '')} {getattr(v, 'name', '')}".lower()
                if hint in label:
                    return getattr(v, "id", None)
        for cand in FALLBACK_VOICE_HINTS.get(lang, ()):
            for v in pool:
                label = f"{getattr(v, 'id', '')} {getattr(v, 'name', '')}".lower()
                if cand in label:
                    return getattr(v, "id", None)
        return getattr(pool[0], "id", None)

    # -- status ----------------------------------------------------------
    def label(self) -> str:
        if not self.enabled:
            return "voice off"
        if self.muted:
            return "muted"
        if self._thread is None:
            return "voice idle"
        return self.status
