#!/usr/bin/env python3
"""Generate a German Buzz website issue from the same JSON used by the app.

This tool writes files locally only. It never commits or pushes changes.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
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


def first_value(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", []):
            return value
    return default


def require_text(data: dict[str, Any], *keys: str) -> str:
    value = first_value(data, *keys)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Missing required text field. Expected one of: {', '.join(keys)}")
    return value.strip()


def optional_text(data: dict[str, Any], *keys: str, default: str = "") -> str:
    value = first_value(data, *keys, default=default)
    return str(value).strip() if value is not None else default


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def parse_iso_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{field_name} must use YYYY-MM-DD format: {value}") from exc


def format_date_range(start: date, end: date) -> str:
    if start.year == end.year and start.month == end.month:
        return f"{start.day}–{end.day} {start.strftime('%B %Y')}"
    if start.year == end.year:
        return f"{start.day} {start.strftime('%B')} – {end.day} {end.strftime('%B %Y')}"
    return f"{start.day} {start.strftime('%B %Y')} – {end.day} {end.strftime('%B %Y')}"


@dataclass(frozen=True)
class Topic:
    eyebrow: str
    title: str
    context: str
    explanation: str
    sentence: str


@dataclass(frozen=True)
class Issue:
    issue_id: str
    year: int
    week: int
    slug: str
    start_date: date
    end_date: date
    title: str
    summary: str
    topics: tuple[Topic, ...]

    @property
    def kw(self) -> str:
        return f"KW {self.week}"

    @property
    def date_range(self) -> str:
        return format_date_range(self.start_date, self.end_date)

    @property
    def url(self) -> str:
        return f"{SITE_URL}/mygermanfreund/german-buzz/{self.slug}/"


def normalize_issue(raw: dict[str, Any]) -> Issue:
    if not isinstance(raw, dict):
        raise ValidationError("The JSON root must be an object.")

    issue_id = require_text(raw, "id", "issue_id", "issueId")
    match = re.fullmatch(r"(\d{4})-W(\d{2})", issue_id)
    if not match:
        raise ValidationError("Issue id must use YYYY-W## format, for example 2026-W31.")

    year = int(match.group(1))
    week = int(match.group(2))
    if not 1 <= week <= 53:
        raise ValidationError(f"Invalid calendar week: {week}")

    start_raw = optional_text(raw, "start_date", "startDate", "week_start", "weekStart")
    end_raw = optional_text(raw, "end_date", "endDate", "week_end", "weekEnd")
    if start_raw and end_raw:
        start_date = parse_iso_date(start_raw, "start_date")
        end_date = parse_iso_date(end_raw, "end_date")
    else:
        start_date = date.fromisocalendar(year, week, 1)
        end_date = date.fromisocalendar(year, week, 7)

    if end_date < start_date:
        raise ValidationError("end_date cannot be earlier than start_date.")

    title = require_text(raw, "title", "headline", "web_title", "webTitle")
    summary = require_text(raw, "summary", "description", "intro", "web_summary", "webSummary")

    topics_raw = first_value(raw, "topics", "items", "sections")
    if not isinstance(topics_raw, list) or not topics_raw:
        raise ValidationError("topics must be a non-empty array.")

    topics: list[Topic] = []
    for index, topic_raw in enumerate(topics_raw, start=1):
        if not isinstance(topic_raw, dict):
            raise ValidationError(f"Topic {index} must be an object.")
        eyebrow = require_text(topic_raw, "eyebrow", "german_title", "germanTitle", "topic", "name")
        topic_title = require_text(topic_raw, "title", "english_title", "englishTitle", "heading")
        context = require_text(topic_raw, "context", "english_context", "englishContext", "why_it_matters", "whyItMatters")
        explanation = require_text(topic_raw, "explanation", "german_explanation", "germanExplanation", "worum_geht_es", "worumGehtEs", "body")
        sentence = require_text(topic_raw, "sentence", "conversation_sentence", "conversationSentence", "starter", "phrase")
        topics.append(Topic(eyebrow, topic_title, context, explanation, sentence))

    return Issue(
        issue_id=issue_id,
        year=year,
        week=week,
        slug=f"kw-{week}",
        start_date=start_date,
        end_date=end_date,
        title=title,
        summary=summary,
        topics=tuple(topics),
    )


def render_topic(topic: Topic) -> str:
    return (
        '        <section class="topic-card">'
        f'<p class="eyebrow">{escape(topic.eyebrow)}</p>'
        f'<h2>{escape(topic.title)}</h2>'
        f'<p>{escape(topic.context)}</p>'
        '<h3>Worum geht es?</h3>'
        f'<p>{escape(topic.explanation)}</p>'
        f'<p><strong>Satz zum Thema:</strong> {escape(topic.sentence)}</p>'
        '</section>'
    )


def render_issue(issue: Issue) -> str:
    topics_html = "\n".join(render_topic(topic) for topic in issue.topics)
    published = datetime.now().astimezone().isoformat(timespec="seconds")
    structured = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": issue.title,
        "description": issue.summary,
        "datePublished": published,
        "dateModified": published,
        "mainEntityOfPage": issue.url,
        "author": {"@type": "Organization", "name": "Athirikya"},
        "publisher": {"@type": "Organization", "name": "Athirikya", "url": f"{SITE_URL}/"},
        "isPartOf": {"@type": "CreativeWorkSeries", "name": "German Buzz"},
    }
    structured_json = json.dumps(structured, ensure_ascii=False, separators=(",", ":"))
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(issue.title)} | {escape(issue.kw)}</title>
  <meta name="description" content="{escape(issue.summary)}">
  <link rel="canonical" href="{issue.url}">
  <meta name="robots" content="index,follow">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{escape(issue.title)} | {escape(issue.kw)}">
  <meta property="og:description" content="{escape(issue.summary)}">
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
  <header class="site-header"><a class="brand" href="../../../index.html" aria-label="Athirikya home"><img src="../../../assets/athirikya-logo.png" alt="Athirikya"></a><nav class="nav" aria-label="Main navigation"><a href="../../../index.html">Home</a><a href="../">German Buzz</a><a href="../../../mygermanfreund.html">MyGermanFreund</a></nav></header>
  <main class="content-page">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../../../index.html">Athirikya</a> / <a href="../">German Buzz</a> / {escape(issue.kw)}</nav>
    <article>
      <header class="content-hero issue-intro"><div class="issue-meta"><span>{escape(issue.kw)}</span><span>{escape(issue.date_range)}</span></div><h1>{escape(issue.title)}</h1><p class="content-lead">{escape(issue.summary)}</p></header>
      <div class="topic-grid">
{topics_html}
      </div>
      <section class="issue-cta"><h2>Continue learning with MyGermanFreund</h2><p>German Buzz in MyGermanFreund adds guided dialogues and weekly conversation practice so you can use these topics more confidently in real life.</p><a class="button primary" href="../../../mygermanfreund.html">Explore MyGermanFreund</a></section>
    </article>
  </main>
  <footer class="site-footer"><div><img src="../../../assets/athirikya-logo.png" alt="Athirikya"></div><nav aria-label="Footer navigation"><a href="../../../privacy.html">Privacy</a><a href="../../../terms.html">Terms</a><a href="../../../impressum.html">Impressum</a><a href="../../../contact.html">Contact</a></nav><p>© 2026 Athirikya. All rights reserved.</p></footer>
</body>
</html>
'''


def render_issue_card(issue: Issue) -> str:
    return (
        f'      <article class="issue-card" data-issue-id="{escape(issue.issue_id)}">\n'
        f'        <div class="issue-meta"><span>{escape(issue.kw)}</span><span>{escape(issue.date_range)}</span></div>\n'
        f'        <h2>{escape(issue.title)}</h2>\n'
        f'        <p>{escape(issue.summary)}</p>\n'
        f'        <a class="text-link text-link-cta" href="{escape(issue.slug)}/">Read German Buzz {escape(issue.kw)} <span aria-hidden="true">→</span></a>\n'
        '      </article>'
    )


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
        cards = [new_card] + re.findall(r'<article class="issue-card".*?</article>', managed, flags=re.DOTALL)
        block = "\n" + "\n".join(cards) + "\n    "
        return before + START_MARKER + block + END_MARKER + after

    section_match = re.search(r'(<section class="issue-list".*?>.*?<h2[^>]*>.*?</h2>)(.*?)(</section>)', content, re.DOTALL)
    if not section_match:
        raise ValidationError(f"Could not locate issue-list section in {LANDING_PAGE}.")
    prefix, existing, suffix = section_match.groups()
    managed = f"\n    {START_MARKER}\n{new_card}\n    {existing.strip()}\n    {END_MARKER}\n    "
    return content[: section_match.start()] + prefix + managed + suffix + content[section_match.end() :]


def update_sitemap(content: str, issue: Issue) -> str:
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    root = ET.fromstring(content)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    existing_urls = {
        node.find("sm:loc", namespace).text
        for node in root.findall("sm:url", namespace)
        if node.find("sm:loc", namespace) is not None
    }
    if issue.url not in existing_urls:
        url_node = ET.SubElement(root, "{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        ET.SubElement(url_node, "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text = issue.url
        ET.SubElement(url_node, "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod").text = date.today().isoformat()
        ET.SubElement(url_node, "{http://www.sitemaps.org/schemas/sitemap/0.9}changefreq").text = "never"
        ET.SubElement(url_node, "{http://www.sitemaps.org/schemas/sitemap/0.9}priority").text = "0.8"
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def changed(path: Path, new_content: str) -> bool:
    return not path.exists() or path.read_text(encoding="utf-8") != new_content


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a German Buzz HTML issue locally.")
    parser.add_argument("json_file", type=Path, help="Path to the weekly German Buzz JSON file")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Website repository root")
    parser.add_argument("--dry-run", action="store_true", help="Validate and show planned changes without writing")
    parser.add_argument("--force", action="store_true", help="Allow replacing an existing weekly issue page")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    json_path = args.json_file.resolve()
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        issue = normalize_issue(raw)

        landing_path = repo_root / LANDING_PAGE
        sitemap_path = repo_root / SITEMAP
        issue_path = repo_root / ISSUES_DIR / issue.slug / "index.html"

        if not landing_path.exists():
            raise ValidationError(f"Missing landing page: {landing_path}")
        if not sitemap_path.exists():
            raise ValidationError(f"Missing sitemap: {sitemap_path}")
        if issue_path.exists() and not args.force:
            raise ValidationError(f"Issue page already exists: {issue_path}. Use --force only after reviewing the existing page.")

        issue_html = render_issue(issue)
        landing_html = update_landing(landing_path.read_text(encoding="utf-8"), issue)
        sitemap_xml = update_sitemap(sitemap_path.read_text(encoding="utf-8"), issue)

        planned = [
            (issue_path, issue_html),
            (landing_path, landing_html),
            (sitemap_path, sitemap_xml),
        ]
        modifications = [(path, content) for path, content in planned if changed(path, content)]

        print(f"Validated {issue.issue_id}: {len(issue.topics)} topics")
        if not modifications:
            print("No changes required.")
            return 0
        for path, _ in modifications:
            action = "CREATE" if not path.exists() else "UPDATE"
            print(f"{action}: {path.relative_to(repo_root)}")

        if args.dry_run:
            print("Dry run complete. No files were written.")
            return 0

        for path, content in modifications:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        print("Files generated locally. Review them with Git before committing.")
        return 0
    except (OSError, json.JSONDecodeError, ValidationError, ET.ParseError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
