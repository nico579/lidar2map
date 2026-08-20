"""Géocodage terrain injecté et testable hors réseau."""

import json
import urllib.error
import urllib.parse
import urllib.request


def geocoder_ville_wgs84(
    nom_ville,
    *,
    country,
    http_ua,
    log_req,
    urlopen,
):
    """Géocode une ville avec Nominatim et filtre les réponses non habitées."""
    code_pays = (country or "fr").lower()
    url = (
        "https://nominatim.openstreetmap.org/search"
        f"?q={urllib.parse.quote(nom_ville)}"
        f"&countrycodes={code_pays}"
        "&format=json&limit=1&addressdetails=1"
    )
    req = urllib.request.Request(url, headers={"User-Agent": http_ua})
    log_req(url, "Nominatim")
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        json.JSONDecodeError,
        OSError,
        TimeoutError,
    ) as exc:
        print(f"  ERROR geocoding ({type(exc).__name__}): {exc}")
        return None, None
    if not data:
        print(f"  ERROR: town not found: {nom_ville}")
        return None, None

    types_ok = {
        "city", "town", "village", "municipality", "administrative",
        "suburb", "quarter", "neighbourhood",
    }
    types_doute = {"hamlet", "locality", "isolated_dwelling", "farm"}
    resultat = data[0]
    addrtype = (resultat.get("addresstype") or "").lower()
    display = resultat.get("display_name", "(?)")
    categorie = (resultat.get("class") or "").lower()

    if categorie not in ("place", "boundary", "landuse"):
        print(
            f"  ERROR: lieu '{nom_ville}' non reconnu comme ville/village.\n"
            f"  Nominatim a renvoyé : {display} (type={categorie}/{addrtype}).\n"
            "  Précisez le nom de la commune."
        )
        return None, None

    lat = float(resultat["lat"])
    lon = float(resultat["lon"])
    if addrtype not in types_ok:
        if addrtype in types_doute:
            print(f"  ⚠ '{nom_ville}' resolved to {display} (type={addrtype}).")
            print("  Check that this is the expected place.")
        else:
            print(
                f"  ERROR: lieu '{nom_ville}' ambiguous - Nominatim returned "
                f"{display} (type={addrtype})."
            )
            print("  Specify the full name (municipality, not POI).")
            return None, None

    print(f"  {nom_ville} -> lat={lat:.5f}, lon={lon:.5f}")
    return lat, lon


def _bbox_departement(cache_entry, *, bbox_transform, wgs84_vers_natif):
    bx1, by1, bx2, by2 = bbox_transform(
        wgs84_vers_natif,
        cache_entry["lon_min"], cache_entry["lat_min"],
        cache_entry["lon_max"], cache_entry["lat_max"],
    )
    marge = 500
    return bx1 - marge, by1 - marge, bx2 + marge, by2 + marge


