"""Non-secret, in-game OpenAI-compatible gateway configuration."""
import pygame

from .setup import save_gateway, valid_gateway


class GatewaySetupMixin:
    def _gateway_action(self, action):
        if action == "gateway_open":
            self.gateway_values = [str(self.config.get("llm.base_url", "") or ""),
                                   str(self.config.get("llm.model", "") or ""),
                                   str(self.config.get("llm.api_key_env", "") or "")]
            self.gateway_focus = 0
            self.gateway_error = ""
            self.show_gateway = True
        elif action == "gateway_close":
            self.show_gateway = False
        elif action.startswith("gateway_field:"):
            index = int(action.split(":", 1)[1])
            if index in range(3):
                self.gateway_focus = index
        elif action == "gateway_save":
            url, model, key_env = (s.strip() for s in self.gateway_values)
            if not valid_gateway(url, model, key_env):
                self.gateway_error = self.i18n.t("gateway.invalid")
                return True
            try:
                save_gateway(self.config.path, url, model, key_env)
            except (OSError, ValueError):
                self.gateway_error = self.i18n.t("gateway.save_error")
                return True
            self.show_gateway = False
            self.show_provider_setup = False
            self.toast(self.i18n.t("gateway.saved"), 8.0)
        else:
            return False
        return True

    def _gateway_key(self, event):
        if not self.show_gateway:
            return False
        if event.key == pygame.K_ESCAPE:
            self.show_gateway = False
        elif event.key == pygame.K_TAB:
            self.gateway_focus = (self.gateway_focus + (-1 if event.mod & pygame.KMOD_SHIFT else 1)) % 3
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._gateway_action("gateway_save")
        elif event.key == pygame.K_BACKSPACE:
            self.gateway_values[self.gateway_focus] = self.gateway_values[self.gateway_focus][:-1]
        else:
            text = self._paste() if event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL else event.unicode
            if text and text.isprintable():
                limit = 500 if self.gateway_focus == 0 else 128
                self.gateway_values[self.gateway_focus] = (self.gateway_values[self.gateway_focus] + text)[:limit]
        return True
