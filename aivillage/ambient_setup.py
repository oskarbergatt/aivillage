"""In-app selection of an optional model for background conversations."""
import pygame

from .setup import save_ambient_model, valid_model_id


class AmbientModelSetupMixin:
    def _ambient_model_action(self, action: str) -> bool:
        if action == "ambient_model_open":
            self.ambient_model_input = str(self.config.get("llm.ambient_model", "") or "")
            self.ambient_model_error = ""
            self.show_ambient_model = True
        elif action == "ambient_model_close":
            self.show_ambient_model = False
        elif action == "ambient_model_save":
            model = self.ambient_model_input.strip()
            if not valid_model_id(model):
                self.ambient_model_error = self.i18n.t("model.invalid")
                return True
            try:
                save_ambient_model(self.config.path, model)
            except (OSError, ValueError):
                self.ambient_model_error = self.i18n.t("model.save_error")
                return True
            self.config.set("llm.ambient_model", model)
            self.show_ambient_model = False
            self.toast(self.i18n.t("model.saved"))
        else:
            return False
        return True

    def _ambient_model_key(self, event) -> bool:
        if not self.show_ambient_model:
            return False
        if event.key == pygame.K_ESCAPE:
            self.show_ambient_model = False
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._ambient_model_action("ambient_model_save")
        elif event.key == pygame.K_BACKSPACE:
            self.ambient_model_input = self.ambient_model_input[:-1]
            self.ambient_model_error = ""
        elif event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
            self.ambient_model_input = (self.ambient_model_input + self._paste())[:120]
            self.ambient_model_error = ""
        elif event.unicode and event.unicode.isprintable():
            self.ambient_model_input = (self.ambient_model_input + event.unicode)[:120]
            self.ambient_model_error = ""
        return True
