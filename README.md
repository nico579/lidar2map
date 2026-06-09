***English** | [Français](README.fr.md)*

# lidar2map

**Offline archaeological LiDAR maps, multi-country + IGN raster/vector + OSM, for Locus Map / OsmAnd / TwoNav**

A self-contained Python tool that downloads public LiDAR data from national portals across **16 countries** (France, UK, Germany, Austria, Netherlands, Switzerland, Norway, Belgium, Finland, Denmark, Ireland, Czechia, Spain, Poland, Canada, New Zealand), computes relief visualizations tuned for archaeological prospection, and generates maps usable offline on a smartphone (MBTiles, RMAP, SQLiteDB, Mapsforge formats). The IGN raster/vector maps remain France-only.

![Same place: satellite, OpenStreetMap, then LiDAR relief (SVF)](screenshots/hero.png)

*The same extent under three views: aerial imagery and the OSM map show nothing of the micro-relief — the Sky-View Factor computed from the HD LiDAR reveals it instantly.*

> ⚠️ **Status**: personal project, publicly released. Heavily tested on Windows 10/11. Linux and macOS tested partially — known cases + cross-OS troubleshooting in the *Troubleshooting* section of [BUILD.md](BUILD.md). Feedback welcome via [GitHub issues](https://github.com/nico579/lidar2map/issues).
>
> **Note:** the GUI auto-detects your language (English/French, with a manual toggle) and the CLI flags and `--help` are in English. The former French flag names still work as aliases, so older example commands keep working.

---

## Who is it for?

- **Amateur archaeologists** interested in LiDAR prospection — the tool works across **16 countries** (France, UK, Germany, Austria, Netherlands, Switzerland, Norway, Belgium, Finland, Denmark, Ireland, Czechia, Spain, Poland, Canada, New Zealand) with more in progress. The relief computations (multi, SVF, LRM, RRIM) are identical from one country to the next.
- **French hikers** who want offline IGN topo maps on their phone (Locus Map Pro, OsmAnd+) — the IGN raster/vector tabs remain France-only.
- **Landscape surveyors** who combine historical orthophotos (1950-1995, France) with a DEM to spot human remains before agricultural land abandonment erases them.
- **Cavers / explorers** who need accurate base maps in areas not covered by mainstream apps.

The tool is **not** intended for metal detecting. The code strictly respects the open licenses involved (Etalab FR, CC BY 4.0 NO, CC-0 NL, BGDI CH).

## What it produces

From a town, GPS coordinates, a bbox, a département or a whole region:

- **Archaeological relief** from national LiDAR (0.5 m to 1 m resolution depending on source):
  - Multidirectional hillshade (25° sun angle for micro-relief)
  - Configurable SVF (Sky-View Factor) — reveals ditches, terraces, enclosures.
    `flux` convention (cos²γ, more visual contrast, default) or `rvt` (1−sin γ,
    the Kokalj/Hesse archaeology standard / openness); adjustable horizon
    distance (10–200 m, default 20 m); display gamma; sweep-horizon kernel.
    Flags: `--svf-conv flux|rvt`, `--svf-dist M`, `--svf-gamma G`,
    `--svf-sweep` / `--no-svf-sweep` (or the SVF panel in the GUI).
  - LRM (Local Relief Model) — removes the natural terrain, keeps the anomalies
  - RRIM (Red Relief Image Map) — color composite (slope + LRM)

  Supported LiDAR sources (via the `--provider <code>` flag):

  *Europe*
  - **France** (`fr-ign`, default) — IGN LiDAR HD, 0.5 m, national coverage
  - **Netherlands** (`nl-ahn`) — AHN4/5, 0.5 m, national coverage
  - **Switzerland** (`ch-swisstopo`) — swissALTI3D, 0.5 m, national coverage
  - **Norway** (`no-kartverket`) — Nasjonal Høydemodell, 1 m, national coverage
  - **Germany** (`de-nrw`, `de-bayern`, `de-niedersachsen`) — DGM1, 1 m (3 Länder, open data)
  - **Austria** (`at-tirol`, `at-osttirol`) — DGM 0.5 m (Tyrol + East Tyrol, tiris WCS)
  - **United Kingdom** (`gb-england`, `gb-wales`) — LIDAR Composite DTM, 1 m (EA/NRW)
  - **Belgium** (`be-flanders`) — DHMV II DTM, 1 m, Flandre+Bruxelles (Digitaal Vlaanderen WCS) — also exposes pre-computed SVF 25 cm and multi-hillshade 25 cm
  - **Finland** (`fi-maanmittauslaitos`) — Elevation Model, 2 m, national coverage (NLS WCS, API key required)
  - **Denmark** (`dk-datafordeler`) — DHM DTM, 0.4 m, national coverage (Datafordeler WCS, API key required)
  - **Ireland** (`ie-gsi`) — LiDAR DTM, 1 m, ~60% coverage (GSI, CC BY 4.0)
  - **Czechia** (`cz-cuzk`) — DMR 5G, 1 m, national coverage (ČÚZK Atom feed; LAZ → GeoTIFF, requires `lazrs`)
  - **Spain** (`es-cnig`) — MDT 5 m, national coverage (IGN INSPIRE WCS). Note: 5 m = landscape scale; the bare-earth 2 m LiDAR is only behind the session-based CNIG portal (not cleanly integrable)
  - **Poland** (`pl-gugik`) — NMT 1 m LiDAR (ISOK project), national coverage (GUGiK WCS, open data)

  *Americas*
  - **Canada** (`ca-nrcan`) — HRDEM Mosaic, 1 m, ~95% population coverage (NRCan STAC; windowed COG reads /vsicurl/)
  - **USA** (`us-tnm`, `us-3dep`) — 3DEP 1 m (TNMAccess direct S3, no account; or OpenTopography with free key)

  *Oceania*
  - **New Zealand** (`nz-linz`) — 1 m national seamless DEM (LINZ S3 STAC; windowed COG reads)

  *In progress* (providers drafted, not yet functional):
  - Sweden (`se-lantmateriet`, Lantmäteriet account required), Australia (`au-ga`, to be written)

- **IGN raster maps** *(France only)*: Plan IGN, orthophotos (current + historical 1950, 1965, 1980), 19th-century État-Major, Pléiades satellite, CIR, etc.

- **Vector maps**: OSM Mapsforge `.map` (international, via Geofabrik) or IGN BD TOPO *(France only)*

- **Outputs**: MBTiles (universal), RMAP (CompeGPS / TwoNav), SQLiteDB (RMaps schema — Locus Map / OsmAnd), Mapsforge `.map` (OsmAnd / Locus)

---

## Installation and usage

Two ways to use lidar2map:

| | **A. Python script** | **B. Standalone executable** |
|---|---|---|
| **Requirements** | Python 3.12 | None |
| **First install** | ~5 min (deps bootstrap) | None |
| **Updates** | `git pull` + relaunch | Patch the 3 existing binaries on the GitHub release in one command: `python update_app.py --release` (see [`update_app.py`](update_app.py)) |
| **Distributable** | No — each user installs Python | Yes — `.exe` / `.app` / Linux binary + zip bundle side by side |
| **Best for** | dev / Linux / contributing code | end user / Windows / distributing |

### A. Python script

On first launch, the script creates `~/.lidar2map/venv` and installs the critical dependencies there (Pillow, pyproj, numpy, rasterio, pywebview + PyQt6/QtWebEngine…). GDAL (Windows), the Temurin 21 JRE and osmosis are downloaded on demand. ~400 MB total, **once**.

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

The script will ask permission to install GDAL via `sudo apt install gdal-bin`.

Troubleshooting: the *Troubleshooting* section of [BUILD.md](BUILD.md) (including Linux/macOS-specific cases: PEP 668, Qt distro packages, Wayland, Gatekeeper on the JRE…).

### B. Standalone executable

No Python for the end user to install. The deliverable carries its own runtime (embedded Python, deps, JRE, osmosis).

#### 1. Get the deliverable

**Option a — Download from [Releases](https://github.com/nico579/lidar2map/releases)** (if the version is published for your platform):

| OS | Archive | Extract with |
|----|---------|--------------|
| Windows 10/11 (x86_64) | `lidar2map-windows-x86_64.zip` | `Expand-Archive` (PowerShell) or double-click |
| Linux Ubuntu 24.04+ (x86_64) | `lidar2map-linux-x86_64.tar.gz` | `tar xzf` |
| macOS 12+ (Apple Silicon) | `lidar2map-macos-arm64.zip` | `unzip` then `xattr -dr com.apple.quarantine LIDAR2MAP.app` |

The archive extracts into a `lidar2map-<os>-x86_64/` folder containing the binary and its `lidar2map_bundle.zip` side by side. No system installation.

**Option b — Build it yourself.** Two scripts per platform: a machine setup (do **once**) then a build (re-run each time `lidar2map.py` is updated).

##### Windows

```powershell
git clone https://github.com/nico579/lidar2map
cd lidar2map
.\setup_build_windows.ps1     # 1. Setup: Python 3.12, deps, JRE, osmosis, PyInstaller
.\lidar2map_win_build.ps1     # 2. Build: 3 steps -> dist\lidar2map.exe + dist\lidar2map_bundle.zip
```

##### macOS (Apple Silicon)

```bash
git clone https://github.com/nico579/lidar2map
cd lidar2map
bash setup_build_mac.sh       # 1. Setup
bash lidar2map_mac_build.sh   # 2. Build -> dist/LIDAR2MAP.app
```

##### Linux (Ubuntu / Debian)

Linux reuses the Windows specs (`_win.spec` produces an ELF on Linux — the name is misleading).

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

The first launch extracts the bundle (~30-60 s, once — it contains Qt) into:
- Windows: `%LOCALAPPDATA%\lidar2map\`
- macOS: `~/Library/Application Support/lidar2map/`
- Linux: `~/.local/share/lidar2map/`

Clean uninstall: `lidar2map(.exe) --desinstaller`.

---

## Usage

Two modes, selected automatically based on the arguments (same logic as the
twin project [gpxsolar](https://github.com/nico579/gpxsolar)):

- **No argument → graphical interface** (pywebview / Qt). The common mode.
- **With arguments → command-line computation** (headless, no window).
  Handy for scripting, running on a server, or reproducing an exact render.

Everything below applies to the binary as well as the script — just replace
`python lidar2map.py` with `lidar2map.exe` (Windows), `./lidar2map` (Linux) or
`LIDAR2MAP.app` (macOS).

### Command-line examples

> The flags below are English. The former French flag names still work as aliases, so older commands keep working.

**SVF relief + IGN topo map over a town (1 km² zone around Garéoult, France):**
```bash
python lidar2map.py --lidar --zone-city Gareoult --zone-radius 1 \
    --shadings multi svf --file-formats mbtiles --yes
```

**Relief over Amsterdam (Netherlands, AHN4):**
```bash
python lidar2map.py --provider nl-ahn --lidar --download \
    --zone-bbox 120000,486000,122000,488000 --zone-name amsterdam \
    --shadings multi --file-formats mbtiles --yes
```

**Relief over Geneva (Switzerland, swissALTI3D):**
```bash
python lidar2map.py --provider ch-swisstopo --lidar --download \
    --zone-city Geneve --zone-radius 1 \
    --shadings svf --file-formats mbtiles --yes
```

**Relief over Oslo (Norway, Kartverket):**
```bash
python lidar2map.py --provider no-kartverket --lidar --download \
    --zone-city Oslo --zone-radius 1 \
    --shadings multi --file-formats mbtiles --yes
```

**Historical 1950-1965 orthophoto over an archaeological survey area:**
```bash
python lidar2map.py --raster --zone-bbox 6.0,43.3,6.1,43.4 \
    --layer ortho_1950 --zoom-min 14 --zoom-max 18 --yes
```

**OSM vector map (Mapsforge .map) for Locus, whole département:**
```bash
python lidar2map.py --osm --zone-department 83 --file-formats map --yes
```

**Whole region (`--zone-region`) — available for all modes:**
```bash
# OSM: a single map for the whole region, no re-splitting
# (the Geofabrik PBF IS already regional — far faster than looping per département)
python lidar2map.py --osm --zone-region provence-alpes-cote-d-azur --yes

# IGN vector: paths/routes for the whole region as GeoJSON + Locus .map
python lidar2map.py --vector --zone-region provence-alpes-cote-d-azur \
    --layer chemins --file-formats gz map --yes
```
The slug is the one from [Geofabrik France](https://download.geofabrik.de/europe/france.html) (old-style regions: `provence-alpes-cote-d-azur`, `bretagne`, `corse`, `rhone-alpes`…). In OSM the region is processed as one block (the Geofabrik file is already regional, no per-département geocoding); for the raster/vector/lidar modes the area is the bbox enclosing all the départements of the region. An unknown slug lists the available regions.

**IGN BD TOPO map (roads + buildings) as compressed GeoJSON + Mapsforge .map:**
```bash
python lidar2map.py --vector --zone-department 83 \
    --layer routes batiments --file-formats gz map --yes
```
The `map` format converts the IGN GeoJSON into a Mapsforge `.map` map (readable by Locus Map / OsmAnd).

## LiDAR providers — adding a country

The provider abstraction lets you add a national LiDAR source without touching the core of the pipeline. Each provider lives in `providers/<code>.py` (~50-200 lines) and exposes:

```python
NAME, CODE, COUNTRY, LICENSE          # metadata
CRS_NATIF, RESOLUTION_M, DALLE_KM     # geometry
discover_dalles(bbox_wgs, bbox_natif, cache)  # → {name: url}
# + helpers: dalle_filename, dalle_url, subdir_from_name, dalles_pour_bbox
```

The downstream pipeline (SVF, relief, EPSG:3857 warp, MBTiles) is provider-agnostic: it consumes the GeoTIFFs returned by `discover_dalles`, regardless of the native CRS or the index format used upstream.

| Code | Country | Native CRS | Resolution | API paradigm |
|---|---|---|---|---|
| `fr-ign` | France | EPSG:2154 (Lambert-93) | 0.5 m | Vector TMS PBF + WMS GetMap |
| `nl-ahn` | Netherlands | EPSG:28992 (RD New) | 0.5 m | ATOM feed + JSON FeatureCollection |
| `ch-swisstopo` | Switzerland | EPSG:2056 (CH1903+/LV95) | 0.5 m | STAC REST API |
| `no-kartverket` | Norway | EPSG:25833 (UTM33N) | 1 m | ArcGIS ImageServer exportImage |
| `de-bayern` · `de-nrw` · `de-niedersachsen` | Germany (3 Länder) | EPSG:25832 (UTM32N) | 1 m | metalink / index.json / STAC COG |
| `at-tirol` · `at-osttirol` | Austria (Tyrol) | EPSG:31254/31255 (MGI M28/M31) | 0.5 m | WCS 1.0.0 GetCoverage |
| `gb-england` · `gb-wales` | United Kingdom | EPSG:27700 (OSGB36) | 1 m | WCS 2.0.1 / WFS catalogue |
| `be-flanders` | Belgium (Flanders) | EPSG:31370 (Lambert 1972) | 1 m | WCS 2.0.1 (+ pre-computed 25 cm shadings) |
| `fi-maanmittauslaitos` | Finland | EPSG:3067 (TM35FIN) | 2 m | WCS 2.0.1 (free API key) |
| `dk-datafordeler` | Denmark | EPSG:25832 (UTM32N) | 0.4 m | WCS 1.0.0 (free API key) |
| `ie-gsi` | Ireland | EPSG:2157 (ITM) | 1 m | ArcGIS FeatureServer → ZIP (post_fetch) |
| `cz-cuzk` | Czechia | EPSG:5514 (S-JTSK/Krovak) | 1 m | Atom INSPIRE 2-level → LAZ (post_fetch) |
| `ca-nrcan` | Canada | EPSG:3979 (LCC Canada) | 1 m | STAC + mosaic COG (windowed read) |
| `us-tnm` · `us-3dep` | USA | EPSG:3857 | 1 m | TNMAccess S3 / OpenTopography |
| `es-cnig` | Spain | EPSG:25830 (UTM30N) | 5 m | WCS 2.0.1 INSPIRE (MDT) |
| `pl-gugik` | Poland | EPSG:2180 (PUWG 1992) | 1 m | WCS 2.0.1 (NMT ISOK) |
| `nz-linz` | New Zealand | EPSG:2193 (NZTM2000) | 1 m | STAC + national COG (windowed read) |

Selection: `--provider <code>` flag (CLI), `LIDAR2MAP_PROVIDER` env var, or the dropdown at the top of the GUI.

To add a new country: copy the provider closest in paradigm (WCS, STAC, ArcGIS ImageServer, direct COG, FeatureServer catalogue…) and adapt URLs/CRS/naming format. The first provider for a new paradigm takes ~½ day; subsequent ones with the same pattern take ~1–2 h. A [provider roadmap](docs/lidar_providers_roadmap.md) documents ~40 evaluated sources across 25+ countries.

## Main features

- **Auto-bootstrap**: no pre-installed dependency required. The script downloads on demand: Python deps (Pillow, pyproj, numpy, scipy), GDAL (Windows) or asks for system install (Linux/macOS), Temurin 21 JRE, osmosis, mapwriter.
- **Memory streaming**: département-scale processing without saturating RAM (ijson, rasterio windowed reads, tile-by-tile MBTiles generation).
- **Clean cancellation**: `Ctrl+C` once → stops after the current chunk. `Ctrl+C` twice → immediate stop.
- **Resume after interruption**: the same command resumes where it stopped, via a `.json` manifest that tracks completed chunks.
- **Up-front splitting**: for large areas, split into an N×N grid **or ~K km squares** (`--split-radius`, bounded chunk size — recommended at national scale) — useful so you don't have to regenerate the whole area if something crashes. Per-chunk disk cleanup (`--cleanup`) and a free-space guard (`--min-free-gb`) for very large coverage.
- **Crash-safe history**: each run is recorded *at startup* (status "running") then finalized to "ok" or "ko". A hard crash (kill -9, power loss) leaves the entry visible in the UI — the trace is kept for debugging.
- **Multi-provider LiDAR**: a `providers/<code>.py` abstraction that lets you plug in any LiDAR source. Shipped providers: **FR** (IGN), **NL** (AHN), **CH** (swisstopo), **NO** (Kartverket), **DE** (Bavaria, NRW, Lower Saxony), **AT** (Tyrol, East Tyrol), **GB** (England, Wales), **BE** (Flanders WCS), **FI** (NLS WCS), **DK** (Datafordeler WCS), **IE** (GSI catalogue), **CA** (NRCan STAC), **NZ** (LINZ S3), **AU** (Geoscience Australia WCS), **US** (3DEP 1m, no account) — covering varied API paradigms (TMS PBF, JSON FeatureCollection, STAC, ArcGIS FeatureServer/ImageServer, Metalink/`index.json`, **per-tile WCS `GetCoverage`**, S3 public COG). Providers can also expose **pre-computed shadings** (`PROVIDES_SHADINGS`) — the pipeline downloads them directly instead of computing from the DEM (e.g. BE Flanders SVF 25 cm, multi-hillshade 25 cm). Adding a country = ~100–150 lines (see *LiDAR coverage & evaluated sources* below).
- **Interactive GUI**: 6 tabs (LiDAR, IGN raster, IGN vector, OSM, Merge, Splitting), provider selector at the top of the form (IGN Raster/Vector tabs hidden automatically for non-FR providers), history of the last 50 commands with status badges, parameter validation, live log, error modal.
- **Historical orthophoto maps**: a unique combo for archaeology — SVF 2024 (current LiDAR) + 1950 ortho (before land abandonment) → reveals structures still legible 70 years later.

## LiDAR coverage & evaluated sources

![lidar2map LiDAR coverage map](coverage.png)

*16 countries with national bare-earth LiDAR. USA & Canada are supported too (3DEP / HRDEM) but their coverage is project/population-based, so they're not drawn.*

🗺️ **[Interactive coverage map](coverage.geojson)** — also rendered directly by GitHub (click the file), or droppable into [geojson.io](https://geojson.io) / QGIS to test a point.

**Countries on the map** (national bare-earth LiDAR): France · Netherlands · Switzerland · Norway · Germany (Bavaria · NRW · Lower Saxony) · Austria (Tyrol) · United Kingdom (England · Wales) · Belgium (Flanders) · Finland · Denmark · Ireland · Czechia · Spain *(5 m)* · Poland · New Zealand. Resolutions 0.5–1 m unless noted — see the provider list above for codes and details.

The map is regenerated by `coverage_map.py`, which reads zone titles from `providers/*.py` — so the map and the GUI can't drift. Clicking a zone in the interactive GeoJSON shows its `NAME` and code(s).

**🇺🇸 USA & 🇨🇦 Canada — supported and working, just not drawn.** `us-tnm` / `us-3dep` (3DEP 1 m) and `ca-nrcan` (HRDEM 1 m) are fully functional, but their coverage is **project/population-based** (not wall-to-wall national), so a full-country polygon would over-claim — hence the note rather than a shape. Check your US area on the [TNM Downloader](https://apps.nationalmap.gov/downloader/). Note: USGS 1 m tiles are 10×10 km (~150–300 MB).

**🇧🇪 Belgium (Flanders)**: a bonus — the WCS also exposes `DHMV_II_SVF_25cm` (Sky-View Factor at 25 cm, 16 directions, r=2.5 m) and `DHMV_II_HILL_25cm` (multidirectional hillshade at 25 cm, pre-computed by Digitaal Vlaanderen). When one of those shadings is requested, lidar2map downloads it directly instead of computing it from the 1 m DEM — both faster and at higher resolution.

A source plugs in cleanly when it exposes **deterministic tiles** (one URL per
~1 km tile), **a WCS** (`GetCoverage` by bbox), **mosaic COGs** (windowed
`/vsicurl/` read on the bbox, see `ca-nrcan`) or **LAZ/ZIP tiles** (`post_fetch`
hook: unzip + point-cloud→GeoTIFF via `laspy`+`lazrs`, see `cz-cuzk`, `ie-gsi`).
Still a poor fit: sources via **form/email order**, **WMS only** (rendered, no raw
elevation) or **ASC without a CRS**.

Sources **evaluated but not retained** so far (documented to avoid re-digging):

| Source | Reason |
|---|---|
| DE — BKG national DGM1 | paid (≥ €8,000) |
| DE — Saxony-Anhalt | WCS `GetCoverage` returns 500 ; download = 4 large blocks |
| DE — Thuringia / Saxony | no documented clean programmatic access (portal) |
| DE — Baden-Württemberg | XYZ (ASCII) + JS portal, no clear tiled GeoTIFF |
| AT — BEV national | 50 km tiles via portal |
| AT — Vorarlberg | WMS only (no raw elevation) |
| ES — CNIG MDT02 | LAZ blocks + 2 m (coarse) — needs `post_fetch` LAZ→GeoTIFF (PDAL) |
| SE — Lantmäteriet | LAZ tiles (CC0) — needs `post_fetch` LAZ→GeoTIFF (PDAL) |
| CZ — ČÚZK DMR 5G | LAZ zipped — needs `post_fetch` LAZ→GeoTIFF (PDAL) |
| BE — Wallonia | 0.5 m but large provincial blocks; WCS availability unconfirmed |
| GB — Scotland | per-phase fragmentation; AWS S3 accessible but index complex |
| IT — Aosta Valley / regions | portal order form |
| IT — South Tyrol | 0.5 m built-up areas only / 2.5 m elsewhere |
| SI — Slovenia (ARSO) | ASC without CRS + per-block index |
| LV — LGIA | DTM/DSM 0.4 m; download API not publicly accessible (WMS only) |
| PT — DGT | 0.5 m national 2024; API to be validated |

Germany is covered as far as cleanly possible (3 clean states + Tyrol on the Alps side); the remaining states have no clean programmatic access so far (see table). This table is maintained by hand as sources are probed — it exists to avoid re-digging the same dead ends.

## Screenshots

### Graphical interface

Six tabs to drive LiDAR, IGN raster/vector, OSM, merge and splitting.

| HD LiDAR (archaeological relief) | IGN raster (Plan / ortho / historical) | IGN vector (BD TOPO) |
|---|---|---|
| ![LiDAR tab](screenshots/GUI/IGN_Lidar.PNG) | ![IGN raster tab](screenshots/GUI/IGN_Raster.PNG) | ![IGN vector tab](screenshots/GUI/IGN_Vectoriel.PNG) |

| OSM vector (Mapsforge) | Vector merge | Raster splitting |
|---|---|---|
| ![OSM tab](screenshots/GUI/OSM_Vectoriel.PNG) | ![Merge tab](screenshots/GUI/Fusion_Vectoriel.PNG) | ![Splitting tab](screenshots/GUI/Decoupage_Raster.PNG) |

### Rendering in Locus Map

Archaeological LiDAR relief shown as an overlay on the terrain in Locus Map.

| SVF (Sky-View Factor) | Multi-hillshade overlay |
|---|---|
| ![SVF in Locus Map](screenshots/LIDAR_Samples/Svf_LocusMap.jpg) | ![Multi-hillshade in Locus Map](screenshots/LIDAR_Samples/Multi_LocusMap.jpg) |

### What SVF reveals — same area, three sources

Under tree cover, the aerial photo and OSM show nothing. The LiDAR SVF makes
the terraces (dry-stone restanques) and old paths appear — invisible from above.

| Satellite photo | OSM | SVF (HD LiDAR) |
|---|---|---|
| ![Satellite view](screenshots/LIDAR_Samples/sat.png) | ![OSM view](screenshots/LIDAR_Samples/osm.png) | ![SVF view](screenshots/LIDAR_Samples/svf.png) |
| Opaque scrubland | Almost no detail | Crisp terraces + paths |

#### Reproducing this render

The header SVF and the triptych above (Rougiers area, dép. 83, France) were computed with:

```bash
python lidar2map.py \
  --zone-gps <lat> <lon> --zone-radius 1 --zone-name hero \
  --lidar --download --workers 8 \
  --shadings svf --shading-elevation 25 \
  --svf-conv rvt --svf-dist 20 --svf-gamma 0.8 --svf-sweep \
  --file-formats mbtiles --zoom-min 8 --zoom-max 18 \
  --image-format jpeg --image-quality 85 --yes
```

Replace `<lat> <lon>` with your own area; the SVF parameters above are the ones
used for the visual. The exact coordinates of a micro-relief are deliberately
not published (ethics: do not guide anyone toward a specific site — see the
anti-detecting disclaimer above).

## Documentation

- **User README**: this file
- **Build & deployment**: [BUILD.md](BUILD.md) — bundle architecture, per-OS build scripts, updating without rebuild, troubleshooting (including Linux- and macOS-specific cases)
- **Built-in help**: `python lidar2map.py --help` (LiDAR), `--raster --help` (raster), `--vector --help` (vector), `--osm --help`, `--merge --help`

## License

Code distributed under the **GNU General Public License v3.0** — see [LICENSE](LICENSE).

You are free to use, modify and redistribute this software under the terms of the GPL v3. In particular: if you redistribute a modified version, you must provide the modified source code under the same license.

## Author

Designed and architected by **Nicolas Martin** ([@nico579](https://github.com/nico579)). Code developed with the assistance of Claude (Anthropic) as a development tool.

## Acknowledgements

Data used:
- **IGN** (French National Institute of Geographic and Forest Information) — LiDAR HD, BD ORTHO (including the historical 1950-1995 versions), BD TOPO, under the Etalab 2.0 license
- **AHN** (Actueel Hoogtebestand Nederland) — AHN4/5 0.5m (Netherlands), CC BY 4.0
- **swisstopo** (Swiss Federal Office of Topography) — swissALTI3D 0.5m (Switzerland), free open data © swisstopo
- **Kartverket** — Nasjonal Høydemodell 1m (Norway), CC BY 4.0
- **Geobasis NRW · LDBV Bayern · LGLN Niedersachsen** — DGM1 1m (Germany, 3 Länder), Datenlizenz Deutschland Namensnennung 2.0
- **Land Tirol** (tiris) — DGM 0.5m (Austria, Tyrol), CC BY 4.0
- **Environment Agency** (England) & **DataMapWales / Natural Resources Wales** — LIDAR Composite DTM 1m (UK), Open Government Licence v3
- **USGS** — 3DEP / The National Map 1m (USA), public domain
- **Digitaal Vlaanderen** — DHMV II DTM/SVF/Hillshade (Belgium Flanders), Open Data Licentie Vlaanderen
- **Maanmittauslaitos** — Elevation Model 2m (Finland), CC BY 4.0
- **Klimadatastyrelsen / Datafordeler** — DHM DTM 0.4m (Denmark), CC BY
- **Geological Survey Ireland** — LiDAR DTM 1m (Ireland), CC BY 4.0
- **Natural Resources Canada** — HRDEM Mosaic 1m (Canada), Open Government Licence
- **ČÚZK** (Czech Office for Surveying, Mapping and Cadastre) — DMR 5G 1m (Czechia), Open Data
- **IGN España / CNIG** — MDT 5m (Spain), CC BY 4.0
- **GUGiK** (Polish Head Office of Geodesy and Cartography) — NMT 1m LiDAR ISOK (Poland), open data
- **LINZ** (Land Information New Zealand) — 1m DEM (New Zealand), CC BY 4.0
- **OpenStreetMap** — vector data under the ODbL license, distributed by Geofabrik
- **Apache JMapsforge / mapsforge-map-writer** — offline vector rendering engine

Bundled tools: GDAL, osmosis, py7zr, pyproj, numpy, scipy, Pillow, ijson, pywebview.
