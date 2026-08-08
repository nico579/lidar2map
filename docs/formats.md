# Output formats and mobile applications

***English** | [Français](formats.fr.md) · [Documentation index](README.md)*

Generated formats are not interchangeable. Choose the format for the target
application before starting a large job. For installation and the graphical
workflow, see [Getting started](getting-started.md).

## Map families

### LiDAR and raster maps

LiDAR relief visualizations and classic imagery are written as tiled raster
maps. Available classic raster sources include:

- **IGN, France only:** Plan IGN, current orthophotos, historical orthophotos
  from 1950, 1965, and 1980, nineteenth-century État-Major maps, Pléiades
  satellite imagery, colour infrared imagery, and other IGN layers.
- **USGS, USA (`--layer naip`):** public-domain NAIP-derived aerial imagery at
  about 1 m. The cache is complete through zoom 16 and complements 3DEP LiDAR
  from the `us-tnm` provider.

Raster deliverables can be MBTiles, OsmAnd/RMaps SQLiteDB, or RMAP.

For IGN raster, `--provider fr-ign` uses WMTS and `--layer` accepts an alias or
the full WMTS identifier. `planign` is the default alias. Public aliases are:

| Family | IGN raster aliases |
|---|---|
| Topographic | `planign etatmajor40 etatmajor10 pentes` |
| Imagery | `ortho ortho_1950 ortho_1965 ortho_1980 ortho_irc pleiades spot edugeo_marseille_1969 edugeo_marseille_1980 edugeo_marseille_1987 edugeo_marseille_1988 edugeo_marseille_2010 edugeo_toulon_1972` |
| Thematic | `cadastre ombrage` |

The professional aliases `scan25`, `scan25tour`, `scan100`, and `scanoaci`
require a `cartes.gouv.fr` key through `--api-key`; public layers do not. For
USA imagery, use `--provider us-tnm --layer naip`. Raster download defaults to
eight parallel connections.

### Vector maps

lidar2map can create an international OSM Mapsforge `.map`, or use IGN BD TOPO
vector data in France. Automatic Geofabrik selection currently covers France;
for another country, supply the corresponding `.osm.pbf` with `--source`.
Vector data can also be exported as GeoJSON.

Both OSM and IGN selections can be rendered as `transparent-raster`: selected
features such as paths, roads, and rivers are drawn as alpha-transparent PNG
tiles inside a `.sqlitedb` file. This is intended to float above LiDAR relief
as an OsmAnd overlay, because OsmAnd cannot natively overlay arbitrary vector
data.

With `--osm`, `--layer` accepts any free-form OSM `key=value` tag. If omitted,
the selection is:

```text
highway=* waterway=* boundary=administrative natural=water
natural=coastline waterway=river waterway=stream waterway=canal
```

The graphical catalogue also offers `natural=*`, `landuse=*`, `building=*`,
and `historic=*`. For a French `--zone-region`, the Geofabrik regional PBF is
already clipped to the real administrative outline, so it is used directly
rather than re-clipped to a rectangular bounding box.

With `--vector`, the default IGN WFS layer is `cadastre`. Available aliases are:

```text
cadastre cours_eau troncons_eau plans_eau detail_hydro batiments
constructions cimetieres routes chemins lignes_orog detail_orog forets
reserves lieux_dits communes rpg
```

IGN WFS downloads use at most four parallel connections; requesting more makes
layers start to fail. `--vector-simplify M` sets an explicit Douglas–Peucker
tolerance in metres; otherwise lidar2map chooses it automatically.

Vector merge accepts several GeoJSON sources, including a glob, and can combine
neighbouring runs or IGN and OSM layers from the same area. `--output-file`
sets the result name. The merged data can remain GeoJSON or directly produce a
Mapsforge map or transparent raster overlay.

## Processing screens

The five workflows share the same area and output controls, while exposing
only the source-specific settings that apply to the selected operation.

| Classic raster | IGN vector | OSM vector |
|---|---|---|
| <img src="../screenshots/GUI/raster.PNG" alt="Classic raster workflow" width="300"> | <img src="../screenshots/GUI/vector_ign.PNG" alt="IGN vector workflow" width="300"> | <img src="../screenshots/GUI/vector_osm.PNG" alt="OSM vector workflow" width="300"> |

| Vector merge | Raster split |
|---|---|
| <img src="../screenshots/GUI/vector_merge.PNG" alt="Vector merge workflow" width="440"> | <img src="../screenshots/GUI/raster_split.PNG" alt="Raster split workflow" width="440"> |

