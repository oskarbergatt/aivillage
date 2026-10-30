"""Procedural sound effects — no audio files, everything is synthesised."""
from __future__ import annotations

import math
import random

import numpy as np
import pygame

SR = 22050


def _to_sound(samples: np.ndarray) -> pygame.mixer.Sound:
    samples = np.clip(samples, -1.0, 1.0)
    data = (samples * 32767).astype(np.int16)
    if data.ndim == 1:
        data = np.column_stack([data, data])
    return pygame.sndarray.make_sound(np.ascontiguousarray(data))


def _env(n: int, attack: float = 0.01, decay: float = 0.4) -> np.ndarray:
    a = max(1, int(SR * attack))
    d = max(1, int(SR * decay))
    env = np.ones(n)
    a = min(a, n)
    env[:a] = np.linspace(0, 1, a)
    tail = min(d, n)
    env[-tail:] *= np.linspace(1, 0, tail) ** 1.5
    return env


def tone(freq: float, dur: float, wave: str = "square", vol: float = 0.4,
         decay: float = 0.25, sweep: float = 0.0) -> np.ndarray:
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = freq + sweep * t
    phase = 2 * math.pi * np.cumsum(f) / SR
    if wave == "square":
        s = np.sign(np.sin(phase))
    elif wave == "saw":
        s = 2 * ((phase / (2 * math.pi)) % 1.0) - 1
    elif wave == "tri":
        s = 2 * np.abs(2 * ((phase / (2 * math.pi)) % 1.0) - 1) - 1
    else:
        s = np.sin(phase)
    return s * _env(n, decay=decay) * vol


def noise(dur: float, vol: float = 0.3, decay: float = 0.3, lowpass: int = 4) -> np.ndarray:
    n = int(SR * dur)
    rng = np.random.default_rng(7)
    raw = rng.uniform(-1, 1, n)
    if lowpass > 1:
        kernel = np.ones(lowpass) / lowpass
        raw = np.convolve(raw, kernel, mode="same")
    return raw * _env(n, attack=0.005, decay=decay) * vol


def bell(freq: float = 1180.0, dur: float = 1.1, vol: float = 0.35) -> np.ndarray:
    n = int(SR * dur)
    t = np.arange(n) / SR
    partials = [(1.0, 1.0), (2.02, 0.5), (3.01, 0.28), (4.16, 0.16), (5.43, 0.08)]
    s = np.zeros(n)
    for mult, amp in partials:
        s += amp * np.sin(2 * math.pi * freq * mult * t) * np.exp(-t * (2.2 + mult * 0.6))
    return s * vol


class Sfx:
    def __init__(self, enabled: bool = True, volume: float = 0.85):
        self.enabled = enabled
        self.volume = volume
        self.ok = pygame.mixer.get_init() is not None
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self._loops: dict[str, pygame.mixer.Sound] = {}
        if not self.ok or not enabled:
            return
        try:
            self._build()
        except Exception:
            self.ok = False

    def _build(self) -> None:
        self.sounds = {
            "click": _to_sound(tone(660, 0.05, "square", 0.20, 0.04)),
            "select": _to_sound(tone(520, 0.07, "tri", 0.22, 0.06, sweep=200)),
            "bell": _to_sound(bell()),
            "coin": _to_sound(np.concatenate([tone(880, 0.06, "square", 0.2, 0.05),
                                              tone(1320, 0.12, "square", 0.2, 0.1)])),
            "hammer": _to_sound(np.concatenate([noise(0.05, 0.35, 0.04, 2),
                                                tone(180, 0.09, "saw", 0.25, 0.08)])),
            "splash": _to_sound(noise(0.22, 0.28, 0.2, 6)),
            "step": _to_sound(noise(0.04, 0.10, 0.03, 3)),
            "chirp": _to_sound(tone(1800, 0.09, "sine", 0.16, 0.08, sweep=900)),
            "chop": _to_sound(np.concatenate([noise(0.06, 0.3, 0.05, 3),
                                              tone(120, 0.1, "tri", 0.2, 0.09)])),
            "rain": _to_sound(noise(1.8, 0.16, 1.8, 10)),
            "wind": _to_sound(noise(2.4, 0.12, 2.4, 24)),
            "error": _to_sound(tone(180, 0.18, "square", 0.22, 0.16)),
        }

    def play(self, name: str, volume: float | None = None) -> None:
        if not (self.ok and self.enabled):
            return
        snd = self.sounds.get(name)
        if snd:
            try:
                snd.set_volume(self.volume if volume is None else volume)
                snd.play()
            except Exception:
                pass

    def start_loop(self, name: str) -> None:
        if not (self.ok and self.enabled):
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        try:
            snd.set_volume(self.volume * 0.6)
            snd.play(loops=-1)
        except Exception:
            pass

    def stop_loops(self) -> None:
        if not self.ok:
            return
        try:
            pygame.mixer.stop()
        except Exception:
            pass

    def chime(self) -> None:
        self.play("bell")
