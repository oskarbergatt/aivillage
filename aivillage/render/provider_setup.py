"""In-game, non-secret AI provider selection."""
import pygame

from ..assets.font import draw_text, draw_wrapped
from ..assets.palette import P
from ..setup import PROVIDERS


def draw_provider_setup(ui, screen, app, w: int, h: int) -> None:
    t = ui.i18n.t
    shade = pygame.Surface((w, h), pygame.SRCALPHA)
    shade.fill((8, 8, 14, 190))
    screen.blit(shade, (0, 0))
    rect = pygame.Rect((w - 700) // 2, (h - 500) // 2, 700, 500)
    ui._panel(screen, rect)
    draw_text(screen, t("setup.title"), (rect.x + 20, rect.y + 16), 16, P["ui_accent"])
    ui._button(screen, pygame.Rect(rect.right - 52, rect.y + 10, 34, 28), "X", "provider_close")
    draw_text(screen, t("setup.choose"), (rect.x + 20, rect.y + 48), 16, P["ui_text"])
    for i, provider in enumerate(PROVIDERS):
        x = rect.x + 20 + (i % 2) * 335
        y = rect.y + 75 + (i // 2) * 34
        ui._button(screen, pygame.Rect(x, y, 320, 29), t("setup." + provider),
                   "provider_select:" + provider, active=app.setup_provider == provider)
    y = rect.y + 257
    draw_wrapped(screen, t("setup.help_" + app.setup_provider),
                 (rect.x + 20, y), rect.w - 40, 16, P["ui_text"], max_lines=3)
    if app.setup_provider in ("auto", "ollama", "subscription", "claude_cli", "codex_cli",
                              "openai", "anthropic", "openai_compatible"):
        ui._button(screen, pygame.Rect(rect.x + 20, rect.y + 318, 190, 28),
                   t("setup.website"), "provider_website")
    if app.setup_provider in ("auto", "ollama"):
        ui._button(screen, pygame.Rect(rect.x + 225, rect.y + 318, 280, 28),
                   t("setup.download"), "provider_download",
                   enabled=not app.setup_download.running)
        status = app.setup_download.status
        if status != "idle":
            draw_wrapped(screen, t("setup.download_" + status,
                                   progress=app.setup_download.detail),
                         (rect.x + 20, rect.y + 352), rect.w - 40, 16,
                          P["ui_dim"], max_lines=2)
    if app.setup_provider == "openai_compatible":
        ui._button(screen, pygame.Rect(rect.x + 225, rect.y + 318, 280, 28),
                   t("gateway.open"), "gateway_open")
    draw_wrapped(screen, t("setup.restart"), (rect.x + 20, rect.y + 385),
                 rect.w - 40, 16, P["ui_dim"], max_lines=2)
    ui._button(screen, pygame.Rect(rect.x + 20, rect.bottom - 52, 180, 32),
               t("setup.save"), "provider_save")
    ui._button(screen, pygame.Rect(rect.x + 215, rect.bottom - 52, 180, 32),
               t("setup.cancel"), "provider_close")
