"""Traitement des sources autonomes LiDAR et WMTS.

Le module conserve les sorties immédiates historiques par ``SystemExit`` et
ne résout aucune zone. Les conversions et l'historique sont injectés par la
façade afin de préserver les coutures applicatives.
"""

from dataclasses import dataclass
from pathlib import Path
import time


@dataclass(frozen=True)
class DependancesSourcesTerrain:
    generer_rmap: object
    generer_sqlitedb: object
    historique: object
    hist_t_debut: object


def _convertir_mbtiles(source, args, dependances):
    ok = True
    if args.rmap:
        ok = (
            dependances.generer_rmap(source, ecraser=True) is not None
        ) and ok
    if args.sqlitedb:
        ok = (
            dependances.generer_sqlitedb(source, ecraser=True) is not None
        ) and ok
    maintenant = time.time()
    dependances.historique(
        int(maintenant - (dependances.hist_t_debut or maintenant)),
        statut="ok" if ok else "ko",
    )
    raise SystemExit(0 if ok else 1)


def traiter_source_autonome(args, *, dependances):
    """Traite ``--source`` pour le workflow LiDAR/OSM."""
    if not args.source:
        return None

    source = Path(args.source)
    if not source.exists():
        extension = source.suffix.lower()
        if extension in (".tif", ".tiff"):
            print(f"  WARNING: source TIF not found : {source.name}")
            print("  Recompute from tiles...")
            args.source = None
        else:
            print(f"  ERROR: source file not found: {args.source}")
            raise SystemExit(1)
    extension = Path(args.source).suffix.lower() if args.source else ""

    if extension == ".mbtiles":
        if not args.rmap and not args.sqlitedb:
            print(
                "  ERROR: choose --file-formats rmap and/or sqlitedb "
                "for MBTiles conversion."
            )
            print(f"  Ex: --source {source.name} --file-formats rmap")
            raise SystemExit(1)
        _convertir_mbtiles(source, args, dependances)

    if extension in (".pbf", ".osm"):
        if not args.osm:
            print("  ERROR: --osm required with a .pbf source.")
            print(f"  E.g.: --source {source.name} --zone-city gareoult --osm")
            raise SystemExit(1)
        return None

    if extension in (".tif", ".tiff"):
        try:
            import rasterio

            with rasterio.open(str(source)) as dataset:
                epsg = dataset.crs.to_epsg() if dataset.crs else None
            if epsg == 3857:
                args._source_already_warped = True
                print("  Source TIF EPSG:3857 detected -> direct tiling (no warp)")
            else:
                args._source_already_warped = False
                print(f"  Source TIF EPSG:{epsg} -> Mercator warp required")
        except Exception as exc:
            print(f"  WARNING CRS not detected ({exc}) — warp applied by default")
            args._source_already_warped = False
        return None

    print(f"  ERROR: unrecognised extension for --source: {extension}")
    print("  Accepted extensions: .tif .tiff .mbtiles .pbf .osm")
    raise SystemExit(1)


def traiter_source_wmts(args, *, dependances):
    """Convertit une source MBTiles autonome du workflow raster WMTS."""
    if not args.source:
        return None
    source = Path(args.source)
    if not source.exists():
        print(f"  ERROR: file not found: {args.source}")
        raise SystemExit(1)
    if source.suffix.lower() != ".mbtiles":
        print(f"  ERROR: --source expects a .mbtiles (got: {source.suffix})")
        raise SystemExit(1)
    if not args.rmap and not args.sqlitedb:
        print("  ERROR: choose --file-formats rmap and/or sqlitedb.")
        print(f"  Ex: --source {source.name} --file-formats rmap")
        print(f"  Ex: --source {source.name} --file-formats sqlitedb")
        raise SystemExit(1)
    _convertir_mbtiles(source, args, dependances)
