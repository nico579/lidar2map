#!/usr/bin/env python3
"""Validate local links in the published documentation sources."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parent.parent
PUBLISHED_ALIASES = {
    (ROOT / "README.md").resolve(): (ROOT / "README_Github.md").resolve(),
    (ROOT / "README.fr.md").resolve(): (ROOT / "README_Github.fr.md").resolve(),
    (ROOT / "BUILD.md").resolve(): (ROOT / "README_LIDAR2MAP.md").resolve(),
}

MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
HTML_LINK = re.compile(r"(?:src|href)=[\"']([^\"']+)[\"']", re.IGNORECASE)

CANONICAL_BILINGUAL_PAGES = (
    "getting-started",
    "cli",
    "shadings",
    "dfm",
    "formats",
    "providers",
    "remote",
    "contributing-providers",
    "data-licenses",
)

GUI_SCREENSHOTS = {
    "lidar_dtm.PNG",
    "lidar_laz_classes.PNG",
    "lidar_laz_csf.PNG",
    "raster.PNG",
    "vector_ign.PNG",
    "vector_osm.PNG",
    "vector_merge.PNG",
    "raster_split.PNG",
    "phone.PNG",
}


def _target_from_markdown(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("<") and ">" in raw:
        return raw[1:raw.index(">")]
    return raw.split(maxsplit=1)[0]


def _resolve_local(source: Path, raw_target: str) -> Optional[Path]:
    target = unquote(raw_target.strip())
    if not target or target.startswith("#"):
        return None
    if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
        return None
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return None
    resolved = (source.parent / target).resolve()
    return PUBLISHED_ALIASES.get(resolved, resolved)


def main() -> int:
    sources = [ROOT / "README_Github.md", ROOT / "README_Github.fr.md"]
    sources.extend(sorted((ROOT / "docs").rglob("*.md")))
    sources.append(ROOT / "tools" / "README_rlidar2map.md")

    failures: list[str] = []
    referenced_gui_screenshots: set[str] = set()
    checked = 0
    for source in sources:
        text = source.read_text(encoding="utf-8")
        if text.count("```") % 2:
            failures.append(f"{source.relative_to(ROOT)}: bloc de code non fermé")
        links = [_target_from_markdown(value)
                 for value in MARKDOWN_LINK.findall(text)]
        links.extend(HTML_LINK.findall(text))
        for raw_target in links:
            target = _resolve_local(source, raw_target)
            if target is None:
                continue
            checked += 1
            if not target.exists():
                relative_source = source.relative_to(ROOT)
                failures.append(
                    f"{relative_source}: {raw_target!r} -> "
                    f"{target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}"
                )
            elif target.parent == (ROOT / "screenshots" / "GUI").resolve():
                referenced_gui_screenshots.add(target.name)

    for stem in CANONICAL_BILINGUAL_PAGES:
        for suffix in (".md", ".fr.md"):
            page = ROOT / "docs" / f"{stem}{suffix}"
            if not page.exists():
                failures.append(f"page canonique absente: {page.relative_to(ROOT)}")

    missing_screenshots = GUI_SCREENSHOTS - referenced_gui_screenshots
    if missing_screenshots:
        failures.append(
            "captures GUI non référencées: " + ", ".join(sorted(missing_screenshots))
        )

    if failures:
        print("BROKEN LOCAL DOCUMENTATION LINKS")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"TOUS OK — {checked} liens locaux vérifiés dans {len(sources)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
