#!/usr/bin/env python3
"""Generate a compact German Buzz website issue from the app JSON.

The tool writes files locally only. It never commits, pushes or deploys.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

SITE_URL = "https://athirikya.com"
ISSUES_DIR = Path("mygermanfreund/german-buzz")
LANDING_PAGE = ISSUES_DIR / "index.html"
SITEMAP = Path("sitemap.xml")
START_MARKER = "<!-- GERMAN_BUZZ_ISSUES_START -->"
END_MARKER = "<!-- GERMAN_BUZZ_ISSUES_END -->"


class ValidationError(ValueError):
    pass


def require_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Missing required text field: {key}")
    return value.strip()


def escape(value: str) -> str:
    return html.escape(value, quote=True)


@dataclass(frozen=True)
class Topic:
    title: str
    whats_happening: str
    sentence: str


@dataclass(frozen=True)
class Issue:
    issue_id: str
    year: int
    week: int
    date_range: str
    tagline: str
    weekly_summary: str
    topics: tuple[Topic, ...]

    @property
    def slug(self) -> str:
        return f"kw-{self.week}"

    @property
    def kw(self) -> str:
        return f"KW {self.week}"

    @property
    def url(self) -> str:
        return f"{SITE_URL}/mygermanfreund/german-buzz/{self.slug}/"


def normalize_issue(raw: dict[str, Any]) -> Issue:
    if not isinstance(raw, dict):
        raise ValidationError("The JSON root must be an object.")

    issue_id = require_text(raw, "id")
    match = re.fullmatch(r"(\d{4})-W(\d{2})", issue_id)
    if not match:
        raise ValidationError("id must use YYYY-W## format, for example 2026-W31.")

    year = int(match.group(1))
    week = int(match.group(2))
    if not 1 <= week <= 53:
        raise ValidationError(f"Invalid calendar week: {week}")

    if raw.get("year") != year or raw.get("weekNumber") != week:
        raise ValidationError("year and weekNumber must match the id field.")

    topics_raw = raw.get("topics")
    if not isinstance(topics_raw, list) or not topics_raw:
        raise ValidationError("topics must be a non-empty array.")

    topics: list[Topic] = []
    for index, item in enumerate(topics_raw, start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"Topic {index} must be an object.")
        topics.append(
            Topic(
                title=require_text(item, "title"),
                whats_happening=require_text(item, "whatsHappening"),
                sentence=require_text(item, "germanContext"),
            )
        )

    return Issue(
        issue_id=issue_id,
        year=year,
        week=week,
        date_range=require_text(raw, "dateRange"),
        tagline=require_text(raw, "tagline"),
        weekly_summary=require_text(raw, "weeklySummary"),
        topics=tuple(topics),
    )


def render_topic(topic: Topic) -> str:
    return f'''        <section class="topic-card">
          <h2>{escape(topic.title)}</h2>
          <h3>Worum geht es?</h3>
          <p>{escape(topic.whats_happening)}</p>
          <p><strong>Satz zum Thema:</strong> {escape(topic.sentence)}</p>
        </section>'''


def render_issue(issue: Issue) -> str:
    topics_html = "\n".join(render_topic(topic) for topic in issue.topics)
    description = f"German Buzz {issue.kw} ({issue.date_range}): {issue.weekly_summary}."
    structured = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": f"German Buzz {issue.kw}",
        "description": description,
        "mainEntityOfPage": issue.url,
        "author": {"@type": "Organization", "name": "Athirikya"},
        "publisher": {"@type": "Organization", "name": "Athirikya", "url": f"{SITE_URL}/"},
        "isPartOf": {"@type": "CreativeWorkSeries", "name": "German Buzz"},
    }
    structured_json = json.dumps(structured, ensure_ascii=False, separators=(",", ":"))

    return f'''<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>German Buzz {escape(issue.kw)} | MyGermanFreund</title>
  <meta name="description" content="{escape(description)}">
  <link rel="canonical" href="{issue.url}">
  <meta name="robots" content="index,follow">
  <meta property="og:type" content="article">
  <meta property="og:title" content="German Buzz {escape(issue.kw)} | MyGermanFreund">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url" content="{issue.url}">
  <meta property="og:site_name" content="Athirikya">
  <link rel="icon" href="../../../assets/athirikya-logo.png?v=6" type="image/png">
  <link rel="stylesheet" href="../../../styles.css">
  <link rel="stylesheet" href="../../../soothing.css">
  <link rel="stylesheet" href="../../../seo-content.css">
  <link rel="stylesheet" href="../../../humanized.css">
  <script type="application/ld+json">{structured_json}</script>
</head>
<body>
  <header class="site-header">
    <a class="brand" href="../../../index.html" aria-label="Athirikya home"><img src="../../../assets/athirikya-logo.png" alt="Athirikya"></a>
    <nav class="nav" aria-label="Main navigation"><a href="../../../index.html">Home</a><a href="../">German Buzz</a><a href="../../../mygermanfreund.html">MyGermanFreund</a></nav>
  </header>
  <main class="content-page">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../../../index.html">Athirikya</a> / <a href="../">German Buzz</a> / {escape(issue.kw)}</nav>
    <article>
      <header class="content-hero issue-intro">
        <div class="issue-meta"><span>{escape(issue.kw)}</span><span>{escape(issue.date_range)}</span></div>
        <h1>German Buzz</h1>
        <p class="content-lead">{escape(issue.tagline)}</p>
        <p>{escape(issue.weekly_summary)}</p>
      </header>
      <div class="topic-grid">
{topics_html}
      </div>
      <section class="issue-cta">
        <h2>Continue learning with MyGermanFreund</h2>
        <p>The app adds guided dialogues, useful words and practical weekly conversation support.</p>
        <a class="button primary" href="../../../mygermanfreund.html">Explore MyGermanFreund</a>
      </section>
    </article>
  </main>
  <footer class="site-footer"><div><img src="../../../assets/athirikya-logo.png" alt="Athirikya"></div><nav aria-label="Footer navigation"><a href="../../../privacy.html">Privacy</a><a href="../../../terms.html">Terms</a><a href="../../../impressum.html">Impressum</a><a href="../../../contact.html">Contact</a></nav><p>© 2026 Athirikya. All rights reserved.</p></footer>
</body>
</html>
'''


def render_issue_card(issue: Issue) -> str:
    return f'''      <article class="issue-card" data-issue-id="{escape(issue.issue_id)}">
        <div class="issue-meta"><span>{escape(issue.kw)}</span><span>{escape(issue.date_range)}</span></div>
        <h2>{escape(issue.weekly_summary)}</h2>
        <p>{escape(issue.tagline)}</p>
        <a class="text-link text-link-cta" href="{escape(issue.slug)}/">Read German Buzz {escape(issue.kw)} <span aria-hidden="true">→</span></a>
      </article>'''


def update_landing(content: str, issue: Issue) -> str:
    new_card = render_issue_card(issue)
    if START_MARKER in content and END_MARKER in content:
        before, remainder = content.split(START_MARKER, 1)
        managed, after = remainder.split(END_MARKER, 1)
        managed = re.sub(
            rf'\s*<article class="issue-card" data-issue-id="{re.escape(issue.issue_id)}">.*?</article>',
            "",
            managed,
            flags=re.DOTALL,
        )
        existing_cards = re.findall(r'<article class="issue-card".*?</article>', managed, flags=re.DOTALL)
        block = "\n" + "\n".join([new_card, *existing_cards]) + "\n      "
        return before + START_MARKER + block + END_MARKER + after

    match = re.search(r'(<section class="issue-list"[^>]*>\s*<h2[^>]*>.*?</h2>)(.*?)(</section>)', content, re.DOTALL)
    if not match:
        raise ValidationError(f"Could not locate issue-list section in {LANDING_PAGE}.")

    existing = match.group(2).strip()
    managed = f"\n      {START_MARKER}\n{new_card}\n{existing}\n      {END_MARKER}\n    "
    return content[: match.start()] + match.group(1) + managed + match.group(3) + content[match.end() :]


def update_sitemap(content: str, issue: Issue) -> str:
    namespace_uri = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace_uri)
    root = ET.fromstring(content)
    ns = {"sm": namespace_uri}

    for node in root.findall("sm:url", ns):
        loc = node.find("sm:loc", ns)
        if loc is not None and loc.text == issue.url:
            return content

    url_node = ET.SubElement(root, f"{{{namespace_uri}}}url")
    ET.SubElement(url_node, f"{{{namespace_uri}}}loc").text = issue.url
    ET.SubElement(url_node, f"{{{namespace_uri}}}changefreq").text = "weekly"
    ET.SubElement(url_node, f"{{{namespace_uri}}}priority").text = "0.8"
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a compact German Buzz HTML issue locally.")
    parser.add_argument("json_file", type=Path, help="Path to the weekly German Buzz JSON file")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Website repository root")
    parser.add_argument("--dry-run", action="store_true", help="Validate and show planned changes without writing")
    parser.add_argument("--force", action="store_true", help="Allow replacing an existing weekly issue page")
    args = parser.parse_args()

    try:
        repo_root = args.repo_root.resolve()
        raw = json.loads(args.json_file.resolve().read_text(encoding="utf-8"))
        issue = normalize_issue(raw)

        issue_path = repo_root / ISSUES_DIR / issue.slug / "index.html"
        landing_path = repo_root / LANDING_PAGE
        sitemap_path = repo_root / SITEMAP

        if not landing_path.exists():
            raise ValidationError(f"Missing landing page: {landing_path}")
        if not sitemap_path.exists():
            raise ValidationError(f"Missing sitemap: {sitemap_path}")
        if issue_path.exists() and not args.force:
            raise ValidationError(f"Issue already exists: {issue_path}. Use --force only after reviewing it.")

        outputs = [
            (issue_path, render_issue(issue)),
            (landing_path, update_landing(landing_path.read_text(encoding="utf-8"), issue)),
            (sitemap_path, update_sitemap(sitemap_path.read_text(encoding="utf-8"), issue)),
        ]

        for path, _ in outputs:
            print(f"{'WOULD WRITE' if args.dry_run else 'WRITE'}: {path}")

        if args.dry_run:
            return 0

        for path, content in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        print("Generation complete. Review with git status and git diff before committing.")
        return 0

    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
