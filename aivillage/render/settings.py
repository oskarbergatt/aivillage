"""Drawing and hit targets for the settings and save-slot panel."""
import pygame

from ..assets.font import draw_text
from ..assets.palette import P


def draw_settings(ui, screen, app, w: int, h: int) -> None:
    t = ui.i18n.t
    rect = pygame.Rect((w - 520) // 2, (h - 460) // 2, 520, 460)
    ui._panel(screen, rect)
    draw_text(screen, t("settings.title"), (rect.x + 20, rect.y + 18), 16, P["ui_accent"])
    ui._button(screen, pygame.Rect(rect.x + 265, rect.y + 12, 190, 26),
               t("model.open"), "ambient_model_open")
    ui._button(screen, pygame.Rect(rect.right - 55, rect.y + 12, 38, 26), "X", "settings")
    for i, (key, label) in enumerate((
            ("llm.ambient_dialogue", "settings.ambient"),
            ("llm.self_directed", "settings.self"),
            ("social.group_chats", "settings.groups"),
            ("social.threads", "settings.threads"),
            ("voice.speak_ambient", "settings.ambient_voice"))):
        y = rect.y + 58 + i * 39
        draw_text(screen, t(label), (rect.x + 20, y + 4), 16, P["ui_text"])
        enabled = bool(app.config.get(key, True))
        ui._button(screen, pygame.Rect(rect.right - 105, y, 82, 28),
                   t("settings.on") if enabled else t("settings.off"),
                   "toggle:" + key, active=enabled)
    draw_text(screen, t("settings.slots"), (rect.x + 20, rect.y + 270), 16, P["ui_text"])
    for slot in range(1, 6):
        ui._button(screen, pygame.Rect(rect.x + 20 + (slot - 1) * 55, rect.y + 298, 48, 28),
                   str(slot), f"slot:{slot}", active=app.selected_slot == slot)
    ui._button(screen, pygame.Rect(rect.x + 20, rect.y + 345, 150, 30),
               t("settings.save"), "save")
    ui._button(screen, pygame.Rect(rect.x + 185, rect.y + 345, 150, 30),
               t("settings.load"), "load_slot")
    draw_text(screen, t("settings.autosave", slot=app.save_slot),
              (rect.x + 20, rect.y + 392), 16, P["ui_dim"])
    ui._button(screen, pygame.Rect(rect.right - 200, rect.y + 385, 180, 30),
               t("setup.title"), "provider_open")
    draw_text(screen, t("settings.voice_status", status=app.voice.label())[:62],
              (rect.x + 20, rect.y + 430), 8, P["ui_dim"])
