# LiDAR provider roadmap

The public mirror of the internal notes on which national bare-earth LiDAR
sources are wired into lidar2map, which were evaluated and set aside, and why.
Kept by hand so we do not re-dig the same dead ends every few months. Last
reviewed 2026-07-14.

For the integrated providers and their exact access mechanism, see the
[provider table](../README.md#lidar-providers--adding-a-country) in the README.
This document is the fuller registry: the sources that did *not* make it, with a
precise reason each time.

## The eligibility test

A country plugs in when there is a **programmable endpoint** (WCS, WFS, ATOM
INSPIRE, STAC, ArcGIS REST Image/FeatureServer, a derivable direct URL, or an S3
listing) that returns either **bare-earth elevation raster** (GeoTIFF / COG /
ASC) or **ground-classified LAZ**. If yes, it is wireable.

Things the pipeline already handles, so they are **not** blockers:

- **Classified LAZ to DTM** (`post_fetch`: PDAL `filters.range Classification[2:2]`,
  laspy+scipy fallback), see `cz-cuzk`.
- **One giant COG read windowed** over the bbox via `/vsicurl/`, no full-tile
  download, see `ca-nrcan`, `at-bev`, `se-lantmateriet`, `lu-act`.
- **S3 / object listing as a spatial index** (the key encodes the position),
  see `gb-scotland`.
- **HTTP auth on the COG**: a provider can supply GDAL options (scoped) through
  `gdal_env_options()`, see `se-lantmateriet` (Basic auth on the download host).
- **Account / API key**: `us-3dep`, `dk-datafordeler`, `fi-maanmittauslaitos`,
  `pt-dgt`, `se-lantmateriet` all need a free account; a missing credential just
  skips the provider, it is not a disqualifier.

Real blocking reasons (always record the code + the endpoint probed):

- **B1** no programmable endpoint: interactive basket, deferred e-mail delivery.
- **B2** elevation served as **rendered tiles** (WMS/WMTS/TPK images), not values.
- **B3** inadequate coverage: coastal strip only, or resolution >= 10 m.
- **B4** not open / restricted licence / e-signature required.

Re-evaluation tags: `[WATCH ~date]` evolving portal, re-check around then;
`[STABLE]` unlikely to change, re-probe only on an external signal; `[HARD]`
close to permanent (data does not exist or is classified).

Two integrated providers sit at the edge of this criterion and are kept as
"best available for that area", not as exemplars (flagged so we do not cite them
as precedent):

- **au-nsw** is a 5 m **stereo-photogrammetric** DEM, not LiDAR (`providers/au_nsw.py`
  says so). This is in tension with rejecting Iceland's ArcticDEM for being
  satellite-stereo; the pragmatic line is that NSW ships nothing better openly.
- **us-3dep** defaults to `USGS10m` (10 m), which sits exactly on the B3 "≥ 10 m"
  exclusion. It is really the 1 m academic path (`USGS1m`); for public 1 m use
  `us-tnm`. The 10 m default is a fallback, not the intended resolution.

## Integrated (27 countries + US/NL territories)

France, Netherlands, Switzerland, Norway, **Sweden**, Germany (11 Länder:
Bavaria, NRW, Lower Saxony, Thuringia, Hesse, Baden-Württemberg,
Mecklenburg-Vorpommern, Saxony-Anhalt, Brandenburg, Berlin, Rhineland-Palatinate),
**Austria**
(national BEV + Tyrol + East Tyrol), United Kingdom (England, Wales, Scotland),
Belgium (Flanders), Luxembourg, Finland, Denmark, Ireland, Czechia, Slovenia,
Estonia, **Latvia**, Spain (5 m national; Catalonia 0.5 m, Basque Country 1 m, Navarre 2 m),
**Portugal**, **Italy** (Emilia-Romagna 5 m, Sardinia 1 m), Poland,
USA (+ CNMI territory), Canada, New Zealand, Australia (Queensland, NSW, national
GA scattered), **Philippines** (Taal volcano area only), Japan.

Coverage is national unless noted. **Territorial / insular** (real but local, not
national, per the review's distinction): us-cnmi (Northern Mariana Is.),
ph-taal (Taal volcano ~20 km). Deferred insular that ARE wireable but low value:
Anegada (BVI, USGS 1 m) is a 38 km² coral island maxing at ~9 m elevation, almost
no micro-relief signal for archaeology, plus an ESRI:102045 CRS to relabel: not
worth it. Montevideo (Uruguay) LiDAR exists but only behind the "imnube" cloud
portal (no stable programmable endpoint, like Saxony) — deferred, not wired.

By access paradigm:

- **WCS 2.0.1**: es-cnig, de-hessen, de-bw, de-mv, de-st, de-brandenburg,
  it-emilia-romagna, it-sardegna, es-navarra, gb-england, gb-wales, be-flanders,
  fi, dk, pl, au-ga.
- **WCS 1.0.0** (older protocol, BBOX + WIDTH/HEIGHT, ArcGIS MapServer WCSServer):
  es-euskadi.
- **STAC + windowed COG**: ch-swisstopo, de-niedersachsen, ca-nrcan, nz-linz,
  se-lantmateriet, at-bev (STAC-like ATOM index).
- **ArcGIS Image/FeatureServer**: no-kartverket, ie-gsi, us-tnm, us-3dep,
  au-qld, au-nsw, si-arso.
- **ATOM INSPIRE index**: cz-cuzk (LAZ), de-thueringen (XYZ), de-berlin (zipped XYZ).
- **Static point-cloud index → PDAL/laspy class-2 binning** (`common.las_to_dtm`):
  cz-cuzk (Atom → LAZ), lv-lgia (S3 list of ~66k LAS; tile extents measured from
  LAS headers because the TKS-93 sheet origin is not cleanly derivable from the
  sheet number; min-z ground binning + bounded hole-fill).
- **Metalink (.meta4) index**: de-bayern (deterministic URL), de-rlp (URL carries
  the survey year, so the index holds the per-tile URL; post_fetch strips the
  compound vertical CRS).
- **Single windowed COG / VRT** (`/vsicurl`, no full download): lu-act, es-icgc
  (one national COG), us-cnmi (a NOAA mosaic VRT; `gdal_env_options()` whitelists
  the `.vrt` extension; pattern for a generic NOAA-territories provider).
- **Direct / derivable tiles**: fr-ign (vector TMS), ee-maaamet, at-tirol,
  jp-gsi (XYZ text tiles), gb-scotland (S3 listing).
- **Static tile grid → direct GeoTIFF**: de-bayern (metalink coverage),
  ph-taal (GeoJSON grid on GitHub Pages → per-tile GeoTIFF on S3, GRIDREF-derived).

## Evaluated, not integrated

### Watch (could unblock)

| Zone | Reason | Tag |
|---|---|---|
| Saxony (DE) | Raster exists and is fine (the review downloaded a Dresden DGM1 GeoTIFF: EPSG:25833, 2000×2000, Float32, 1 m, NoData -9999), but the ONLY access is a Nextcloud GeoCloud share whose public WebDAV is disabled (401 on every standard token auth, even with a live session + `requesttoken`). Not reproducibly wireable without a brittle browser-session scraper. Full analysis in "Candidates" below. B1/B2. | [WATCH ~2027] |
| ~~Latvia (LĢIA)~~ | **INTEGRATED 2026-07-15** as `lv-lgia` (external review was right, the old "download not public" was stale). LĢIA publishes ~66k classified LAS tiles on a public S3 with a static list; class-2 ground binning → 1 m DTM. Kept here only as a correction pointer. | done |
| Hong Kong | Open DTM is a 5 m ASC (whole-HK ZIP, EPSG:2326), trivially wireable **but** non bare-earth (bridges/elevated roads kept, canopy height) and 5 m is under the bare-earth threshold (B3). The fine CEDD LiDAR is order-only (B1). Re-proposable if you want HK coverage despite the 5 m hybrid quality. | [WATCH ~2027] |
| Wallonia (BE) | 0.5/1 m MNT raster + classified LAZ exist (EPSG:3812) but download is a 48 h e-mail basket (B1); the ArcGIS `RELIEF` server (`geoservices.wallonie.be`) exposes only rendered MapServers (hillshade / colored relief), no float32 ImageServer or WCS (B2). Confirmed 2026-07. Unblocks if SPW publishes a WCS or INSPIRE ATOM. | [WATCH ~2027] |

### Structural / hard blocks

| Zone | Reason | Tag |
|---|---|---|
| Slovakia (ÚGKK/ZBGIS) | 1 m DMR 5.0 open, but no per-bbox access: OGC services are ZBGIS REST MapServers with empty `supportedExtensions` (rendered, B2); the 1 m TIFF is only regional ZIP blocks (tens of GB) or a MAPKA basket (B1). A range-readable COG would be fine, a regional ZIP is not windowable. | [STABLE] |
| Northern Ireland (DAERA) | the hub "DTM" is a MapServer/WMTS (rendered, B2); the real data is coastal-strip LAZ 2021 only (B3); the national OSNI model is 10/50 m. Nothing usable inland. | [STABLE] |
| Lithuania | registration + electronic signature required (B4). | [STABLE] |
| Taiwan | 1 m DTM is a classified official secret (gov-only, seal + request, B4); only the 20 m is open (too coarse). | [HARD] |
| Iceland (ÍslandsDEM) | not LiDAR: derived from ArcticDEM (satellite stereo, PGC), surface model, not bare-earth. Open service is a 10 m rendered MapServer (B2); the 2 m native is 18x100 km strips via a JS viewer (B1). Criterion: require LiDAR-grade bare-earth, not satellite-stereo DEM. | [HARD] |
| W. Australia (Landgate) | 1 m LiDAR/DEM on quote + fee (B4); only the coverage index is open, not the data. | [STABLE] |
| Liechtenstein | elevation = swissALTI3D over LI (2 m) but redistributed for a fee by the Amt für Tiefbau (CAD formats, not open, B4). Not covered by ch-swisstopo (STAC is CH only). | [STABLE] |
| Germany, BKG national | national DGM1 is paid (>= EUR 8,000); `basemap.de` is rendered WMTS (B2, no values via WCS). No free national aggregator; each Land is a dedicated build (9 done, see the candidates below for the rest). | [STABLE] |
| Italy (national) | national coverage is order-form only; regions open piecemeal (Emilia-Romagna 5 m and Sardinia 1 m integrated; South Tyrol 0.5 m built-up only; other regions each a bespoke GeoServer WCS hunt). | [WATCH ~2027] |
| Croatia, Hungary | no open national LiDAR (only global 30 m DEMs). | [HARD] |
| Africa | no open national bare-earth LiDAR anywhere; only global 30 m DEMs (SRTM, Copernicus GLO-30), which are satellite radar, out of scope. | [HARD] |
| OpenTopography (global) | fine LiDAR is point clouds (LAZ) with no per-bbox raster API; DTMs are async processing jobs, not a GET; the only simple raster API is 30-90 m global satellite DEMs. The one useful slice (USGS 3DEP raster) is already `us-3dep`. Not a "multiplier". | [STABLE] |

### Candidates: two integrated, one blocked (2026-07-15)

- **Berlin (DE): INTEGRATED** as `de-berlin`. ATOM feed (`gdi.berlin.de/data/dgm1/atom`
  → dataset feed `0.atom`, 297 tiles), 2×2 km zipped XYZ, EPSG:25833,
  dl-de/zero-2-0. Same model as `de-thueringen` (post_fetch XYZ → GeoTIFF).
- **Rhineland-Palatinate (DE): INTEGRATED** as `de-rlp`. Metalink
  `geobasis-rlp.de/data/dgm1/current/meta4/dgm1_tif_07.meta4` (~21k GeoTIFF tiles,
  URL carries the survey year), EPSG:25832 with a compound vertical CRS that
  post_fetch strips to 25832, dl-de/zero-2-0.
- **Saxony (DE): still blocked, harder than the review implied.** The GeoCloud
  share (`geocloud.landesvermessung.sachsen.de/index.php/s/JCcXyifaNdLDnxZ`) is a
  Nextcloud instance with **public WebDAV disabled**: `PROPFIND` on
  `public.php/webdav/` (and `remote.php/dav/public-files/`) returns 401 for every
  standard token auth form (`token:`, `token:token`, `token:null`), even with a
  live share session cookie + `requesttoken` header; the share HTML embeds no file
  list and guessed `/download?files=` names 404. The review's PROPFIND-207 did not
  reproduce. Getting in would require reverse-engineering the exact browser
  session handshake against one specific share link Saxony can rotate: a bespoke,
  brittle scraper that fails the "programmable endpoint" criterion (mouton à
  5 pattes). Left out on purpose. Unblocks the day Saxony publishes a WCS/ATOM or
  an open metalink like RLP. `[WATCH ~2027]`

## Finding new sources (catalog discovery)

`tools/discover_providers.py` queries a CSW metadata catalog (INSPIRE) for
elevation **services** and auto-probes each WCS (GetCapabilities →
DescribeCoverage → resolution / CRS / extent), printing a shortlist of wireable
coverages. INSPIRE mandates that every EU state/region publish elevation as a
standardized service, so a national catalog enumerates them at once.

**Its blind spot, learned the hard way (2026-07):** the CSW harvest only sees
services a catalog actually indexes under the queried keyword. Brandenburg
(clean `el_dgm1_wcs`), Basque Country and Navarre (fine 1-2 m LiDAR WCS) were all
**missed** by the GDI-DE / IDEE harvest yet found immediately by probing each
region's own geoportal directly. Catalog discovery is a first pass, not a
substitute for the boring, reliable method: go country/region by region and hit
the national mapping agency's own service endpoint. The tool de-duplicates by
host and declares a WCS "wireable" from DescribeCoverage alone, without a
GetCoverage and without distinguishing DTM from DSM (surface), so its output is
strictly a shortlist.

```bash
python tools/discover_providers.py de        # Germany (GDI-DE) — found de-mv, de-st
python tools/discover_providers.py es         # Spain (IDEE)
python tools/discover_providers.py <csw_url> "<keyword>" [dc|iso]
```

Reality check: this harvests cleanly for federal states with a proper
service-catalog (Germany), less so where the fine data is portal-gated (Spain
tops out at the 5 m already served nationally) or the catalog does not expose
service URLs (Italy fragments by region). Always validate a shortlisted
candidate with a real tile download before writing the provider.

## Adding a provider

Copy the provider closest in paradigm and adapt URLs / CRS / naming:

- **WCS** → `es_cnig.py` (or `de_hessen.py`): synthetic 1 km grid clipped to the
  coverage extent, `GetCoverage` per bbox. First one ~half a day, next ones 1-2 h.
- **STAC + windowed COG** → `ca_nrcan.py`: per-bbox cache, select the DTM asset,
  the core reads the bbox window via `/vsicurl/`. Add `gdal_env_options()` if the
  download host needs HTTP auth (see `se_lantmateriet.py`).
- **ATOM index** → `de_thueringen.py` (grid) or `cz_cuzk.py` (two-level, LAZ).
- **ArcGIS ImageServer** → `no_kartverket.py` (`exportImage`, reproject on
  download if the server only speaks its native CRS, see `au_ga.py`).

Each provider is `providers/<code>.py`, ~50-200 lines, exposing `CODE`, `NAME`,
`COUNTRY`, `CRS_NATIF`, `RESOLUTION_M`, `DALLE_KM`, `PX_PAR_DALLE`,
`SEUIL_DALLE_VALIDE` and `discover_dalles(bbox_wgs84, bbox_natif, cache_path)`.
The downstream pipeline (SVF, relief, EPSG:3857 warp, MBTiles) is
provider-agnostic. Always validate a new provider with a **real tile download**
before shipping, and add a smoke-test point in `Tests/smoke_providers.py`.
