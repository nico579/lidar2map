"""Aperçus des échantillons techniques natifs, sans qualification de vestiges."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("NUMBA_NUM_THREADS", "4")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from _ombrages_pures import _lrm_array, _svf_numpy

base = ROOT / "cache/native-provider-validation"
cases = [
    ("Wallonie — 0,5 m", base / "be_wallonia_native_crop.tif", "Z : DNG"),
    ("Bratislava — 1 m", base / "sk_bratislava/native_crop.tif", "Z : ETRS89-h"),
    ("Banská Štiavnica — 1 m", base / "sk_banska_stiavnica/native_crop.tif", "Z : ETRS89-h"),
]
fig, axes = plt.subplots(3, 3, figsize=(12, 11), constrained_layout=True)
for row, (title, path, reference) in enumerate(cases):
    with rasterio.open(path) as src:
        a = src.read(1)
        res = src.res[0]
        lrm, _ = _lrm_array(a.copy(), src.nodata, 2/res)
        svf = _svf_numpy(a.copy(), int(15/res), resolution=res, nodata=src.nodata)
    halo = int(20/res)
    a, lrm, svf = (array[halo:-halo, halo:-halo] for array in (a, lrm, svf))
    width = a.shape[1]*res
    extent = (0, width, 0, a.shape[0]*res)
    limit = max(.025, float(np.percentile(np.abs(lrm), 98)))
    images = [axes[row, 0].imshow(a, cmap="terrain", extent=extent),
              axes[row, 1].imshow(lrm, cmap="RdBu_r", vmin=-limit, vmax=limit, extent=extent),
              axes[row, 2].imshow(svf, cmap="gray", extent=extent)]
    labels = [f"{title}\nMNT ({reference}, m)", "LRM σ = 2 m (m)", "SVF rayon = 15 m (0–1)"]
    for col, (im, label) in enumerate(zip(images, labels)):
        axes[row, col].set_title(label, fontsize=10)
        axes[row, col].set_xlabel("m")
        axes[row, col].set_ylabel("m")
        fig.colorbar(im, ax=axes[row, col], shrink=.72, pad=.02)
fig.suptitle("Données natives : lecture du relief sur trois échantillons techniques\n"
             "Plages de couleurs propres à chaque image — aucune validation de vestiges", fontsize=12)
target = ROOT / "docs/native-wallonie-slovaquie-apercus.png"
fig.savefig(target, dpi=150)
plt.close(fig)
print(target)
