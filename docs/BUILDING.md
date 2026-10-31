# Building desktop apps

The app builder produces a standalone folder on Windows and Linux, and an `.app` bundle on macOS.
The target operating system and processor architecture are those of the Python interpreter used
to build. PyInstaller does **not** cross-compile: build on each target OS and architecture.

## Windows

Double-click `Build aivillage.cmd`, confirm the download, and wait for the `dist` folder to appear.
Python 3.11 or 3.12 and an internet connection are needed on the build machine. Distribute the
entire `dist/windows-<architecture>/aivillage` folder, not just the `.exe`.

## macOS and Linux

On the target machine, with Python 3.11 or 3.12:

```sh
python3 build_app.py --install
```

The output is `dist/macos-<architecture>/aivillage.app` or
`dist/linux-<architecture>/aivillage/aivillage`. On Linux, distribute the entire `aivillage`
folder. Linux builds may depend on the target system's compatible glibc and graphical libraries;
building on an older supported distribution improves compatibility. Desktop and display libraries
are still required. Do not assume a build supports a different processor or OS release without
testing it.

`--install` downloads dependencies into a temporary isolated environment. If your current Python
environment already has PyInstaller and all project dependencies, omit `--install`. Use
`--output /another/path` to choose a different destination. Existing build outputs are **never
replaced**; choose a new output directory for each build. The builder does not remove your saves or
settings.

## Create an installer

First build the app on the target OS and architecture as described above. Then run:

```sh
python build_installer.py
```

On Windows you can instead double-click `Build installer.cmd`. It requires **Inno Setup 6.7 or newer**
from <https://jrsoftware.org/isinfo.php>. The resulting setup `.exe` installs for the current user
and has an original pixel-art wizard background, panels and a branded icon. The desktop shortcut
is optional. The full-page background directives require Inno Setup 6.7 or later.

On macOS, install `dmgbuild` in the Python environment you use to run the installer builder. For
example, with the same Python architecture used for the app build:

```sh
python3 -m venv .installer-venv
source .installer-venv/bin/activate
python -m pip install 'dmgbuild>=1.6.5,<2'
python build_installer.py
```

The output is a branded `.dmg` containing the app and an Applications shortcut over a pixel-art
Finder background. Drag the app into Applications. Finder can override the custom view depending
on user settings. The builder also uses `sips`, `iconutil`, `codesign` and `hdiutil`; its ad-hoc
signature is not Apple notarization.

On Debian-based Linux, `dpkg-deb` creates a `.deb` with an application-menu entry and a custom
icon. Install it using your system's package manager; installation may require administrator
permission. Other Linux distributions should use the standalone folder. A Debian package is tied
to its architecture and may not run on every distribution or release. The package manager controls
its installation window and background, so the `.deb` cannot supply a custom installer background.

Installers are written to `dist/installers/`. Existing files are not overwritten. To package an
app from another location, use `python build_installer.py --app PATH --output OUTPUT_DIRECTORY`.
The supplied app **must** be a clean build for the current OS and Python interpreter architecture;
the installer builder does not inspect its binary architecture. It packages the entire supplied
folder, so do not place personal files in it. These tools create installers; they do not install
the program on the build machine or remove your saved village.

## GitHub Actions

The **Build desktop apps** workflow runs on pushes, pull requests, and manually from the repository's
Actions tab. Windows, macOS and Linux runners build native applications and installers. Open a workflow
run and download `aivillage-app-<OS>-<architecture>` for the standalone application or
`aivillage-installer-<OS>-<architecture>` for its installer. Extract the downloaded artifact; standalone
apps are inside a `.tar.gz` archive to preserve executable permissions and macOS links. The app artifact
is uploaded before installer creation, so it remains available if the installer step fails. Installer
jobs also check the output: Windows checks the executable header, macOS inspects the disk image, and
Linux inspects the Debian package. A failed installer build or check fails that platform's job.

Builds are not cross-compiled and only cover the architecture shown in the artifact name. Linux builds
use Ubuntu 22.04; compatibility with older distributions is not guaranteed. The workflow does not publish
GitHub Releases or sign or notarize builds. Workflow artifacts expire according to repository settings.

## Notes

- Builds are **unsigned**. Windows SmartScreen or macOS Gatekeeper may warn or block them; public
  distribution needs your own code-signing certificate, and macOS distribution may require Apple
  notarization. Windows installers are unsigned and macOS builds use only an ad-hoc signature;
  the builders do not provide trusted signing or notarization.
- Speech uses the installed voice backend and is best supported on Windows with SAPI. AI providers,
  subscriptions, API keys and Ollama models are not included in the app.
- Packaged apps keep their own settings and saves outside the bundle:
  `%LOCALAPPDATA%\aivillage` on Windows, `~/Library/Application Support/aivillage` on macOS,
  and `${XDG_DATA_HOME:-~/.local/share}/aivillage` on Linux. Source-run `data/` and `saves/` are
  not automatically migrated or overwritten.
- The application bundle can contain third-party dependencies; review their licences before
  distribution.
