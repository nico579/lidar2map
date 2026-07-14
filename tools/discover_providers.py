#!/usr/bin/env python3
"""discover_providers.py — trouve des sources LiDAR/MNT branchables en interrogeant
un catalogue de métadonnées CSW (INSPIRE), au lieu de chercher pays par pays.

L'idée : la directive INSPIRE impose à chaque État/région de l'UE de publier ses
données d'élévation via des services standardisés (WCS surtout). Un catalogue CSW
les recense. On les liste, puis on AUTO-SONDE chaque WCS (GetCapabilities →
DescribeCoverage) pour lire résolution / CRS / étendue et classer :
  - WIREABLE : coverage raster (float) → clonable en provider (cf. providers/es_cnig.py).
  - RENDERED : que du WMS/MapServer (images) → inexploitable comme MNT.
  - DEAD / NO_COVERAGE : endpoint mort ou vide.

L'outil NE télécharge PAS : il sort une shortlist. On valide ensuite un candidat
par un download réel (une tuile GetCoverage, vérifier magic TIFF + float32 +
résolution) AVANT d'écrire le provider. C'est le garde-fou du projet.

Ce qui marche bien : les pays fédéraux à catalogue-services propre (Allemagne
GDI-DE → de-mv, de-st trouvés ainsi). Limite : la donnée fine est souvent
portail-gated hors de ce cas, et chaque CSW a son schéma (Dublin Core vs ISO).

Usage :
  python tools/discover_providers.py de        # preset Allemagne (GDI-DE)
  python tools/discover_providers.py es         # Espagne (IDEE, ISO)
  python tools/discover_providers.py <csw_url> "<mot-clef>" [dc|iso]

Self-contained : stdlib uniquement.
"""
import re
import ssl
import sys
import urllib.parse
import urllib.request

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _CTX = ssl.create_default_context()

UA = "lidar2map-discovery/1.0"

# Presets : (CSW, mot-clef, schéma). Schéma = 'dc' (Dublin Core, WCS dans
# dct:references) ou 'iso' (ISO19139, WCS dans gmd:linkage).
PRESETS = {
    "de": ("https://gdk.gdi-de.org/geonetwork/srv/ger/csw",
           "Digitales Geländemodell", "dc"),
    "es": ("https://www.idee.es/csw-inspire-idee/srv/spa/csw",
           "modelo digital del terreno", "iso"),
    "it": ("https://geodati.gov.it/RNDT/csw",
           "modello digitale del terreno", "iso"),
}