def geocoder_departement(
    num_dep,
    *,
    cache_dir,
    bbox_transform,
    wgs84_vers_natif,
    ecrire_json_atomique,
    http_ua,
    log_req,
    urlopen,
    sleep,
):
    """Résout un département via cache local puis Overpass, sans réseau caché."""
    cache_path = cache_dir / "dep_bbox_cache.json"
    cache = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    if num_dep in cache:
        entree = cache[num_dep]
        print(f"  Department {num_dep}: {entree['nom']} (local cache)", flush=True)
        print(
            f"  BBox WGS84 : {entree['lon_min']:.4f},{entree['lat_min']:.4f} → "
            f"{entree['lon_max']:.4f},{entree['lat_max']:.4f}"
        )
        bx1, by1, bx2, by2 = _bbox_departement(
            entree, bbox_transform=bbox_transform, wgs84_vers_natif=wgs84_vers_natif,
        )
        surface_km2 = (bx2 - bx1) / 1000 * (by2 - by1) / 1000
        print(f"  BBox Lambert 93 : {bx1:.0f},{by1:.0f} → {bx2:.0f},{by2:.0f}")
        print(f"  Estimated area: ~{surface_km2:.0f} km²")
        return entree["nom"], bx1, by1, bx2, by2

    query = (
        '[out:json];relation["boundary"="administrative"]'
        f'["admin_level"="6"]["ref:INSEE"="{num_dep}"];out bb;'
    )
    url = "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": http_ua})
    nom = None
    lat_min = lat_max = lon_min = lon_max = None

    for tentative in range(3):
        try:
            log_req(req.full_url, "Overpass")
            with urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read())
            elements = data.get("elements", [])
            if elements:
                element = elements[0]
                bounds = element.get("bounds", {})
                lat_min, lat_max = bounds.get("minlat"), bounds.get("maxlat")
                lon_min, lon_max = bounds.get("minlon"), bounds.get("maxlon")
                nom = element.get("tags", {}).get("name", f"dep{num_dep}")
            break
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            json.JSONDecodeError,
            OSError,
            TimeoutError,
        ) as exc:
            if tentative < 2:
                print(
                    f"  Overpass unavailable ({type(exc).__name__}: {exc}) - "
                    f"retry {tentative + 1}/3...",
                    flush=True,
                )
                sleep(5)
            else:
                print(f"  ERROR Overpass: {type(exc).__name__}: {exc}")

    if lat_min is None:
        print(f"  ERROR: cannot geocode the department {num_dep}.")
        print("  Overpass API unavailable. Use --zone-bbox W,S,E,N (WGS84 degrees).")
        print("  Example Var 83 : --zone-bbox 5.66,42.98,6.79,43.61")
        return None, None, None, None, None

    entree = {
        "nom": nom, "lat_min": lat_min, "lat_max": lat_max,
        "lon_min": lon_min, "lon_max": lon_max,
    }
    cache[num_dep] = entree
    try:
        ecrire_json_atomique(cache_path, cache, indent=2)
    except Exception:
        pass

    print(f"  Department {num_dep}: {nom}")
    print(f"  BBox WGS84 : {lon_min:.4f},{lat_min:.4f} → {lon_max:.4f},{lat_max:.4f}")
    bx1, by1, bx2, by2 = _bbox_departement(
        entree, bbox_transform=bbox_transform, wgs84_vers_natif=wgs84_vers_natif,
    )
    surface_km2 = (bx2 - bx1) / 1000 * (by2 - by1) / 1000
    print(f"  BBox Lambert 93 : {bx1:.0f},{by1:.0f} → {bx2:.0f},{by2:.0f}")
    print(f"  Estimated area: ~{surface_km2:.0f} km²")
    return nom, bx1, by1, bx2, by2


def geocoder_region(
    slug,
    *,
    departements_de_region,
    regions_disponibles,
    geocoder_departement,
    crs_natif,
):
    """Agrège les bbox des départements appartenant à une région Geofabrik."""
    slug = slug.strip().lower()
    departements = departements_de_region(slug)
    if not departements:
        print(f"  ERROR: region '{slug}' unknown.")
        print(f"  Available regions: {', '.join(regions_disponibles())}")
        return None, None, None, None, None
    print(
        f"  Region {slug}, {len(departements)} departments: "
        f"{', '.join(departements)}",
        flush=True,
    )
    bx1 = by1 = float("inf")
    bx2 = by2 = float("-inf")
    for code in departements:
        nom_dep, dx1, dy1, dx2, dy2 = geocoder_departement(code)
        if nom_dep is None:
            print(f"  ERROR: geocoding of department {code} failed - incomplete region.")
            return None, None, None, None, None
        bx1, by1 = min(bx1, dx1), min(by1, dy1)
        bx2, by2 = max(bx2, dx2), max(by2, dy2)
    nom = slug.replace("-", " ").title()
    surface_km2 = (bx2 - bx1) / 1000 * (by2 - by1) / 1000
    print(f"  Region bbox {crs_natif} : {bx1:.0f},{by1:.0f} → {bx2:.0f},{by2:.0f}")
    print(f"  Surface (bbox englobante) : ~{surface_km2:.0f} km²")
    return nom, bx1, by1, bx2, by2
