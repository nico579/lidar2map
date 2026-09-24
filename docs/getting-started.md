# Getting started with lidar2map

***English** | [Français](getting-started.fr.md) · [Documentation index](README.md)*

This guide covers installation, the first launch, and the everyday graphical
workflow. For map formats and phone import, see [Formats and mobile apps](formats.md).
Building and publishing the application are documented separately in
[BUILD.md](../BUILD.md).

## 1. Choose how to run lidar2map

The standalone binary application is the normal choice for end users. It
contains its own Python runtime, dependencies, Java runtime, and osmosis; it
does not install them system-wide.

| | **Standalone binary application** | **Python script** |
|---|---|---|
| Requirements | None beyond a supported OS | Python 3.12 |
| First setup | No installation; the bundled runtime is extracted on first launch | About 5 minutes; automatic bootstrap into a private virtual environment |
| Updating | Download and extract the newer release | `git pull`, then launch again |
| Distributable | Yes: launcher/application and `lidar2map_bundle.zip` travel together | No: each computer prepares its own Python environment |
| Best suited to | End users and redistribution | Development, Linux source use, and contribution |

Publishing or patching the standalone archives is a maintainer workflow. The
build scripts, bundle architecture, and `update_app.py` release workflow are
covered only in [BUILD.md](../BUILD.md).

### 1.1. Standalone binary application

#### 1.1.1. Download and extract

