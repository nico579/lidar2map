***English** | [Français](contributing-providers.fr.md) · [Provider catalogue](providers.md) · [Documentation index](README.md)*

# Contributing a LiDAR provider

lidar2map isolates national and regional source logic in `providers/`. A
provider discovers source data for a geographic extent and hands normalized
GeoTIFF inputs to the common pipeline; relief computation, EPSG:3857
reprojection, tiling, and output formats remain provider-agnostic.

This guide describes the integration contract. It intentionally does not
repeat the user-facing [provider catalogue](providers.md). The
[provider roadmap](lidar_providers_roadmap.md) records sources already
evaluated, including rejected and deferred candidates.

## 1. Eligibility

A source is a direct fit when a programmable endpoint returns either:

- bare-earth elevation values as GeoTIFF, COG, ASC, or another reliably
  convertible raster; or
- a ground-classified LAZ/LAS point cloud that can be converted to a terrain
  model.

Supported discovery and access patterns include:

- deterministic tile URLs;
- WCS `GetCoverage` by extent;
- STAC catalogues;
- window-readable mosaic COGs or VRTs;
- ATOM, WFS, ArcGIS FeatureServer, or object-store spatial indexes;
- ArcGIS ImageServer elevation exports;
- convertible LAZ, LAS, ZIP, XYZ, or ASC tiles.

The common pipeline already handles classified LAZ-to-DTM conversion, windowed
reads from very large COGs, object-store listings used as spatial indexes,
scoped GDAL HTTP authentication, and free-account/API-key sources.

### Blocking cases

Record the endpoint tested and one precise reason when a source cannot be
integrated:

- **B1 — no programmable endpoint:** interactive basket, form, or deferred
  e-mail delivery only;
- **B2 — rendered imagery only:** WMS/WMTS/TPK pixels with no raw elevation
  values;
- **B3 — inadequate data:** coastal strip only, unusable gaps, or nominal
  resolution at or above roughly 10 m for this workflow;
- **B4 — incompatible access or licence:** restricted redistribution/use,
  unavailable from abroad, or a mandatory process that cannot be automated.

Missing or unreliable CRS metadata requires explicit handling and validation;
it must never be guessed silently.

Two legacy integrations are exceptions, not precedents: `au-nsw` is a 5 m
stereo-photogrammetric DEM kept as the best openly available state source, and
`us-3dep` has a 10 m default fallback even though its intended high-resolution
path is `USGS1m`. Prefer `us-tnm` for public US 1 m data.

## 2. Start from the nearest access pattern

Copy the closest working provider and adapt its endpoint, CRS, naming, and
coverage:

| Access pattern | Starting point | Notes |
|---|---|---|
| WCS 2.0 | `providers/es_cnig.py` or `providers/de_hessen.py` | Synthetic grid clipped to the coverage extent; `GetCoverage` per bbox |
| WCS 1.0 | `providers/es_euskadi.py` or `providers/it_piemonte.py` | Older BBOX/WIDTH/HEIGHT contract; validate the returned pixel type |
| STAC + windowed COG | `providers/ca_nrcan.py` | Select the elevation asset and read only the requested window through `/vsicurl/` |
| Authenticated STAC/COG | `providers/se_lantmateriet.py` | Return scoped options from `gdal_env_options()`; never set global credentials |
| ATOM index | `providers/de_thueringen.py` or `providers/cz_cuzk.py` | Grid/XYZ and two-level LAZ examples |
| ArcGIS ImageServer | `providers/no_kartverket.py` | `exportImage` by bbox; reproject on download only when required |
| ArcGIS FeatureServer | `providers/ie_gsi.py` or `providers/si_arso.py` | Feature index leading to downloadable/convertible source tiles |
| Object-store listing | `providers/gb_scotland.py` or `providers/lv_lgia.py` | Object keys or LAS headers supply spatial extents |
| Metalink | `providers/de_bayern.py` or `providers/de_rlp.py` | Use the index when survey year or the real tile URL is not deterministic |
| Single large COG/VRT | `providers/lu_act.py`, `providers/es_icgc.py`, or `providers/us_cnmi.py` | Windowed range reads; never fetch the full national file |

The first provider for a new access paradigm can take substantially longer;
once a pattern exists, a close variant is usually a small module rather than a
core-pipeline change.

## 3. Provider module contract

Provider codes use hyphens (`no-kartverket`); Python filenames use underscores
(`providers/no_kartverket.py`). Modules are discovered automatically from
`providers/*.py`, so there is no central registry to edit. A utility module
without `CODE` is ignored, and `*_laz.py` twins are hidden from the GUI provider
list.

