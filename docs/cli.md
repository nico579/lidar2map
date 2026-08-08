***English** | [Français](cli.fr.md) · [Documentation index](README.md)*

# Command-line reference

The CLI exposes every lidar2map workflow: LiDAR relief, classic raster maps,
OSM and IGN vector maps, vector merging, raster splitting, phone sharing,
index-sheet rebuilding, and remote execution.

This page documents the behaviour of the current parsers. For installation and
the GUI, see [Getting started](getting-started.md). For choosing a deliverable,
see [Formats and mobile applications](formats.md); for source availability, see
[Providers and coverage](providers.md).

## Command form and mode selection

Examples use the Python source form:

```bash
python lidar2map.py <mode> <area> [options]
```

With a release, replace `python lidar2map.py` with `lidar2map.exe` on Windows,
`./lidar2map` on Linux, or the executable inside `LIDAR2MAP.app` on macOS.

- No argument opens the GUI.
- Any processing argument selects the headless CLI.
- Use one primary mode per invocation: `--lidar`, `--raster`, `--osm`,
  `--vector`, `--merge`, `--split`, or `--serve`.
- `--lidar` and `--osm` are the one useful combination: one invocation can
  produce both LiDAR relief and an OSM vector map for the same area.
- `--remote-cli` and `--remote-gui` are early-dispatch prefixes and must be the
  first argument after the executable.
- `--index-sheet DIR` is a standalone maintenance mode.

Mode-specific help is authoritative:

```bash
python lidar2map.py --help
python lidar2map.py --raster --help
python lidar2map.py --vector --help
python lidar2map.py --merge --help
python lidar2map.py --split --help
python lidar2map.py --remote-cli --help
```

