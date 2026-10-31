"""Gateway settings dialog; credentials are never entered here."""
import pygame

from ..assets.font import draw_text, draw_wrapped
from ..assets.palette import P


def draw_gateway_setup(ui, screen, app, w, h):
    t = ui.i18n.t
    shade = pygame.Surface((w, h), pygame.SRCALPHA)
    shade.fill((8, 8, 14, 190))
    screen.blit(shade, (0, 0))
    rect = pygame.Rect((w - 700) // 2, (h - 500) // 2, 700, 500)
    ui._panel(screen, rect)
    draw_text(screen, t("gateway.title"), (rect.x + 20, rect.y + 16), 16, P["ui_accent"])
    draw_wrapped(screen, t("gateway.help"), (rect.x + 20, rect.y + 45), rect.w - 40,
                 16, P["ui_dim"], max_lines=3)
    for i, label in enumerate(("gateway.url", "gateway.model", "gateway.key_env")):
        y = rect.y + 115 + i * 70
        draw_text(screen, t(label), (rect.x + 20, y), 16, P["ui_text"])
        field = pygame.Rect(rect.x + 20, y + 24, rect.w - 40, 30)
        pygame.draw.rect(screen, P["ui_bg2"], field)
        pygame.draw.rect(screen, P["ui_accent"] if app.gateway_focus == i else P["ui_line"], field, 1)
        draw_text(screen, app.gateway_values[i][-66:], (field.x + 6, field.y + 6), 16, P["ui_text"])
        ui.hits[f"gateway_field:{i}"] = field
    if app.gateway_error:
        draw_wrapped(screen, app.gateway_error, (rect.x + 20, rect.y + 332), rect.w - 40,
                     16, P["ui_bad"], max_lines=3)
    else:
        draw_wrapped(screen, t("gateway.security"), (rect.x + 20, rect.y + 332), rect.w - 40,
                     16, P["ui_dim"], max_lines=3)
    ui._button(screen, pygame.Rect(rect.x + 20, rect.bottom - 52, 180, 32), t("model.save"), "gateway_save")
    ui._button(screen, pygame.Rect(rect.x + 215, rect.bottom - 52, 180, 32), t("model.cancel"), "gateway_close")
