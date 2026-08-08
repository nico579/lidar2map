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

The first launch extracts the Qt-based bundle once and usually takes 30–60
seconds. The extracted runtime is stored in:

- Windows: `%LOCALAPPDATA%\lidar2map\`
- macOS: `~/Library/Application Support/lidar2map/`
- Linux: `~/.local/share/lidar2map/`

Later launches reuse that copy.

### 1.2. Python script

On first launch, the script creates `~/.lidar2map/venv` and installs the
critical dependencies there: Pillow, pyproj, numpy, rasterio, pywebview, and
PyQt6/QtWebEngine. The system Python environment is not modified. Use
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

Linux/macOS cases such as PEP 668, distribution Qt packages, Wayland, and
Gatekeeper on the Java runtime are covered in the
[BUILD.md troubleshooting section](../BUILD.md#9-dépannage).

## 2. First launch and graphical workflow — binary application or Python script

### 2.1. Open the graphical interface

Whether it is started from the standalone binary application or the Python
script, lidar2map opens the graphical interface when run without arguments.
Supplying arguments starts a headless command-line job instead. The interface
detects English or French automatically and also provides a manual language
toggle.

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
