***English** | [Français](data-licenses.fr.md) · [Provider catalogue](providers.md) · [Documentation index](README.md)*

# Data sources, licences, and acknowledgements

lidar2map combines its own GPL-licensed code with public elevation, imagery,
and vector datasets published under their respective terms. Source licences
remain applicable to downloaded data and may require attribution when data or
derived products are redistributed.

This page centralizes the acknowledgements currently carried by the project.
The [provider catalogue](providers.md) records source-specific access and
coverage details; each provider module also carries `LICENSE` and `DOC_URL`
metadata. Always check the publisher's current terms for a distribution or
professional use case.

## lidar2map code

lidar2map is distributed under the **GNU General Public License v3.0**; see
[LICENSE](../LICENSE).

You may use, modify, and redistribute the software under GPL v3. In particular,
if you redistribute a modified version, you must provide the modified source
code under the same licence.

## Data sources

- **IGN** (French National Institute of Geographic and Forest Information):
  LiDAR HD, BD ORTHO including historical 1950–1995 versions, and BD TOPO,
  under the Etalab 2.0 licence.
- **AHN** (Actueel Hoogtebestand Nederland): AHN4/5 0.5 m, Netherlands,
  CC BY 4.0.
- **swisstopo** (Swiss Federal Office of Topography): swissALTI3D 0.5 m,
  Switzerland, free open data © swisstopo.
- **Kartverket**: Nasjonal Høydemodell 1 m, Norway, CC BY 4.0.
- **Geobasis NRW · LDBV Bayern · LGLN Niedersachsen · TLBG Thüringen**:
  DGM 1 m (1–2 m in Thuringia), Germany, Datenlizenz Deutschland
  Namensnennung 2.0.
- **Land Tirol** (tiris): DGM 0.5 m, Austria/Tyrol, CC BY 4.0.
- **Environment Agency** (England) and **DataMapWales / Natural Resources
  Wales**: LIDAR Composite DTM 1 m, United Kingdom, Open Government Licence v3.
- **Scottish Government / JNCC** (Scottish Remote Sensing Portal): Scottish
  Public Sector LiDAR DTM 0.5 m, Scotland, Open Government Licence v3.
- **ACT** (Administration du Cadastre et de la Topographie): BD-L-Lidar 2024
  DTM 0.5 m, Luxembourg, CC0.
- **USGS**: 3DEP / The National Map 1 m, USA, public domain.
- **GSI** (Geospatial Information Authority of Japan): DEM5A elevation tiles
  5 m, Japan, GSI content terms.
- **Digitaal Vlaanderen**: DHMV II DTM/SVF/Hillshade, Flanders, Open Data
  Licentie Vlaanderen.
- **Maanmittauslaitos**: Elevation Model 2 m, Finland, CC BY 4.0.
- **Klimadatastyrelsen / Datafordeler**: DHM DTM 0.4 m, Denmark, CC BY.
- **Geological Survey Ireland**: LiDAR DTM 1 m, Ireland, CC BY 4.0.
- **Natural Resources Canada**: HRDEM Mosaic 1 m, Canada, Open Government
  Licence.
- **ČÚZK** (Czech Office for Surveying, Mapping and Cadastre): DMR 5G 1 m,
  Czechia, Open Data.
- **IGN España / CNIG**: MDT 5 m, Spain, CC BY 4.0.
- **ICGC** (Institut Cartogràfic i Geològic de Catalunya): MET LiDAR 50 cm,
  Catalonia, CC BY 4.0.
- **GUGiK** (Polish Head Office of Geodesy and Cartography): NMT 1 m LiDAR
  ISOK, Poland, open data.
- **LINZ** (Land Information New Zealand): DEM 1 m, New Zealand, CC BY 4.0.
- **QSpatial** (State of Queensland) and **Spatial Services NSW**: DEM 0.5 m /
  5 m, Australia, CC BY 4.0.
- **Geoscience Australia**: DEM of Australia derived from LiDAR 5 m, national
  scattered coverage, CC BY 4.0.
- **OpenStreetMap contributors**: vector data under the
  [Open Database License](https://www.openstreetmap.org/copyright), distributed
  in regional extracts by Geofabrik.

## Vector-map engine

- **Apache JMapsforge / mapsforge-map-writer** provides the offline vector-map
  rendering and writing engine.

## Scientific figures

The visualisation guide stores scientific figures locally so it remains
readable offline. Source, author, modification, and licence information for
each figure is recorded in
[Figure sources and licences](images/shadings/README.md).

## Bundled and runtime tools

The distributed application uses or bundles:

- GDAL
- osmosis
- py7zr
- pyproj
- NumPy
- SciPy
- Pillow
- ijson
- pywebview

These projects retain their own copyright and licence terms. Their inclusion
does not relicense them under lidar2map's GPL notice.
