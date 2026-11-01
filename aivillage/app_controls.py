"""Extracted methods for VillageApp."""
from __future__ import annotations

from .app_shared import (
    load_slot,
    math,
    pygame,
    slot_path,
)
from .app_dev import handle_dev_key

from . import app as _public_module


class VillageControlsMixin:
    def _action(self, action: str) -> None:
        if self._gateway_action(action):
            return
        if self._ambient_model_action(action):
            return
        t = self.i18n.t
        if action == "pause":
            self.clock.toggle_pause()
            self.sfx.play("click")
        elif action.startswith("speed:"):
            self.clock.set_speed(int(action.split(":")[1]))
            self.sfx.play("click")
        elif action == "live":
            self.clock.return_to_live()
            self.sfx.play("click")
        elif action == "mute":
            muted = self.voice.toggle_mute()
            self.toast(t("ui.mute") if muted else t("ui.unmute"))
        elif action == "lang":
            lang = self.i18n.toggle()
            self.config.set("general.language", lang)
            self.toast(t("ui.language") + ": " + lang.upper())
        elif action == "chronicle":
            self.show_chronicle = not self.show_chronicle
            self.ui.chronicle_scroll = 0
        elif action == "save":
            target = self.selected_slot if self.show_settings else self.save_slot
            if _public_module.save_village(self.snapshot(), slot_path(target)):
                self.save_slot = target
                self.toast(t("ui.saved"))
                self.sfx.play("coin")
            else:
                self.toast(t("ui.save_failed"))
        elif action == "visitor":
            if not self.spawn_visitor(force=True):
                pass
        elif action == "talk":
            self.open_chat()
        elif action == "self":
            self.request_self()
        elif action == "jobs":
            self.show_jobs = not self.show_jobs
        elif action == "close_jobs":
            self.show_jobs = False
        elif action == "help":
            self.show_help = not self.show_help
        elif action == "close_help":
            self.show_help = False
        elif action == "send":
            self.submit_chat()
        elif action == "close_chat":
            self.close_chat()
        elif action == "close_chronicle":
            self.show_chronicle = False
        elif action == "close_setup":
            self.setup_dismissed = True
        elif action == "close_dispatch":
            self.dispatch_card = None
        elif action == "llm_retry":
            self.llm.retry_resolve()
            self.toast(self.llm.label)
        elif action == "provider_open":
            from .setup import PROVIDERS
            current = str(self.config.get("llm.provider", "auto"))
            self.setup_provider = current if current in PROVIDERS else "auto"
            self.show_provider_setup = True
        elif action == "provider_close":
            self.show_provider_setup = False
        elif action == "provider_website":
            from .setup import provider_website
            import webbrowser
            url = provider_website(self.setup_provider)
            if url:
                try:
                    if not webbrowser.open(url):
                        self.toast(t("setup.browser_error"))
                except Exception:
                    self.toast(t("setup.browser_error"))
        elif action == "provider_download":
            if self.setup_provider in ("auto", "ollama"):
                import os
                base = str(self.config.get("llm.base_url", "") or
                           os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"))
                self.setup_download.start(base)
        elif action.startswith("provider_select:"):
            from .setup import PROVIDERS
            choice = action.split(":", 1)[1]
            if choice in PROVIDERS:
                self.setup_provider = choice
        elif action == "provider_save":
            from .setup import save_provider
            try:
                save_provider(self.config.path, self.setup_provider)
            except (OSError, ValueError):
                self.toast(t("setup.save_error"))
            else:
                self.show_provider_setup = False
                self.toast(t("setup.saved"), 8.0)
        elif action == "settings":
            self.show_settings = not self.show_settings
        elif action.startswith("slot:"):
            self.selected_slot = int(action.split(":", 1)[1])
        elif action == "load_slot":
            data, _ = load_slot(self.selected_slot)
            if not data:
                self.toast(t("settings.empty"))
            elif int(data.get("seed", self.seed)) != self.seed:
                self.toast(t("settings.seed_mismatch"))
            else:
                self._apply_save(data)
                self.save_slot = self.selected_slot
                self.toast(self._saved_banner(data))
        elif action.startswith("toggle:"):
            key = action.split(":", 1)[1]
            if key in ("social.group_chats", "social.threads", "llm.ambient_dialogue", "llm.self_directed", "voice.speak_ambient"):
                self.config.set(key, not self.config.get(key, True))
                if key == "voice.speak_ambient":
                    self.voice.speak_ambient = bool(self.config.get(key, True))

    def _paste(self) -> str:
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            raw = pygame.scrap.get(pygame.SCRAP_TEXT)
            if not raw:
                return ""
            text = raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else str(raw)
            return " ".join(text.replace("\x00", "").split())
        except Exception:
            return ""

    def _key(self, e) -> None:
        if self._gateway_key(e):
            return
        if self._ambient_model_key(e):
            return
        if self.show_help:
            if e.key in (pygame.K_F1, pygame.K_ESCAPE):
                self.show_help = False
            return
        if e.key == pygame.K_F10:
            self.photo_mode = not self.photo_mode
            return
        if self.photo_mode:
            if e.key == pygame.K_F12:
                self._screenshot()
            elif e.key == pygame.K_F11:
                self._postcard()
            elif e.key == pygame.K_ESCAPE:
                self.photo_mode = False
            return
        if e.key == pygame.K_F1:
            self.show_help = True
            return
        if self.chat.active:
            if e.key == pygame.K_ESCAPE:
                self.close_chat()
            elif e.key == pygame.K_RETURN or e.key == pygame.K_KP_ENTER:
                self.submit_chat()
            elif e.key == pygame.K_BACKSPACE:
                self.chat.input = self.chat.input[:-1]
            elif e.key == pygame.K_v and (e.mod & pygame.KMOD_CTRL):
                pasted = self._paste()
                if pasted:
                    self.chat.input = (self.chat.input + " " + pasted).strip()[:220]
            elif e.unicode and e.unicode.isprintable() and len(self.chat.input) < 220:
                self.chat.input += e.unicode
            return

        if self.show_provider_setup:
            if e.key == pygame.K_ESCAPE:
                self.show_provider_setup = False
            return
        if self.show_settings:
            if e.key in (pygame.K_ESCAPE, pygame.K_F3):
                self.show_settings = False
            return
        if self.show_jobs:
            if e.key in (pygame.K_ESCAPE, pygame.K_j):
                self.show_jobs = False
            return

        if self.show_chronicle:
            if e.key in (pygame.K_ESCAPE, pygame.K_c):
                self.show_chronicle = False
            elif e.key == pygame.K_DOWN:
                self.ui.scroll(-1)
            elif e.key == pygame.K_UP:
                self.ui.scroll(1)
            return
        if handle_dev_key(self, e):
            return

        if e.key == pygame.K_ESCAPE:
            if self.inside_house:
                self.inside_house = ""
            elif self.selected is not None:
                self.selected = None
                self.follow_selected = False
            elif not self.setup_dismissed and not self.llm.available:
                self.setup_dismissed = True
        elif e.key == pygame.K_t:
            self.open_chat()
        elif e.key == pygame.K_r:
            self._action("self")
        elif e.key == pygame.K_j:
            self._action("jobs")
        elif e.key == pygame.K_c:
            self.show_chronicle = True
            self.ui.chronicle_scroll = 0
        elif e.key == pygame.K_m:
            self._action("mute")
        elif e.key == pygame.K_s:
            self._action("save")
        elif e.key == pygame.K_v:
            self._action("visitor")
        elif e.key == pygame.K_F2:
            self._action("lang")
        elif e.key == pygame.K_F3:
            self._action("settings")
        elif e.key == pygame.K_SPACE:
            self._action("pause")
        elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            speeds = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 4, pygame.K_4: 8}
            self.clock.set_speed(speeds[e.key])
        elif e.key == pygame.K_l:
            self.clock.return_to_live()
        elif e.key == pygame.K_u and self.update_url:
            if self.update_info and self.update_info.get("installer"):
                if not self.update_installing:
                    self.update_installing = True
                    self.toast(self.i18n.t("update.downloading",
                                           version=self.update_version), 12.0)
                    from .update_check import install_update
                    install_update(self.update_info, lambda success, error: setattr(
                        self, "_update_result", ("install", (success, error), "")))
            else:
                import webbrowser
                try:
                    webbrowser.open(self.update_url)
                except Exception:
                    self.toast(self.i18n.t("update.open_error"))
        elif e.key == pygame.K_n:
            self.clock.sleep_until_dawn()
            self.toast(self.i18n.t("ui.sleep_until_dawn"))
        elif e.key == pygame.K_F12:
            self._screenshot()

    def _pick(self, pos):
        wx, wy = self.camera.screen_to_world(*pos)
        best = None
        best_d = 1e9
        for agent in self.agents:
            d = math.hypot(agent.x - wx, (agent.y - 8) - wy)
            if d < 15 and d < best_d:
                best, best_d = agent, d
        for visitor in self.visitors:
            if visitor.state == "gone":
                continue
            d = math.hypot(visitor.x - wx, (visitor.y - 8) - wy)
            if d < 15 and d < best_d:
                best, best_d = visitor, d
        return best

    def _mouse_down(self, e) -> None:
        if self.photo_mode:
            return
        if e.button == 1:
            action = self.ui.action_at(e.pos)
            if action:
                self._action(action)
                self._press_world = False
                return
            if self.show_help:
                return
            if self.show_provider_setup or self.show_settings:
                return
            if self.show_jobs:
                self.show_jobs = False
                return
            if self.show_chronicle:
                self.show_chronicle = False
                return
            self._press_world = True
            self._dragging = False
            self._drag_last = e.pos
        elif e.button == 3:
            if self.show_help:
                self.show_help = False
            elif self.chat.active:
                self.close_chat()
            elif self.show_jobs:
                self.show_jobs = False
            elif self.show_chronicle:
                self.show_chronicle = False
            else:
                self.selected = None
                self.follow_selected = False