A normal provider exposes at least:

```python
NAME = "Human-readable source name"
CODE = "cc-source"
COUNTRY = "cc"
LICENSE = "Source licence and attribution"
DOC_URL = "https://official-source.example/"

CRS_NATIF = "EPSG:0000"
RESOLUTION_M = 1.0
DALLE_KM = 1
PX_PAR_DALLE = 1000
SEUIL_DALLE_VALIDE = 100_000

def discover_dalles(bbox_wgs84, bbox_natif, cache_path, workers=1):
    """Return {safe_tile_filename: URL_or_source_descriptor}."""
    ...
```

`discover_dalles` must return only the sources intersecting the requested area.
Tile names must be deterministic and safe as local filenames. Use helpers from
`providers/common.py` rather than duplicating download, conversion, or spatial
logic.

For a new country, also add its display order and English/French names to
`providers.common.COUNTRY_INFO` so the GUI groups it correctly.

### Optional hooks

Use optional hooks only for source-specific behaviour:

- `post_fetch`: unpack or convert ZIP, LAZ, LAS, ASC, or XYZ input into the
  GeoTIFF contract consumed downstream;
- `pre_download`: prepare or reuse a derived local source before the normal
  download path;
- `gdal_env_options()`: return host-scoped GDAL HTTP options;
- `set_apikey(key)`: accept `--api-key` without hard-coding credentials;
- `sign_url(url)`: sign a remote asset at download time;
- `subdir_from_name`: distribute large caches without changing tile identity.

The exact hook signatures are best copied from the nearest current provider,
because the common downloader calls them defensively and supports several
source descriptor types.

## 4. Classified point clouds and DFM twins

Add a `providers/<stem>_laz.py` twin only when the source publishes the **full,
dense, classified point cloud** through a reproducible endpoint. A raster DTM
or a ground-only cloud cannot restore standing structures that the producer
already removed.

Reuse `providers.common.LazProvider` for parameter handling, injective cache
naming, class-based or CSF ground construction, CRS checks, and download/
conversion hooks. The twin is selected through `--laz` on its parent provider;
it is not a second entry in the GUI dropdown.

Density, class semantics, CRS, tile bounds, authentication, and archive format
must be validated independently for every source. Do not assume ASPRS/IGN class
codes are portable; use CSF as the default where producer classes are not
reliably documented.

## 5. Discovering candidate services

`tools/discover_providers.py` queries an INSPIRE CSW catalogue for elevation
services and probes WCS capabilities:

```bash
python tools/discover_providers.py de
python tools/discover_providers.py es
python tools/discover_providers.py <csw_url> "<keyword>" [dc|iso]
```

This produces a shortlist, not proof of compatibility. National catalogues can
miss valid regional services, and a successful `DescribeCoverage` does not prove
that the layer is a DTM rather than a DSM or that `GetCoverage` returns usable
data. Search the national mapping agency and regional geoportals directly as a
second pass.

## 6. Validation checklist

Before opening a PR:

1. Verify the official licence, attribution, geographic coverage, nominal
   resolution, CRS, units, NoData convention, and update cycle.
2. Probe the real endpoint and download at least one real tile inside coverage.
   A catalogue or header-only check is insufficient.
3. Confirm that the decoded values are elevations, not a rendered image or a
   surface model accidentally labelled as terrain.
4. Run `discover_dalles` on a small bbox and check deterministic, collision-free
   filenames and bounded discovery results.
5. Validate every conversion path through to a georeferenced GeoTIFF with the
   advertised resolution and CRS.
6. Run a small end-to-end lidar2map job through relief generation, reprojection,
   and tiled output.
7. Add an in-coverage smoke-test point to `Tests/smoke_providers.py`.
8. Regenerate `coverage.png` / `coverage.fr.png` / `coverage.geojson` with
   `coverage_map.py` when the geographic catalogue changes.
9. Update the [provider catalogue](providers.md), credentials section if
   applicable, and [data/source acknowledgements](data-licenses.md).

The current status and previous runs are available in the
[provider smoke-test workflow](https://github.com/nico579/lidar2map/actions/workflows/smoke.yml).

Never commit a private token, username, password, signed URL, or temporary
session cookie. Public keys supplied by the official source should still be
documented explicitly rather than hidden in unrelated code.

## 7. Record rejected and deferred sources

Do not discard investigation results. Add the tested endpoint, date, status,
and precise blocker to the
[provider roadmap](lidar_providers_roadmap.md), using its `WATCH`, `STABLE`,
or `HARD` convention where appropriate. This avoids repeating the same portal
investigation and makes future re-evaluation evidence-based.
