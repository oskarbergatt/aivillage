"""Small model selector for automatic villager conversations."""
import pygame

from ..assets.font import draw_text, draw_wrapped
from ..assets.palette import P


def draw_ambient_model(ui, screen, app, w: int, h: int) -> None:
    t = ui.i18n.t
    shade = pygame.Surface((w, h), pygame.SRCALPHA)
    shade.fill((8, 8, 14, 190))
    screen.blit(shade, (0, 0))
    rect = pygame.Rect((w - 650) // 2, (h - 300) // 2, 650, 300)
    ui._panel(screen, rect)
    draw_text(screen, t("model.title"), (rect.x + 20, rect.y + 18), 16, P["ui_accent"])
    draw_wrapped(screen, t("model.help"), (rect.x + 20, rect.y + 50),
                 rect.w - 40, 16, P["ui_text"], max_lines=3)
    field = pygame.Rect(rect.x + 20, rect.y + 125, rect.w - 40, 32)
    pygame.draw.rect(screen, P["ui_bg2"], field)
    pygame.draw.rect(screen, P["ui_line"], field, 1)
    text = app.ambient_model_input or t("model.default")
    draw_text(screen, text[-65:], (field.x + 8, field.y + 7), 16,
              P["ui_text"] if app.ambient_model_input else P["ui_dim"])
    if app.ambient_model_error:
        draw_wrapped(screen, app.ambient_model_error, (rect.x + 20, rect.y + 168),
                     rect.w - 40, 16, P["ui_bad"], max_lines=2)
    else:
        draw_text(screen, t("model.keyboard"), (rect.x + 20, rect.y + 170), 16, P["ui_dim"])
    ui._button(screen, pygame.Rect(rect.x + 20, rect.bottom - 52, 160, 32),
               t("model.save"), "ambient_model_save")
    ui._button(screen, pygame.Rect(rect.x + 195, rect.bottom - 52, 160, 32),
               t("model.cancel"), "ambient_model_close")
