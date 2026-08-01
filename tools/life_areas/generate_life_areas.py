#!/usr/bin/env python3
"""Generate the 15 Athirikya Life Area pages from JSON.

The first year is intentionally exploratory: Life Areas are the stable,
expandable backbone; Knowledge Units remain empty until real German Buzz
experiences justify them.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

SITE_URL = "https://athirikya.com"
OUTPUT_ROOT = Path("mygermanfreund/life-areas")
LIFE_AREAS_FILE = Path(__file__).with_name("life_areas.json")
KNOWLEDGE_UNITS_FILE = Path(__file__).with_name("knowledge_units.json")


class ValidationError(ValueError):
    pass


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_life_areas(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, dict) or not isinstance(raw.get("lifeAreas"), list):
        raise ValidationError("life_areas.json must contain a lifeAreas array.")

    areas: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw["lifeAreas"], start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"Life Area {index} must be an object.")
        area_id = item.get("id")
        title = item.get("title")
        description = item.get("description")
        if not all(isinstance(value, str) and value.strip() for value in (area_id, title, description)):
            raise ValidationError(f"Life Area {index} requires id, title and description.")
        if area_id in seen:
            raise ValidationError(f"Duplicate Life Area id: {area_id}")
        seen.add(area_id)
        areas.append({"id": area_id.strip(), "title": title.strip(), "description": description.strip()})
    return areas


def validate_knowledge_units(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise ValidationError("knowledge_units.json must contain an array.")
    return [item for item in raw if isinstance(item, dict)]


def render_page(area: dict[str, str], units: list[dict[str, Any]]) -> str:
    area_units = [unit for unit in units if unit.get("lifeArea") == area["id"]]
    if area_units:
        units_html = "\n".join(
            f'''      <article class="notice-card">
        <h3>{esc(str(unit.get("title", unit.get("id", "Knowledge Unit"))))}</h3>
        <p>{esc(str(unit.get("summary", "This Knowledge Unit is evolving through German Buzz.")))}</p>
      </article>'''
            for unit in area_units
        )
    else:
        units_html = '''      <article class="notice-card">
        <p>No Knowledge Units have been added yet. This area will grow from real German Buzz experiences.</p>
      </article>'''

    canonical = f"{SITE_URL}/mygermanfreund/life-areas/{area['id']}/"
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(area['title'])} | Life Areas | MyGermanFreund</title>
  <meta name="description" content="{esc(area['description'])}">
  <link rel="canonical" href="{canonical}">
  <meta name="robots" content="index,follow">
  <link rel="icon" href="../../../assets/athirikya-logo.png?v=6" type="image/png">
  <link rel="stylesheet" href="../../../styles.css">
  <link rel="stylesheet" href="../../../soothing.css">
  <link rel="stylesheet" href="../../../seo-content.css">
  <link rel="stylesheet" href="../../../humanized.css">
</head>
<body>
  <header class="site-header">
    <a class="brand" href="../../../index.html" aria-label="Athirikya home"><img src="../../../assets/athirikya-logo.png" alt="Athirikya"></a>
    <nav class="nav" aria-label="Main navigation"><a href="../../../index.html">Home</a><a href="../../german-buzz/">German Buzz</a><a href="../../../mygermanfreund.html">MyGermanFreund</a></nav>
  </header>
  <main class="content-page">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../../../index.html">Athirikya</a> / <a href="../../../mygermanfreund.html">MyGermanFreund</a> / Life Areas / {esc(area['title'])}</nav>
    <article>
      <header class="content-hero">
        <p class="eyebrow">Life Area</p>
        <h1>{esc(area['title'])}</h1>
        <p class="content-lead">{esc(area['description'])}</p>
      </header>
      <section class="guide-section" aria-labelledby="knowledge-units">
        <h2 id="knowledge-units">Knowledge Units</h2>
        <div class="guide-grid">
{units_html}
        </div>
      </section>
      <section class="guide-section notice-card" aria-labelledby="buzz-experiences">
        <h2 id="buzz-experiences">German Buzz Experiences</h2>
        <p>No experiences have been added yet. Weekly topics will gradually enrich this Life Area.</p>
      </section>
      <section class="guide-section notice-card"><h2>Related Letter Types</h2><p>Coming soon.</p></section>
      <section class="guide-section notice-card"><h2>Related Did You Know?</h2><p>Coming soon.</p></section>
      <section class="guide-section notice-card"><h2>Official Resources</h2><p>Coming soon.</p></section>
    </article>
  </main>
  <footer class="site-footer"><div><img src="../../../assets/athirikya-logo.png" alt="Athirikya"></div><nav aria-label="Footer navigation"><a href="../../../privacy.html">Privacy</a><a href="../../../terms.html">Terms</a><a href="../../../impressum.html">Impressum</a><a href="../../../contact.html">Contact</a></nav><p>© 2026 Athirikya. All rights reserved.</p></footer>
</body>
</html>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Athirikya Life Area pages.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Website repository root")
    parser.add_argument("--dry-run", action="store_true", help="Validate and show planned output without writing")
    args = parser.parse_args()

    try:
        repo_root = args.repo_root.resolve()
        areas = validate_life_areas(load_json(LIFE_AREAS_FILE))
        units = validate_knowledge_units(load_json(KNOWLEDGE_UNITS_FILE))

        for area in areas:
            path = repo_root / OUTPUT_ROOT / area["id"] / "index.html"
            print(f"{'WOULD WRITE' if args.dry_run else 'WRITE'}: {path}")
            if not args.dry_run:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(render_page(area, units), encoding="utf-8")

        print(f"Life Areas processed: {len(areas)}")
        return 0
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
