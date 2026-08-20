"""Résolution orchestrée des zones LiDAR/OSM."""

import math
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DependancesResolutionTerrain:
    provider: object
    normaliser_nom: object
    regions_disponibles: object
    geocoder_region: object
    geocoder_departement: object
    calculer_grille_bbox: object
    bbox_enveloppe_transform: object
    wgs84_vers_natif: object
    nom_zone_bbox_auto: object
    nom_zone_gps_auto: object
    geocoder_ville_natif: object
    calculer_grille: object
    parse_block: object
    calculer_sous_zones_priori: object


def resoudre_zone_lidar(args, osm_seul, *, dependances):
    d = dependances
    source_tif_sans_zone = (
        args.source and Path(args.source).suffix.lower() in (".tif", ".tiff")
        and not args.zone_departement and not args.zone_bbox
        and not args.zone_ville and not args.zone_gps
        and not getattr(args, "zone_region", None)
    )
    if source_tif_sans_zone:
        print("  ERROR: --source TIF requires a zone: --zone-city/--zone-width, "
              "--zone-bbox, --zone-department or --zone-region")
        sys.exit(1)

    cx = cy = 0.0
    if getattr(args, "zone_region", None):
        slug = args.zone_region.strip().lower()
        nom_zone = d.normaliser_nom(args.zone_nom) if args.zone_nom else d.normaliser_nom(slug)
        if osm_seul:
            if slug not in d.regions_disponibles():
                print(f"  ERROR: region '{slug}' unknown.")
                print(f"  Available regions: {', '.join(d.regions_disponibles())}")
                sys.exit(1)
            bbox = (0.0, 0.0, 0.0, 0.0)
        else:
            nom_reg, bx1, by1, bx2, by2 = d.geocoder_region(slug)
            if nom_reg is None:
                sys.exit(1)
            bbox = d.calculer_grille_bbox(bx1, by1, bx2, by2)
        print(f"  Folder : {nom_zone}")

    elif args.zone_departement:
        num_dep = args.zone_departement.strip().upper()
        nom_dep, bx1, by1, bx2, by2 = d.geocoder_departement(num_dep)
        if nom_dep is None:
            sys.exit(1)
        bbox = ((bx1, by1, bx2, by2) if osm_seul
                else d.calculer_grille_bbox(bx1, by1, bx2, by2))
        nom_auto = d.normaliser_nom(nom_dep) + "_" + num_dep.lower()
        nom_zone = d.normaliser_nom(args.zone_nom) if args.zone_nom else nom_auto
        print(f"  Folder : {nom_zone}")

    elif args.zone_bbox:
        try:
            lon1, lat1, lon2, lat2 = [float(v.strip()) for v in args.zone_bbox.split(",")]
        except (ValueError, IndexError):
            print("  Invalid BBox format. Example (WGS84 W,S,E,N): "
                  "--zone-bbox 5.9,43.1,6.6,43.8")
            sys.exit(1)
        if not all(math.isfinite(v) for v in (lon1, lat1, lon2, lat2)):
            print("  ERROR: non-finite bbox coordinate.")
            sys.exit(1)
        lon1, lon2 = min(lon1, lon2), max(lon1, lon2)
        lat1, lat2 = min(lat1, lat2), max(lat1, lat2)
        if lon1 == lon2 or lat1 == lat2:
            print("  ERROR: degenerate bbox (zero width or height).")
            sys.exit(1)
        if not (-180 <= lon1 <= 180 and -180 <= lon2 <= 180
                and -90 <= lat1 <= 90 and -90 <= lat2 <= 90):
            print("  ERROR: BBox is WGS84 degrees (W,S,E,N): "
                  "lon in [-180,180], lat in [-90,90].")
            sys.exit(1)
        bx1, by1, bx2, by2 = d.bbox_enveloppe_transform(
            d.wgs84_vers_natif, lon1, lat1, lon2, lat2,
        )
        cx, cy = (bx1 + bx2) / 2, (by1 + by2) / 2
        bbox = ((bx1, by1, bx2, by2) if osm_seul
                else d.calculer_grille_bbox(bx1, by1, bx2, by2))
        surface_km2 = (bx2 - bx1) / 1000 * (by2 - by1) / 1000
        print(f"  BBox WGS84 : {lon1:.4f},{lat1:.4f} → {lon2:.4f},{lat2:.4f}")
        print(f"  BBox {d.provider.CRS_NATIF} : {bx1:.0f},{by1:.0f} → {bx2:.0f},{by2:.0f}")
        print(f"  Area: ~{surface_km2:.0f} km²")
        nom_zone = (d.normaliser_nom(args.zone_nom) if args.zone_nom
                    else d.nom_zone_bbox_auto(lon1, lat1, lon2, lat2))
        if not nom_zone:
            sys.exit(1)

    elif args.zone_gps:
        try:
            parts = [p.strip() for p in args.zone_gps.replace(";", ",").split(",")]
            lat, lon = float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            print("  Invalid GPS format. Example: 43.3156,6.0423")
            sys.exit(1)
        if not (math.isfinite(lat) and math.isfinite(lon)
                and -90 <= lat <= 90 and -180 <= lon <= 180):
            print("  ERROR: GPS out of range (lat [-90,90], lon [-180,180]).")
            sys.exit(1)
        nom_zone = (d.normaliser_nom(args.zone_nom) if args.zone_nom
                    else d.nom_zone_gps_auto(lat, lon))
        if not nom_zone:
            sys.exit(1)
        print(f"  GPS -> lat={lat:.5f}, lon={lon:.5f}")
        cx, cy = d.wgs84_vers_natif(lon, lat)
        print(f"  {d.provider.CRS_NATIF} -> X={cx:.0f}, Y={cy:.0f}")

    elif args.zone_ville:
        nom_zone = d.normaliser_nom(args.zone_nom or args.zone_ville)
        print(f"  Geocoding '{args.zone_ville}'...")
        cx, cy = d.geocoder_ville_natif(args.zone_ville)
        if cx is None:
            sys.exit(1)
    else:
        print("  ERROR: a zone option is required (--zone-city / --zone-gps / "
              "--zone-bbox / --zone-department / --zone-region)")
        sys.exit(1)

    variant_tag = getattr(d.provider, "variant_tag", None)
    if variant_tag:
        tag = d.normaliser_nom(variant_tag())
        if tag and not nom_zone.endswith(tag):
            nom_zone = f"{nom_zone}_{tag}"
            print(f"  Variant mode ({tag}): project name -> {nom_zone}")

    if not args.zone_bbox and not args.zone_departement and not getattr(args, "zone_region", None):
        bbox = d.calculer_grille(cx, cy, (args.zone_width or 20.0) / 2.0)

    try:
        bloc = d.parse_block(getattr(args, "block", ""))
    except ValueError as exc:
        print(f"  ERROR: {exc}")
        sys.exit(1)
    if bloc and not osm_seul:
        index, total = bloc
        blocs, _ = d.calculer_sous_zones_priori(
            bbox[0], bbox[1], bbox[2], bbox[3], total, 0.0, unite_m=True,
        )
        zone = blocs[index - 1]
        bbox = (zone[2], zone[3], zone[4], zone[5])
        nom_zone = f"{nom_zone}_b{index}"
        print(f"  Block {index}/{total} ({len(blocs)} blocs): this run = bbox "
              f"{bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f} → "
              f"project {nom_zone}")
    return bbox, nom_zone, cx, cy, bloc
