#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

SITE_URL = "https://athirikya.com"
OUTPUT_ROOT = Path("mygermanfreund/life-areas")
LIFE_AREAS_FILE = Path(__file__).with_name("life_areas.json")
KNOWLEDGE_UNITS_FILE = Path(__file__).with_name("knowledge_units.json")
PUBLISHED_GUIDES_FILE = Path(__file__).with_name("published_guides.json")
SAFE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ISSUE_ID = re.compile(r"^\d{4}-W\d{2}$")


class ValidationError(ValueError):
    pass


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string.")
    return value.strip()


def normalize_slug(value: Any, name: str) -> str:
    slug = require_text(value, name)
    if not SAFE_SLUG.fullmatch(slug):
        raise ValidationError(f"{name} must be a safe lowercase slug: {slug!r}")
    return slug


def validate_life_areas(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, dict) or not isinstance(raw.get("lifeAreas"), list):
        raise ValidationError("life_areas.json must contain a lifeAreas array.")
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw["lifeAreas"], start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"Life Area {index} must be an object.")
        area_id = normalize_slug(item.get("id"), f"Life Area {index} id")
        if area_id in seen:
            raise ValidationError(f"Duplicate Life Area id: {area_id}")
        seen.add(area_id)
        output.append(
            {
                "id": area_id,
                "title": require_text(item.get("title"), f"Life Area {index} title"),
                "description": require_text(
                    item.get("description"), f"Life Area {index} description"
                ),
            }
        )
    return output


def expected_issue_url(issue_id: str) -> str:
    week = issue_id.split("-W", 1)[1]
    return f"/mygermanfreund/german-buzz/kw-{int(week)}/"


def validate_experiences(
    raw: Any, unit_index: int, global_seen: set[tuple[str, str]]
) -> list[dict[str, str]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValidationError(
            f"Knowledge Unit {unit_index} experiences must be an array."
        )
    output: list[dict[str, str]] = []
    for index, item in enumerate(raw, start=1):
        prefix = f"Knowledge Unit {unit_index} experience {index}"
        if not isinstance(item, dict):
            raise ValidationError(f"{prefix} must be an object.")
        issue = require_text(item.get("issueId"), f"{prefix} issueId")
        if not ISSUE_ID.fullmatch(issue):
            raise ValidationError(f"{prefix} issueId must use YYYY-W## format.")
        topic = require_text(item.get("topic"), f"{prefix} topic")
        url = require_text(item.get("url"), f"{prefix} url")
        expected_url = expected_issue_url(issue)
        if url != expected_url:
            raise ValidationError(
                f"{prefix} url must match {issue}: expected {expected_url}, got {url}"
            )
        key = (issue, topic.casefold())
        if key in global_seen:
            raise ValidationError(
                f"Duplicate experience across Knowledge Units: {issue} / {topic}"
            )
        global_seen.add(key)
        output.append({"issueId": issue, "topic": topic, "url": url})
    return output


def validate_knowledge_units(raw: Any, valid_areas: set[str]) -> None:
    if not isinstance(raw, list):
        raise ValidationError("knowledge_units.json must contain an array.")
    seen: set[str] = set()
    global_experiences: set[tuple[str, str]] = set()
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"Knowledge Unit {index} must be an object.")
        unit_id = normalize_slug(item.get("id"), f"Knowledge Unit {index} id")
        area = normalize_slug(item.get("lifeArea"), f"Knowledge Unit {index} lifeArea")
        if area not in valid_areas:
            raise ValidationError(
                f"Knowledge Unit {index} references unknown Life Area: {area}"
            )
        if unit_id in seen:
            raise ValidationError(f"Duplicate Knowledge Unit id: {unit_id}")
        seen.add(unit_id)
        require_text(item.get("title"), f"Knowledge Unit {index} title")
        require_text(item.get("summary"), f"Knowledge Unit {index} summary")
        validate_experiences(item.get("experiences"), index, global_experiences)


