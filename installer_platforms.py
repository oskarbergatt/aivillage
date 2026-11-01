"""Native installer staging and branding, without touching installed applications."""
from __future__ import annotations

import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

from installer_art import write_background_bitmap, write_bitmap, write_ico, write_svg


def find_inno() -> str | None:
    found = shutil.which("ISCC.exe") or shutil.which("ISCC")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"),
                 os.environ.get("LOCALAPPDATA")):
        if base:
            for parent in (Path(base), Path(base) / "Programs"):
                candidate = parent / "Inno Setup 6" / "ISCC.exe"
                if candidate.is_file():
                    return str(candidate)
    return None


def windows_installer(app: Path, work: Path, version: str) -> Path:
    compiler = find_inno()
    if not compiler:
        raise RuntimeError("Inno Setup 6.7 or newer is required: https://jrsoftware.org/isinfo.php")
    if not (app / "aivillage.exe").is_file():
        raise ValueError("Expected a Windows app folder containing aivillage.exe")
    banner, badge = work / "wizard.bmp", work / "badge.bmp"
    write_bitmap(banner, 164, 314)
    write_bitmap(badge, 55, 55)
    background = work / "background.bmp"
    write_background_bitmap(background, 994, 720, arrow=False)
    icon = work / "aivillage.ico"
    write_ico(icon)
    script = work / "setup.iss"
    script.write_text(f'''[Setup]
AppId=aivillage.desktop
AppName=aivillage
AppVersion={version}
AppPublisher=aivillage
Uninstallable=yes
DefaultDirName={{localappdata}}\\Programs\\aivillage
DefaultGroupName=aivillage
PrivilegesRequired=lowest
UninstallDisplayIcon={{app}}\\aivillage.ico
SetupIconFile={icon}
OutputDir={work}
OutputBaseFilename=aivillage-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
WizardImageFile={banner}
WizardSmallImageFile={badge}
WizardBackColor=#f4f2e6
WizardBackImageFile={background}
WizardBackImageOpacity=90

[Files]
Source: "{app / '*'}"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{icon}"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\aivillage"; Filename: "{{app}}\\aivillage.exe"; IconFilename: "{{app}}\\aivillage.ico"
Name: "{{group}}\\Uninstall aivillage"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\aivillage"; Filename: "{{app}}\\aivillage.exe"; IconFilename: "{{app}}\\aivillage.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{{app}}\\aivillage.exe"; Description: "Launch aivillage"; Flags: nowait postinstall skipifsilent unchecked
''', encoding="utf-8-sig")
    try:
        subprocess.run([compiler, str(script)], check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Installer compilation failed; full backgrounds require Inno Setup 6.7 or newer. See compiler output above.") from exc
    return work / "aivillage-setup.exe"


def macos_installer(app: Path, work: Path, version: str) -> Path:
    if not (app / "Contents" / "Info.plist").is_file():
        raise ValueError("Expected a macOS .app bundle")
    for tool in ("sips", "iconutil", "hdiutil", "codesign"):
        if not shutil.which(tool):
            raise RuntimeError(f"{tool} is required and must be run on macOS")
    stage = work / "volume"
    stage.mkdir()
    staged_app = stage / "aivillage.app"
    shutil.copytree(app, staged_app, symlinks=True)
    iconset = work / "aivillage.iconset"
    iconset.mkdir()
    bitmap = work / "icon.bmp"
    write_bitmap(bitmap, 1024, 1024)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            suffix = "@2x" if scale == 2 else ""
            png = iconset / f"icon_{size}x{size}{suffix}.png"
            pixels = str(size * scale)
            subprocess.run(["sips", "-s", "format", "png", "-z", pixels, pixels,
                            str(bitmap), "--out", str(png)], check=True, capture_output=True)
    icon = staged_app / "Contents" / "Resources" / "aivillage.icns"
    icon.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(icon)], check=True)
    plist = staged_app / "Contents" / "Info.plist"
    with plist.open("rb") as stream:
        metadata = plistlib.load(stream)
    metadata["CFBundleIconFile"] = "aivillage.icns"
    with plist.open("wb") as stream:
        plistlib.dump(metadata, stream)
    # Changing Info.plist invalidates PyInstaller's ad-hoc signature.
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(staged_app)], check=True)
    (stage / "Applications").symlink_to("/Applications", target_is_directory=True)
    (stage / "Read Me.txt").write_text(
        "aivillage\n\nDrag aivillage into Applications to install it.\n"
        "Your village saves live in Library/Application Support/aivillage.\n"
        "This build is unsigned and may be blocked by macOS Gatekeeper.\n", encoding="utf-8")
    background_bmp = work / "background.bmp"
    background_png = work / "background.png"
    write_background_bitmap(background_bmp, 640, 420)
    subprocess.run(["sips", "-s", "format", "png", str(background_bmp),
                    "--out", str(background_png)], check=True, capture_output=True)
    settings = work / "dmg_settings.py"
    settings.write_text(
        f"files = [{str(staged_app)!r}, {str(stage / 'Read Me.txt')!r}]\n"
        "symlinks = {'Applications': '/Applications'}\n"
        f"background = {str(background_png)!r}\n"
        "window_rect = ((200, 120), (640, 420))\n"
        "default_view = 'icon-view'\nicon_size = 96\n"
        "icon_locations = {'aivillage.app': (170, 210), 'Applications': (470, 210), "
        "'Read Me.txt': (320, 345)}\n", encoding="utf-8")
    output = work / "aivillage.dmg"
    try:
        subprocess.run([sys.executable, "-m", "dmgbuild", "-s", str(settings),
                        "aivillage", str(output)], check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Could not create disk image. Install dmgbuild into this Python environment and check the output above.") from exc
    return output


def deb_architecture(arch: str) -> str:
    mapping = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64",
               "i686": "i386", "i386": "i386"}
    if arch.lower() not in mapping:
        raise ValueError(f"Unsupported Debian architecture: {arch}")
    return mapping[arch.lower()]


def linux_installer(app: Path, work: Path, version: str, arch: str) -> Path:
    compiler = shutil.which("dpkg-deb")
    if not compiler:
        raise RuntimeError("dpkg-deb is required; build on a Debian-based Linux system")
    if not (app / "aivillage").is_file():
        raise ValueError("Expected a Linux app folder containing the aivillage executable")
    stage = work / "package"
    control = stage / "DEBIAN"
    control.mkdir(parents=True)
    (control / "control").write_text(
        f"Package: aivillage\nVersion: {version}\nArchitecture: {deb_architecture(arch)}\n"
        "Maintainer: aivillage contributors\nSection: games\nPriority: optional\n"
        "Depends: libc6, libx11-6, libasound2 | libasound2t64\n"
        "Description: A pixel-art village simulation\n"
        " A small village that lives on your clock, weather and news.\n", encoding="utf-8")
    shutil.copytree(app, stage / "opt" / "aivillage", symlinks=True)
    desktop = stage / "usr" / "share" / "applications" / "aivillage.desktop"
    desktop.parent.mkdir(parents=True)
    desktop.write_text("[Desktop Entry]\nType=Application\nName=aivillage\n"
                       "Comment=A little village living on your clock\n"
                       "Exec=/opt/aivillage/aivillage\nIcon=aivillage\n"
                       "Categories=Game;Simulation;\nTerminal=false\n", encoding="utf-8")
    icon = stage / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps" / "aivillage.svg"
    icon.parent.mkdir(parents=True)
    write_svg(icon)
    output = work / "aivillage.deb"
    subprocess.run([compiler, "--build", "--root-owner-group", str(stage), str(output)], check=True)
    return output
