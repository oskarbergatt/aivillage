"""Offline Windows speech, on a dedicated worker thread.

pyttsx3/SAPI5 is not thread-safe and blocks while speaking, so every utterance
goes through a queue owned by one thread. Failure is always non-fatal: the
village simply becomes silent.
"""
from __future__ import annotations

import queue
import re
import sys
import threading
import time

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
            if isinstance(lang, bytes) and len(lang) >= 2:
                # SAPI commonly returns a length byte followed by a little-endian LCID.
                lcid = int.from_bytes(lang[-2:], "little")
                primary = lcid & 0x3ff
                if primary == 7:
                    return "de"
                if primary == 9:
                    return "en"
            text = lang.decode("ascii", "ignore") if isinstance(lang, (bytes, bytearray)) \
                else str(lang)
        except Exception:
            text = ""
        low = text.lower()
        if re.search(r"(?:^|[^a-z])de(?:[^a-z]|$)", low):
            return "de"
        if re.search(r"(?:^|[^a-z])en(?:[^a-z]|$)", low):
            return "en"
    name = f"{getattr(voice, 'id', '')} {getattr(voice, 'name', '')}".lower()
    if (re.search(r"(?:^|[^a-z])de[-_]de(?:[^a-z]|$)", name) or
            any(k in name for k in ("german", "deutsch", "hedda", "katja", "conrad"))):
        return "de"
    if (re.search(r"(?:^|[^a-z])en[-_](?:us|gb)(?:[^a-z]|$)", name) or
            any(k in name for k in ("english", "zira", "david", "mark", "hazel", "george", "susan"))):
        return "en"
    return "unknown"