def validate_published_guides(
    raw: Any, valid_areas: set[str]
) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        raise ValidationError("published_guides.json must contain an array.")
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"Published guide {index} must be an object.")
        guide_id = normalize_slug(item.get("id"), f"Published guide {index} id")
        if guide_id in seen:
            raise ValidationError(f"Duplicate published guide id: {guide_id}")
        seen.add(guide_id)
        area = normalize_slug(
            item.get("lifeArea"), f"Published guide {index} lifeArea"
        )
        if area not in valid_areas:
            raise ValidationError(
                f"Published guide {index} references unknown Life Area: {area}"
            )
        url = require_text(item.get("url"), f"Published guide {index} url")
        expected_url = f"/mygermanfreund/guides/{guide_id}/"
        if url != expected_url:
            raise ValidationError(
                f"Published guide {index} url must be {expected_url}."
            )
        issue = require_text(
            item.get("sourceIssueId"), f"Published guide {index} sourceIssueId"
        )
        if not ISSUE_ID.fullmatch(issue):
            raise ValidationError(
                f"Published guide {index} sourceIssueId must use YYYY-W## format."
            )
        output.append(
            {
                "id": guide_id,
                "lifeArea": area,
                "title": require_text(
                    item.get("title"), f"Published guide {index} title"
                ),
                "summary": require_text(
                    item.get("summary"), f"Published guide {index} summary"
                ),
                "url": url,
                "sourceIssueId": issue,
                "sourceTopic": require_text(
                    item.get("sourceTopic"), f"Published guide {index} sourceTopic"
                ),
            }
        )
    return output


def render_guide(guide: dict[str, str]) -> str:
    return f'''      <article class="notice-card" id="{esc(guide["id"])}">
        <h2>{esc(guide["title"])}</h2>
        <p>{esc(guide["summary"])}</p>
        <a class="text-link text-link-cta" href="{esc(guide["url"])}">Read guide <span aria-hidden="true">→</span></a>
      </article>'''


def render_page(area: dict[str, str], guides: list[dict[str, str]]) -> str:
    area_guides = [guide for guide in guides if guide["lifeArea"] == area["id"]]
    content = "\n".join(render_guide(guide) for guide in area_guides)
    if not content:
        content = '      <p class="small-note">Practical guidance for this area will be added when there is useful, specific information to share.</p>'
    canonical = f"{SITE_URL}/mygermanfreund/life-areas/{area['id']}/"
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(area['title'])} | MyGermanFreund</title>
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
    <a class="brand" href="../../../index.html" aria-label="Athirikya home"><img src="../../../assets/athirikya-wordmark.png" alt="Athirikya"></a>
    <nav class="nav" aria-label="Main navigation"><a href="../../../index.html">Home</a><a href="../../german-buzz/">German Buzz</a><a href="../../../mygermanfreund.html">MyGermanFreund</a></nav>
  </header>
  <main class="content-page">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../../../index.html">Athirikya</a> / <a href="../../../mygermanfreund.html">MyGermanFreund</a> / {esc(area['title'])}</nav>
    <article>
      <header class="content-hero"><h1>{esc(area['title'])}</h1><p class="content-lead">{esc(area['description'])}</p></header>
      <section class="guide-section">
{content}
      </section>
    </article>
  </main>
  <footer class="site-footer"><div><img src="../../../assets/athirikya-wordmark.png" alt="Athirikya"></div><nav aria-label="Footer navigation"><a href="../../../privacy.html">Privacy</a><a href="../../../terms.html">Terms</a><a href="../../../impressum.html">Impressum</a><a href="../../../contact.html">Contact</a></nav><p>© 2026 Athirikya. All rights reserved.</p></footer>
</body>
</html>
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        root = args.repo_root.resolve()
        areas = validate_life_areas(load_json(LIFE_AREAS_FILE))
        valid_areas = {area["id"] for area in areas}
        validate_knowledge_units(load_json(KNOWLEDGE_UNITS_FILE), valid_areas)
        guides = validate_published_guides(
            load_json(PUBLISHED_GUIDES_FILE), valid_areas
        )
        for area in areas:
            path = root / OUTPUT_ROOT / area["id"] / "index.html"
            print(f"{'WOULD WRITE' if args.dry_run else 'WRITE'}: {path}")
            if not args.dry_run:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(render_page(area, guides), encoding="utf-8")
        print(f"Public topic pages processed: {len(areas)}")
        return 0
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
