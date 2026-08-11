"""Types d'ombrages, presets par résolution et parsing de `--shading`.

Source de vérité unique pour tous les types d'ombrage disponibles
(``_SHADING_TYPES``), leur ordre d'affichage (``SHADING_TYPES_ORDRE``,
``SHADING_TOUS``), les presets par résolution (``SHADING_PRESETS``,
``_resoudre_preset_shading``) et le parsing de la syntaxe répétable
``--shading TYPE:cle=val,...`` (``parser_shading_spec``).

Module entièrement pur : dictionnaires/listes statiques et fonctions sans
état ni dépendance applicative — aucune injection nécessaire.
"""

from __future__ import annotations


# ── Instances d'ombrages paramétrées (--shading TYPE:cle=val,...) ────────────
# Types et paramètres admis. Syntaxe répétable façon ffmpeg/GDAL : chaque
# --shading produit UNE instance avec SES paramètres — deux instances du même
# type (ex. svf à 20 m ET 100 m) coexistent, les params étant encodés dans le
# nom de fichier de sortie.


# Ordre = utilité pratique. LRM d'abord : le plus rapide (flou gaussien, pas de
# ray-cast) et le plus lisible pour un néophyte (structures continues), donc le
# défaut. Puis VAT (détecteur multi-échelle complet), SVF, la paire openness,
# RRIM, les hillshades (multi > directionnels), slope en dernier (terne seul,
# surtout couche du VAT). Pilote le dropdown GUI, le menu interactif, les
# choices argparse et l'ordre de `--shadings tous`.
_SHADING_TYPES = {
    "lrm":    {"sigma"},
    "vat":    {"dist", "gamma"},
    "e4mstp": {"dist", "gamma"},
    "svf":   {"conv", "dist", "gamma", "sweep"},
    "opos":  {"dist", "gamma", "sweep"},
    "oneg":  {"dist", "gamma", "sweep"},
    "rrim":  {"sigma"},
    "multi": {"elevation"},
    "315":   {"elevation"},
    "045":   {"elevation"},
    "135":   {"elevation"},
    "225":   {"elevation"},
    "slope": set(),
}

# Source UNIQUE pour toutes les listes de types d'ombrage (argparse choices, menu
# interactif, expansion "tous"). Dérivées de _SHADING_TYPES → ajouter un type au
# dict suffit, plus de liste recopiée à la main qui se désynchronise.
#   SHADING_TYPES_ORDRE : tous les types, dans l'ordre d'affichage (vat inclus).
#   SHADING_TOUS        : ce que produit `--shadings tous`. 'vat' et 'e4mstp'
#       EXCLUS : composites lourds qui recalculent svf/opos/slope (redondant
#       quand "tous" génère déjà ces couches). Restent atteignables via
#       --shadings vat|e4mstp / --shading vat|e4mstp / menu.
SHADING_TYPES_ORDRE = list(_SHADING_TYPES)
SHADING_TOUS        = [t for t in SHADING_TYPES_ORDRE if t not in ("vat", "e4mstp")]


# Presets de stack par résolution : params en METRES (intention indépendante de la
# taille de pixel) pour cibler la même échelle de structures que le MNT soit à
# 0,25 m ou 5 m. Sans ça, à 5 m le rayon SVF de 20 m ne fait que 4 px et le LRM
# enleve 75 m de relief. 'auto' choisit le palier selon RESOLUTION_M. Opt-in
# (--shading-preset) : le comportement par defaut reste inchange. Valeurs a
# l'appreciation de l'archeologue (tunables).
SHADING_PRESETS = {
    # nom          svf/opos rayon (m)   LRM sigma (m)   elevation soleil (deg)
    "micro":       (15.0,               8.0,            25),   # micro-relief, MNT fin (<=0,75 m)
    "standard":    (30.0,               15.0,           25),   # MNT ~1 m
    "landscape":   (80.0,               40.0,           30),   # grandes structures / MNT grossier (>=5 m)
}


def _resoudre_preset_shading(name, res_m):
    """(nom_resolu, [instances (type, params)], elevation) pour un preset.
    'auto' choisit le palier par la resolution du provider. Les instances portent
    les params en metres ; le pipeline existant les nomme/encode (cache preserve)."""
    if name == "auto":
        name = ("micro" if res_m <= 0.75 else
                "standard" if res_m <= 2.5 else "landscape")
    dist, sigma, elev = SHADING_PRESETS[name]
    insts = [("svf", {"dist": dist}), ("opos", {"dist": dist}),
             ("lrm", {"sigma": sigma})]
    return name, insts, elev


def parser_shading_spec(spec):
    """Parse 'TYPE[:cle=val,...]' → (type, params explicites).

    Exemples :
      --shading svf:dist=20,gamma=2,conv=flux --shading svf:dist=100
      --shading oneg:dist=20,gamma=1.5 --shading 315:elevation=20
      --shading lrm:sigma=10 --shading slope

    Paramètres par type :
      315/045/135/225/multi : elevation (degrés)
      svf                   : conv (flux|rvt), dist (m), gamma,
                              sweep (1|0, kernel sweep-horizon — défaut --svf-sweep)
      opos/oneg             : dist (m), gamma,
                              sweep (1|0, kernel sweep-horizon — défaut --svf-sweep)
      lrm/rrim              : sigma (m, écart-type gaussien — défaut 15 px du provider)
      vat                   : dist (m, rayon SVF/openness), gamma (du composite)
      e4mstp                : dist (m, rayon SVF/openness), gamma (RGB final,
                              défaut 0.8 ; échelles MSTP/SLRM inchangées)
      slope                 : aucun

    Lève ValueError (message clair) si type ou clé inconnus.
    """
    typ, _, reste = spec.strip().partition(":")
    typ = typ.strip().lower()
    if typ not in _SHADING_TYPES:
        raise ValueError(f"type d'ombrage inconnu : {typ!r}"
                         f" (valides : {', '.join(sorted(_SHADING_TYPES))})")
    admis = _SHADING_TYPES[typ]
    params = {}
    for kv in reste.split(","):
        kv = kv.strip()
        if not kv:
            continue
        k, sep, v = kv.partition("=")
        k = k.strip().lower()
        if not sep or k not in admis:
            raise ValueError(
                f"paramètre {k!r} invalide pour {typ}"
                f" (admis : {', '.join(sorted(admis)) or 'aucun'})")
        if k == "conv":
            v = v.strip().lower()
            if v not in ("flux", "rvt"):
                raise ValueError(f"conv={v!r} (attendu : flux ou rvt)")
            params[k] = v
        else:
            try:
                params[k] = float(v)
            except ValueError:
                raise ValueError(f"{k}={v.strip()!r} : nombre attendu")
    return typ, params