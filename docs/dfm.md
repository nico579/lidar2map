***English** | [Français](dfm.fr.md) · [Providers](providers.md) · [LiDAR CLI reference](../README.md#31-lidar) · [Visualization guide](shadings.md) · [Back to the main documentation](../README.md#documentation)*

# Standing structures with LAZ, DFM, and CSF

National bare-earth digital terrain models are excellent for earthworks, but
they can erase the very feature being searched for when it still stands above
the ground. lidar2map's point-cloud mode rebuilds a surface from the full
classified LAZ/LAS source so that low standing structures can remain available
to LRM, SVF, openness, VAT, and every other relief visualization.

> **This is a candidate-generation tool, not a wall or archaeology
> classifier.** Vegetation, rocks, modern objects, and classification errors can
> return with the walls. Keep the area small, compare independent layers, and
> validate interpretations on the ground where access and heritage rules allow.

## Why a bare-earth DTM can lose a ruin

National producers deliberately classify a terrain model as **bare earth**.
For IGN LiDAR HD, ground/water/virtual-ground returns form the terrain base,
while a wall still standing above roughly 1 m is commonly classified as
vegetation or unclassified. The official DTM interpolates through the resulting
gap. Once the wall has been removed from that raster, no hillshade or other
visualization computed from the DTM can restore it.

This creates a useful distinction:

- low banks, ditches, terraces, and heavily collapsed walls often remain in the
  official DTM and are best surveyed with the normal lidar2map workflow;
- roofless walls and other low standing structures may require the full point
  cloud and a reconstructed **Digital Feature Model** (DFM).

The DFM concept—terrain plus archaeological standing features in one
model—comes from
[Štular et al. (2021)](https://doi.org/10.3390/rs13091855). lidar2map's
automatic class/height selection is its own first-pass heuristic, calibrated
on two sites in the Var, France. The published workflow uses more deliberate,
often semi-manual reclassification. The implementation must therefore be read
as prospection assistance, not as the published method reproduced exactly.

## Enable point-cloud mode

In the GUI, select a provider that exposes a point-cloud mode and enable
**DFM mode** next to it. In the CLI, select the normal parent provider and add
`--laz`:

```bash
python lidar2map.py \
  --lidar --provider fr-ign --laz --download \
  --zone-gps <lat>,<lon> --zone-width 1 --zone-name site \
  --shadings lrm svf --file-formats mbtiles
```

All requested visualizations are then computed from the reconstructed
point-cloud surface instead of the official DTM. DFM changes the **input
surface**; LRM, SVF, VAT, and the other outputs still have their normal meaning.
See the [visualization guide](shadings.md) when choosing how to render the
result.

Start with a small zone around a known or suspected structure. A department- or
region-scale point-cloud run is rarely a sensible first experiment.

<p align="center">
  <img src="../screenshots/GUI/lidar_laz_classes.PNG" alt="DFM form using producer classes" width="440">
  <img src="../screenshots/GUI/lidar_laz_csf.PNG" alt="DFM form using the Cloth Simulation Filter" width="440">
</p>

*The GUI exposes the class-based and CSF ground-base methods separately while
keeping the same LiDAR outputs.*

## Two reconstruction methods

lidar2map exposes two ground-base methods under the same `--laz` mode. Output
names distinguish them as `laz_dfm` (class re-injection) and `laz_csf` (cloth
filter).

### Class-based re-injection

Select `--laz-ground classes`. On IGN, this is the default.

The pipeline:

1. bins the provider's selected terrain classes to form a ground base;
2. fills that base temporarily to estimate each point's height above ground;
3. selects low non-ground points inside the `hmin`–`hmax` band;
4. re-injects those points **only into cells where the terrain base has a
   hole**;
5. performs a final interpolation bounded to 200 m and writes the DFM GeoTIFF.

For `fr-ign`, the default selected classes are `1,2,3,4,9,66`. Classes
`2,9,66` form the terrain base and `1,3,4` are candidates for re-injection
between 0.4 and 2.5 m above it.

This mode is fast and preserves producer knowledge, but its result depends on
the source's class semantics. One ground return inside a wall cell keeps the
ground and prevents the wall from being re-injected there. Dense scrub can also
return as speckle. If a wall looks incomplete, first check the provider's class
scheme; on IGN, class 5 can be tested explicitly when walls were classified as
high vegetation.

### Cloth Simulation Filter

Select `--laz-ground csf`. Most non-IGN point-cloud providers use it by default
because their producer classes are heterogeneous or insufficiently documented.

The [Cloth Simulation Filter](https://www.cloudcompare.org/doc/wiki/index.php/CSF_(plugin))
inverts the cloud and drapes a virtual cloth over it. lidar2map deliberately
uses a soft cloth so low continuous structures can be absorbed into the
reconstructed surface while canopy points are rejected. A class-independent
canopy pre-filter first keeps points within 3.5 m of a 5 m local minimum; on the
calibration clouds this retained about 57% of the points.

On the two Var validation sites, CSF retained an equivalent wall signal with a
cleaner background than class re-injection. It is much slower, remains
sensitive to terrain and density, and is not a wall classifier.

`hmin`, `hmax`, and `classes` are ignored in CSF mode. Conversely, `csf-*`
settings are ignored in class mode; lidar2map reports either mismatch.

| Choose | Best starting point | Main cost or risk |
|---|---|---|
| `classes` | Well-documented producer classes; rapid retuning; IGN | Speckle and missed walls where a ground return already occupies the cell |
| `csf` | Heterogeneous classes; cleaner background; most international providers | Several minutes per tile, ~3 GB RAM per conversion, parameter sensitivity |

## Parameters

Defaults can vary by provider and are shown by the GUI. The values below are
the common defaults; `fr-ign` defaults to `classes` while most other
point-cloud providers default to `csf`.

| CLI option | Common default | Applies to | Effect |
|---|---:|---|---|
| `--laz` | off | both | Switch from the official DTM to the provider's classified point cloud |
| `--laz-ground classes\|csf` | provider-specific | both | Select class re-injection or cloth reconstruction |
| `--laz-hmin M` | 0.4 m | classes | Minimum candidate height above the reference ground |
| `--laz-hmax M` | 2.5 m | classes | Maximum candidate height above the reference ground |
| `--laz-classes LIST` | provider-specific | classes | Comma-separated terrain and candidate LAS classes |
| `--laz-csf-threshold M` | 0.5 m | CSF | Maximum point-to-cloth distance absorbed as ground; increasing it can retain more degraded walls **and** more scrub |
| `--laz-csf-resolution M` | 0.5 m | CSF | Cloth grid size; valid range 0.1–3.0 m |
| `--laz-csf-rigidness N` | 1 | CSF | `1` steep/soft, `2` intermediate, `3` flat/rigid; `3` approaches bare earth and can erase standing walls |
| `--laz-parallel N` | 1 | conversion | Concurrent LAZ conversions; budget roughly 3 GB RAM per conversion |

Threshold and cloth resolution accept 0.1–3.0 m. The solver's time step,
iteration count, and canopy pre-filter are intentionally fixed: they are
implementation controls rather than interpretable site parameters.

Advanced class behaviour:

- omitting class 2 produces a slice-like output containing band-selected
  objects on a transparent background; heights are still referenced to
  class-2 ground;
- selecting no re-injected class produces approximately a rebuilt DTM.

These are diagnostic configurations, not recommended first runs.

## Time, storage, RAM, and cache

Costs depend on point density, archive format, server access, CPU, and the
selected method. Measurements below are orders of magnitude, not guarantees:

| Source/example | Download or density | Classes | CSF | Memory note |
|---|---|---:|---:|---|
| IGN LiDAR HD, France | ~205 MB/km²; dense COPC | ~20–25 s/tile | ~3–4 min/tile | ~2.9–3 GB peak on a ~45 M-point tile |
| swissSURFACE3D | ~125 MB/km² | provider-dependent | around 6 min/tile | Keep the area targeted |
| Denmark DHM/Punktsky | ~82 MB and ~12 M points/km² | ~19 s/tile | ~6.4 min/tile | Denser cloth simulation is slower |
| NRCan COPC sample | ~40 points/m² | provider-dependent | provider-dependent | 1 km² can mean ~1 GB temporary LAS and ~3 GB RAM |

Times were measured on specific machines and datasets. A 4-core machine showed
no useful gain from running several conversions concurrently because one CSF
conversion already uses multiple cores. Increase `--laz-parallel` only on a
larger VM with both spare cores and roughly `N × 3 GB` available RAM.

### Cache behaviour

- The downloaded LAZ/LAS cloud is kept in the tile cache.
- The derived DFM/CSF GeoTIFF lives in production output.
- The same cloud is shared across class, height-band, and CSF experiments.
- Non-default settings are encoded in derived tile and project names, preventing
  DTM, class-DFM, and CSF outputs from being silently mixed.
- Retuning rebuilds from the cached cloud without another network download.
- Use `--download-overwrite` only when the source itself must be fetched again.

Conversions are written atomically through a temporary file, so an interrupted
conversion is not accepted later as a complete GeoTIFF. Dependencies
(`laspy`, `lazrs`, and CSF when requested) are checked before a heavy download
and installed on demand in the managed Python environment; standalone bundles
already include them.

## Multi-provider scope

DFM mode requires the **full, dense, classified point cloud**. A bare-earth
raster or ground-only cloud has already lost the standing structures and cannot
support it. The current point-cloud implementations are summarized below; the
[provider catalogue](providers.md) remains authoritative for live availability,
credentials, coverage, and source sizes.

| Parent provider | Point-cloud notes | Default | Validation status or caution |
|---|---|---|---|
| `fr-ign` | IGN COPC, ~205 MB/km² | classes | Class and CSF methods field-checked on two Var sites |
| `ch-swisstopo` | swissSURFACE3D `.las.zip`, ~125 MB/km² | CSF | End-to-end conversion; field validation recommended |
| `pl-gugik` | ~28 points/m²; PL-2000 CRS varies by zone | CSF | End-to-end validated |
| `ee-maaamet` | ~4 points/m² in the tested standard cloud | CSF | Technically valid but marginal for a 0.5 m grid; field validation pending |
| `be-flanders` | ~11 points/m²; OpenLidar classified cloud | CSF | End-to-end validated |
| `ca-nrcan` | Windowed remote COPC, up to ~40 points/m² in the test | CSF | Only the requested bbox is read; dense windows remain RAM-heavy |
| `ca-quebec` | Direct LAZ, ~10 points/m² in the test; multiple MTM zones | CSF | End-to-end validated; project-based coverage |
| `us-3dep` | Windowed Planetary Computer COPC; ~5 points/m² in the tested older survey, often denser in newer projects | CSF | No account for LAZ; project-based coverage |
| `dk-datafordeler` | ~12 points/m²; API key required | CSF | End-to-end validated; CSF measured around 6.4 min/tile |
| `fr-craig` | Very dense regional campaigns, up to ~60 points/m² in the test | CSF | Named regional campaigns, not wall-to-wall France |

“End-to-end validated” means discovery, download, CRS handling, conversion, and
GeoTIFF output were exercised. It does **not** mean that archaeological recall
and false-positive rates were field-validated for that country.

## Visual comparison

This roofless house ruin in the Var, France has walls around 1.5 m high under
scrub. The aerial image barely hints at them. The classic LRM from the official
DTM shows surrounding terraces but not the ruin. Both point-cloud methods bring
the rectangular footprint back; CSF produces the cleaner background.

| Aerial ortho | Classic LRM from the DTM |
|---|---|
| ![Aerial ortho, walls hidden under scrub](../screenshots/LIDAR_Samples/Ruins/ortho.jpg) | ![LRM from the bare-earth DTM, ruin not visible](../screenshots/LIDAR_Samples/Ruins/lrm.jpg) |
| Walls lost under vegetation | Terraces show; the ruin does not |
| **DFM-LRM: class re-injection** | **DFM-LRM: CSF cloth base** |
| ![DFM by class re-injection, walls reappear with speckle](../screenshots/LIDAR_Samples/Ruins/dfm_lrm.jpg) | ![DFM with CSF cloth ground base, cleaner background](../screenshots/LIDAR_Samples/Ruins/csf_lrm.jpg) |
| Rectangular building reappears, with speckle | Same walls, cleaner background |

## Interpretation and field validation

Never interpret the DFM layer alone. A practical review stack is:

1. official-DTM LRM or another familiar bare-earth visualization;
2. class-DFM and/or CSF LRM using the same scale;
3. DFM minus DTM delta where available;
4. current and historical orthophotos;
5. SVF, openness, slope, or another independent visualization;
6. field observation where lawful and safe.

Read continuous lines, corners, repeated geometry, and agreement between
independent views more seriously than isolated bright/dark dots. Scrub commonly
appears as speckle; rocks, scarps, terraces, forestry traces, buildings, and
modern debris can mimic archaeological forms.

Known limitations:

- class re-injection can miss a wall when a single ground return occupies its
  cell;
- CSF can retain vegetation or erase walls, especially with an unsuitable
  threshold or `rigidness=3`;
- low-density clouds may not sample narrow masonry well enough for a 0.5 m
  output;
- the integrated output does not yet provide measured/interpolated, density,
  confidence, or re-injection masks;
- interpolation can bridge data gaps by up to 200 m, so a smooth shape is not
  proof of direct measurement;
- minimum-height binning remains sensitive to an abnormally low return that was
  not marked as noise/withheld; a robust low-quantile alternative still needs
  field calibration;
- cloth filtering has no cross-tile halo yet; inspect suspicious features at
  tile boundaries;
- CSF uses OpenMP and is not guaranteed bit-identical between runs. Validate
  the final raster and interpretation, not raw CSF point-index lists;
- acquisition year, classification scheme, and survey density vary between and
  sometimes within providers.

Avoid launching separate processes against the same point-cloud cache and area
at the same time: derived files are atomic, but a cross-process LAZ conversion
lock is not implemented yet.

The pipeline automatically rejects incompatible CRS/unit combinations where
they can be resolved, filters ASPRS noise classes 7/18 and withheld points
before minimum-height binning, and uses nominal tile bounds where available to
reduce seams. If a ZIP unexpectedly contains several point clouds, it warns and
currently keeps only the largest one.

Field validation remains the decisive test. The current heuristic needs
adversarial checks on known ruins and negative areas containing rocks, cliffs,
terraces, and scrub, including structures that cross several source tiles.
Do not publish precise coordinates of sensitive remains, dig, or use the output
to bypass archaeological and land-access rules.

## Standalone QGIS comparison tool

For a targeted **IGN France** comparison outside the main pipeline,
[`tools/dfm_ruines.py`](../tools/dfm_ruines.py) downloads the COPC LAZ, performs
class-based reconstruction, and writes three georeferenced EPSG:2154 GeoTIFFs:

- `<prefix>_lrm_mnt.tif` — LRM of the reconstructed ground-only DTM;
- `<prefix>_lrm_dfm.tif` — LRM of the DFM, with standing candidates and scrub;
- `<prefix>_delta.tif` — DFM minus DTM in metres.

```bash
python tools/dfm_ruines.py \
  --center <lon>,<lat> --rayon 150 --out site

python tools/dfm_ruines.py \
  --bbox <west>,<south>,<east>,<north> --out zone --cache laz_cache
```

Standalone defaults are 0.5 m output, height band 0.4–2.5 m, candidate classes
`1,3,4`, LRM sigma 7.5 m, and `./laz_cache`. Class 6 can be included for a
specific built-feature test. This script does not run CSF.

In QGIS, a useful first comparison is to display `*_lrm_dfm.tif` in grayscale
around −0.5 to +0.5 m over the orthophoto, then threshold `*_delta.tif` around
0.4–1 m to inspect candidates. Adjust those display limits to the site and
always compare with `*_lrm_mnt.tif`. Lines and rectangles are candidates;
speckle is commonly scrub.

One IGN source tile is roughly 205 MB/km², so this remains a few-km² inspection
tool. It uses `laspy`/`lazrs`, rasterio, SciPy, NumPy, and pyproj; the managed
lidar2map environment already provides these dependencies.

## Related documentation

- [LiDAR providers, coverage, credentials, and DFM-capable sources](providers.md)
- [LiDAR CLI reference](../README.md#31-lidar)
- [Choosing and understanding relief visualizations](shadings.md)
- [Engineering review log for LAZ/DFM/CSF](dfm_reviews.md), retained as a
  historical decision record rather than a user guide
