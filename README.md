***English** | [Français](README.fr.md)*

# lidar2map

[![Smoke providers](https://github.com/nico579/lidar2map/actions/workflows/smoke.yml/badge.svg)](https://github.com/nico579/lidar2map/actions/workflows/smoke.yml)

**Offline archaeological LiDAR maps, multi-country + IGN raster/vector + OSM, for Locus Map / OsmAnd / TwoNav**

A self-contained tool that downloads public national LiDAR, computes relief
visualizations tuned for archaeological prospection, and generates offline
smartphone maps (MBTiles, RMAP, SQLiteDB, Mapsforge). See the dedicated
[LiDAR coverage and countries](#lidar-coverage-and-evaluated-sources) chapter;
IGN raster/vector maps remain France-only.

![Same place: satellite, OpenStreetMap, then LiDAR relief (SVF)](screenshots/hero.png)

*The same extent under three views: aerial imagery and the OSM map show nothing of the micro-relief, the Sky-View Factor computed from the HD LiDAR reveals it instantly.*

> ⚠️ **Status**: personal project, publicly released. Heavily tested on Windows 10/11. Linux and macOS tested partially, known cases + cross-OS troubleshooting in the *Troubleshooting* section of [BUILD.md](BUILD.md). Feedback welcome via [GitHub issues](https://github.com/nico579/lidar2map/issues).
>
> **Note:** the GUI auto-detects your language (English/French, with a manual toggle); the CLI flags and `--help` are in English.

---

## Who is it for?

- **Amateur archaeologists** interested in LiDAR prospection: the tool covers many [countries and national sources](#lidar-coverage-and-evaluated-sources), with the same relief computations (multi, SVF, openness, LRM, RRIM, VAT) from one provider to the next.
- **French hikers** who want offline IGN topo maps on their phone (Locus Map Pro, OsmAnd+): the IGN raster/vector tabs remain France-only.
- **Landscape surveyors** who combine historical orthophotos (1950-1995, France) with a DEM to spot human remains before agricultural land abandonment erases them.
- **Cavers / explorers** who need accurate base maps in areas not covered by mainstream apps.

The tool is **not** intended for metal detecting. The code strictly respects the open licenses involved (Etalab FR, CC BY 4.0 NO, CC-0 NL, BGDI CH).

## Main features

- **Multi-provider LiDAR**: national sources are isolated in `providers/<code>.py`; the [provider table](#available-providers) is the exhaustive list.
- **Raster maps**: IGN (France) and USGS NAIP (USA), see [Raster maps](#raster-maps).
- **Vector maps**: OSM Mapsforge (international) and IGN BD TOPO (France), see [Vector maps](#vector-maps).
- **Vector map merging**: `--merge` combines several GeoJSON files (glob accepted) into one, for example the IGN and OSM layers of one area, or the exports of neighbouring runs; can directly produce a Mapsforge `.map` or a `transparent-raster` overlay from the merged result.
- **Splitting and disk control**: `--split-width`, `--cleanup`, and `--min-free-gb` keep large jobs manageable.
- **Raster split**: `--split` re-splits an already-generated MBTiles after the fact, into a grid (`--cols`/`--rows`) or squares of a given width (`--split-width`), with optional per-chunk conversion to RMAP or SQLiteDB. Handy for staying under FAT32's 4 GB limit, or spreading a deliverable across several devices. All possible output formats: [Output formats and compatibility](#output-formats-and-compatibility).
- **Standalone cross-platform executables**: `lidar2map` runs with no Python to install on Windows, macOS, and Linux (GUI or CLI on the current computer); this is the standard way to use it, see [Installation](#installation).
- **Automatic bootstrap** (Python script): installs its dependencies and mapping tools on demand.
- **Memory streaming**: large areas are processed without loading all data into RAM.
- **Clean stop and resume**: `Ctrl+C` can wait for the current chunk, and a manifest tracks completed chunks for resumption.
- **Crash-safe history**: each run remains visible with its state and logs.
- **Interactive GUI**: five processing types, validation, live log, history, and processing queue.
- **Send to phone**: after generating, the GUI's 📲 button (or `--serve --zone-name X` in CLI) serves the maps over local WiFi and displays a QR code. Nothing leaves the network. In Locus, use **Map Manager → Import map → system file manager**.
- **Processing queue**: in the GUI, `＋ Queue` stacks several areas and `Run queue` processes them unattended; one failed job does not stop the following jobs.
- **Index sheet**: every run creates a `<product>_planche.png` showing the extent and output cells. `--index-sheet DIRECTORY` rebuilds it from an existing project and `--no-index-map` disables it.
- **Remote execution and multi-VM sharding**: `rlidar2map_GUI` prepares a remote RDP desktop on a VM; `rlidar2map_CLI` runs headless jobs with monitoring, reconnection, and result synchronization; `--block i/M` splits one area across several VMs running in parallel for large surfaces (e.g. a département split into 3 blocks, one VM each). Details: [Remote execution](#remote-execution-on-a-vm).

## What it produces

From a town, GPS coordinates, a bbox, a département or a whole region:

### Archaeological relief visualizations

Computed from national LiDAR (0.5 m to 1 m resolution depending on source):

| Type | What it reveals | Parameters |
|------|-----------------|------------|
| `multi` | Multidirectional hillshade (Mark 1992), general relief with reduced azimuth bias | `elevation` (° sun, default 25, low = micro-relief, 45 = general use) |
| `315` `045` `135` `225` | Directional hillshades, emphasize structures perpendicular to the chosen azimuth | `elevation` (same) |
| `slope` | Slope 0-90° stretched to 1-255, banks, breaks, terraces | (none) |
| `svf` | Sky-View Factor, fraction of visible sky: ditches, terraces, enclosures shown dark | `conv` (`flux` = cos²γ contrasted, default; `rvt` = 1−sin γ, the Kokalj/Hesse archaeology standard), `dist` (horizon radius in m, default 20, 20 = micro-relief, 100 = enclosures/roads), `gamma` (contrast, default 2.0) |
| `opos` | Positive openness (Yokoyama 2002), mean horizon angle above the horizontal: ridges, mounds, barrows shown bright | `dist`, `gamma` |
| `oneg` | Inverted negative openness, the "looking down" view: ditches, banks and hollow ways shown dark, the SVF's companion (inherently grainier: sensitive to DTM noise) | `dist`, `gamma` (applied mirrored: deepens hollows without darkening the background) |
| `lrm` | Simplified **Local Relief Model** (Gaussian SLRM), subtracting smoothed terrain to retain local anomalies. Fast and readable: the GUI default | `sigma` (Gaussian standard deviation in m; default 15 provider pixels) |
| `rrim` | lidar2map colour composite inspired by the **Red Relief Image Map** (RRIM, Chiba 2008): slope in red, SLRM as light/dark | `sigma` (of the internal SLRM) |
| `vat` | lidar2map composite inspired by **Visualization for Archaeological Topography**: SVF + positive openness + slope in grayscale | `dist` (SVF/openness radius in m, default 20), `gamma` (final contrast, default 2.0) |
| `e4mstp` | lidar2map variant inspired by the **published e4MSTP** (Kokalj 2025, *enhanced version 4* of **MSTP**, *Multiscale Topographic Position*): MSTP + SVF + O+/O− + slope + two SLRMs. Rich but expensive; differs from the exact RVT preset | `dist` (default 20), `gamma` (default 0.8) |

**[Detailed visualization guide: history, formulas, diagrams, strengths, limitations, and comparison workflow](docs/shadings.md).**

Two ways to request them:

```bash
# Simple: list of types, shared global parameters
--shadings multi svf oneg --svf-dist 20 --svf-gamma 2

# Parameterized instances (repeatable): each occurrence carries ITS OWN params
# → several instances of the same type in a single run
--shading svf:dist=20,gamma=2 --shading svf:dist=100,gamma=1.5 \
--shading oneg:dist=20 --shading 315:elevation=20 --shading lrm:sigma=10

# Resolution preset (opt-in): a stack (svf + opos + lrm + multi + slope) sized
# in METRES for the DEM resolution, so the same ground-scale features are
# targeted whether the DEM is 0.25 m or 5 m. 'auto' picks the tier per provider:
#   micro (<=0.75 m) / standard (~1 m) / landscape (>=5 m)
--shading-preset auto
```

Explicit parameters that differ from the defaults are encoded in the output
filename (`zone_svf_flux_100m_g1p5_ombrage.tif`, `zone_315_e20_ombrage.tif`):
no collision between instances, and already-computed shadings are reused.
In the GUI, the "to process" list (+/− buttons) does the same: each added
instance has its own little parameter form.
`--svf-sweep` / `--no-svf-sweep` (sweep-horizon kernel, SVF only) stays global.

LiDAR sources: choose `--provider <code>` in the CLI or use the GUI provider
selector. The [LiDAR coverage](#lidar-coverage-and-evaluated-sources) and
[provider table](#available-providers) are the single reference
for countries, resolutions, CRS, access mechanisms, and API keys.

> **Known limit: standing ruins.** National bare-earth DTMs *remove by
> design* walls still standing above ~1 m (the classifier files them as
> vegetation or "unclassified"), so no shading computed from the DTM can
> bring them back.
>
> Two ground bases built into the pipeline work around this: tick the
> **"DFM mode"** checkbox next to the provider (or CLI `--laz`) and every
> shading runs on a **DFM** (*Digital Feature Model*, Štular et al. 2021)
> computed from the classified point cloud instead of the DTM, with a
> choice between class-based re-injection (`--laz-ground classes`,
> default) or a **Cloth Simulation Filter** (`--laz-ground csf`, Zhang et
> al. 2016: cleaner background, ~3 min/tile instead of ~20 s). Full
> parameter list (`--laz-hmin/-hmax/-classes`, `--laz-csf-*`) in the
> [CLI reference for LAZ mode](#31-lidar). Cost:
> downloads the full COPC LAZ point cloud (~205 MB/km²), so keep the area
> small.
>
> For targeted prospection outside the pipeline (manual comparison in
> QGIS), [`tools/dfm_ruines.py`](tools/dfm_ruines.py) rebuilds the same
> kind of model as a standalone script and outputs georeferenced
> LRM-DTM / LRM-DFM / delta GeoTIFFs to drape over the orthophoto.
>
> DFM mode is not France-only: it also runs on Switzerland's
> swissSURFACE3D and on any provider that publishes a full, dense,
> classified point cloud (see the [provider table](#available-providers));
> a bare-earth DTM raster or a ground-only cloud cannot get it.

A roofless house ruin (walls ~1.5 m, dép. 83, France), under scrub. The
aerial photo barely hints at the walls; the classic LRM (from the DTM) shows
the terraces but not the ruin; the DFM brings the building footprint back,
and the CSF ground base cleans up the background.

| Aerial ortho | Classic LRM (from the DTM) |
|---|---|
| ![Aerial ortho, walls hidden under scrub](screenshots/LIDAR_Samples/Ruins/ortho.jpg) | ![LRM from the bare-earth DTM, ruin not visible](screenshots/LIDAR_Samples/Ruins/lrm.jpg) |
| Walls lost under vegetation | Terraces show, the ruin does not |
| **DFM-LRM (class re-injection)** | **DFM-LRM (CSF cloth base)** |
| ![DFM by class re-injection, walls reappear with speckle](screenshots/LIDAR_Samples/Ruins/dfm_lrm.jpg) | ![DFM with CSF cloth ground base, cleaner background](screenshots/LIDAR_Samples/Ruins/csf_lrm.jpg) |
| Rectangular building reappears (speckly) | Same walls, cleaner background |

Besides LiDAR, lidar2map also produces two more classic map families, with no relief computation:

### Raster maps

- **IGN** *(France only)*: Plan IGN, orthophotos (current + historical 1950, 1965, 1980), 19th-century État-Major, Pléiades satellite, CIR, etc.
- **USGS** *(USA, `--layer naip`)*: public-domain NAIP-derived aerial imagery (~1 m, cache complete to z16), pairs with the 3DEP LiDAR (`us-tnm`).

### Vector maps

OSM Mapsforge `.map` (international, via Geofabrik) or IGN BD TOPO *(France only)*. Both can also render as **`transparent-raster`**: the selected layers (paths, roads, rivers...) drawn on transparent tiles (.sqlitedb), to float above the LiDAR relief as an OsmAnd overlay (OsmAnd cannot overlay vector data natively).

### Output formats and compatibility

The generated formats are not interchangeable: choose the one matching the target
application. The table reflects how lidar2map writes each format (tiled raster,
Mapsforge vector map, or interchange GeoJSON).

| Generated format | Type written by lidar2map | Main applications | Recommendation |
|---|---|---|---|
| **MBTiles** (`.mbtiles`) | XYZ/TMS tiled raster (JPEG/PNG; alpha possible at edges) | **Locus Map**, **OruxMaps**, **AlpineQuest**, **Guru Maps**, QGIS | Most versatile raster format; recommended for Locus. OsmAnd does not use it directly as a raster map: request `sqlitedb` too or convert it. |
| **OsmAnd/RMaps SQLiteDB** (`.sqlitedb`) | Tiled raster in OsmAnd's expected SQLite schema | **OsmAnd** (map and overlay), RMaps; importable by Guru Maps and other RMaps-compatible apps | Recommended for OsmAnd. `transparent-raster` writes alpha-transparent PNG tiles intended for OsmAnd overlays. Prefer lidar2map's MBTiles output for Locus. |
| **RMAP** (`.rmap`) | Georeferenced raster with JPEG tiles (proprietary format) | **TwoNav / CompeGPS**, **OruxMaps**, AlpineQuest; limited support in Locus | Mainly for TwoNav/CompeGPS. lidar2map re-encodes tiles as JPEG as required by RMAP. |
| **Mapsforge** (`.map`) | OSM/IGN vector map in Mapsforge format | **Locus Map** and **OruxMaps** | Put it in the app's vector-map directory. It is not a raster; OsmAnd uses its own `.obf` vector format and cannot read it. |
| **GeoJSON** (`.geojson` or `.geojson.gz`) | Vector data (paths, roads, rivers, buildings...) | **Locus Map** (data import), **Guru Maps** (overlay), **QGIS**, geojson.io, GIS tools | Locus can import the features, but GeoJSON is not an offline map displayed like `.map` or MBTiles. Decompress `.gz` before importing into an app that does not handle gzip. For a real Locus vector map, use Mapsforge `.map`. |

References: [Locus — external formats](https://docs.locusmap.app/doku.php/manual%3Auser_guide%3Amaps_external), [OsmAnd — file formats](https://www.osmand.net/docs/technical/osmand-file-formats/), [TwoNav — RMAP](https://manual.twonav.com/manual/Manual_TwoNav_Tablet_22_en.pdf), [OruxMaps](https://www.oruxmaps.com/index_en.html), [AlpineQuest](https://www.alpinequest.net/en/help/v2/maps/file-based-select), [Guru Maps](https://gurumaps.app/docs/intro).

---

## Installation

**Quick start: download the standalone executable for your OS from the [Releases page](https://github.com/nico579/lidar2map/releases), extract, run. No Python, no dependencies, nothing to install.**

Two ways to use lidar2map:

| | **A. Standalone executable** | **B. Python script** |
|---|---|---|
| **Requirements** | None | Python 3.12 |
| **First install** | None | ~5 min (auto bootstrap in its own venv) |
| **Updates** | Patch the 3 existing binaries on the GitHub release in one command: `python update_app.py --release` (see [`update_app.py`](update_app.py)) | `git pull` + relaunch |
| **Distributable** | Yes, `.exe` / `.app` / Linux binary + zip bundle side by side | No, each user installs Python |
| **Best for** | end user / Windows / distributing | dev / Linux / contributing code |

### A. Standalone executable

The deliverable carries its own runtime: Python, dependencies, JRE, osmosis.

#### 1. Get the deliverable

**Option a, Download from [Releases](https://github.com/nico579/lidar2map/releases)** (if the version is published for your platform):

| OS | Archive | Extract with |
|----|---------|--------------|
| Windows 10/11 (x86_64) | `lidar2map-windows-x86_64.zip` | `Expand-Archive` (PowerShell) or double-click |
| Linux Ubuntu 24.04+ (x86_64) | `lidar2map-linux-x86_64.tar.gz` | `tar xzf` |
| macOS 12+ (Apple Silicon) | `lidar2map-macos-arm64.zip` | `unzip` then `xattr -dr com.apple.quarantine LIDAR2MAP.app` |
| macOS 12+ (Intel) | `lidar2map-macos-x86_64.zip` | same |

The archive extracts into a `lidar2map-<os>-x86_64/` folder containing the binary and its `lidar2map_bundle.zip` side by side. No system installation.

**Option b, Build it yourself.** Two scripts per platform: a machine setup (do **once**) then a build (re-run each time `lidar2map.py` is updated).

##### Windows

```powershell
git clone https://github.com/nico579/lidar2map
cd lidar2map
.\setup_build_windows.ps1     # 1. Setup: Python 3.12, deps, JRE, osmosis, PyInstaller
.\lidar2map_win_build.ps1     # 2. Build: 3 steps -> dist\lidar2map.exe + dist\lidar2map_bundle.zip
```

##### macOS (Apple Silicon or Intel)

```bash
git clone https://github.com/nico579/lidar2map
cd lidar2map
bash setup_build_mac.sh       # 1. Setup
bash lidar2map_mac_build.sh   # 2. Build -> dist/LIDAR2MAP.app
```

The archive takes the architecture of the machine it is built on
(`lidar2map-macos-arm64.zip` or `-x86_64.zip`). PyInstaller does not
cross-compile, so an Intel build requires an Intel Mac (or Rosetta 2 with an
x86_64 Python).

##### Linux (Ubuntu / Debian)

Linux reuses the Windows specs (`_win.spec` produces an ELF on Linux, the name is misleading).

```bash
git clone https://github.com/nico579/lidar2map
cd lidar2map
bash setup_build_linux.sh       # 1. Setup
bash lidar2map_linux_build.sh   # 2. Build -> dist/lidar2map + dist/lidar2map_bundle.zip
```

Requirement: `sudo apt install zip` if missing. The produced binary depends on the build machine's libc (build on Ubuntu 22.04 → runs on Ubuntu ≥ 22.04 / Debian 12+).

Full build documentation (bundle architecture, updating without rebuild, troubleshooting): **[BUILD.md](BUILD.md)**.

#### 2. Run the deliverable

| OS | Command |
|----|---------|
| Windows | Double-click `lidar2map.exe` (or run from a terminal to see the log) |
| Linux | `chmod +x lidar2map && ./lidar2map` in the extracted folder |
| macOS | Double-click `LIDAR2MAP.app`. First launch blocked by Gatekeeper: `xattr -dr com.apple.quarantine LIDAR2MAP.app` then double-click |
| Linux | `chmod +x lidar2map && ./lidar2map` |

The first launch extracts the bundle (~30-60 s, once, it contains Qt) into:
- Windows: `%LOCALAPPDATA%\lidar2map\`
- macOS: `~/Library/Application Support/lidar2map/`
- Linux: `~/.local/share/lidar2map/`

Clean uninstall: `lidar2map(.exe) --desinstaller`.
### B. Python script

On first launch, the script creates `~/.lidar2map/venv` and installs the critical dependencies there (Pillow, pyproj, numpy, rasterio, pywebview + PyQt6/QtWebEngine…): your system Python is never touched (`--bootstrap=none` if you prefer to manage the environment yourself). The Temurin 21 JRE and osmosis are downloaded on demand; no system GDAL needed, the rasterio wheels embed their own. ~400 MB total, **once**.

#### Windows 10+

1. Install [Python 3.12+](https://www.python.org/downloads/)
2. Get the code:
   ```powershell
   git clone https://github.com/nico579/lidar2map
   cd lidar2map
   python lidar2map.py
   ```

#### macOS 11+

```bash
brew install python@3.12
git clone https://github.com/nico579/lidar2map
cd lidar2map
python3.12 lidar2map.py
```

#### Linux (Debian / Ubuntu)

```bash
sudo apt install python3.12 python3.12-venv git
git clone https://github.com/nico579/lidar2map
cd lidar2map
python3.12 lidar2map.py
```

Troubleshooting: the *Troubleshooting* section of [BUILD.md](BUILD.md) (including Linux/macOS-specific cases: PEP 668, Qt distro packages, Wayland, Gatekeeper on the JRE…).


---

## Usage

Two local modes, selected automatically based on the arguments:

- **No argument → graphical interface** (pywebview / Qt). The common mode.
- **With arguments → command-line computation** (headless, no window).
  Handy for scripting, running on a server, or reproducing an exact render.

Everything below applies to the binary as well as the script, just replace
`python lidar2map.py` with `lidar2map.exe` (Windows), `./lidar2map` (Linux) or
`LIDAR2MAP.app` (macOS).

### Complete CLI parameter reference

The tables list the canonical options exposed by the actual parsers.
`python lidar2map.py <mode> --help` also prints mode-specific help.

Numbered like the GUI form: 1. project directories, 2. geographic area,
3. processing type (five types, 3.1 to 3.5, in tab order), 4. output format,
5. sharing/maintenance, 6. France-specific parameters.

#### 1. Project directories

| Parameter | Value / default | Function |
|---|---|---|
| `--zone-name NAME` | automatic | Project name; required with `--zone-gps` and `--zone-bbox`. |
| `--output-dir PATH` | `Projets/` | Deliverable root; the remote CLI reserves it to isolate sessions. |
| `--cache-dir PATH` | `cache/` | Root of persistent tile, WMTS, PBF, and discovery-index caches. |
| `--production-dir PATH` | `production/` | Reusable computed artifacts, notably TIFFs generated from LAZ. |

#### 2. Geographic area

| Parameter | Value / default | Function |
|---|---|---|
| `--zone-city NAME` | — | Geocodes a town with Nominatim. |
| `--zone-gps LAT,LON` | — | WGS84 centre, for example `43.3156,6.0423`. |
| `--zone-bbox W,S,E,N` | — | WGS84 extent in degrees. |
| `--zone-width KM` | `20` | Side of the square around a town/GPS point, not its radius. |

Département and region (France): see [France-specific parameters](#6-france-specific-parameters).

#### 3. Processing type

Five types, selected by a mode:

| Parameter | Function |
|---|---|
| *(no argument)* | Opens the graphical interface. |
| `-h`, `--help` | Prints help for the selected mode. |
| `--version` | Prints the version and exits. |
| `--lidar` | Downloads/processes LiDAR, computes relief visualizations, and generates raster maps. |
| `--raster` | Downloads a raster layer from the provider (`fr-ign`, or `us-tnm` with `naip`). |
| `--osm` | Generates a vector map: OSM Mapsforge, GeoJSON, or a transparent raster overlay (international). |
| `--vector` | Generates a vector map from IGN WFS (France, see below). |
| `--merge` | Merges several GeoJSON files. Requires `--source`. |
| `--split` | Splits an existing MBTiles after generation. Requires `--source`. |
| `--serve` | Sends a project's deliverables to the phone: serves the folder on the local WiFi with a URL and QR code. |
| `--index-sheet DIR` | Regenerates only the index sheet of an existing project. |

`--source PATH...`: existing source to reuse, depending on the mode: TIFF to
tiled raster, MBTiles to RMAP/SQLiteDB, PBF to OSM, or multiple GeoJSON files
with `--merge`.

##### 3.1 LiDAR

**3.1.1 Data source**

| Parameter | Value / default | Function |
|---|---|---|
| `--provider CODE` | `fr-ign` | LiDAR source; codes are in the [provider table](#available-providers). |
| `--api-key KEY` | environment variable supported | Provider key when required by the source. |
| `--laz` | off (computes from the DTM) | Switches to the classified point cloud (LAZ) to reconstruct standing structures; without it, lidar2map computes from the provider's official DTM. |
| `--laz-ground` | `[classes]\|csf` | Producer-class ground base or Cloth Simulation Filter. |
| `--laz-hmin M` | `0.4` | Minimum reinjected height with the `classes` ground base. |
| `--laz-hmax M` | `2.5` | Maximum reinjected height with the `classes` ground base. |
| `--laz-classes LIST` | `1,2,3,4,9,66` | Participating comma-separated LAS classes. |
| `--laz-csf-threshold M` | `0.5` | CSF point-to-cloth absorption distance. |
| `--laz-csf-resolution M` | `0.5` | CSF cloth grid size. |
| `--laz-csf-rigidness` | `[1]\|2\|3` | CSF rigidity for steep, intermediate, or flat terrain. |
| `--laz-parallel N` | `1` | Concurrent LAZ conversions; allow roughly 3 GB RAM per conversion. |

**3.1.2 Pre-split (large areas)**

| Parameter | Value / default | Function |
|---|---|---|
| `--split-cols N` | `1` | Number of columns for splitting before processing. |
| `--split-rows N` | `1` | Number of rows for splitting before processing. |
| `--split-width KM` | — | Splits into squares approximately `KM` km wide, alternative to the grid. |
| `--block i/M` | — | Processes only block `i` of `M`, to distribute an area across machines. |
| `--cleanup` | off | Deletes intermediates after each successful chunk. |
| `--cleanup-keep-tiles` | off | With `--cleanup`, preserves shared downloaded tiles. |
| `--min-free-gb GB` | off | Clean exit code 3 before a chunk when free space falls below the threshold. |

**3.1.3 Download**

| Parameter | Value / default | Function |
|---|---|---|
| `--download` | off | Downloads missing tiles. |
| `--workers N` | `8` | Parallel connections. |
| `--download-compress` | on | DEFLATE compression of cached tiles. |
| `--download-force` | off | Downloads already-cached tiles again. |
| `--download-overwrite` | off | Overwrites and downloads cached data again; equivalent to `--download-force`. |
| `--tiles-dir PATH` | below project | Separate tile cache, takes priority over `--cache-dir`. |

**3.1.4 Compute relief visualizations**

| Parameter | Value / default | Function |
|---|---|---|
| `--shadings TYPE...` | interactive | Types: `lrm vat e4mstp svf opos oneg rrim multi 315 045 135 225 slope`, plus `all`/`none`. |
| `--shading TYPE[:k=v,...]` | repeatable | Adds a parameterized instance, for example `svf:dist=100,gamma=1.5`. Per-type parameters below. |
| `--shading-preset` | off; `auto`\|`micro`\|`standard`\|`landscape` | Adds a resolution-tuned SVF, openness, LRM, multi, and slope stack. |
| `--shading-elevation DEG` | `25` | Sun elevation for directional/multidirectional hillshades. |
| `--svf-conv` | `[flux]\|rvt` | Sky-View Factor convention. |
| `--svf-dist M` | `20` | Horizon radius for SVF, openness, and composites. |
| `--svf-gamma G` | `2.0` | Final gamma for SVF, openness, and VAT. |
| `--svf-sweep` / `--no-svf-sweep` | on | Enables or disables the accelerated SVF kernel. |
| `--shadings-overwrite` | off | Recomputes existing relief TIFFs. |
| `--shadings-compress` | off | Compresses existing raw relief TIFFs. |

Parameters accepted by `--shading TYPE:k=v,...`, by relief type:

| Parameter | Applies to | Value / default | Function |
|---|---|---|---|
| `elevation` | `multi 315 045 135 225` | degrees, `[25]` | Sun elevation of the hillshade; low = grazing light/micro-relief, high = general use. |
| `conv` | `svf` | `[flux]\|rvt` | Sky-View Factor calculation convention. |
| `dist` | `svf opos oneg vat e4mstp` | metres, `[20]` | Horizon radius used for the calculation. |
| `gamma` | `svf opos oneg vat` | `[2.0]` | Final contrast applied to the result. |
| `gamma` | `e4mstp` | `[0.8]` | Final contrast applied to the result. |
| `sweep` | `svf` | boolean, `[on]` | Enables the accelerated SVF kernel (horizon sweep). |
| `sigma` | `lrm rrim` | provider pixels, `[15]` | Gaussian smoothing standard deviation (SLRM); larger = wider relief retained. |
| *(none)* | `slope` | — | No tunable parameter. |

**3.1.5 Generate the map**: zoom, image format, and file formats are shared
across all types, see [Output format](#4-output-format).

##### 3.2 Raster

**3.2.1 Data source**

| Parameter | Value / default | Function |
|---|---|---|
| `--provider CODE` | `fr-ign` | `fr-ign` (France, WMTS) or `us-tnm` (USA, with `--layer naip`). |
| `--layer LAYER` | `planign` | Alias or full WMTS identifier; full catalogue in [France-specific parameters](#6-france-specific-parameters). |
| `--api-key KEY` | — | `cartes.gouv.fr` key, required only for professional IGN Scan layers. |

**3.2.2 Pre-split**: same parameters as LiDAR above (`--split-cols`,
`--split-rows`, `--split-width`, `--cleanup`, `--min-free-gb`), without
`--block` or `--cleanup-keep-tiles`.

**3.2.3 Download**

| Parameter | Value / default | Function |
|---|---|---|
| `--workers N` | `8` | Parallel connections. |

**3.2.4 Generate the map**: see [Output format](#4-output-format).

##### 3.3 Vector

**3.3.1 Data source**

| Parameter | Value / default | Function |
|---|---|---|
| `--osm` | — | OSM / Geofabrik source (PBF), international. |
| `--vector` | — | IGN Géoplateforme source (WFS), France only. |
| `--layer TAGS...` with `--osm` | default if omitted: `highway=* waterway=* boundary=administrative natural=water natural=coastline waterway=river waterway=stream waterway=canal` | OSM tags to include (free-form, any `key=value`). Catalogue offered by the GUI: `highway=* waterway=* natural=water natural=* boundary=administrative landuse=* building=* historic=*`. |
| `--layer NAME...` with `--vector` | `[cadastre]` | IGN layers, full catalogue in [France-specific parameters](#6-france-specific-parameters). |
| `--zone-region SLUG` with `--osm` | — | The Geofabrik regional PBF already matches the administrative boundary: used as-is instead of being re-clipped to a rectangular bbox (faster, keeps the real outline, France). |

**3.3.2 Download**

| Parameter | Value / default | Function |
|---|---|---|
| `--workers N` | `4` | Parallel connections; the IGN WFS caps concurrency at 4, beyond which layers start failing. |

**3.3.3 Generate the map**

| Parameter | Value / default | Function |
|---|---|---|
| `--vector-simplify M` | automatic | Douglas-Peucker tolerance in metres for vector outputs. |

File formats: see [Output format](#4-output-format).

##### 3.4 Vector merge

| Parameter | Value / default | Function |
|---|---|---|
| `--source PATH...` | required | GeoJSON files to merge, glob accepted. |
| `--output-file FILE` | automatic | Name of the merged GeoJSON. |
| `--no-gz` | off | Writes uncompressed `.geojson` instead of `.geojson.gz`. |
| `--vector-simplify M` | automatic | Douglas-Peucker tolerance in metres for the merged result. |

File formats: see [Output format](#4-output-format).

##### 3.5 Raster split

| Parameter | Value / default | Function |
|---|---|---|
| `--source PATH` | required | MBTiles to re-split. |
| `--cols N` | `1` | Columns of the splitting grid. |
| `--rows N` | `1` | Rows of the splitting grid. |
| `--split-width KM` | — | Splits into squares approximately `KM` km wide, alternative to the grid. |

File formats: see [Output format](#4-output-format).

#### 4. Output format

| Parameter | Value / default | Function |
|---|---|---|
| `--file-formats FMT...` | LiDAR/raster/split: `mbtiles rmap sqlitedb`; vector/merge: `map geojson gz transparent-raster` | File formats to generate, mode-dependent. |
| `--zoom-min N` | `13` LiDAR, `10` raster | Minimum tiled-map zoom. |
| `--zoom-max N` | `18` LiDAR, `16` raster | Maximum tiled-map zoom. |
| `--image-format` | `[auto]\|jpeg\|png` | Raster tile encoding. Edge tiles may remain alpha PNG. |
| `--image-quality Q` | `85` | JPEG quality from 1 to 100. |
| `--tiles-overwrite` | off | Regenerates existing MBTiles, SQLiteDB, RMAP, or Mapsforge files. |
| `--index-map` | on | Generates `<product>_planche.png` (extent, split grid, numbered cells). |

#### 5. Sharing and maintenance

| Parameter | Mode | Function |
|---|---|---|
| `--serve` | — | Sends a project's deliverables to the phone: serves the folder on the local WiFi with a URL and QR code. |
| `--zone-name NAME` | with `--serve` | Project to send to the phone. |
| `--tiles-purge-invalid` | LiDAR | Removes undersized or invalid cached tiles. |
| `--tiles-purge-out-of-zone` | LiDAR | Removes cached tiles outside the requested area. |
| `--bootstrap` | `[auto]\|pip\|none` | Startup: automatic venv, installation in the active environment, or no installation. |
| `--help-bootstrap` | startup | Prints bootstrap help. |
| `--installer-deps` | maintenance/build | Installs all dependencies, including optional ones, then exits. |
| `--telecharger-outils` | maintenance/build | Downloads the JRE, osmosis, and mapwriter, then exits. |
| `--desinstaller` | maintenance | Removes the venv and installed tools, but not the script/executable. |
| `--smoketest` | validation | Runs the built-in validation of the main pipelines. |

#### 6. France-specific parameters

| Parameter | Value / default | Function |
|---|---|---|
| `--zone-department NUM` | — | French département. Accepts one number, a list (`30,35,75`), or a range (`1-10`). |
| `--zone-region SLUG` | — | French Geofabrik region; with `--osm`, the regional PBF is used as-is (already at the region's boundary) instead of being re-clipped to a rectangular bbox. |
| `--vector` | — | Downloads IGN WFS layers and produces `geojson`, `gz`, `map`, or `transparent-raster`. |
| `--layer NAME...` with `--vector` | `[cadastre]` | IGN layers: `cadastre cours_eau troncons_eau plans_eau detail_hydro batiments constructions cimetieres routes chemins lignes_orog detail_orog forets reserves lieux_dits communes rpg`. |
| `--raster --provider fr-ign` | — | IGN WMTS raster. |
| `--layer LAYER` with IGN raster | `[planign]` | Public topo: `planign etatmajor40 etatmajor10 pentes`. Public imagery: `ortho ortho_1950 ortho_1965 ortho_1980 ortho_irc pleiades spot edugeo_marseille_1969 edugeo_marseille_1980 edugeo_marseille_1987 edugeo_marseille_1988 edugeo_marseille_2010 edugeo_toulon_1972`. Public thematic: `cadastre ombrage`. Professional, key required: `scan25 scan25tour scan100 scanoaci`. |
| `--api-key KEY` with IGN raster | — | `cartes.gouv.fr` key for `scan25`, `scan25tour`, `scan100`, and `scanoaci`; unnecessary for public layers. |

### Command-line examples

**SVF relief + IGN topo map over a town (2 km zone around Garéoult, France):**
```bash
python lidar2map.py --lidar --zone-city Gareoult --zone-width 2 \
    --shadings multi svf --file-formats mbtiles
```

**Historical 1950-1965 orthophoto over an archaeological survey area:**
```bash
python lidar2map.py --raster --zone-bbox 6.0,43.3,6.1,43.4 \
    --layer ortho_1950 --zoom-min 14 --zoom-max 18
```

**OSM vector map (Mapsforge .map) for Locus, whole département:**
```bash
python lidar2map.py --osm --zone-department 83 --file-formats map
```

**Whole region (`--zone-region`), available for all modes:**
```bash
# OSM: a single map for the whole region, no re-splitting
# (the Geofabrik PBF IS already regional, far faster than looping per département)
python lidar2map.py --osm --zone-region provence-alpes-cote-d-azur
# IGN vector: paths/routes for the whole region as GeoJSON + Locus .map
python lidar2map.py --vector --zone-region provence-alpes-cote-d-azur \
    --layer chemins --file-formats gz map
```
The slug is the one from [Geofabrik France](https://download.geofabrik.de/europe/france.html) (old-style regions: `provence-alpes-cote-d-azur`, `bretagne`, `corse`, `rhone-alpes`…). In OSM the region is processed as one block (the Geofabrik file is already regional, no per-département geocoding); for the raster/vector/lidar modes the area is the bbox enclosing all the départements of the region. An unknown slug lists the available regions.

**IGN BD TOPO map (roads + buildings) as compressed GeoJSON + Mapsforge .map:**
```bash
python lidar2map.py --vector --zone-department 83 \
    --layer routes batiments --file-formats gz map
```
The `map` format converts the IGN GeoJSON into a Mapsforge `.map` map (readable by Locus Map; OsmAnd uses its own OBF vector format and cannot read Mapsforge files, but its built-in offline map already provides the vector layer, so on OsmAnd simply put the LiDAR raster on top as an overlay).

## Remote execution on a VM

For large surfaces (a whole département, several regions), lidar2map can run
on a compute VM instead of the local computer, with multi-VM sharding via
`--block i/M`. All three programs are standalone on Windows, Linux and macOS:

| Program | Use | How it works |
|---|---|---|
| `lidar2map` | Local processing | GUI or CLI on the current computer |
| `rlidar2map_GUI` | Remote graphical desktop | prepares an Ubuntu 24.04/26.04 VM with XFCE + xrdp, installs lidar2map, then opens the RDP client |
| `rlidar2map_CLI` | Headless remote processing | installs and starts lidar2map in `tmux`, monitors the run, and progressively synchronizes its results |

The remote clients require no Python installation on the originating computer.
They are published alongside lidar2map on the [Releases page](https://github.com/nico579/lidar2map/releases).
The [Run lidar2map on a VM](tools/README_rlidar2map.md) guide covers the GUI/CLI
choice, SSH connection, RDP account, long-running jobs, splitting a job across
multiple machines with `--block i/M`, and supported platforms.

## LiDAR providers and coverage

### Available providers

| Code | Country | Dataset | Res. | Native CRS | Access & specifics |
|---|---|---|---|---|---|
| `fr-ign` | France *(default)* | IGN LiDAR HD | 0.5 m | EPSG:2154 (Lambert-93) | Vector TMS PBF + WMS GetMap, national coverage (mainland) |
| `fr-reunion` · `fr-guadeloupe` | France (Réunion, Guadeloupe DROM) | IGN LiDAR HD | 0.5 m | EPSG:2975 / 5490 (UTM40S / UTM20N) | WFS `IGNF_MNT-LIDAR-HD:dalle` index (each tile feature carries its direct download `url`), 0.5 m GeoTIFF, Licence Ouverte 2.0 (Martinique/Mayotte announced but WFS empty for now) |
| `fr-ign` + **DFM mode** | France (**standing-ruins mode**, experimental) | DFM from classified LiDAR HD point cloud | 0.5 m | EPSG:2154 (Lambert-93) | GUI checkbox "DFM mode" (or CLI `--laz`): downloads the **COPC LAZ** tiles (~205 MB/km²!) and rebuilds the model from the default ground base `--laz-ground classes` (class set `1,2,3,4,9,66`: classes 2/9/66 = terrain base as in the official DTM, the others re-injected into ground gaps) or `--laz-ground csf`. **Can re-introduce returns compatible with standing walls** that the DTM erases (candidates, not a wall classifier: scrub comes back too; see "Known limit" box). Full tuning parameters (`--laz-hmin/-hmax/-classes`, `--laz-csf-*`): [CLI reference](#31-lidar). Zone name auto-suffixed (`_laz_dfm` / `_laz_csf`), so point-cloud outputs never mix with DTM ones. The LAZ is kept in the tile cache: changing the settings re-converts without re-downloading. Targeted prospection of a few km², not large maps |
| `nl-ahn` | Netherlands | AHN4/5 | 0.5 m | EPSG:28992 (RD New) | ATOM feed + JSON FeatureCollection, national coverage |
| `ch-swisstopo` | Switzerland | swissALTI3D | 0.5 m | EPSG:2056 (CH1903+/LV95) | STAC REST API, national coverage |
| `ch-swisstopo` + **DFM mode** | Switzerland (**standing-structures mode**, experimental) | DFM from classified swissSURFACE3D point cloud | 0.5 m | EPSG:2056 (CH1903+/LV95) | GUI checkbox "DFM mode" (or CLI `--laz`) on the Swiss provider: downloads the **swissSURFACE3D `.las.zip`** tiles (~125 MB/km²) via the same STAC API, unzips the point cloud and rebuilds the standing-structures model. Default ground base is **CSF** (`--laz-ground csf`, Cloth Simulation Filter) since swisstopo's class codes are not guaranteed IGN-compatible; the `classes` mode is also available. Same per-site tuning and cache-then-retune behaviour as the France DFM (~6 min/tile). Targeted prospection, field validation recommended |
| **+ LAZ mode (other providers)** | Poland, Estonia, Flanders, Canada (NRCan + Quebec), USA, Denmark, France (CRAIG) | DFM/CSF from the national classified point cloud | 0.5 m | *(each provider's CRS)* | **LAZ mode** (`--laz`) also runs on providers whose country publishes the full classified point cloud: `pl-gugik-laz`, `ee-maaamet-laz`, `be-flanders-laz`, `ca-nrcan-laz` (windowed COPC), `us-3dep-laz` (windowed COPC, no account), `ca-quebec-laz`, `dk-datafordeler-laz` (API key), `fr-craig-laz`. Same DFM/CSF machinery as fr/ch; density, classes and CRS vary. Details: `docs/lidar_providers_roadmap.md`. Experimental, targeted prospection |
| `no-kartverket` | Norway | Nasjonal Høydemodell | 1 m | EPSG:25833 (UTM33N) | ArcGIS ImageServer exportImage, national coverage |
| `se-lantmateriet` | Sweden | Markhöjdmodell (laser) | 1 m | EPSG:3006 (SWEREF99 TM) | STAC + 10 km mosaic COG (windowed read), national coverage; **free GeoTorget account** (env `LANTMATERIET_USER`/`LANTMATERIET_PASS`) for the download |
| `de-bayern` · `de-nrw` · `de-niedersachsen` · `de-rlp` | Germany (4 Länder: Bavaria, NRW, Lower Saxony, Rhineland-Palatinate) | DGM1 | 1 m | EPSG:25832 (UTM32N) | metalink / index.json / STAC COG, open data (de-rlp: Metalink index of ~21k GeoTIFF tiles, post_fetch strips the compound vertical CRS to 25832) |
| `de-thueringen` · `de-berlin` · `de-sh` | Germany (Thuringia, Berlin, Schleswig-Holstein) | DGM / DGM1 | 1-2 m / 1 m | EPSG:25832 / 25833 (UTM32N/33N) | Spatial index (ATOM or GeoJSON) → XYZ text tiles (post_fetch → GeoTIFF), open data (Thuringia/SH CC BY / dl-de/by-2-0, Berlin dl-de/zero-2-0) |
| `de-hessen` · `de-bw` · `de-mv` · `de-st` · `de-brandenburg` | Germany (Hesse, Baden-Württemberg, Mecklenburg-Vorpommern, Saxony-Anhalt, Brandenburg) | DGM1 | 1 m | EPSG:25832/25833 (UTM32N/33N) | WCS 2.0.1 INSPIRE GetCoverage, open data dl-de/by-2-0 (de-mv/de-st found via the GDI-DE catalog auto-discovery) |
| `at-bev` | Austria (national) | ALS-DGM | 1 m | EPSG:3035 (LAEA Europe) | ATOM index + 50 km mosaic COG (windowed read via `/vsicurl`), latest survey per tile, CC BY 4.0 (BEV) |
| `at-tirol` · `at-osttirol` | Austria (Tyrol + East Tyrol) | DGM | 0.5 m | EPSG:31254/31255 (MGI M28/M31) | WCS 1.0.0 GetCoverage (tiris), finer than `at-bev` over Tyrol |
| `gb-england` · `gb-wales` | United Kingdom | LIDAR Composite DTM | 1 m | EPSG:27700 (OSGB36) | WCS 2.0.1 / WFS catalogue (EA / NRW) |
| `gb-scotland` | United Kingdom (Scotland) | Scottish Public Sector LiDAR DTM | 0.5 m | EPSG:27700 (OSGB36) | Public AWS S3 bucket (no account), OS-grid tile listing (`ListObjectsV2`) → COG, modern 50 cm coverage (national programme + Orkney) |
| `be-flanders` | Belgium (Flanders + Brussels) | DHMV II DTM | 1 m | EPSG:31370 (Lambert 1972) | WCS 2.0.1, also exposes pre-computed 25 cm SVF and multi-hillshade |
| `lu-act` | Luxembourg | BD-L-Lidar 2024 DTM | 0.5 m | EPSG:2169 (LUREF) | Single national COG (~40 GB) read **windowed** via `/vsicurl` HTTP range, never downloads the whole file; CC0 |
| `fi-maanmittauslaitos` | Finland | Elevation Model | 2 m | EPSG:3067 (TM35FIN) | WCS 2.0.1, free API key required, national coverage |
| `dk-datafordeler` | Denmark | DHM DTM | 0.4 m | EPSG:25832 (UTM32N) | WCS 1.0.0, free API key required, national coverage |
| `ie-gsi` | Ireland | LiDAR DTM | 1 m | EPSG:2157 (ITM) | ArcGIS FeatureServer → ZIP (post_fetch), ~60% coverage, CC BY 4.0 |
| `cz-cuzk` | Czechia | DMR 5G | 1 m | EPSG:5514 (S-JTSK/Krovak) | Atom INSPIRE 2-level → LAZ (post_fetch, requires `lazrs`), national coverage |
| `si-arso` | Slovenia | DMR1 (2011-2015 LiDAR) | 1 m | EPSG:3794 (D96/TM) | ArcGIS REST fishnet index + x;y;z text tiles → GeoTIFF (post_fetch), national coverage |
| `ee-maaamet` | Estonia | DTM 1 m (2021-2024 ALS) | 1 m | EPSG:3301 (L-EST97) | Direct per-sheet URLs, 1:10000 grid (sheet numbering = pure formula, no index), national coverage, open data |
| `lv-lgia` | Latvia | DTM 1 m (LiDAR ALS) | 1 m | EPSG:3059 (LKS-92/TM) | S3 index of ~66k classified LAS tiles → download → class-2 binning to GeoTIFF with hole-fill (requires `laspy`), national coverage, CC BY 4.0 (tile extents measured from LAS headers, TKS-93 sheet grid) |
| `es-cnig` | Spain | MDT | 5 m | EPSG:25830 (UTM30N) | WCS 2.0.1 INSPIRE, 5 m = landscape scale (the 2 m bare-earth LiDAR requires the session-based CNIG portal) |
| `es-icgc` | Spain (Catalonia) | MET LiDAR | 0.5 m | EPSG:25831 (UTM31N) | Single regional COG (~433 GB) read **windowed** via `/vsicurl` HTTP range, 50 cm, far finer than es-cnig 5 m; CC BY 4.0 (ICGC) |
| `es-euskadi` | Spain (Basque Country) | MDT LiDAR | 1 m | EPSG:25830 (UTM30N) | WCS 1.0.0 (ArcGIS MapServer WCSServer, geoEuskadi), 1 m bare-earth, far finer than es-cnig 5 m; CC BY 4.0 |
| `es-navarra` | Spain (Navarre) | MDT LiDAR | 2 m | EPSG:25830 (UTM30N) | WCS 2.0.1 INSPIRE (IDENA), 2 m bare-earth, NoData 3.4e38; CC BY 4.0 |
| `pt-dgt` | Portugal | MDT LiDAR (2024) | 0.5 m | EPSG:3763 (PT-TM06) | OGC-API + POST /search (CQL2), national coverage; **free DGT account** (env `DGT_USER`/`DGT_PASS`) for the authenticated download |
| `it-emilia-romagna` | Italy (Emilia-Romagna) | DTM (RER) | 5 m | EPSG:7791 (RDN2008/UTM32N) | WCS 2.0.1 GetCoverage, regional coverage, CC BY 4.0 (the 0.5 m LiDAR 2023/24 is served once its coverage completes) |
| `it-sardegna` | Italy (Sardinia) | DTM (RAS) | 1 m | EPSG:7791 (RDN2008/UTM32N) | WCS 2.0.1 GetCoverage (GeoServer), island-wide LiDAR mosaic with gaps (coast, towns, Gallura, river bands), clean nodata off-coverage, CC BY 4.0 |
| `it-piemonte` | Italy (Piedmont) | DTM (ICE LiDAR) | 5 m | EPSG:32632 (UTM32N) | WCS 1.0.0 GetCoverage (MapServer), `format=image/tiff` for the real Float32 (GTiff returns quantised UInt8), NoData -99, CC BY 4.0 |
| `pl-gugik` | Poland | NMT (ISOK project) | 1 m | EPSG:2180 (PUWG 1992) | WCS 2.0.1, open data, national coverage |
| `ca-nrcan` | Canada | HRDEM Mosaic | 1 m | EPSG:3979 (LCC Canada) | STAC + mosaic COG (windowed read), ~95% of population |
| `us-tnm` · `us-3dep` | USA | 3DEP | 1 m | EPSG:3857 | TNMAccess direct S3 (no account) / OpenTopography (free key) |
| `us-cnmi` | Northern Mariana Islands (US territory) | Topobathy DEM | 1 m | EPSG:8693 (NAD83(MA11)/UTM55N) | Single NOAA mosaic **VRT** read windowed via `/vsicurl` (bucket `noaa-nos-coastal-lidar-pds`), ground-class bare earth on land + bathymetry offshore, public domain (pattern for a generic NOAA provider) |
| `jp-gsi` | Japan (partial) | DEM5A (GSI 標高タイル) | 5 m | EPSG:3857 | Open elevation XYZ **text tiles**, no account (post_fetch → GeoTIFF), partial 5 m coverage (rivers/plains/populated) |
| `ph-taal` | Philippines (Taal volcano area only) | DTM 1 m (UP TCAGP) | 1 m | EPSG:32651 (UTM51N) | Static GeoJSON tile grid → direct GeoTIFF on S3 (`<GRIDREF>_DTM.tif`), ~20 km around Taal volcano, open data |
| `nz-linz` | New Zealand | National seamless DEM | 1 m | EPSG:2193 (NZTM2000) | LINZ S3 STAC + COG (windowed read) |
| `au-qld` · `au-nsw` | Australia (QLD 0.5 m · NSW 5 m) | LiDAR DEM | 0.5-5 m | EPSG:3857 | ArcGIS ImageServer (ELVIS), **per-state** coverage |
| `au-ga` | Australia (national, scattered) | DEM derived from LiDAR | 5 m | EPSG:3857 (served as 4283) | WCS 1.0.0 GetCoverage (Geoscience Australia) → reprojected on download, ~245,000 km² across all states (coastal + Murray-Darling), opens SA/VIC/TAS/WA beyond QLD·NSW |

Selection: `--provider <code>` flag (CLI), `LIDAR2MAP_PROVIDER` env var, or the dropdown at the top of the GUI.

### LiDAR coverage and evaluated sources

![lidar2map LiDAR coverage map](coverage.png)

The colour map summarizes the available national coverage. Interactive version
(click = `NAME` + code):

🗺️ **[Interactive coverage map](coverage.geojson)**, rendered directly by GitHub, or droppable into [geojson.io](https://geojson.io) / QGIS to test a point.

The map is regenerated by `coverage_map.py`, which reads zone titles from `providers/*.py`, so the map and the GUI can't drift. Clicking a zone in the interactive GeoJSON shows its `NAME` and code(s).

**🇺🇸 USA & 🇨🇦 Canada, supported and working, just not drawn.** `us-tnm` / `us-3dep` (3DEP 1 m) and `ca-nrcan` (HRDEM 1 m) are fully functional, but their coverage is **project/population-based** (not wall-to-wall national), so a full-country polygon would over-claim, hence the note rather than a shape. Check your US area on the [TNM Downloader](https://apps.nationalmap.gov/downloader/). The USGS 1 m tiles are 10×10 km COGs, **read windowed** to your bbox via `/vsicurl/`, no full-tile download.

### Adding a LiDAR provider

The provider abstraction adds a national or regional source without changing
the core pipeline. Each `providers/<code>.py` module exposes at least its
metadata, geometry, and discovery function:

```python
NAME, CODE, COUNTRY, LICENSE
CRS_NATIF, RESOLUTION_M, DALLE_KM

def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    ...  # returns {tile_name: URL_or_source}
```

Optional hooks handle special cases, notably `post_fetch` for unpacking or
converting LAZ/ZIP tiles to GeoTIFF. The downstream pipeline (relief
visualizations, EPSG:3857 reprojection, tiling, and output formats) remains
provider-agnostic: it consumes the discovered GeoTIFF files regardless of the
native CRS or access mechanism.

A source fits directly when it exposes **deterministic tile URLs**, a **WCS**
(`GetCoverage` by extent), a **STAC** catalogue, window-readable mosaic
**COGs**, an **ATOM/FeatureServer** index, or convertible **LAZ/ZIP** tiles.
Form or email orders, rendered-only WMS services with no raw elevation, and
files with no CRS require extra work or do not fit the current pipeline.

The [provider roadmap](docs/lidar_providers_roadmap.md) centralizes every
evaluated source—integrated or set aside—with its state and precise reason. To
propose a new source, open an issue or PR and start from the existing provider
whose access mechanism is the closest match.

## Screenshots

### Graphical interface

Five processing types: LiDAR, raster, vector, vector merge and raster splitting. The LiDAR tab covers both surfaces, the DTM raster and the LAZ point cloud (DFM "standing structures" mode, with a class-based or CSF cloth ground base).

| LiDAR (DTM surface) | LiDAR (LAZ, class-based ground) | LiDAR (LAZ, CSF cloth ground) |
|---|---|---|
| ![LiDAR tab, DTM surface](screenshots/GUI/lidar_dtm.PNG) | ![LiDAR tab, LAZ point cloud with class-based ground](screenshots/GUI/lidar_laz_classes.PNG) | ![LiDAR tab, LAZ point cloud with CSF cloth ground](screenshots/GUI/lidar_laz_csf.PNG) |

| Raster (Plan / ortho / historical) | Vector, IGN BD TOPO (WFS) | Vector, OSM (Mapsforge) |
|---|---|---|
| ![Raster tab](screenshots/GUI/raster.PNG) | ![Vector tab, IGN source](screenshots/GUI/vector_ign.PNG) | ![Vector tab, OSM source](screenshots/GUI/vector_osm.PNG) |

| Vector merge | Raster splitting |
|---|---|
| ![Vector merge tab](screenshots/GUI/vector_merge.PNG) | ![Raster splitting tab](screenshots/GUI/raster_split.PNG) |

Send to phone: the 📲 button serves the generated maps over local WiFi. Scan the QR code, download, then import in Locus through **Map Manager → Import map → system file manager**. "Open with" may also work depending on Android.

![Send to phone (QR)](screenshots/GUI/phone.PNG)

The index sheet dropped next to the deliverables: real department outline and numbered chunk cells (here a Var department VAT run split into 3×4 zones; the slight overlaps are the real shared edge tiles at low zooms). The index sheet itself works everywhere; the administrative-outline background is a best-effort touch (département in France, a geocoded equivalent elsewhere): offline or when no boundary resolves, the sheet is still generated, just with the extent and cells alone.

![Index sheet](screenshots/index_sheet.png)

### Rendering in Locus Map

Archaeological LiDAR relief shown as an overlay on the terrain in Locus Map.

| SVF (Sky-View Factor) | Multi-hillshade overlay |
|---|---|
| ![SVF in Locus Map](screenshots/LIDAR_Samples/Svf_LocusMap.jpg) | ![Multi-hillshade in Locus Map](screenshots/LIDAR_Samples/Multi_LocusMap.jpg) |

### Rendering in OsmAnd

LiDAR relief (LRM) as a semi-transparent Overlay map above the standard
OsmAnd map (Configure map > Overlay map, transparency slider around the
middle).

<p align="center"><img src="screenshots/LIDAR_Samples/LRM_OSMAND_Transparent.jpg" alt="LRM overlay in OsmAnd" width="380"></p>

### What SVF reveals, same area, three sources

Under tree cover, the aerial photo and OSM show nothing. The LiDAR SVF makes
the terraces (dry-stone restanques) and old paths appear, invisible from above.

| Satellite photo | OSM | SVF (HD LiDAR) |
|---|---|---|
| ![Satellite view](screenshots/LIDAR_Samples/sat.png) | ![OSM view](screenshots/LIDAR_Samples/osm.png) | ![SVF view](screenshots/LIDAR_Samples/svf.png) |
| Opaque scrubland | Almost no detail | Crisp terraces + paths |

#### Reproducing this render

The header SVF and the triptych above (Rougiers area, dép. 83, France) were computed with:

```bash
python lidar2map.py \
  --zone-gps <lat>,<lon> --zone-width 2 --zone-name hero \
  --lidar --download --workers 8 \
  --shadings svf --shading-elevation 25 \
  --svf-conv rvt --svf-dist 20 --svf-gamma 0.8 --svf-sweep \
  --file-formats mbtiles --zoom-min 8 --zoom-max 18 \
  --image-format jpeg --image-quality 85
```

Replace `<lat>,<lon>` with your own area; the SVF parameters above are the ones
used for the visual. The exact coordinates of a micro-relief are deliberately
not published (ethics: do not guide anyone toward a specific site, see the
anti-detecting disclaimer above).

## Documentation

- **User README**: this file
- **Choosing a LiDAR visualization**: [history, formulas, diagrams, strengths and limitations of every output](docs/shadings.md)
- **Build & deployment**: [BUILD.md](BUILD.md), bundle architecture, per-OS build scripts, updating without rebuild, troubleshooting (including Linux- and macOS-specific cases)
- **Built-in help**: `python lidar2map.py --help` (LiDAR), `--raster --help` (raster), `--vector --help` (vector), `--osm --help`, `--merge --help`

## License

Code distributed under the **GNU General Public License v3.0**, see [LICENSE](LICENSE).

You are free to use, modify and redistribute this software under the terms of the GPL v3. In particular: if you redistribute a modified version, you must provide the modified source code under the same license.

## Author

Designed and architected by **Nicolas Martin** ([@nico579](https://github.com/nico579)). Code developed with the assistance of Claude (Anthropic) as a development tool.

## Acknowledgements

Data used:
- **IGN** (French National Institute of Geographic and Forest Information), LiDAR HD, BD ORTHO (including the historical 1950-1995 versions), BD TOPO, under the Etalab 2.0 license
- **AHN** (Actueel Hoogtebestand Nederland), AHN4/5 0.5m (Netherlands), CC BY 4.0
- **swisstopo** (Swiss Federal Office of Topography), swissALTI3D 0.5m (Switzerland), free open data © swisstopo
- **Kartverket**, Nasjonal Høydemodell 1m (Norway), CC BY 4.0
- **Geobasis NRW · LDBV Bayern · LGLN Niedersachsen · TLBG Thüringen**, DGM 1m (1-2m Thuringia) (Germany, 4 Länder), Datenlizenz Deutschland Namensnennung 2.0
- **Land Tirol** (tiris), DGM 0.5m (Austria, Tyrol), CC BY 4.0
- **Environment Agency** (England) & **DataMapWales / Natural Resources Wales**, LIDAR Composite DTM 1m (UK), Open Government Licence v3
- **Scottish Government / JNCC** (Scottish Remote Sensing Portal), Scottish Public Sector LiDAR DTM 0.5m (Scotland), Open Government Licence v3
- **ACT** (Administration du Cadastre et de la Topographie), BD-L-Lidar 2024 DTM 0.5m (Luxembourg), CC0
- **USGS**, 3DEP / The National Map 1m (USA), public domain
- **GSI** (Geospatial Information Authority of Japan), DEM5A elevation tiles 5m (Japan), GSI content terms
- **Digitaal Vlaanderen**, DHMV II DTM/SVF/Hillshade (Belgium Flanders), Open Data Licentie Vlaanderen
- **Maanmittauslaitos**, Elevation Model 2m (Finland), CC BY 4.0
- **Klimadatastyrelsen / Datafordeler**, DHM DTM 0.4m (Denmark), CC BY
- **Geological Survey Ireland**, LiDAR DTM 1m (Ireland), CC BY 4.0
- **Natural Resources Canada**, HRDEM Mosaic 1m (Canada), Open Government Licence
- **ČÚZK** (Czech Office for Surveying, Mapping and Cadastre), DMR 5G 1m (Czechia), Open Data
- **IGN España / CNIG**, MDT 5m (Spain), CC BY 4.0
- **ICGC** (Institut Cartogràfic i Geològic de Catalunya), MET LiDAR 50cm (Catalonia), CC BY 4.0
- **GUGiK** (Polish Head Office of Geodesy and Cartography), NMT 1m LiDAR ISOK (Poland), open data
- **LINZ** (Land Information New Zealand), 1m DEM (New Zealand), CC BY 4.0
- **QSpatial** (State of Queensland) & **Spatial Services NSW**, 0.5m / 5m DEM (Australia), CC BY 4.0
- **Geoscience Australia**, DEM of Australia derived from LiDAR 5m (Australia, national), CC BY 4.0
- **OpenStreetMap**, vector data under the ODbL license, distributed by Geofabrik
- **Apache JMapsforge / mapsforge-map-writer**, offline vector rendering engine

Bundled tools: GDAL, osmosis, py7zr, pyproj, numpy, scipy, Pillow, ijson, pywebview.
