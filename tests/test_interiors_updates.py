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


def test_clicking_house_roof_enters_without_hitting_the_door(app):
    house = app.world.buildings["pip"]
    point = (house.x + house.sprite.get_width() // 2,
             house.y + house.sprite.get_height() // 3)
    screen_pos = app.camera.world_to_screen(*point)
    app._press_world = True
    app._mouse_up(SimpleNamespace(button=1, pos=screen_pos))
    assert app.inside_house == "pip"


def test_update_versions_are_compared_safely():
    from aivillage.update_check import installer_for, newer_version
    assert newer_version("0.5.0", "0.4.0")
    assert not newer_version("0.4.0", "0.4.0")
    assert not newer_version("unknown", "0.4.0")
    assets = [{"name": "aivillage-0.4.1-windows-amd64.exe"},
              {"name": "SHA256SUMS.txt"}]
    assert installer_for(assets, "Windows")[0]["name"].endswith(".exe")
    assert installer_for(assets, "FreeBSD") is None


def test_update_installer_requires_matching_sha256(tmp_path, monkeypatch):
    import hashlib
    from aivillage import update_check
    filename = "aivillage-0.4.1-linux-x86_64.deb"
    payload = b"verified test installer"
    digest = hashlib.sha256(payload).hexdigest()
    responses = {
        "https://github.com/checksums": f"{digest} *{filename}\n".encode(),
        "https://github.com/installer": payload,
    }
    monkeypatch.setattr(update_check.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(update_check, "_request", lambda url, limit=update_check.MAX_DOWNLOAD: responses[url])
    target = update_check.download_verified_installer(
        "https://github.com/installer", "https://github.com/checksums", filename)
    assert target.read_bytes() == payload

    responses["https://github.com/checksums"] = ("0" * 64 + f" *{filename}\n").encode()
    import pytest
    with pytest.raises(ValueError, match="checksum"):
        update_check.download_verified_installer(
            "https://github.com/installer", "https://github.com/checksums", filename)


def test_updater_rejects_untrusted_hosts_and_paths():
    import pytest
    from aivillage.update_check import download_verified_installer
    with pytest.raises(ValueError, match="HTTPS host"):
        download_verified_installer("https://attacker.example/app.exe", "https://github.com/sums",
                                    "aivillage-setup.exe")
    with pytest.raises(ValueError, match="filename"):
        download_verified_installer("https://github.com/app", "https://github.com/sums", "../evil.exe")


def test_house_interior_draws_for_named_house(app):
    surface = pygame.Surface((960, 600))
    app.renderer.draw_interior(surface, app.world.buildings["pip"], app.agents, app.i18n)
    assert surface.get_at((480, 300))[:3] != (29, 25, 36)