class VoiceService:
    def __init__(self, config, i18n, profiles: dict[str, VoiceProfile] | None = None):
        self.config = config
        self.i18n = i18n
        self.profiles = profiles or {}
        self.enabled = bool(config.get("voice.enabled", True))
        self.speak_ambient = bool(config.get("voice.speak_ambient", True))
        self.volume = float(config.get("voice.volume", 0.85))
        self.rate_scale = float(config.get("voice.rate_scale", 1.0))

        self.muted = False
        self.ok = False
        self.status = "voice idle"
        self.voice_count = 0
        self._q: queue.Queue = queue.Queue()
        self._queue_lock = threading.RLock()
        self._pending = 0
        self._pending_since = 0.0
        self._speaking_key: str | None = None
        self._speaking_started = 0.0
        self._speaking_seconds = 0.0
        self._stalled = False
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._voices = None
        self._retry_after = 0.0
        self._speech_errors = 0

    # -- lifecycle -------------------------------------------------------
    def ensure(self) -> bool:
        if not self.enabled or self._stop.is_set():
            return False
        if self._stalled:
            return False
        if sys.platform != "win32":
            self.status = "SAPI voice requires Windows"
            return False
        if self._thread is not None and self._thread.is_alive():
            return True
        if time.monotonic() < self._retry_after:
            return False
        self._thread = threading.Thread(target=self._run, daemon=True, name="tts")
        self._thread.start()
        return True

    def shutdown(self) -> None:
        self._stop.set()
        self._q.put(None)

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        if self.muted:
            self._drain()
        return self.muted

    def _drain(self) -> None:
        with self._queue_lock:
            while True:
                try:
                    item = self._q.get_nowait()
                except queue.Empty:
                    break
                if item is None:
                    if self._stop.is_set():
                        self._q.put(None)
                    break
                self._pending = max(0, self._pending - 1)
            if not self._pending:
                self._pending_since = 0.0

    def is_busy(self) -> bool:
        """Whether audible speech is queued or being played."""
        with self._queue_lock:
            if not self.enabled or self.muted or self._stalled:
                return False
            timeout = max(15.0, float(self.config.get("voice.playback_timeout_s", 90)))
            if self._pending and time.monotonic() - self._pending_since > timeout:
                self._stalled = True
                self.status = "voice playback stalled"
                self._drain()
                return False
            return self._pending > 0

    def is_speaking(self, key: str) -> bool:
        with self._queue_lock:
            return (self.enabled and not self.muted and not self._stalled
                    and self._speaking_key == key)

    @staticmethod
    def _estimate_seconds(text: str, rate: int) -> float:
        """Rough spoken length, used to prepare the next turn just in time."""
        words = max(1, len(text.split()))
        return max(0.8, words * 60.0 / max(90.0, float(rate)))

    def ending_within(self, seconds: float = 1.0) -> bool:
        """Whether the current utterance should end within *seconds*."""
        with self._queue_lock:
            if (not self.enabled or self.muted or self._stalled
                    or not self._speaking_started):
                return False
            elapsed = time.monotonic() - self._speaking_started
            return elapsed >= self._speaking_seconds - max(0.0, seconds)

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
        if not self.ensure():
            return
        with self._queue_lock:
            # The worker may fail while ensure() is starting it. In that case
            # do not leave an orphaned item that would block future dialogue.
            if self._stop.is_set() or time.monotonic() < self._retry_after:
                return
            if self._stalled:
                return
            if not self._pending:
                self._pending_since = time.monotonic()
            self._pending += 1
            self._q.put((text, max(80, int(rate * self.rate_scale)),
                         max(0.05, min(1.0, volume)), hint, lang, key))

    # -- worker ----------------------------------------------------------
    def _run(self) -> None:
        com_initialized = False
        try:
            import ctypes
            # SAPI's COM objects are created and used on this worker thread.
            result = ctypes.windll.ole32.CoInitializeEx(None, 2)
            com_initialized = result in (0, 1)
            import pyttsx3
            engine = pyttsx3.engine.Engine(driverName="sapi5")
        except Exception as exc:
            self.ok = False
            self.status = f"voice unavailable ({str(exc)[:40]})"
            with self._queue_lock:
                self._retry_after = time.monotonic() + 30.0
                self._drain()
            if com_initialized:
                ctypes.windll.ole32.CoUninitialize()
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

        def on_error(name, exception):
            # pyttsx3 can report driver errors through callbacks instead of
            # raising from runAndWait; surface those failures in settings.
            self._speech_errors += 1
            self.ok = False
            self.status = f"voice error ({str(exception)[:40]})"

        first = True
        while not self._stop.is_set():
            item = self._q.get()
            if item is None:
                break
            text, rate, volume, hint, lang, key = item
            with self._queue_lock:
                self._speaking_key = key
                self._pending_since = time.monotonic()
            previous_errors = self._speech_errors
            try:
                # Reusing the SAPI5 engine after runAndWait can cause the
                # next utterance to finish immediately with completed=False.
                # A fresh engine per utterance avoids the stale driver state.
                if not first:
                    engine = pyttsx3.engine.Engine(driverName="sapi5")
                first = False
                if hasattr(engine, "connect"):
                    try:
                        engine.connect("error", on_error)
                    except Exception:
                        pass
                engine.setProperty("rate", rate)
                engine.setProperty("volume", max(0.0, min(1.0, volume * self.volume)))
                vid = self._pick_voice(hint, lang)
                if vid:
                    engine.setProperty("voice", vid)
                engine.say(text)
                with self._queue_lock:
                    self._speaking_started = time.monotonic()
                    self._speaking_seconds = self._estimate_seconds(text, rate)
                engine.runAndWait()
                if self._speech_errors == previous_errors:
                    self.ok = True
                    self.status = f"{self.voice_count} voices"
            except Exception as exc:
                # A dead SAPI voice should not take the village with it.
                self.ok = False
                self.status = f"voice error ({str(exc)[:40]})"
            finally:
                with self._queue_lock:
                    self._pending = max(0, self._pending - 1)
                    self._speaking_key = None
                    self._speaking_started = 0.0
                    self._speaking_seconds = 0.0
                    self._pending_since = time.monotonic() if self._pending else 0.0
                    if self._stalled:
                        self._stalled = False
                        self.status = f"{self.voice_count} voices"
        try:
            engine.stop()
        except Exception:
            pass
        if com_initialized:
            ctypes.windll.ole32.CoUninitialize()

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
