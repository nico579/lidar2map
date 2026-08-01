"""Régressions du partage LAN vers le téléphone (sans réseau externe)."""

import importlib.util
import os
import tempfile
import unittest
import urllib.request
from pathlib import Path


os.environ["LIDAR2MAP_BOOTSTRAP"] = "none"
ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("l2m_phone_share", ROOT / "lidar2map.py")
L2M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(L2M)


class PhoneShareTests(unittest.TestCase):
    def test_automatic_output_uses_the_normalized_project_name(self):
        with tempfile.TemporaryDirectory() as td:
            old_work = L2M.DOSSIER_TRAVAIL
            try:
                L2M.DOSSIER_TRAVAIL = Path(td)
                expected = Path(td) / "Projets" / "lidar2map_thones-20km"
                deliverable = expected / "lidar" / "fr" / "relief.mbtiles"
                deliverable.parent.mkdir(parents=True)
                deliverable.write_bytes(b"sqlite")

                resolved = L2M._dossier_partage_projet("lidar2map_Thônes-20km")

                self.assertEqual(resolved, expected)
                # WindowsPath compare sans tenir compte de la casse : cette
                # assertion textuelle verrouille aussi la régression Linux.
                self.assertEqual(resolved.name, "lidar2map_thones-20km")
                self.assertEqual(L2M._livrables_projet(resolved), [deliverable])
            finally:
                L2M.DOSSIER_TRAVAIL = old_work

    def test_custom_output_directory_is_used_directly(self):
        with tempfile.TemporaryDirectory() as td:
            custom = Path(td) / "sortie-directe"
            custom.mkdir()
            deliverable = custom / "slope.mbtiles"
            deliverable.write_bytes(b"sqlite")

            resolved = L2M._dossier_partage_projet("nom-ignore", str(custom))

            self.assertEqual(resolved, custom)
            self.assertEqual(L2M._livrables_projet(resolved), [deliverable])
            self.assertFalse((custom / "nom-ignore").exists())

    def test_mobile_page_recommends_the_reliable_locus_import(self):
        with tempfile.TemporaryDirectory() as td:
            deliverable = Path(td) / "relief.mbtiles"
            deliverable.write_bytes(b"sqlite")
            server = L2M._PartageServeur()
            try:
                server.demarrer([deliverable])
                port = server._httpd.server_address[1]
                pages = {}
                for lang in ("en", "fr"):
                    req = urllib.request.Request(
                        f"http://127.0.0.1:{port}/",
                        headers={"Accept-Language": lang},
                    )
                    with urllib.request.urlopen(req, timeout=5) as response:
                        pages[lang] = response.read().decode("utf-8")
                self.assertIn("Map Manager", pages["en"])
                self.assertIn("Import map", pages["en"])
                self.assertIn("depending on Android", pages["en"])
                self.assertIn("Gestionnaire de cartes", pages["fr"])
                self.assertIn("Importer une carte", pages["fr"])
                self.assertIn("selon Android", pages["fr"])
            finally:
                server.arreter()

    def test_gui_copy_mentions_the_locus_internal_import(self):
        app_js = (ROOT / "gui" / "app.js").read_text(encoding="utf-8")
        index_html = (ROOT / "gui" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Gestionnaire de cartes → Importer une carte", app_js)
        self.assertIn("Map Manager → Import map", app_js)
        self.assertIn("Gestionnaire de cartes → Importer une carte", index_html)


if __name__ == "__main__":
    unittest.main()