def http(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, f"__ERR__ {type(e).__name__}: {str(e)[:70]}"


def csw_services(csw, query, schema, pages=6, per=30):
    """→ {url_wcs_base: titre}. Paginé sur les records de type 'service'."""
    urls = {}
    typenames = "gmd:MD_Metadata" if schema == "iso" else "csw:Record"
    outschema = ("http://www.isotc211.org/2005/gmd" if schema == "iso"
                 else "http://www.opengis.net/cat/csw/2.0.2")
    for start in range(1, pages * per, per):
        params = {"SERVICE": "CSW", "VERSION": "2.0.2", "REQUEST": "GetRecords",
                  "typeNames": typenames, "resultType": "results",
                  "elementSetName": "full", "outputSchema": outschema,
                  "constraintLanguage": "CQL_TEXT",
                  "constraint_language_version": "1.1.0",
                  "startPosition": start, "maxRecords": per,
                  "constraint": f"Type='service' AND AnyText like '%{query}%'"}
        st, xml = http(csw + "?" + urllib.parse.urlencode(params), 90)
        if st != 200 or xml.startswith("__ERR__"):
            break
        if schema == "iso":
            for m in re.finditer(r"<gmd:CI_OnlineResource>(.*?)</gmd:CI_OnlineResource>",
                                 xml, re.S):
                blk = m.group(1)
                u = re.search(r"<gmd:URL>([^<]+)</gmd:URL>", blk)
                p = re.search(r"<gmd:protocol>\s*<gco:CharacterString>([^<]+)<", blk, re.S)
                if u and re.search(r"wcs|coverage", u.group(1) + (p.group(1) if p else ""), re.I):
                    urls.setdefault(u.group(1).replace("&amp;", "&").split("?")[0], "")
        else:
            for rec in re.split(r"<csw:(?:Summary)?Record", xml)[1:]:
                title = re.search(r"<dc:title>([^<]+)</dc:title>", rec)
                for u in re.findall(r"<dct:references[^>]*>([^<]+)</dct:references>", rec) \
                       + re.findall(r"<dc:URI[^>]*>([^<]+)</dc:URI>", rec):
                    u = u.replace("&amp;", "&")
                    if re.search(r"wcs|coverage", u, re.I):
                        urls.setdefault(u.split("?")[0], title.group(1)[:45] if title else "")
    return urls


def sonde_wcs(base):
    """→ (verdict, détail). Cherche un coverage raster et lit sa résolution."""
    for ver in ("2.0.1", "1.0.0"):
        st, caps = http(f"{base}?service=WCS&version={ver}&request=GetCapabilities", 40)
        if st != 200 or "Capabilities" not in caps:
            continue
        ids = (re.findall(r"<(?:wcs:)?CoverageId>([^<]+)</", caps)
               or re.findall(r"<(?:wcs:)?(?:Coverage)?[Ii]dentifier>([^<]+)</", caps)
               or re.findall(r"<name>([^<]+)</name>", caps, re.I))
        if not ids:
            return "NO_COVERAGE", f"{ver} {len(caps)}o"
        # préférer un coverage DGM/DTM 1 m
        cid = next((i for i in ids if re.search(r"dgm1|dtm|_1\b|1m|elevation", i, re.I)), ids[0])
        st2, dc = http(f"{base}?service=WCS&version={ver}&request=DescribeCoverage"
                       f"&coverageId={urllib.parse.quote(cid)}", 40)
        res = "?"
        for o in re.findall(r"offsetVector[^>]*>([^<]+)<", dc):
            pp = o.split()
            if len(pp) >= 2 and max(abs(float(pp[0])), abs(float(pp[1]))) > 0:
                res = max(abs(float(pp[0])), abs(float(pp[1])))
                break
        srs = re.search(r"EPSG/0/(\d+)|EPSG::?(\d+)", dc)
        epsg = (srs.group(1) or srs.group(2)) if srs else "?"
        return "WIREABLE", f"cov={cid[:34]} epsg={epsg} res={res}m ({len(ids)} covs) {ver}"
    return "DEAD", "no WCS caps"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    arg = sys.argv[1]
    if arg in PRESETS:
        csw, query, schema = PRESETS[arg]
    else:
        csw = arg
        query = sys.argv[2] if len(sys.argv) > 2 else "elevation"
        schema = sys.argv[3] if len(sys.argv) > 3 else "dc"
    print(f"# Catalogue : {csw}\n# Requête   : services '{query}' (schéma {schema})\n")
    urls = csw_services(csw, query, schema)
    print(f"{len(urls)} service(s) WCS candidat(s) extrait(s)\n")
    results = []
    seen = set()
    for base, title in urls.items():
        host = urllib.parse.urlparse(base).netloc
        if host in seen:
            continue
        seen.add(host)
        verdict, detail = sonde_wcs(base)
        m = re.search(r"res=([\d.]+)m", detail)
        res = float(m.group(1)) if m else 1e9
        results.append((verdict != "WIREABLE", res, verdict, detail, base, title))
    for _, res, verdict, detail, base, title in sorted(results):
        if verdict == "WIREABLE":
            tag = "  <= FIN (<=2 m)" if res <= 2 else ""
            print(f"[{verdict}] {detail}{tag}")
            print(f"           {base}   {title}")
    print("\nValider un candidat par un download réel (magic TIFF + float32 + "
          "résolution) AVANT d'écrire le provider (cf. providers/es_cnig.py).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
