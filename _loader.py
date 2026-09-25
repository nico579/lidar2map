# _loader.py — Entry point du binaire PyInstaller (macOS/Linux/Windows)
#
# Ce fichier est compilé dans le binaire PyInstaller et NE CHANGE JAMAIS.
# Il se contente de trouver lidar2map.py dans _internal/ et de l'exécuter.
#
# lidar2map.py est stocké comme fichier texte dans le zip/bundle. Ce choix
# servait au patch sans reconstruction (update_app.py), retiré en 1.53.0 :
# toute nouvelle version est désormais une release complète, reconstruite par
# release.yml.

import sys
import runpy
from pathlib import Path

# En mode PyInstaller onedir, sys._MEIPASS pointe vers _internal/
# En mode développement (python lidar2map.py direct), _MEIPASS absent.
_base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
_script = _base / "lidar2map.py"

# Fallback : chercher à côté du binaire (structure pré-PyInstaller-6)
if not _script.exists():
    _script = Path(sys.executable).parent / "_internal" / "lidar2map.py"

if not _script.exists():
    print(f"ERREUR : lidar2map.py introuvable dans {_base}")
    print("  Vérifiez que _internal/lidar2map.py est présent dans le bundle.")
    sys.exit(1)

# sys.argv[0] doit pointer vers le script pour que __file__ soit cohérent
sys.argv[0] = str(_script)

# runpy.run_path exécute le script en lui donnant __file__, __name__ = '__main__'
# correctement, comme si on avait fait `python lidar2map.py`.
runpy.run_path(str(_script), run_name="__main__")
