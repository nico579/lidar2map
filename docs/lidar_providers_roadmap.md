# LiDAR provider roadmap

The public mirror of the internal notes on which national bare-earth LiDAR
sources are wired into lidar2map, which were evaluated and set aside, and why.
Kept by hand so we do not re-dig the same dead ends every few months. Last
reviewed 2026-07-15.

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

France, Netherlands, Switzerland, Norway, **Sweden**, Germany (12 Länder:
Bavaria, NRW, Lower Saxony, Thuringia, Hesse, Baden-Württemberg,
Mecklenburg-Vorpommern, Saxony-Anhalt, Brandenburg, Berlin, Rhineland-Palatinate,
**Schleswig-Holstein**), **Austria**
(national BEV + Tyrol + East Tyrol), United Kingdom (England, Wales, Scotland),
Belgium (Flanders), Luxembourg, Finland, Denmark, Ireland, Czechia, Slovenia,
Estonia, **Latvia**, Spain (5 m national; Catalonia 0.5 m, Basque Country 1 m, Navarre 2 m),
**Portugal**, **Italy** (Emilia-Romagna 5 m, Sardinia 1 m, Piedmont 5 m), Poland,
USA (+ CNMI territory), Canada, New Zealand, Australia (Queensland, NSW, national
GA scattered), **Philippines** (Taal volcano area only), Japan.