`--version` prints the version and exits. English option names are canonical;
the compatibility aliases in [French aliases](#french-aliases) remain accepted.

## Two-minute LiDAR start

A LiDAR command requires an explicit provider and one area. When the area is a
town or GPS point, it also requires the width of the square to process:

```bash
python lidar2map.py --lidar --provider fr-ign \
  --zone-city Gareoult --zone-width 2
```

That command, without hidden prompts:

1. explicitly selects provider `fr-ign`;
2. creates a square 2 km wide around the geocoded town;
3. downloads only missing source tiles;
4. computes `lrm`;
5. writes an MBTiles map at zooms 13–18;
6. creates an index sheet when a readable deliverable exists.

The normal behaviour already reuses every valid cached tile and downloads only
missing source data. To prohibit source-data downloads and require an
already-populated cache:

```bash
python lidar2map.py --lidar --provider fr-ign \
  --zone-city Gareoult --zone-width 2 --no-download
```

If the required data is absent, cache-only processing exits with an error and
does not fetch it. `--no-download` controls LiDAR source-data downloads;
geocoding or provider discovery may still need network access.

GPS and bbox runs no longer need `--zone-name`:

```bash
python lidar2map.py --lidar --provider fr-ign \
  --zone-gps 43.3156,6.0423 --zone-width 2
python lidar2map.py --lidar --provider fr-ign \
  --zone-bbox 6.0,43.3,6.1,43.4
```

They receive stable names derived from coordinates rounded to five decimals,
such as `gps_43_31560_6_04230`. Use `--zone-name` when a human name is clearer.

## Areas, names, and directories

Exactly one area selector is required for every area-based workflow. The only
exception is direct conversion of an existing `.mbtiles` file.

| Option | Value / default | Meaning |
|---|---|---|
| `--zone-city NAME` | required selector | Geocode a town with Nominatim. |
| `--zone-gps LAT,LON` | required selector | WGS84 centre; a semicolon is also accepted as the separator. |
| `--zone-bbox W,S,E,N` | required selector | WGS84 west, south, east, north in degrees. Reversed pairs are normalized; a zero-area or out-of-range bbox is rejected. |
| `--zone-department NUM` | France only | One French département, or a list/range handled as successive runs; see [France-specific areas](#france-specific-areas). |
| `--zone-region SLUG` | France / Geofabrik | An old-style Geofabrik France region slug. |
| `--zone-width KM` | required for `--lidar` with a town/GPS point; otherwise `20` where applicable | Side of the square around a town or GPS point, not its radius. It does not alter a bbox, département, or region. |
| `--zone-name NAME` | automatic | Overrides the normalized project name. City, GPS, bbox, département, and region all have automatic names. |

The working directory is the script directory when running from source and the
outer executable directory for a release. Default paths are:

```text
<work-dir>/Projets/<zone>/lidar/<country>/
<work-dir>/Projets/<zone>/raster/
<work-dir>/Projets/<zone>/osm_vecteur/
<work-dir>/Projets/<zone>/ign_vecteur/
<work-dir>/cache/
<work-dir>/production/
```

| Option | Default | Meaning |
|---|---|---|
| `--output-dir PATH` | mode-specific path under `Projets/<zone>` | Writes directly into `PATH`; it is the final mode output directory, not a parent to which lidar2map adds the project name. |
| `--cache-dir PATH` | `<work-dir>/cache` | Root of persistent LiDAR tiles, WMTS tiles, OSM PBFs, provider discovery indexes, and other downloaded caches. |
| `--production-dir PATH` | `<work-dir>/production` | Root of computed but reusable LAZ-derived GeoTIFFs. Meaningful for LiDAR point-cloud mode. |
| `--tiles-dir PATH` | storage policy below | Overrides the source-tile location for LiDAR only and takes priority over `--cache-dir` and `--production-dir`. |

Without `--tiles-dir`, downloaded DTM tiles live under
`cache/lidar/<country>`. In point-cloud mode, downloaded LAZ/LAS remains in the
cache while the derived GeoTIFF lives under `production/lidar/<country>`.
Windowed COG/COPC fragments are project-specific and therefore stay inside the
project. See [DFM, LAZ, and CSF](dfm.md) for the full storage model.

## LiDAR workflow

### Defaults and data acquisition

```bash
python lidar2map.py --lidar --provider CODE AREA [LIDAR OPTIONS]
```

| Option | Default / values | Meaning |
|---|---|---|
| `--lidar` | off | Selects terrain processing. The legacy alias is `--ignlidar`. |
| `--provider CODE` | required; no implicit provider | Explicitly selects a source from the [provider catalogue](providers.md). `LIDAR2MAP_PROVIDER` alone does not satisfy this CLI requirement. |
| `--api-key KEY` | provider environment variable when supported | Supplies credentials for providers that require them. |
| `--download` / `--no-download` | reuse valid cache entries and download only missing data | `--no-download` prohibits source-data downloads; missing sources are not fetched. |
| `--workers N` | `8` | Parallel source-tile connections; must be positive. A provider can impose a lower effective limit. |
| `--download-compress` / `--no-download-compress` | on | Enables or disables DEFLATE compression of cached raster tiles. |
| `--download-force` | off | Fetches valid cached source data again. |
| `--download-overwrite` | off | Equivalent to `--download-force`, including LAZ point clouds. |

The normal behaviour and explicit `--download` both mean “download what is
missing,” not “download everything again.” An existing valid cache entry is
skipped unless one of the two force flags is present. `--no-download` simply
forbids source-data downloads and therefore requires all needed sources to be
present in the cache.

### Selecting visualizations

The default for a normal `--lidar` run is `lrm`. Select ordinary instances with
one multi-value option:

```bash
python lidar2map.py --lidar --provider fr-ign \
  --zone-city Gareoult --zone-width 2 \
  --shadings multi svf oneg --svf-dist 20 --svf-gamma 2
```

Or add independently parameterized instances with repeatable `--shading`:

```bash
python lidar2map.py --lidar --provider fr-ign \
  --zone-city Gareoult --zone-width 2 \
  --shading svf:dist=20,gamma=2 \
  --shading svf:dist=100,gamma=1.5 \
  --shading oneg:dist=20 \
  --shading 315:elevation=20 \
  --shading lrm:sigma=10
```

Non-default parameters are encoded in output names, so distinct instances do
not collide and completed visualizations can be reused.

| Option | Default / values | Meaning |
|---|---|---|
| `--shadings TYPE...` | `lrm` in a normal run | Types: `lrm vat e4mstp svf opos oneg rrim multi 315 045 135 225 slope`, plus `all`, `none`, `tous`, `aucun`. |
| `--shading TYPE[:k=v,...]` | none; repeatable | Adds one instance with its own parameters. A type covered here is not also generated from `--shadings` at global defaults. |
| `--shading-preset NAME` | off | Adds the resolution-aware stack described below. Values: `auto`, `micro`, `standard`, `landscape`. |
| `--shading-elevation DEG` | `25` | Global sun elevation for `multi` and directional hillshades. |
| `--svf-conv flux\|rvt` | `flux` | Global SVF convention: contrasted cos²γ flux or the 1−sin γ RVT convention. |
| `--svf-dist M` | `20` | Global horizon radius in metres for SVF, openness, and composites. About 100 m targets broader enclosures or roads. |
| `--svf-gamma G` | `2.0` | Global contrast for SVF, openness, and VAT. e4MSTP has its own default of `0.8`. |
| `--svf-sweep` / `--no-svf-sweep` | on | Enables or disables the accelerated horizon-sweep kernel. |
| `--shadings-overwrite` | off | Recomputes an existing shading GeoTIFF. |

`all` and its French alias `tous` expand to every simple output except the two
heavy composites `vat` and `e4mstp`, whose internal calculations would repeat
work already requested. Ask for either composite explicitly when wanted.
`none` and `aucun` suppress every shading, including instances supplied with
`--shading`.

Per-instance keys are:

| Type | Accepted keys | Defaults |
|---|---|---|
| `multi 315 045 135 225` | `elevation` | 25° |
| `svf` | `conv`, `dist`, `gamma`, `sweep` | `flux`, 20 m, 2.0, on |
| `opos oneg` | `dist`, `gamma`, `sweep` | 20 m, 2.0, on |
| `vat` | `dist`, `gamma` | 20 m, 2.0 |
| `e4mstp` | `dist`, `gamma` | 20 m, 0.8 |
| `lrm rrim` | `sigma` in metres | `15 × provider resolution`, equivalent to 15 source pixels |
| `slope` | none | no tunable parameter |

For `sweep`, numeric boolean values such as `1` and `0` are accepted in an
instance specification. For the scientific meaning, strengths, and limits of
each type, use the [visualization guide](shadings.md).

### Resolution presets

Every preset adds `svf`, `opos`, `lrm`, `multi`, and `slope`. Its dimensions are
metres on the ground, not pixels:

| Preset | Selected by `auto` | SVF/openness radius | LRM sigma | Sun elevation |
|---|---|---:|---:|---:|
| `micro` | resolution ≤ 0.75 m | 15 m | 8 m | 25° |
| `standard` | 0.75 m < resolution ≤ 2.5 m | 30 m | 15 m | 25° |
| `landscape` | resolution > 2.5 m | 80 m | 40 m | 30° |

```bash
python lidar2map.py --lidar --provider ch-swisstopo \
  --zone-city Lausanne --zone-width 2 --shading-preset auto
```

Explicitly supplied instance parameters remain separately named outputs.

### Point-cloud / DFM mode

`--laz` switches the selected parent provider to its `-laz` twin. It is only
available where the provider publishes a dense classified point cloud. Keep a
first experiment small: the source and conversion are much heavier than a DTM.

| Option | Common default | Meaning |
|---|---:|---|
| `--laz` | off | Uses the classified point cloud instead of the official bare-earth DTM. |
| `--laz-ground classes\|csf` | provider-specific | Selects producer-class re-injection or Cloth Simulation Filter. `fr-ign` defaults to `classes`; most other twins default to `csf`. |
| `--laz-hmin M` | 0.4 m | Minimum reinjected height in class mode. |
| `--laz-hmax M` | 2.5 m | Maximum reinjected height in class mode. |
| `--laz-classes LIST` | provider-specific; `1,2,3,4,9,66` for `fr-ign` | Comma-separated participating LAS classes. |
| `--laz-csf-threshold M` | 0.5 m | Point-to-cloth absorption distance, valid from 0.1 to 3.0 m. |
| `--laz-csf-resolution M` | 0.5 m | Cloth grid size, valid from 0.1 to 3.0 m. |
| `--laz-csf-rigidness N` | `1` | `1` steep/soft, `2` intermediate, `3` flat/rigid. |
| `--laz-parallel N` | `1` | Concurrent conversions; budget roughly 3 GB RAM per conversion. |

`hmin`, `hmax`, and `classes` are ignored in CSF mode; `csf-*` parameters are
ignored in class mode. Output project names are suffixed by the active variant,
so DTM, class-DFM, and CSF products do not mix. Full interpretation and
provider-specific defaults: [Standing structures with LAZ, DFM, and CSF](dfm.md).

### Large areas, resume, and disk control

Pre-splitting processes one chunk at a time and stores progress in
`manifeste.json`. Re-run the same command after an interruption to resume
completed chunks.

| Option | Default | Meaning |
|---|---:|---|
| `--split-cols N` | `0` | Grid columns. A grid is active only when both columns and rows are positive. |
| `--split-rows N` | `0` | Grid rows. |
| `--split-width KM` | `0` | Alternative square chunk side; takes effect when positive. |
| `--block i/M` | off | Processes only geographic block `i` of `M`, for sharding the same area across machines. |
| `--cleanup` | off | Removes successful-chunk intermediates while preserving final deliverables. |
| `--cleanup-keep-tiles` | off | With cleanup, retains shared downloaded source tiles for another run. |
| `--min-free-gb GB` | `0` | Before a chunk, exits with code 3 if free disk is below the threshold. |

For memory-heavy SVF/openness work, a practical starting target is at most
about 600 km² per chunk on a 32 GB machine and about 1,150 km² on 64 GB. Source
tile density can make equally sized chunks differ. See the detailed
[remote RAM and chunk guidance](remote.md#ram-and-chunk-size).

### LiDAR output controls

| Option | Default / values | Meaning |
|---|---|---|
| `--file-formats FMT...` | `mbtiles` in a productive normal LiDAR run | `mbtiles`, `rmap`, and/or `sqlitedb`. Vector formats are also accepted only when `--osm` is combined. |
| `--zoom-min N` | `13` | Minimum raster zoom. |
| `--zoom-max N` | `18` | Maximum raster zoom. Valid zooms are 0–22 and minimum must not exceed maximum. |
| `--image-format FMT` | `auto` | `auto`, `jpeg`, or `png`; alpha edge tiles can remain PNG. |
| `--image-quality Q` | `85` | JPEG quality from 1 to 100. |
| `--tiles-overwrite` | off | Rebuilds an existing tiled map or conversion output. |
| `--index-map` / `--no-index-map` | on | Enables or disables the best-effort `<product>_planche.png` index sheet for this parser. |

Web Mercator ground resolution is
`156543.03 × cos(latitude) / 2^zoom` metres per pixel. Around mainland France,
zoom 18 is about 0.42–0.44 m/px, so it is appropriate for a 0.5 m DEM. A useful
native-zoom rule is `ceil(log2(156543.03 × cos(latitude) / resolution))`:
roughly z19 for 0.25 m, z18 for 0.5 m, z17 for 1 m, z16 for 2 m, and z15 for 5 m.

### LiDAR examples

Multidirectional hillshade and SVF over a 2 km town extent:

```bash
python lidar2map.py --lidar --provider fr-ign \
  --zone-city Gareoult --zone-width 2 \
  --shadings multi svf --file-formats mbtiles
```

The command above produces LiDAR relief only. A Plan IGN background is a
separate `--raster` invocation; primary raster and LiDAR mode flags must not be
combined.

Reproduce the README's SVF settings while substituting your own coordinates:

```bash
python lidar2map.py --lidar --provider fr-ign \
  --zone-gps <lat>,<lon> --zone-width 2 --zone-name hero \
  --download --workers 8 \
  --shadings svf --svf-conv rvt --svf-dist 20 --svf-gamma 0.8 --svf-sweep \
  --file-formats mbtiles --zoom-min 8 --zoom-max 18 \
  --image-format jpeg --image-quality 85
```

The exact example-site coordinates are intentionally omitted: do not publish
the location of sensitive archaeological micro-relief.

## Classic raster workflow

```bash
python lidar2map.py --raster AREA [RASTER OPTIONS]
```

Raster mode downloads map/image tiles automatically and defaults to a Plan IGN
MBTiles at zooms 10–16.

| Option | Default / values | Meaning |
|---|---|---|
| `--raster` | off | Selects classic tiled raster. Legacy alias: `--ignraster`. |
| `--provider CODE` | `fr-ign` | `fr-ign` for IGN WMTS or `us-tnm` with layer `naip`. |
| `--layer LAYER` | `planign` | Short alias below or a full WMTS identifier. |
| `--api-key KEY` | environment / empty | Required only for restricted professional IGN Scan layers. |
| `--workers N` | `8` | Parallel tile connections. |
| `--download-overwrite` | off | Fetches existing cached raster tiles again. |
| `--file-formats FMT...` | `mbtiles` | Any of `mbtiles rmap sqlitedb`. |
| `--zoom-min`, `--zoom-max` | `10`, `16` | Requested zoom range, validated within 0–22 and capped to the layer's advertised range. |
| `--image-format FMT` | `auto` | `auto`, `jpeg`, or `png`. Native JPEG cannot regain quality by conversion to PNG, so that request stays JPEG. |
| `--image-quality Q` | `85` | JPEG quality. |
| `--tiles-overwrite` | off | Rebuilds an existing MBTiles. |
| `--split-cols`, `--split-rows` | `0`, `0` | Sequential pre-split grid; both must be positive. |
| `--split-width KM` | `0` | Alternative square chunk side. |
| `--cleanup` | off | Removes successful-chunk intermediates. |
| `--min-free-gb GB` | `0` | Clean exit code 3 below the disk threshold. |

Public IGN aliases:

| Family | Values |
|---|---|
| Topographic | `planign etatmajor40 etatmajor10 pentes` |
| Imagery | `ortho ortho_1950 ortho_1965 ortho_1980 ortho_irc pleiades spot edugeo_marseille_1969 edugeo_marseille_1980 edugeo_marseille_1987 edugeo_marseille_1988 edugeo_marseille_2010 edugeo_toulon_1972` |
| Thematic | `cadastre ombrage` |

Professional layers `scan25`, `scan25tour`, `scan100`, and `scanoaci` require a
`cartes.gouv.fr` professional account and `--api-key`. Historical and EDUGEO
coverage varies by place and date; test a small area first. US imagery uses:

```bash
python lidar2map.py --raster --provider us-tnm --layer naip \
  --zone-bbox -108.5,37.18,-108.48,37.20
```

Plan IGN over a town:

```bash
python lidar2map.py --raster --zone-city Gareoult --zone-width 2
```

Historical 1950–1965 orthophoto:

```bash
python lidar2map.py --raster --zone-bbox 6.0,43.3,6.1,43.4 \
  --layer ortho_1950 --zoom-min 14 --zoom-max 18
```

## OSM vector workflow

```bash
python lidar2map.py --osm AREA [OSM OPTIONS]
```

With no explicit vector format, `--osm` produces a Mapsforge `.map`. Add
`geojson`, `gz`, or `transparent-raster` as needed.

| Option | Default / values | Meaning |
|---|---|---|
| `--osm` | off | Selects OSM vector processing through a PBF or XML `.osm` source. |
| `--layer TAG...` | list below | Free-form OSM `key=value` filters. Pass separate shell arguments. |
| `--source FILE.pbf` | automatic Geofabrik selection in France | Uses an existing `.pbf` or `.osm`; a geographic area and `--osm` remain required. |
| `--file-formats FMT...` | `map` when no vector format is explicit | `map`, `geojson`, `gz`, and/or `transparent-raster`. |
| `--download-overwrite` | off | Refreshes an existing Geofabrik PBF. Otherwise it is reused and a cache older than 30 days is only reported. |
| `--tiles-overwrite` | off | Rebuilds existing `.map` or transparent raster output. |
| `--zoom-min`, `--zoom-max` | 13–18 for transparent raster | Transparent overlays clamp their minimum to at least z13. |

Default filters:

```text
highway=* waterway=* boundary=administrative natural=water
natural=coastline waterway=river waterway=stream waterway=canal
```

Automatic Geofabrik selection is currently France-only. Outside France,
download the appropriate regional PBF yourself and pass it with `--source`;
lidar2map then clips it to the requested area. Supplying only `gz` or `geojson`
skips Mapsforge/osmosis. `transparent-raster` creates an alpha PNG SQLiteDB for
OsmAnd and also keeps the GeoJSON intermediate it needs.

Whole French département as a Mapsforge map:

```bash
python lidar2map.py --osm --zone-department 83 --file-formats map
```

Custom hiking and history selection as compressed GeoJSON plus `.map`:

```bash
python lidar2map.py --osm --zone-city Gareoult --zone-width 5 \
  --layer highway=* waterway=* historic=* \
  --file-formats gz map
```

Combine the normal LiDAR defaults with the default OSM map:

```bash
python lidar2map.py --lidar --provider fr-ign --osm \
  --zone-city Gareoult --zone-width 2
```

## IGN vector workflow

```bash
python lidar2map.py --vector AREA [IGN VECTOR OPTIONS]
```

This mode is France-only and uses IGN WFS or, for a whole département when
available, the bulk BD TOPO package.

| Option | Default / values | Meaning |
|---|---|---|
| `--vector` | off | Selects IGN vector processing. Legacy alias: `--ignvecteur`. |
| `--layer NAME...` | `cadastre` | One or more aliases below, or full WFS typenames. |
| `--workers N` | `4` | Parallel WFS connections. Keep at or below four; the service rejects excess concurrency. |
| `--download-overwrite` | off | Fetches existing GeoJSON again. |
| `--file-formats FMT...` | `gz` | `geojson`, `gz`, `map`, and/or `transparent-raster`. GeoJSON remains the source for derived outputs. |
| `--vector-simplify M` | automatic | Douglas–Peucker tolerance in metres for Mapsforge output. |
| `--tiles-overwrite` | off | Rebuilds an existing `.map` or transparent overlay. |

Accepted IGN aliases:

```text
cadastre cours_eau troncons_eau plans_eau detail_hydro batiments
constructions cimetieres routes chemins lignes_orog detail_orog forets
reserves lieux_dits communes rpg
```

Automatic simplification is 3 m below 200 km², 8 m below 1,000 km², 15 m
below 15,000 km², 25 m below 100,000 km², and 40 m above that.

Roads and buildings as compressed GeoJSON plus Mapsforge:

```bash
python lidar2map.py --vector --zone-department 83 \
  --layer routes batiments --file-formats gz map
```

Paths as an OsmAnd overlay:

```bash
python lidar2map.py --vector --zone-city Gareoult --zone-width 5 \
  --layer chemins --file-formats gz transparent-raster
```

OsmAnd does not read Mapsforge `.map`; use `transparent-raster` as an overlay or
its own built-in OSM map. Locus and OruxMaps can use the Mapsforge result.

## Merge vector sources

`--merge` combines `.geojson` and `.geojson.gz` sources, including shell globs.
It adds a `source` property identifying the input file to merged features.

```bash
python lidar2map.py --merge \
  --source cadastre.geojson cours_eau.geojson osm_gareoult.geojson \
  --output-file gareoult_fusion.geojson
```

| Option | Default / values | Meaning |
|---|---|---|
| `--source FILE...` | required | Input files; glob patterns are expanded by lidar2map when the shell does not expand them. |
| `--output-file FILE` | derived beside first source | Explicit merged GeoJSON path. |
| `--output-dir PATH` | first source directory | Directory used only when the output filename is automatic. |
| `--no-gz` | off | Makes the automatic primary output `.geojson` instead of `.geojson.gz`. |
| `--file-formats FMT...` | `gz` | Requests secondary `map` and/or `transparent-raster` output; `geojson`/`gz` describe vector formats, while `--no-gz` controls compression of the automatic primary file. |
| `--vector-simplify M` | automatic | Mapsforge simplification tolerance in metres. |

Merge a set selected by a glob and build both a Mapsforge map and OsmAnd
overlay:

```bash
python lidar2map.py --merge \
  --source "Projets/gareoult/*/*.geojson*" \
  --output-file Projets/gareoult/fusion/gareoult.geojson.gz \
  --file-formats gz map transparent-raster
```

A missing or unreadable input makes the run fail visibly even if a partial
merged file could be written.

## Split an existing raster

`--split` re-splits one MBTiles without repeating its original download or
rendering:

```bash
python lidar2map.py --split --source large.mbtiles \
  --cols 3 --rows 4 --file-formats mbtiles sqlitedb
```

| Option | Default / values | Meaning |
|---|---|---|
| `--source FILE.mbtiles` | required | Source raster. |
| `--cols N`, `--rows N` | `0`, `0` | Explicit grid; both must be positive to split. |
| `--split-width KM` | `0` | Alternative approximate square side. |
| `--file-formats FMT...` | `mbtiles` | Keep each chunk as `mbtiles` and/or convert it to `rmap` or `sqlitedb`. |
| `--tiles-overwrite` | off | Replaces existing split chunks. |

With neither a complete grid nor a positive width, the source is returned
unchanged; the command can still convert it to another requested format.

```bash
python lidar2map.py --split --source large.mbtiles \
  --split-width 10 --file-formats rmap
```

If a conversion fails, lidar2map keeps that chunk's intermediate MBTiles rather
than deleting the only surviving data.

## Reuse and convert an existing source

`--source` has extension-dependent behaviour:

| Source | Required context | Result |
|---|---|---|
| `.mbtiles` | no area; explicit `--file-formats rmap` and/or `sqlitedb` | Direct conversion and exit. |
| `.tif` / `.tiff` | an area; preferably `--lidar`; output formats explicit unless `--lidar` supplies the MBTiles default | Existing shading is tiled directly if EPSG:3857, otherwise warped to Web Mercator first. |
| `.pbf` / `.osm` | `--osm` plus an area | Existing OSM data is filtered/rendered without automatic Geofabrik selection. |
| multiple GeoJSON files | `--merge` | Vector merge. |

Examples:

```bash
# MBTiles to both phone raster formats; no zone required
python lidar2map.py --source relief.mbtiles --file-formats rmap sqlitedb

# Existing shading GeoTIFF to raster deliverables
python lidar2map.py --lidar --provider fr-ign --source relief.tif \
  --zone-bbox 6.0,43.3,6.1,43.4 --file-formats mbtiles rmap

# Manually downloaded PBF, including outside France
python lidar2map.py --osm --source my-region-latest.osm.pbf \
  --zone-bbox 7.4,46.9,7.6,47.1 --file-formats map
```

## France-specific areas and examples

`--zone-department` accepts one INSEE code, a comma-separated list, a range, or
a mixture:

```bash
python lidar2map.py --lidar --provider fr-ign --zone-department 83
python lidar2map.py --raster --zone-department 30,35,75 --layer planign
python lidar2map.py --vector --zone-department 1-3,75,83 --layer chemins
```

Codes such as `5` are normalized (`05`), and `2A`, `2B`, and overseas codes are
accepted. A multi-département invocation runs each area in turn and continues
after an ordinary processing error; its final exit is non-zero if any area
failed. An explicit `--zone-name base` becomes `base_<department>` to avoid
collisions.

`--zone-region` uses the old pre-2016 region names published by
[Geofabrik France](https://download.geofabrik.de/europe/france.html), for
example `provence-alpes-cote-d-azur`, `bretagne`, `corse`, or `rhone-alpes`.
An unknown slug prints the accepted list.

For OSM, the selected regional PBF already has the real administrative outline
and is processed as one file without rectangular re-clipping:

```bash
python lidar2map.py --osm \
  --zone-region provence-alpes-cote-d-azur
```

For LiDAR, raster, and IGN vector workflows, the region is the bbox enclosing
all of its départements. IGN paths as compressed GeoJSON plus Mapsforge:

```bash
python lidar2map.py --vector \
  --zone-region provence-alpes-cote-d-azur \
  --layer chemins --file-formats gz map
```

IGN raster and IGN vector layer values are listed in their workflow sections
above. They remain France-only even though LiDAR and manually sourced OSM are
international.

## Cache and shading maintenance

Maintenance commands still require `--lidar`, an explicit `--provider`, and an
area because they must resolve the active provider, project, and cache scope.

| Option | Effect |
|---|---|
| `--tiles-purge-invalid` | Deletes cached source tiles below the active provider's validity threshold (2 MB for `fr-ign`). |
| `--tiles-purge-out-of-zone` | Deletes current-provider cached tiles not named in this project's `dalles_zone.txt`; it never deliberately purges another provider sharing the country cache. |
| `--shadings-compress` | Rewrites existing large raw shading GeoTIFFs with DEFLATE; tiled-warp caches are excluded. |

When one of these is requested without an explicit shading, preset, or output
format, lidar2map treats the invocation as maintenance-only: it does **not** add
the normal download, LRM, or MBTiles defaults.

```bash
# Purge only; no implicit tile download or map generation
python lidar2map.py --lidar --provider fr-ign \
  --zone-department 83 --tiles-purge-invalid

# Purge, then explicitly download missing tiles; still no implicit map
python lidar2map.py --lidar --provider fr-ign --zone-department 83 \
  --tiles-purge-invalid --download

# Compress existing raw shadings without requesting a new one
python lidar2map.py --lidar --provider fr-ign \
  --zone-city Gareoult --zone-width 2 --shadings-compress
```

Out-of-zone purge needs an existing `dalles_zone.txt`. If it is absent, run an
explicit `--download` once to build the zone list. Maintenance suppresses
implicit data transfer, but zone geocoding and provider discovery/index lookup
can still use the network; `--no-download` is the explicit cache-only statement
for source tiles.

## Serve maps to a phone

`--serve` recursively finds `.sqlitedb`, `.rmap`, `.mbtiles`, `.map`, and `.obf`
deliverables, serves them only on the local network, and prints a URL and QR
code. The phone must be on the same Wi-Fi. Stop the server with `Ctrl+C`.

```bash
python lidar2map.py --serve --zone-name gareoult
```

By default, this scans `Projets/gareoult`. With a custom processing output,
pass that exact directory; `--zone-name` remains required by the command:

```bash
python lidar2map.py --serve --zone-name gareoult \
  --output-dir D:/cartes/gareoult
```

In Locus, use **Map Manager → Import map → system file manager**. See
[Formats and mobile applications](formats.md) for app-specific advice.

## Rebuild an index sheet

Zone-based runs generate a best-effort `<product>_planche.png` from readable
deliverables. In the LiDAR/OSM parser, `--no-index-map` disables this automatic
step. Raster and IGN vector runs currently generate it automatically.

Rebuild sheets from an existing directory without reprocessing:

```bash
python lidar2map.py --index-sheet Projets/gareoult
```

`--planche` is the French alias. The command scans recursively and creates one
sheet per product; missing network-derived administrative outlines do not
prevent an extent/cell sheet from being written.

## Remote execution, stop, and purge

The integrated remote prefix must come first. A minimal headless launch on an
Ubuntu 24.04/26.04 x86-64 VM is:

```bash
lidar2map --remote-cli --bundle --session paris-lrm \
  root@192.0.2.10 -- \
  --lidar --provider fr-ign --zone-city Paris --zone-width 5
```

Everything after the standalone `--` is passed to lidar2map on the VM. Use a
different explicit session name for every concurrent run.

SSH host-key rollover is handled automatically: after a confirmed key-change
error, the controller removes only that VM's stale `known_hosts` entry and
retries once. `--reset-host-key` is only the proactive override.

Stop exactly one session, without purging it:

```bash
lidar2map --remote-cli --session paris-lrm --stop root@192.0.2.10
```

The controller first requests a graceful stop, then after 15 seconds targets
only that session's descendant process tree and tmux session. Other sessions
are untouched. The files remain available for diagnosis, reconnection, or a
later `--resume`.

After the session is terminal, perform a final synchronization and purge only
its verified run files:

```bash
lidar2map --remote-cli --session paris-lrm \
  --purge-remote root@192.0.2.10
```

Shared cache, production, source checkout, virtual environment, and runtime are
never purged. During interactive monitoring, `Ctrl+C` asks separately whether
to stop the remote session and whether to purge its files; declining purge is
the right choice when stopping because of a bug and keeping evidence for a
retry.

Read the canonical [remote execution guide](remote.md), especially
[targeted stop and file retention](remote.md#ctrlc-targeted-stop-and-file-retention)
and [safe remote purge](remote.md#safe-remote-purge), for sessions, reconnect,
resume/restart, synchronization, VM setup, and multi-VM sharding.

## Bootstrap and standalone maintenance

These options are consumed before the mode parser:

| Option | Default / effect |
|---|---|
| `--bootstrap auto\|pip\|none` | `auto`; use lidar2map's private venv, install into the active environment, or do no dependency installation. `LIDAR2MAP_BOOTSTRAP` supplies a lower-priority default. |
| `--help-bootstrap` | Prints bootstrap help and exits. |
| `--installer-deps` | Installs critical and optional build/runtime dependencies, then exits. |
| `--telecharger-outils` | Downloads the Temurin JRE, osmosis, and mapwriter, then exits. |
| `--desinstaller` | Removes lidar2map's extracted runtime, private venv, JRE, and osmosis; it does not remove the script, executable, release archive, projects, or shared user data outside those runtime locations. |
| `--smoketest` | Runs the built-in small validation pipelines. It downloads real data and can take several minutes on an empty cache. |

Legacy bootstrap aliases are `--no-bootstrap` → `none`, `--venv` → `auto`, and
`--no-venv` → `pip`.

## French aliases

Canonical English options are recommended in scripts. These compatibility
aliases are accepted by the current parsers:

| Canonical | Alias |
|---|---|
| `--lidar`, `--raster`, `--vector`, `--merge`, `--split` | `--ignlidar`, `--ignraster`, `--ignvecteur`, `--fusionner`, `--decouper` |
| `--zone-city`, `--zone-department`, `--zone-width`, `--zone-name` | `--zone-ville`, `--zone-departement`, `--zone-largeur`, `--zone-nom` |
| `--output-dir`, `--cache-dir`, `--production-dir`, `--tiles-dir` | `--dossier`, `--dossier-cache`, `--dossier-production`, `--dossier-dalles` |
| `--api-key`, `--layer` | `--apikey`, `--couche` |
| `--download`, `--download-force`, `--download-overwrite`, `--download-compress` | `--telechargement`, `--telechargement-forcer`, `--telechargement-ecraser`, `--telechargement-compresser` |
| `--shadings`, `--shading-elevation`, `--shadings-overwrite`, `--shadings-compress` | `--ombrages`, `--ombrages-elevation`, `--ombrages-ecraser`, `--ombrages-compresser` |
| `--file-formats`, `--image-format`, `--image-quality`, `--tiles-overwrite` | `--formats-fichier`, `--formats-image`, `--qualite-image`, `--tuiles-ecraser` |
| `--split-cols`, `--split-rows`, `--split-width`, `--block` | `--cols-decoupe`, `--rows-decoupe`, `--split-largeur`, `--bloc` |
| `--cleanup`, `--min-free-gb`, `--vector-simplify` | `--nettoyage`, `--min-disque-go`, `--simplification-vecteur` |
| `--tiles-purge-invalid`, `--tiles-purge-out-of-zone` | `--dalles-purger-invalides`, `--dalles-purger-hors-zone` |
| `--output-file`, `--index-sheet` | `--sortie`, `--planche` |

Boolean optional actions also expose their negative English form, notably
`--no-download`, `--no-download-compress`, `--no-svf-sweep`, and
`--no-index-map`. `--shadings all`/`none` and `--shadings tous`/`aucun` are
equivalent pairs.

## Exit codes useful in automation

| Code | Meaning |
|---:|---|
| `0` | Completed successfully. |
| `1` | Processing or partial-output failure in most local workflows. |
| `2` | Argument-parser error. |
| `3` | Clean pre-chunk stop caused by `--min-free-gb`. |
| `130` | User interruption (`Ctrl+C`). |

Remote-controller exit codes additionally distinguish SSH, monitoring, and
synchronization failures; see the [remote guide](remote.md).

---

[Documentation index](README.md) · [Getting started](getting-started.md) ·
[Formats](formats.md) · [Providers](providers.md) · [Visualizations](shadings.md)
