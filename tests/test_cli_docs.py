"""Doc1 (docs/preconisations_evolution.md) : chaque option de la ligne de
commande figure dans docs/cli.md ET docs/cli.fr.md.

Les options viennent des vrais parsers (parser._actions), construits sans
lancer de traitement, et non d'une regex sur le code : une option ajoutée à
un parser sans sa documentation, ou retirée d'une des deux docs, fait
échouer ce test.
"""

import importlib.util
import os
import tempfile
import re
import sys
import unittest
from pathlib import Path


os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
# Jamais les vrais dossiers d'état et de sorties de l'utilisateur (voir
# _dossiers.py) : run_tests.py en fournit un, sinon un dossier temporaire.
if not os.environ.get("LIDAR2MAP_HOME"):
    os.environ["LIDAR2MAP_HOME"] = tempfile.mkdtemp(prefix="lidar2map-tests-")
ROOT = Path(__file__).resolve().parent.parent

# Chargé par son chemin, enregistré dans sys.modules avant exec_module :
# même raison que dans test_serve_web.py.
_SPEC = importlib.util.spec_from_file_location("l2m_cli_docs", ROOT / "lidar2map.py")
L2M = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = L2M
_SPEC.loader.exec_module(L2M)

DOCS = (ROOT / "docs" / "cli.md", ROOT / "docs" / "cli.fr.md")

# Un parser par mode : LiDAR/OSM (main), raster, vecteur, découpe, fusion,
# partage LAN et GUI web.
PARSERS = (
    "_construire_parser_lidar",
    "_construire_parser_wmts",
    "_construire_parser_wfs",
    "_construire_parser_decouper",
    "_construire_parser_fusionner",
    "_construire_parser_serve",
    "_construire_parser_serve_gui",
)

# Options lues hors de ces parsers : sys.argv examiné avant le bootstrap, et
# pré-parser du bloc __main__ de lidar2map.py (planche d'assemblage seule).
OPTIONS_HORS_PARSER = (
    "--remote-cli", "--remote-gui",
    "--installer-deps", "--desinstaller", "--telecharger-outils", "--smoketest",
    "--index-sheet", "--planche",
)

# Volontairement absentes de la documentation utilisateur.
EXCLUSIONS = {
    "--help": "aide standard ajoutée par argparse",
}


def _options_des_parsers():
    """{option: premier parser qui la déclare}, formes négatives comprises."""
    options = {}
    for nom in PARSERS:
        for action in getattr(L2M, nom)()._actions:
            for option in action.option_strings:
                if option.startswith("--"):
                    options.setdefault(option, nom)
    return options


def _documentee(option, texte):
    # Frontières explicites : --zone ne doit pas passer pour --zone-name.
    motif = r"(?<![\w-])" + re.escape(option) + r"(?![\w-])"
    return re.search(motif, texte) is not None


class OptionsDocumenteesTests(unittest.TestCase):

    def setUp(self):
        self.textes = {doc.name: doc.read_text(encoding="utf-8") for doc in DOCS}

    def test_options_des_parsers_documentees_en_anglais_et_en_francais(self):
        options = _options_des_parsers()
        # Garde : un parser vide ou mal construit ne doit pas faire passer
        # le test à vide (111 options distinctes au 2026-09-25).
        self.assertGreater(len(options), 100)
        manquantes = [
            f"{option} ({parser}) absente de {nom}"
            for option, parser in sorted(options.items())
            if option not in EXCLUSIONS
            for nom, texte in self.textes.items()
            if not _documentee(option, texte)
        ]
        self.assertEqual(manquantes, [])

    def test_options_hors_parser_existantes_et_documentees(self):
        source = (ROOT / "lidar2map.py").read_text(encoding="utf-8")
        for option in OPTIONS_HORS_PARSER:
            with self.subTest(option=option):
                # Une option retirée du code doit aussi sortir de cette liste.
                self.assertIn(f'"{option}"', source)
                for nom, texte in self.textes.items():
                    self.assertTrue(_documentee(option, texte),
                                    f"{option} absente de {nom}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
