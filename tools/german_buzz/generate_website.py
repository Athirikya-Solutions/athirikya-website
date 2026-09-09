#!/usr/bin/env python3
"""Generate a German Buzz website issue from the canonical app JSON and optional website enrichment."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SITE_URL = "https://athirikya.com"
ISSUES_DIR = Path("mygermanfreund/german-buzz")
LANDING_PAGE = ISSUES_DIR / "index.html"
SITEMAP = Path("sitemap.xml")
START_MARKER = "<!-- GERMAN_BUZZ_ISSUES_START -->"
END_MARKER = "<!-- GERMAN_BUZZ_ISSUES_END -->"


class ValidationError(ValueError):
    pass


def require_text(data: dict[str, Any], key: str, context: str = "") -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        prefix = f"{context}: " if context else ""
        raise ValidationError(f"{prefix}missing required text field: {key}")
    return value.strip()


def escape(value: str) -> str:
    return html.escape(value, quote=True)


@dataclass(frozen=True)
class Guide:
    title: str
    summary: str
    url: str


@dataclass(frozen=True)
class Enrichment:
    english_title: str
    english_context: str
    fact_de: str | None
    fact_en: str | None
    guides: tuple[Guide, ...]


@dataclass(frozen=True)
class Topic:
    title: str
    whats_happening: str
    sentence: str
    enrichment: Enrichment | None = None


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
    def display_date_range(self) -> str:
        return self.date_range if re.search(r"\b\d{4}\b", self.date_range) else f"{self.date_range} {self.year}"

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
    year, week = int(match.group(1)), int(match.group(2))
    if not 1 <= week <= 53 or raw.get("year") != year or raw.get("weekNumber") != week:
        raise ValidationError("year and weekNumber must match a valid id field.")
    topics_raw = raw.get("topics")
    if not isinstance(topics_raw, list) or len(topics_raw) != 4:
        raise ValidationError("topics must contain exactly four items.")
    topics = tuple(
        Topic(
            title=require_text(item, "title", f"Topic {index}"),
            whats_happening=require_text(item, "whatsHappening", f"Topic {index}"),
            sentence=require_text(item, "germanContext", f"Topic {index}"),
        )
        for index, item in enumerate(topics_raw, 1)
        if isinstance(item, dict)
    )
    if len(topics) != 4:
        raise ValidationError("Each topic must be an object.")
    return Issue(issue_id, year, week, require_text(raw, "dateRange"), require_text(raw, "tagline"),
                 require_text(raw, "weeklySummary"), topics)


def load_enrichment(path: Path, issue: Issue) -> dict[str, Enrichment]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValidationError(f"Missing website enrichment: {path}")
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid website enrichment JSON: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("issueId") != issue.issue_id:
        raise ValidationError("website enrichment issueId must match the app issue id.")
    entries = raw.get("topics")
    if not isinstance(entries, list) or len(entries) != 4:
        raise ValidationError("website enrichment must contain exactly four topics.")
    expected = {topic.title for topic in issue.topics}
    result: dict[str, Enrichment] = {}
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            raise ValidationError(f"Website topic {index} must be an object.")
        title = require_text(entry, "title", f"Website topic {index}")
        if title not in expected or title in result:
            raise ValidationError(f"Website topic titles must match the app topics exactly: {title}")
        facts = entry.get("interestingFacts")
        if not isinstance(facts, dict) or not isinstance(facts.get("enabled"), bool):
            raise ValidationError(f"Website topic {index}: interestingFacts.enabled must be boolean.")
        enabled = facts["enabled"]
        fact_de = require_text(facts, "de", f"Website topic {index} fact") if enabled else None
        fact_en = require_text(facts, "en", f"Website topic {index} fact") if enabled else None
        guides_raw = entry.get("guides")
        if not isinstance(guides_raw, list):
            raise ValidationError(f"Website topic {index}: guides must be an array.")
        urls: set[str] = set()
        guides: list[Guide] = []
        for guide_index, guide in enumerate(guides_raw, 1):
            if not isinstance(guide, dict):
                raise ValidationError(f"Website topic {index} guide {guide_index} must be an object.")
            url = require_text(guide, "url", f"Website topic {index} guide {guide_index}")
            if url in urls:
                raise ValidationError(f"Website topic {index}: duplicate guide URL {url}")
            urls.add(url)
            guides.append(Guide(require_text(guide, "title", f"Website topic {index} guide {guide_index}"),
                                require_text(guide, "summary", f"Website topic {index} guide {guide_index}"), url))
        result[title] = Enrichment(require_text(entry, "englishTitle", f"Website topic {index}"),
                                   require_text(entry, "englishContext", f"Website topic {index}"),
                                   fact_de, fact_en, tuple(guides))
    if set(result) != expected:
        raise ValidationError("Website enrichment must cover every app topic exactly once.")
    return result


def with_enrichment(issue: Issue, enrichment: dict[str, Enrichment] | None) -> Issue:
    if enrichment is None:
        return issue
    return Issue(issue.issue_id, issue.year, issue.week, issue.date_range, issue.tagline, issue.weekly_summary,
                 tuple(Topic(t.title, t.whats_happening, t.sentence, enrichment[t.title]) for t in issue.topics))


def render_topic(topic: Topic) -> str:
    extra = ""
    if topic.enrichment:
        e = topic.enrichment
        german_fact = f"<p><strong>Interesting to know:</strong> {escape(e.fact_de or '')}</p>" if e.fact_de else ""
        english_fact = f"<p><strong>Interesting to know:</strong> {escape(e.fact_en or '')}</p>" if e.fact_en else ""
        guides = "".join(f'<li><a href="{escape(g.url)}">{escape(g.title)}</a> — {escape(g.summary)}</li>' for g in e.guides)
        guide_block = f"<h3>More information</h3><ul>{guides}</ul>" if guides else ""
        extra = f"""
          {german_fact}
          <details class="topic-extra">
            <summary>English context</summary>
            <h3>{escape(e.english_title)}</h3>
            <p>{escape(e.english_context)}</p>
            {english_fact}
            {guide_block}
          </details>"""
    return f"""        <section class="topic-card">
          <h2>{escape(topic.title)}</h2>
          <h3>Worum geht es?</h3>
          <p>{escape(topic.whats_happening)}</p>
          <p><strong>Satz zum Thema:</strong> {escape(topic.sentence)}</p>{extra}
        </section>"""


def render_issue(issue: Issue) -> str:
    topics_html = "\n".join(render_topic(topic) for topic in issue.topics)
    description = f"German Buzz {issue.kw} ({issue.display_date_range}): {issue.weekly_summary}."
    structured = json.dumps({"@context":"https://schema.org","@type":"Article","headline":f"German Buzz {issue.kw}","description":description,"mainEntityOfPage":issue.url,"author":{"@type":"Organization","name":"Athirikya"},"publisher":{"@type":"Organization","name":"Athirikya","url":f"{SITE_URL}/"},"isPartOf":{"@type":"CreativeWorkSeries","name":"German Buzz"}}, ensure_ascii=False, separators=(",",":"))
    return f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>German Buzz {escape(issue.kw)} | MyGermanFreund</title><meta name="description" content="{escape(description)}"><link rel="canonical" href="{issue.url}">
<link rel="icon" href="../../../assets/athirikya-logo.png?v=6" type="image/png"><link rel="stylesheet" href="../../../styles.css"><link rel="stylesheet" href="../../../soothing.css"><link rel="stylesheet" href="../../../seo-content.css"><link rel="stylesheet" href="../../../humanized.css"><script type="application/ld+json">{structured}</script></head>
<body><header class="site-header"><a class="brand" href="../../../index.html" aria-label="Athirikya home"><img src="../../../assets/athirikya-wordmark.png" alt="Athirikya"></a><nav class="nav" aria-label="Main navigation"><a href="../../../index.html">Home</a><a href="../">German Buzz</a><a href="../../../mygermanfreund.html">MyGermanFreund</a></nav></header>
<main class="content-page"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../../../index.html">Athirikya</a> / <a href="../">German Buzz</a> / {escape(issue.kw)}</nav><article><header class="content-hero issue-intro"><div class="issue-meta"><span>{escape(issue.kw)}</span><span>{escape(issue.display_date_range)}</span></div><h1>German Buzz</h1><p class="content-lead">{escape(issue.tagline)}</p><p>{escape(issue.weekly_summary)}</p></header><div class="topic-grid">
{topics_html}
</div><section class="issue-cta"><h2>Continue learning with MyGermanFreund</h2><p>The app adds guided dialogues, useful words and practical weekly conversation support.</p><a class="button primary" href="../../../mygermanfreund.html">Explore MyGermanFreund</a></section></article></main><footer class="site-footer"><div><img src="../../../assets/athirikya-wordmark.png" alt="Athirikya"></div><nav aria-label="Footer navigation"><a href="../../../privacy.html">Privacy</a><a href="../../../terms.html">Terms</a><a href="../../../impressum.html">Impressum</a><a href="../../../contact.html">Contact</a></nav><p>© 2026 Athirikya. All rights reserved.</p></footer></body></html>
"""


