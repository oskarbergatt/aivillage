#!/usr/bin/env python3
"""Build an aivillage desktop application for the current operating system.

Run with Python 3.11 or 3.12 on the target OS. --install creates an isolated,
temporary build environment and downloads the build tools and dependencies.
"""
from __future__ import annotations

import argparse
import importlib.util
import platform
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import tomllib
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUPPORTED = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}


def target_info(system: str, machine: str) -> tuple[str, str]:
    if system not in SUPPORTED:
        raise ValueError(f"Unsupported operating system: {system}")
    arch = re.sub(r"[^a-zA-Z0-9_-]", "_", machine.strip().lower()) or "unknown"
    name = "aivillage.app" if system == "Darwin" else "aivillage"
    return f"{SUPPORTED[system]}-{arch}", name


def python_architecture(system: str) -> str:
    """Use the interpreter's target, which may differ from the host under emulation."""
    value = sysconfig.get_platform().lower()
    if system == "Windows":
        return value.removeprefix("win-")
    if system == "Linux":
        return value.removeprefix("linux-")
    if system == "Darwin":
        for arch in ("universal2", "arm64", "x86_64"):
            if value.endswith("-" + arch):
                return arch
    return platform.machine()


def build_command(python: Path, work: Path, system: str) -> list[str]:
    """Create PyInstaller's argument list without shell interpolation."""
    import os
    package = ROOT / "aivillage"
    cmd = [str(python), "-m", "PyInstaller", "--noconfirm", "--onedir",
           "--windowed", "--name", "aivillage", "--paths", str(ROOT),
           "--distpath", str(work / "dist"), "--workpath", str(work / "work"),
           "--specpath", str(work),
           "--add-data", f"{package / 'locales'}{os.pathsep}aivillage/locales",
           "--add-data", f"{package / 'assets' / 'fonts'}{os.pathsep}aivillage/assets/fonts"]
    if system == "Windows":
        cmd += ["--hidden-import", "pyttsx3.drivers.sapi5"]
    cmd.append(str(ROOT / "run.py"))
    return cmd


def build(destination: Path, install: bool = False) -> Path:
    system = platform.system()
    folder, name = target_info(system, python_architecture(system))
    target = destination.resolve() / folder / name
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"Output already exists; choose another --output: {target}")
    if not ((3, 11) <= sys.version_info[:2] < (3, 13)):
        raise RuntimeError("Build using Python 3.11 or 3.12 on the target operating system.")
    if not install and importlib.util.find_spec("PyInstaller") is None:
        raise RuntimeError("PyInstaller not found. Run again with --install to create an isolated build environment.")

    with tempfile.TemporaryDirectory(prefix="aivillage-build-") as temp:
        work = Path(temp)
        python = Path(sys.executable)
        if install:
            env = work / "venv"
            print("Creating an isolated build environment and installing dependencies...", flush=True)
            venv.EnvBuilder(with_pip=True).create(env)
            python = env / ("Scripts/python.exe" if system == "Windows" else "bin/python")
            with (ROOT / "pyproject.toml").open("rb") as stream:
                dependencies = tomllib.load(stream)["project"]["dependencies"]
            subprocess.run([str(python), "-m", "pip", "install",
                            "pyinstaller>=6.11,<7", *dependencies], check=True, cwd=ROOT)
        print(f"Building for {folder}...", flush=True)
        subprocess.run(build_command(python, work, system), check=True, cwd=ROOT)
        artifact = work / "dist" / name
        if not artifact.exists():
            raise RuntimeError(f"Build finished without the expected output: {name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        # Never overwrite an earlier build or any unrelated file.
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"Output appeared during build: {target}")
        shutil.move(str(artifact), str(target))
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true",
                        help="install build requirements in a temporary environment (needs internet)")
    parser.add_argument("--output", type=Path, default=ROOT / "dist",
                        help="output directory (default: dist)")
    args = parser.parse_args(argv)
    try:
        artifact = build(args.output, args.install)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
