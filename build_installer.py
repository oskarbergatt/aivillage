#!/usr/bin/env python3
"""Package an existing native aivillage build as an OS-specific installer."""
from __future__ import annotations

import argparse
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib

from build_app import ROOT, python_architecture, target_info
from installer_platforms import linux_installer, macos_installer, windows_installer


def project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        version = str(tomllib.load(stream)["project"]["version"])
    if not re.fullmatch(r"[0-9][a-zA-Z0-9.+~-]*", version):
        raise ValueError("Project version cannot be used in installer filenames")
    return version


def build_installer(app: Path | None, output: Path) -> Path:
    system = platform.system()
    arch = python_architecture(system)
    folder, app_name = target_info(system, arch)
    source = (app or ROOT / "dist" / folder / app_name).resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"App build not found: {source}. Run build_app.py first.")
    version = project_version()
    ext = {"Windows": "exe", "Darwin": "dmg", "Linux": "deb"}[system]
    target = output.resolve() / f"aivillage-{version}-{folder}.{ext}"
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"Installer already exists; choose another --output: {target}")
    with tempfile.TemporaryDirectory(prefix="aivillage-installer-") as tmp:
        work = Path(tmp)
        if system == "Windows":
            built = windows_installer(source, work, version)
        elif system == "Darwin":
            built = macos_installer(source, work, version)
        else:
            built = linux_installer(source, work, version, arch)
        if not built.is_file():
            raise RuntimeError("Installer tool completed without creating an installer")
        target.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents replacing a file created during the build.
        with target.open("xb") as dst, built.open("rb") as src:
            shutil.copyfileobj(src, dst)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, help="path to an existing native app bundle/folder")
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "installers",
                        help="installer output folder (default: dist/installers)")
    args = parser.parse_args(argv)
    try:
        result = build_installer(args.app, args.output)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Installer build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Installer created: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