def render_issue_card(issue: Issue) -> str:
    return f'''      <article class="issue-card" data-issue-id="{escape(issue.issue_id)}">
        <div class="issue-meta"><span>{escape(issue.kw)}</span><span>{escape(issue.display_date_range)}</span></div>
        <h2>{escape(issue.weekly_summary)}</h2><p>{escape(issue.tagline)}</p>
        <a class="text-link text-link-cta" href="{escape(issue.slug)}/">Read German Buzz {escape(issue.kw)} <span aria-hidden="true">→</span></a>
      </article>'''


def update_landing(content: str, issue: Issue) -> str:
    content = content.replace(">Available web issue</h2>", ">Available web issues</h2>", 1)
    card = render_issue_card(issue)
    if START_MARKER in content and END_MARKER in content:
        before, remainder = content.split(START_MARKER, 1)
        managed, after = remainder.split(END_MARKER, 1)
        managed = re.sub(rf'\s*<article class="issue-card" data-issue-id="{re.escape(issue.issue_id)}">.*?</article>', "", managed, flags=re.DOTALL)
        cards = re.findall(r'<article class="issue-card".*?</article>', managed, flags=re.DOTALL)
        return before + START_MARKER + "\n" + "\n".join([card, *cards]) + "\n      " + END_MARKER + after
    match = re.search(r'(<section class="issue-list"[^>]*>\s*<h2[^>]*>.*?</h2>)(.*?)(</section>)', content, re.DOTALL)
    if not match:
        raise ValidationError(f"Could not locate issue-list section in {LANDING_PAGE}.")
    cards = re.findall(r'<article class="issue-card".*?</article>', match.group(2), flags=re.DOTALL)
    managed = "\n      " + START_MARKER + "\n" + "\n".join([card, *cards]) + "\n      " + END_MARKER + "\n    "
    return content[:match.start()] + match.group(1) + managed + match.group(3) + content[match.end():]