Download the archive for your platform from the
[GitHub Releases page](https://github.com/nico579/lidar2map/releases), then
extract it without moving files inside the extracted folder.

| OS | Archive | Extract with |
|---|---|---|
| Windows 10/11, x86-64 | `lidar2map-windows-x86_64.zip` | File Explorer or `Expand-Archive` in PowerShell |
| Ubuntu 24.04+, x86-64 | `lidar2map-linux-x86_64.tar.gz` | `tar xzf lidar2map-linux-x86_64.tar.gz` |
| macOS 12+, Apple Silicon | `lidar2map-macos-arm64.zip` | `unzip`, then remove quarantine as shown below if Gatekeeper blocks the first launch |
| macOS 12+, Intel | `lidar2map-macos-x86_64.zip` | Same |

The extracted directory contains the launcher (`lidar2map.exe`, `lidar2map`,
or `LIDAR2MAP.app`) and `lidar2map_bundle.zip` side by side. Keep them together.
There is no system installation.

#### 1.1.2. Launch the binary application

| OS | How to start |
|---|---|
| Windows | Double-click `lidar2map.exe`. Starting it from a terminal also exposes the startup log. |
| Linux | Run `chmod +x lidar2map` once, then `./lidar2map` from the extracted directory. |
| macOS | Double-click `LIDAR2MAP.app`. If Gatekeeper blocks it, run `xattr -dr com.apple.quarantine LIDAR2MAP.app`, then double-click again. |

#### 1.1.3. First binary startup and runtime

The first launch extracts the bundle once and usually takes 30–60 seconds.
The extracted runtime is stored in:

- Windows: `%LOCALAPPDATA%\lidar2map\`
- macOS: `~/Library/Application Support/lidar2map/`
- Linux: `~/.local/share/lidar2map/`

Later launches reuse that copy.

### 1.2. Python script

On first launch, the script creates `~/.lidar2map/venv` and installs the
critical dependencies there: Pillow, pyproj, numpy, scipy, ijson, rasterio,
fiona, certifi, and pystray (tray icon). numba (much faster SVF) and osmium
(OSM pipeline) are installed when possible; a failure there does not block the
launch. The system Python environment is not modified. Use
`--bootstrap=none` if you prefer to manage the environment yourself.

Temurin 21 and osmosis are downloaded on demand. No system GDAL installation is
required because rasterio wheels include their own GDAL. Allow roughly 400 MB
for this one-time setup.

#### 1.2.1. Windows 10+

1. Install [Python 3.12 or newer](https://www.python.org/downloads/).
2. Clone and launch:

```powershell
git clone https://github.com/nico579/lidar2map
cd lidar2map
python lidar2map.py
```

#### 1.2.2. macOS 11+

```bash
brew install python@3.12
git clone https://github.com/nico579/lidar2map
cd lidar2map
python3.12 lidar2map.py
```

#### 1.2.3. Debian / Ubuntu

```bash
sudo apt install python3.12 python3.12-venv git
git clone https://github.com/nico579/lidar2map
cd lidar2map
python3.12 lidar2map.py
```

Linux/macOS cases such as PEP 668, distributions without `apt`, a desktop
without a system tray, and Gatekeeper on the Java runtime are covered in the
[BUILD.md troubleshooting section](../BUILD.md#9-dépannage).

## 2. First launch and graphical workflow — binary application or Python script

### 2.1. Open the graphical interface

Whether it is started from the standalone binary application or the Python
script, lidar2map run without arguments starts a small local web server and
opens the interface in your default web browser at `http://127.0.0.1:8766/`.
There is no separate application window: the browser you already use displays
the form. Supplying arguments starts a headless command-line job instead. The
interface detects English or French automatically and also provides a manual
language toggle.

By default the server listens only on this computer (`127.0.0.1`) and accepts
requests only from it; there is no account or password. Closing the browser tab
stops neither the server nor a running job: reopen the page from the tray icon
or at the same address.

### 2.2. Configure the first job

The form follows the processing workflow:

1. Give the project a name and choose its output/cache locations.
2. Define the area from a town, GPS coordinate, bounding box, département, or
   region, depending on the selected provider and country.
3. Select one of the five processing types: LiDAR, raster, vector, vector
   merge, or raster split.
4. Select the source and processing options. In LiDAR mode, the surface can be
   the provider DTM or, where supported, a classified point cloud processed in
   DFM mode with a class-based or CSF cloth ground base.
5. Select formats compatible with the target application, then run. See
   [Formats and mobile apps](formats.md).

![Main LiDAR form using a DTM surface](../screenshots/GUI/lidar_dtm.PNG)

### 2.3. Follow the job

The interface validates the form before starting and shows a live log while a
job is running.

### 2.4. Tray icon, stopping, and a second launch

While the server runs, a lidar2map icon sits in the system tray (notification
area):

| Menu entry | Effect |
|---|---|
| **Ouvrir** (Open) | Opens the interface in the browser again. |
| **Redémarrer** (Restart) | Stops a running job cleanly, then restarts the server with the same options. |
| **Arrêter** (Stop) | Stops a running job cleanly, then stops the server. |

A clean stop lets the current operation finish and close its files; it is
forced after 15 seconds if the job does not end.

If lidar2map is started again while a server already answers on port 8766:

- from a terminal, it asks whether to join the running interface (default:
  press Enter) or to start a second server on the next free port, for a job in
  parallel. The question follows the language chosen in the interface. On
  Windows, double-clicking `lidar2map.exe` opens a console window where it is
  asked;
- without a terminal (for example `LIDAR2MAP.app` opened from the Finder, or a
  Linux desktop shortcut), it joins the running interface: the page opens
  again and no second server starts;
- with `--no-browser` (start at login), it starts nothing.

To run a job in parallel without a terminal, use **➕ New instance** in the
interface: it starts a second server on the next free port and opens it in a
new tab, with its own tray icon to stop it. From a terminal,
`--serve-gui --new-instance` does the same without asking. Up to ten
consecutive ports are tried. Each server runs one job at a time.

On a desktop without a system tray (for example GNOME without the AppIndicator
extension) or on a machine without a display, start with
`--serve-gui --no-tray`, and add `--no-browser` if no browser should open; stop
the server with `Ctrl+C` in its terminal. On Linux without a display,
`--no-tray` is required. The server
options are listed in the
[CLI reference](cli.md#web-interface-server).

### 2.5. Start at login and remote access

The **🌐 Remote access** button opens two settings.

**Start at login.** The checkbox is labelled *Start with Windows* but also works
on macOS and Linux. It starts the server in the background at login, without
opening the browser: a script in the Windows Startup folder, a `launchd` agent
on macOS, or a `systemd --user` service on Linux. The interface is then
available from the tray icon or at `http://127.0.0.1:8766/`. With the
standalone application, the automatically started server uses the same
projects, cache, history, and preferences as a manual launch. If you enabled
this option with an earlier release, uncheck and re-check it once so that the
startup entry is rewritten.

**Trusted host.** To reach the interface from a phone over a mesh VPN such as
Tailscale or WireGuard, enter this computer's address on that network (for
example `100.x.y.z`, given by `tailscale ip`). The setting is saved and applied
immediately. The server must also listen on that address, which is a launch
option:

```bash
python lidar2map.py --serve-gui --bind 100.x.y.z --trusted-host 100.x.y.z
```

With the standalone application, pass the same options to the launcher.

Then open `http://100.x.y.z:8766/`, including on this computer: the page opened
automatically at launch still points to `127.0.0.1`, where this server no
longer listens. Do not use `--bind 0.0.0.0`. The server started at login
listens only on `127.0.0.1`, so it is not reachable through the VPN.

## 3. History, clean stops, and the processing queue

### 3.1. Crash-safe history

Every run remains in History with its state and logs, including interrupted or
failed runs.

### 3.2. Clean stop and resume

Processing can finish the current chunk cleanly; a manifest records completed
chunks so a later run can resume them instead of starting again.

### 3.3. Processing queue

`＋ Queue` stores several configured areas. `Run queue` processes them
unattended, and a failed item does not prevent the following items from
running.

Large areas can also be split into chunks or delegated to one or several VMs;
see the [remote execution guide](remote.md).

## 4. Index sheet

Every run normally creates `<product>_planche.png` next to its deliverables.
It shows the processed extent and numbered output cells, which is particularly
useful for a split project. The slight overlaps visible between cells are the
real edge tiles shared at low zoom levels.

The administrative-outline background is best effort: lidar2map uses a French
département outline or an equivalent geocoded boundary elsewhere. When offline
or when no boundary can be resolved, the sheet is still generated with the
extent and cells alone.

![Example index sheet for a VAT project split into a 3×4 grid](../screenshots/index_sheet.png)

The index sheet is enabled by default. `--no-index-map` disables it, and
`--index-sheet DIRECTORY` rebuilds it from an existing project.

## 5. Uninstall

Use `--desinstaller` with the binary launcher or Python script.

### 5.1. Standalone binary application

On Windows:

```powershell
lidar2map.exe --desinstaller
```

On Linux or macOS:

```bash
./lidar2map --desinstaller
```

### 5.2. Python script

```bash
python3.12 lidar2map.py --desinstaller
```

### 5.3. Removed and retained files

This removes the private virtual environment and installed tools/runtime. It
does not remove the launcher or source script.

---

[Formats and mobile apps →](formats.md) · [Documentation index](README.md)
