"""Cross-platform build configuration and safe output behavior."""
from pathlib import Path

import pytest

import build_app
from aivillage.runtime_paths import data_root


@pytest.mark.parametrize("system,folder,name", [
    ("Windows", "windows-amd64", "aivillage"),
    ("Darwin", "macos-amd64", "aivillage.app"),
    ("Linux", "linux-amd64", "aivillage"),
])
def test_targets_and_resources(system, folder, name, tmp_path):
    assert build_app.target_info(system, "AMD64") == (folder, name)
    cmd = build_app.build_command(Path("python"), tmp_path, system)
    assert "--onedir" in cmd and "--windowed" in cmd
    assert sum("aivillage/locales" in arg for arg in cmd) == 1
    assert sum("aivillage/assets/fonts" in arg for arg in cmd) == 1
    assert ("pyttsx3.drivers.sapi5" in cmd) == (system == "Windows")


def test_existing_output_is_never_replaced(tmp_path, monkeypatch):
    monkeypatch.setattr(build_app.platform, "system", lambda: "Windows")
    monkeypatch.setattr(build_app, "python_architecture", lambda system: "AMD64")
    output = tmp_path / "windows-amd64" / "aivillage"
    output.mkdir(parents=True)
    marker = output / "keep.txt"
    marker.write_text("user data", encoding="utf-8")
    with pytest.raises(FileExistsError):
        build_app.build(tmp_path)
    assert marker.read_text(encoding="utf-8") == "user data"


def test_unsupported_platform_is_rejected():
    with pytest.raises(ValueError):
        build_app.target_info("OtherOS", "x64")


def test_architecture_follows_python_not_host(monkeypatch):
    monkeypatch.setattr(build_app.sysconfig, "get_platform", lambda: "win-amd64")
    monkeypatch.setattr(build_app.platform, "machine", lambda: "ARM64")
    assert build_app.python_architecture("Windows") == "amd64"


def test_frozen_data_paths_are_outside_bundle(tmp_path, monkeypatch):
    import aivillage.runtime_paths as paths
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.platform, "system", lambda: "Windows")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert data_root(Path("bundle")) == tmp_path / "aivillage"
    monkeypatch.setattr(paths.platform, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert data_root(Path("bundle")) == tmp_path / "aivillage"
    monkeypatch.setattr(paths.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: tmp_path))
    assert data_root(Path("bundle")) == tmp_path / "Library" / "Application Support" / "aivillage"


def test_source_data_path_is_unchanged(monkeypatch, tmp_path):
    import aivillage.runtime_paths as paths
    monkeypatch.delattr(paths.sys, "frozen", raising=False)
    assert data_root(tmp_path) == tmp_path
