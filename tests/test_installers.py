"""Installer branding, staging and non-destructive output behavior."""
import os
from pathlib import Path
import plistlib
import sys

import pytest

import build_installer
import installer_art
import installer_platforms as platforms


def test_installer_art_is_valid_bitmap_and_svg(tmp_path):
    bitmap = tmp_path / "wizard.bmp"
    installer_art.write_bitmap(bitmap, 55, 55)
    assert bitmap.read_bytes()[:2] == b"BM"
    import pygame
    assert pygame.image.load(str(bitmap)).get_size() == (55, 55)
    backdrop = tmp_path / "background.bmp"
    installer_art.write_background_bitmap(backdrop, 640, 420)
    assert pygame.image.load(str(backdrop)).get_size() == (640, 420)
    icon = tmp_path / "icon.svg"
    installer_art.write_svg(icon)
    assert "<svg" in icon.read_text(encoding="utf-8")
    windows_icon = tmp_path / "icon.ico"
    installer_art.write_ico(windows_icon)
    assert windows_icon.read_bytes()[:6] == b"\x00\x00\x01\x00\x01\x00"


def test_windows_installer_has_branded_per_user_wizard(tmp_path, monkeypatch):
    app = tmp_path / "app"
    app.mkdir()
    (app / "aivillage.exe").write_bytes(b"exe")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr(platforms, "find_inno", lambda: "ISCC.exe")

    def run(command, **kwargs):
        script = Path(command[1]).read_text(encoding="utf-8-sig")
        assert "PrivilegesRequired=lowest" in script
        assert "WizardImageFile=" in script and "WizardSmallImageFile=" in script
        assert "WizardBackImageFile=" in script and "WizardBackImageOpacity=90" in script
        assert "SetupIconFile=" in script and "IconFilename:" in script
        assert "{localappdata}" in script
        assert (work / "wizard.bmp").read_bytes().startswith(b"BM")
        (work / "aivillage-setup.exe").write_bytes(b"installer")
    monkeypatch.setattr(platforms.subprocess, "run", run)
    assert platforms.windows_installer(app, work, "0.4.0").is_file()


def test_debian_package_has_desktop_icon_and_no_saves(tmp_path, monkeypatch):
    app = tmp_path / "app"
    app.mkdir()
    (app / "aivillage").write_bytes(b"binary")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr(platforms.shutil, "which", lambda name: "/usr/bin/dpkg-deb")

    def run(command, **kwargs):
        stage = Path(command[-2])
        desktop = stage / "usr/share/applications/aivillage.desktop"
        assert "Icon=aivillage" in desktop.read_text(encoding="utf-8")
        assert (stage / "usr/share/icons/hicolor/scalable/apps/aivillage.svg").is_file()
        assert "Architecture: arm64" in (stage / "DEBIAN/control").read_text(encoding="utf-8")
        assert not (stage / "home").exists()
        Path(command[-1]).write_bytes(b"deb")
    monkeypatch.setattr(platforms.subprocess, "run", run)
    assert platforms.linux_installer(app, work, "0.4.0", "aarch64").is_file()


@pytest.mark.skipif(os.name == "nt", reason="creating macOS Applications symlinks needs native Unix semantics")
def test_macos_volume_brands_app_without_modifying_source(tmp_path, monkeypatch):
    app = tmp_path / "original.app"
    contents = app / "Contents"
    contents.mkdir(parents=True)
    with (contents / "Info.plist").open("wb") as stream:
        plistlib.dump({"CFBundleName": "aivillage"}, stream)
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr(platforms.shutil, "which", lambda name: name)
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        if command[0] == "iconutil":
            Path(command[-1]).write_bytes(b"icon")
        elif command[0] == sys.executable and command[1:3] == ["-m", "dmgbuild"]:
            settings = Path(command[command.index("-s") + 1]).read_text(encoding="utf-8")
            assert "background = " in settings and "icon_locations = " in settings
            Path(command[-1]).write_bytes(b"dmg")
    monkeypatch.setattr(platforms.subprocess, "run", run)
    assert platforms.macos_installer(app, work, "0.4.0").is_file()
    with (contents / "Info.plist").open("rb") as stream:
        assert "CFBundleIconFile" not in plistlib.load(stream)
    staged = work / "volume/aivillage.app/Contents/Info.plist"
    with staged.open("rb") as stream:
        assert plistlib.load(stream)["CFBundleIconFile"] == "aivillage.icns"
    assert (work / "volume/Applications").is_symlink()
    assert any(command[0] == "codesign" for command in commands)


def test_builder_refuses_to_replace_installer(tmp_path, monkeypatch):
    monkeypatch.setattr(build_installer.platform, "system", lambda: "Windows")
    monkeypatch.setattr(build_installer, "python_architecture", lambda system: "amd64")
    app = tmp_path / "app"
    app.mkdir()
    output = tmp_path / "output"
    output.mkdir()
    target = output / "aivillage-0.4.0-windows-amd64.exe"
    target.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        build_installer.build_installer(app, output)
    assert target.read_bytes() == b"existing"


def test_unsupported_debian_arch_is_rejected():
    with pytest.raises(ValueError):
        platforms.deb_architecture("universal2")