Coverage is national unless noted. **Territorial / insular** (real but local, not
national, per the review's distinction): us-cnmi (Northern Mariana Is.),
ph-taal (Taal volcano ~20 km), **France DROM** fr-reunion + fr-guadeloupe (IGN
LiDAR HD 0.5 m; `fr-ign` is mainland-only. Martinique + Mayotte are announced in
the national programme but their IGN WFS returns zero tiles for now, so not yet
providers). Deferred insular that ARE wireable but low value:
Anegada (BVI, USGS 1 m) is a 38 km² coral island maxing at ~9 m elevation, almost
no micro-relief signal for archaeology, plus an ESRI:102045 CRS to relabel: not
worth it. Montevideo (Uruguay) LiDAR exists but only behind the "imnube" cloud
portal (no stable programmable endpoint, like Saxony) — deferred, not wired.

By access paradigm:

- **WCS 2.0.1**: es-cnig, de-hessen, de-bw, de-mv, de-st, de-brandenburg,
  it-emilia-romagna, it-sardegna, es-navarra, gb-england, gb-wales, be-flanders,
  fi, dk, pl, au-ga.
- **WCS 1.0.0** (older protocol, BBOX + WIDTH/HEIGHT): es-euskadi (ArcGIS
  MapServer WCSServer), it-piemonte (MapServer; `format=image/tiff` for Float32,
  `GTiff` would give quantised UInt8).
- **STAC + windowed COG**: ch-swisstopo, de-niedersachsen, ca-nrcan, nz-linz,
  se-lantmateriet, at-bev (STAC-like ATOM index).
- **ArcGIS Image/FeatureServer**: no-kartverket, ie-gsi, us-tnm, us-3dep,
  au-qld, au-nsw, si-arso.
- **Spatial index → XYZ text tiles → GeoTIFF**: de-thueringen (ATOM, zipped XYZ),
  de-berlin (ATOM, zipped XYZ), de-sh (GeoJSON index of 18 685 tiles, each feature
  carries the direct `link_data` URL; raw XYZ text, newest survey year per tile).
- **ATOM INSPIRE index (LAZ)**: cz-cuzk.
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
- **WFS index → per-tile direct URL** (`common.ign_lidar_hd_dalles`): fr-reunion,
  fr-guadeloupe (IGN `IGNF_MNT-LIDAR-HD:dalle`; each dalle feature carries its own
  download `url`, WMS GetMap for Réunion / a direct link+public apikey for
  Guadeloupe; 0.5 m).
- **Classified point cloud → DFM-style model** (`common.las_to_dfm`): fr-ign-dfm
  (IGN COPC LAZ via the same WFS, `IGNF_NUAGES-DE-POINTS-LIDAR-HD:dalle`). The
  *Digital Feature Model* concept is from Štular et al. 2021 (ground + standing
  archaeological structures in one model); the automatic selection implemented
  here (low non-ground returns 0.4-2.5 m, classes 1/3/4, re-injected only into
  ground-class holes) is a first-pass heuristic calibrated on 2 Var sites — the
  literature does that step by (semi-)manual reclassification. Reveals standing
  ruins that every national bare-earth DTM erases by design (the taller the
  wall, the cleaner it vanishes; IGN spec documents it). ~205 MB/km², targeted
  prospection only. Exposed as a **mode**, not a source: GUI checkbox "DFM mode"
  on the parent provider / CLI `--dfm` (+ `--dfm-hmin/hmax/classes` per-site
  tuning; the twin module `<code>_dfm.py` is hidden from the provider dropdown).
  Classes are ONE user-visible set (default `1,2,3,4,9,66`: 2/9/66 = terrain
  base as in the official DTM, the rest re-injected into ground gaps within the
  height band); removing class 2 yields a slice (band objects on transparent
  background, heights still referenced to ground; field-tested 2026-07-16 on the
  Var ruins: adds nothing over the full DFM, kept but not promoted). The zone
  name is auto-suffixed
  (`_dfm…`) so DTM and DFM outputs never mix; tiles are gridded on the nominal
  km bounds (no VRT seams); conversions are serialized (RAM) and written
  atomically. The LAZ stays in the tile cache: retuning re-converts in ~20 s
  without re-downloading (core `pre_download` hook).
  **Alternative ground base `--dfm-ground csf`** (Cloth Simulation Filter,
  Zhang et al. 2016, pip `cloth-simulation-filter`): a SOFT cloth (rigidness 1,
  cloth_resolution 0.5, class_threshold 0.5, time_step 0.65, slope smoothing)
  draped over the inverted cloud absorbs low continuous structures (walls) into
  the ground while rejecting vegetation, ignoring producer classes entirely.
  Field-validated 2026-07-16 on both Var sites: background cleaner than class
  re-injection (no speckle), equivalent wall signal. No re-injection afterwards
  (hmin/hmax/classes ignored; cache suffix `csf_` plus the cloth's own
  non-default settings in fixed t/r/g order, injective). The cloth exposes the
  standard CSF surface per site (`--dfm-csf-threshold` absorption distance,
  `--dfm-csf-resolution` cloth cell, `--dfm-csf-rigidness` terrain type 1
  steep default / 2 / 3 flat, per Zhang's own guidance; solver internals
  time_step/iterations/pre-filter stay fixed: without knobs no site could
  ever "demonstrate the need", per Nico). Canopy
  pre-filter before the cloth (5 m min-z grid, keep z ≤ min+3.5 m, ~57% kept);
  `setPointCloud` takes the numpy array directly (no `.tolist()`, RAM ~1.7 GB);
  measured ~3 min per 34M-pt tile vs ~25 s for "classes". A STRICT cloth
  (rigidness 3) as bare-earth and the soft-minus-strict delta were prototyped
  and REJECTED (strict ≈ IGN DTM, erases the walls too; the delta is noise).
  Companion analysis tool:
  `tools/dfm_ruines.py`. Deferred (by choice, after field validation): built-in
  control products (DTM witness / delta / re-injected mask / confidence map —
  the standalone tool provides them), block-wise COPC reading, cross-process LAZ
  lock, min-z vs high-percentile fill. Could extend to any provider whose source
  is a classified cloud (cz-cuzk, lv-lgia) if field-validated.
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
| Slovakia (ÚGKK/ZBGIS) | 1 m DMR 5.0 (and a partial 0.5 m DMR 6.0) open, and an availability-by-extent API exists, but no per-bbox DATA access: OGC services are ZBGIS REST MapServers with empty `supportedExtensions` (rendered, B2); the raster is only regional ZIP blocks (~198 GB for DMR5) or a MAPKA e-mail basket (B1). A range-readable COG would be fine, a regional ZIP is not windowable. Moved STABLE→WATCH per the 2026-07 review: the DMR6 + the API mean this could unblock if ÚGKK exposes a direct/COG endpoint. | [WATCH ~2027] |
| Northern Ireland (DAERA) | the hub "DTM" is a MapServer/WMTS (rendered, B2); the real data is coastal-strip LAZ 2021 only (B3); the national OSNI model is 10/50 m. Nothing usable inland. | [STABLE] |
| Lithuania | the classified LAZ 2025 (15 pts/m², class 2) exists and is good, but no **stable anonymous per-tile endpoint** could be validated; access goes through the Geoportal.lt with registration (the old "electronic signature required" was too categorical, per the 2026-07 review, but there is still no programmable anonymous download). B1/B4. | [WATCH ~2027] |
| Taiwan | 1 m DTM is a classified official secret (gov-only, seal + request, B4); only the 20 m is open (too coarse). | [HARD] |
| Iceland (ÍslandsDEM) | not LiDAR: derived from ArcticDEM (satellite stereo, PGC), surface model, not bare-earth. Open service is a 10 m rendered MapServer (B2); the 2 m native is 18x100 km strips via a JS viewer (B1). Criterion: require LiDAR-grade bare-earth, not satellite-stereo DEM. | [HARD] |
| W. Australia (Landgate) | 1 m LiDAR/DEM on quote + fee (B4); only the coverage index is open, not the data. | [STABLE] |
| Liechtenstein | elevation = swissALTI3D over LI (2 m) but redistributed for a fee by the Amt für Tiefbau (CAD formats, not open, B4). Not covered by ch-swisstopo (STAC is CH only). | [STABLE] |
| Germany, BKG national | national DGM1 is paid (>= EUR 8,000); `basemap.de` is rendered WMTS (B2, no values via WCS). No free national aggregator; each Land is a dedicated build (12 done). Remaining Länder blocked on delivery, not licence (all open CC BY / dl-de): **Saarland** (DGM1 via WebDAV but per-district archives 211 MB to >1 GB), **Bremen** and **Hamburg** (open DGM1 but monolithic ~0.6-1.3 GB archives) → all need the deferred download-once monolith cache; **Saxony** (Nextcloud share, WebDAV disabled, see below). | [WATCH ~2027] |
| Italy (national) | national coverage is order-form only; regions open piecemeal. Integrated: Emilia-Romagna 5 m, Sardinia 1 m, Piedmont 5 m. **Valle d'Aosta**: data is clean and open (per-tile ZIP of ASC/PRJ, a regional 2 m + a 0.5 m Dora-Baltea corridor, verified `DTM2022_DORA_0005_0011.zip` = 500 m tile at 0.5 m, EPSG:32632, real z), but the tile spatial index is behind the JS download portal (`geoportale.regione.vda.it/download/dtm/`, no GeoJSON grid found) — like FVG; buildable once the index is located. South Tyrol 0.5 m built-up only; Tuscany = WMS-only rendered (B2); Trentino = async-job portal; other regions each a bespoke hunt. | [WATCH ~2027] |
| Croatia, Hungary | no open national LiDAR (only global 30 m DEMs). | [HARD] |
| Africa | almost no open national bare-earth LiDAR; mostly global 30 m DEMs (SRTM, Copernicus GLO-30, satellite radar, out of scope). **Exception (2026-07 review): Mauritius + Rodrigues** publish a national 1 m LiDAR DTM, but as a single ~5.3 GB compressed-TIFF ZIP monolith (needs the deferred "download-once monolith cache"), and licence / CRS / NoData are unconfirmed. So the absolute "nowhere in Africa" is no longer true; still not wired (monolith + licence). | [WATCH ~2027] |
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

### World scan (2026-07-15): evaluated, not integrated

A worldwide external review proposed ~11 more. Three held up and were wired
(`lv-lgia`, `us-cnmi`, `ph-taal`). The rest failed real validation, grouped by
why. Lesson: the review over-labelled "wireable" (browser-session / JS-portal
access that does not reproduce programmatically) and "usable" (data unfit for
micro-relief). Each below was probed to a real endpoint.

**Rejected, data unfit for archaeological micro-relief:**

- **Malta** (`malta.coverage.wetransform.eu/dtm_1m_2018/ows`): the WCS returns
  **uint8** samples, i.e. elevation quantised to **whole metres** (0.15 m
  horizontal, but 1 m vertical steps). SVF / LRM / openness would produce
  staircase artefacts and lose the sub-metre features that are the whole point.
  Confirmed by a real GetCoverage. B3-like (vertical resolution).
- **Qatar**: an ImageServer serves a fine Float32 raster, but there is no proof
  it is a bare-earth **LiDAR DTM** (vs a DSM / photogrammetric surface) and no
  clear licence. The review itself said not to integrate it. [HARD until proven]
- **Anegada (BVI)**: see the integrated-section note — 38 km² flat coral island,
  ~9 m max, no relief signal; wireable (one USGS ZIP) but pointless.

**Deferred, portal-gated, no reproducible programmable endpoint (Saxony motif):**

- **Mexico (INEGI)**: the `elevacionesmex` viewer is an OpenLayers JS app with no
  download API exposed in its HTML/JS; the national LiDAR is also 5 m
  (landscape-scale, not micro-relief). Portal-gated + coarse.
- **Friuli-Venezia Giulia (IT)**: the tile grid IS clean
  (`serviziogc.regione.fvg.it/geoserver` `GRIGLIEGEO:QU_DTM_LIDAR_FVG`, 14 917
  1 m DTM tiles as WFS features) but the features carry **no download URL**; the
  actual download is the Eagle.fvg cloud portal, and there is no DTM WCS coverage
  (direct-URL guesses 404/500). Unblocks if FVG exposes a WCS or puts the tile URL
  in the grid attributes.
- **Caribbean Netherlands (Bonaire / Saba / St-Eustatius)**: real 0.5 m Dutch
  LiDAR DTM (CC BY 4.0), **good data**, but access is a proprietary
  `beeldmateriaal.nl` "rasterByExtent" API, not a standard WCS/ImageServer I could
  locate. The one case worth a focused follow-up if Caribbean coverage is wanted.
- **Montevideo (UY)**: see the integrated-section note ("imnube" portal).
- **Dominica**: documented DTM/LAS, but portal / API / WCS all return HTTP 502.

**Deferred, needs a capability the pipeline does not have yet** (deferred
2026-07-15):

- **São Paulo (GeoSampa)**: a public classified EPT (31.7 billion points).
  Wireable in principle with `readers.ept` + a class-2 filter, but the pipeline
  has no **windowed remote-EPT** reader. Would unlock the whole EPT class.
- **Trentino (IT)**: a real create-job → poll → download-ZIP(ASC) workflow; needs
  an **async-job** provider hook, and the API is reverse-engineered from the
  front-end (fragile).
- **Belo Horizonte (BR)**: public LiDAR XYZ, but the index is a Google Drive and
  the points are irregular (need interpolation, not binning).
- **St-Vincent (USGS)** and **Mauritius/Rodrigues**: bare-earth 1 m DTMs, but each
  a single multi-GB monolith (1.38 GB / 5.3 GB) → needs the deferred
  "download-once monolith cache" (or a range-readable COG, which they are not).

### Review 4 (2026-07-16): Americas, evaluated not integrated

This review (which compared against this roadmap and tested downloads) yielded 4
integrations (de-sh, fr-reunion, fr-guadeloupe, it-piemonte). The Americas
candidates did not make it:

- **Colombia (IGAC)**: ~10 ArcGIS ImageServers of 1 m LiDAR MDT (Pereira,
  Dosquebradas, Casanare, Arauca…), Float32, `exportImage` works (au-qld pattern),
  bare-earth (tags LIDAR/Terreno/TIN). **Blocked on licence**: the ArcGIS items
  carry NO `licenseInfo` / `accessInformation`. This project ships only clearly
  open data → deferred until IGAC states an open licence. Otherwise a strong P0.
- **Niterói (BR)**: MDT via an ArcGIS mosaic index (`services8.arcgis.com/…/
  Grouplayer_articulacao_mosaico`, 129 tiles 2019, tx_MDT LAS URLs, EPSG:31983,
  class-2 ground). But the "1 m MDT" is a **sparse ground point set**
  (0.001-0.074 pt/m², ~4 m effective spacing, not a real 1 m DTM), and it is one
  coastal city → low value. Deferred.
- **Rio de Janeiro (BR)**: MDT 5 m served as **LERC**-encoded tiles; no LERC
  decoder in the pipeline → deferred (new hook).
- **Pernambuco PE3D (BR)**: statewide LiDAR + 1 m DTM, but the ArcGIS folders
  return `499 Token Required` (free account) → deferred (needs token handling).
- **Romania (LAKI III / ANCPI)**: good tile index and architecture, but the ANCPI
  domain is down during a migration → re-check later. [WATCH]
- **Indaiatuba (BR)**: the "MDT" ZIP is a shapefile (MDT21), not a raster or LAS
  → not consumable.
- Pacific follow-up (not yet probed here): Guam, American Samoa via NOAA
  bare-earth 1 m DEMs (same `noaa-nos-coastal-lidar-pds` bucket as us-cnmi).

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
