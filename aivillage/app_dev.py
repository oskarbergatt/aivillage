"""Secret, ephemeral developer cheats for local simulation testing."""
from __future__ import annotations

import pygame

DEV_STOCK = 999_999
RESOURCE_KEYS = ("wood", "stone", "food", "coin")


def pin_resources(app) -> None:
    if app.dev_mode:
        app.stats.update({key: DEV_STOCK for key in RESOURCE_KEYS})


def handle_dev_key(app, event) -> bool:
    """Handle the hidden toggle and optional test shortcuts."""
    toggle = (event.key == pygame.K_d
              and (event.mod & (pygame.KMOD_CTRL | pygame.KMOD_SHIFT))
              == (pygame.KMOD_CTRL | pygame.KMOD_SHIFT))
    if toggle:
        app.dev_mode = not app.dev_mode
        if app.dev_mode:
            pin_resources(app)
            app.toast(app.i18n.t("dev.enabled"), 8.0)
        else:
            app.toast(app.i18n.t("dev.disabled"))
        return True

    if not app.dev_mode:
        return False
    if event.key == pygame.K_F5:
        for agent in app.agents:
            agent.needs.hunger = 100.0
            agent.needs.energy = 100.0
            agent.needs.social = 100.0
            agent.needs.fun = 100.0
        app.toast(app.i18n.t("dev.needs_refilled"))
        return True
    if event.key == pygame.K_F6:
        builder = next((a for a in app.agents if a.persona.job == "builder"), None)
        if builder and app.world.build_site:
            app.build(1.0, builder)
        return True
    if event.key == pygame.K_F7:
        app.spawn_visitor(force=True)
        return True
    return False