The LiDAR DTM screen is shown in [Getting started](getting-started.md#first-launch-and-graphical-workflow),
and the two LAZ/DFM variants are shown in [DFM, LAZ, and CSF](dfm.md#enable-point-cloud-mode).

## Format compatibility

The table describes the files as lidar2map writes them: tiled raster,
Mapsforge vector map, or interchange GeoJSON.

| Generated format | Type written by lidar2map | Main applications | Recommendation |
|---|---|---|---|
| **MBTiles** (`.mbtiles`) | XYZ/TMS tiled raster using JPEG or PNG; edge tiles may retain alpha | **Locus Map**, **OruxMaps**, **AlpineQuest**, **Guru Maps**, QGIS | The most versatile raster output and the recommended format for Locus. OsmAnd does not directly use it as a raster map: also request SQLiteDB or convert it. |
| **OsmAnd/RMaps SQLiteDB** (`.sqlitedb`) | Tiled raster in the SQLite schema expected by OsmAnd | **OsmAnd** as a map or overlay, RMaps, Guru Maps, and other RMaps-compatible applications | Recommended for OsmAnd. `transparent-raster` stores alpha-transparent PNG tiles for overlays. Prefer lidar2map MBTiles for Locus. |
| **RMAP** (`.rmap`) | Georeferenced raster using JPEG tiles in a proprietary format | **TwoNav / CompeGPS**, **OruxMaps**, AlpineQuest; limited support in Locus | Intended mainly for TwoNav/CompeGPS. lidar2map re-encodes tiles as JPEG as required by RMAP. |
| **Mapsforge** (`.map`) | OSM or IGN vector map in Mapsforge format | **Locus Map**, **OruxMaps** | Put the file in the application's vector-map directory. It is not a raster. OsmAnd uses `.obf` and cannot read Mapsforge maps. |
| **GeoJSON** (`.geojson` or `.geojson.gz`) | Vector features such as paths, roads, rivers, and buildings | **Locus Map** data import, **Guru Maps** overlay, **QGIS**, geojson.io, and other GIS tools | GeoJSON is interchange data, not an offline map displayed like MBTiles or `.map`. Decompress `.gz` if the target does not handle gzip. For a real Locus vector map, use Mapsforge. |

## Output controls

`--file-formats` accepts mode-dependent values:

- LiDAR, raster, and raster split: `mbtiles`, `rmap`, `sqlitedb`;
- vector and vector merge: `map`, `geojson`, `gz`,
  `transparent-raster`.

The relevant raster controls are:

| Parameter | Default | Effect |
|---|---|---|
| `--zoom-min` | 13 for LiDAR, 10 for classic raster | Lowest tiled-map zoom |
| `--zoom-max` | 18 for LiDAR, 16 for classic raster | Highest tiled-map zoom |
| `--image-format` | `auto` | Chooses JPEG or PNG; explicit `jpeg` and `png` are also accepted |
| `--image-quality` | 85 | JPEG quality from 1 to 100 |
| `--tiles-overwrite` | Off | Regenerates existing MBTiles, SQLiteDB, RMAP, or Mapsforge files |

`gz` writes compressed GeoJSON. During vector merge, `--no-gz` requests a
plain `.geojson` file instead. Raster split can also take an existing MBTiles
and convert each resulting chunk to RMAP or SQLiteDB.

The index sheet generated next to these files is not itself a map format; see
[Index sheet](getting-started.md#index-sheet).

## Send a project to a phone

After generation, select the 📲 button in the graphical interface. lidar2map
serves the project's deliverable directory over the local Wi-Fi network and
shows a URL and QR code. Scan it on the phone and download the desired files.
Nothing is uploaded outside the local network.

The command-line equivalent is:

```bash
lidar2map --serve --zone-name PROJECT_NAME
```

![Local Wi-Fi transfer page and QR code](../screenshots/GUI/phone.PNG)

## Locus Map

- Prefer MBTiles for a LiDAR or imagery raster.
- Use a Mapsforge `.map` for a true offline vector map.
- GeoJSON imports features into the data manager; it does not behave like an
  offline base map.
- In Locus, use **Map Manager → Import map → system file manager** after
  downloading. Android's **Open with** action may also work depending on the
  device and version.

Archaeological LiDAR relief can be displayed directly or as an overlay:

| SVF | Multidirectional hillshade overlay |
|---|---|
| <img src="../screenshots/LIDAR_Samples/Svf_LocusMap.jpg" alt="SVF displayed in Locus Map" width="300"> | <img src="../screenshots/LIDAR_Samples/Multi_LocusMap.jpg" alt="Multidirectional hillshade displayed in Locus Map" width="300"> |

## OsmAnd

- Prefer `.sqlitedb` for a raster map or overlay.
- OsmAnd does not directly use lidar2map MBTiles as raster maps.
- OsmAnd does not read Mapsforge `.map`; it uses its own `.obf` vector format.
- `transparent-raster` is the appropriate output for paths, roads, rivers, or
  other selected vector features above an existing OsmAnd map.

To show a LiDAR raster above the standard map, open **Configure map → Overlay
map** and move the transparency slider to roughly the middle.

<p align="center"><img src="../screenshots/LIDAR_Samples/LRM_OSMAND_Transparent.jpg" alt="Semi-transparent LRM overlay in OsmAnd" width="380"></p>

## Other supported applications

- **TwoNav / CompeGPS:** prefer RMAP.
- **OruxMaps:** accepts MBTiles, RMAP, and Mapsforge maps.
- **AlpineQuest:** accepts MBTiles and RMAP.
- **Guru Maps:** accepts MBTiles and RMaps-compatible SQLiteDB; GeoJSON can be
  used as an overlay.
- **QGIS and GIS tools:** MBTiles is suitable for tiled raster exchange;
  GeoJSON is suitable for vector exchange.

## Application references

- [Locus — external map formats](https://docs.locusmap.app/doku.php/manual%3Auser_guide%3Amaps_external)
- [OsmAnd — file formats](https://www.osmand.net/docs/technical/osmand-file-formats/)
- [TwoNav — RMAP](https://manual.twonav.com/manual/Manual_TwoNav_Tablet_22_en.pdf)
- [OruxMaps](https://www.oruxmaps.com/index_en.html)
- [AlpineQuest](https://www.alpinequest.net/en/help/v2/maps/file-based-select)
- [Guru Maps](https://gurumaps.app/docs/intro)

---

[← Getting started](getting-started.md) · [Documentation index](README.md)