def update_sitemap(content: str, issue: Issue) -> str:
    if issue.url in content:
        return content
    if "</urlset>" not in content:
        raise ValidationError(f"Could not locate closing urlset tag in {SITEMAP}.")
    return content.replace("</urlset>", f"  <url>\n    <loc>{issue.url}</loc>\n    <changefreq>never</changefreq>\n    <priority>0.8</priority>\n  </url>\n</urlset>", 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a German Buzz website issue.")
    parser.add_argument("json_file", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--enrichment-file", type=Path)
    parser.add_argument("--require-enrichment", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        root = args.repo_root.resolve()
        issue = normalize_issue(json.loads(args.json_file.resolve().read_text(encoding="utf-8")))
        enrichment_path = args.enrichment_file or root / "tools/german_buzz/web_enrichment" / f"{issue.issue_id}.web.json"
        enrichment = load_enrichment(enrichment_path, issue) if enrichment_path.exists() or args.require_enrichment else None
        if args.require_enrichment and enrichment is None:
            raise ValidationError(f"Missing website enrichment: {enrichment_path}")
        issue = with_enrichment(issue, enrichment)
        issue_path, landing_path, sitemap_path = root / ISSUES_DIR / issue.slug / "index.html", root / LANDING_PAGE, root / SITEMAP
        if not landing_path.exists() or not sitemap_path.exists():
            raise ValidationError("Missing German Buzz landing page or sitemap.")
        if issue_path.exists() and not args.force:
            raise ValidationError(f"Issue already exists: {issue_path}. Use --force only after review.")
        outputs = [(issue_path, render_issue(issue)), (landing_path, update_landing(landing_path.read_text(encoding="utf-8"), issue)), (sitemap_path, update_sitemap(sitemap_path.read_text(encoding="utf-8"), issue))]
        for path, _ in outputs: print(f"{'WOULD WRITE' if args.dry_run else 'WRITE'}: {path}")
        if not args.dry_run:
            for path, value in outputs:
                path.parent.mkdir(parents=True, exist_ok=True); path.write_text(value, encoding="utf-8")
            print("Generation complete. Review with git status and git diff before committing.")
        return 0
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
