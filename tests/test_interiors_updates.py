from types import SimpleNamespace

import pygame


def test_house_door_enters_and_escape_leaves(app):
    point = app.world.points["home_pip"]
    screen_pos = app.camera.world_to_screen(*point)
    app._press_world = True
    app._mouse_up(SimpleNamespace(button=1, pos=screen_pos))
    assert app.inside_house == "pip"
    app._draw(0.016)
    app._key(SimpleNamespace(key=pygame.K_ESCAPE, mod=0, unicode=""))
    assert app.inside_house == ""


def test_update_versions_are_compared_safely():
    from aivillage.update_check import newer_version
    assert newer_version("0.5.0", "0.4.0")
    assert not newer_version("0.4.0", "0.4.0")
    assert not newer_version("unknown", "0.4.0")


def test_house_interior_draws_for_named_house(app):
    surface = pygame.Surface((960, 600))
    app.renderer.draw_interior(surface, app.world.buildings["pip"], app.agents, app.i18n)
    assert surface.get_at((480, 300))[:3] != (29, 25, 36)
