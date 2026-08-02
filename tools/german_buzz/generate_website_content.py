#!/usr/bin/env python3
"""Generate German Buzz website pages from shared app JSON plus web enrichment.

The weekly app JSON remains unchanged and is the common source for issue metadata
and German topic context. A separate website enrichment JSON supplies English
context and two optional public blocks: interestingFacts and learnMore.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import generate_website as base


class EnrichmentError(base.ValidationError):
    pass


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def require_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnrichmentError(f"{name} must be a non-empty string.")
    return value.strip()


def require_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise EnrichmentError(f"{name} must be true or false.")
    return value


@dataclass(frozen=True)
class InterestingFacts:
    enabled: bool
    de: str | None = None
    en: str | None = None


@dataclass(frozen=True)
class LearnMore:
    enabled: bool
    title: str | None = None
    summary: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class WebTopic:
    title: str
    english_title: str
    english_context: str
    interesting_facts: InterestingFacts
    learn_more: LearnMore


def validate_interesting_facts(raw: Any, name: str) -> InterestingFacts:
    if not isinstance(raw, dict):
        raise EnrichmentError(f"{name} must be an object.")
    enabled = require_bool(raw.get("enabled"), f"{name}.enabled")
    if not enabled:
        return InterestingFacts(enabled=False)
    return InterestingFacts(
        enabled=True,
        de=require_text(raw.get("de"), f"{name}.de"),
        en=require_text(raw.get("en"), f"{name}.en"),
    )


def validate_learn_more(raw: Any, name: str) -> LearnMore:
    if not isinstance(raw, dict):
        raise EnrichmentError(f"{name} must be an object.")
    enabled = require_bool(raw.get("enabled"), f"{name}.enabled")
    if not enabled:
        return LearnMore(enabled=False)
    url = require_text(raw.get("url"), f"{name}.url")
    if not url.startswith("/mygermanfreund/guides/") or not url.endswith("/"):
        raise EnrichmentError(
            f"{name}.url must use /mygermanfreund/guides/<slug>/ format."
        )
    return LearnMore(
        enabled=True,
        title=require_text(raw.get("title"), f"{name}.title"),
        summary=require_text(raw.get("summary"), f"{name}.summary"),
        url=url,
    )


def load_enrichment(path: Path, issue_raw: dict[str, Any]) -> dict[str, WebTopic]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise EnrichmentError("Website enrichment root must be an object.")

    issue_id = base.require_text(issue_raw, "id")
    if require_text(raw.get("issueId"), "issueId") != issue_id:
        raise EnrichmentError("Website enrichment issueId must match weekly JSON id.")

    shared_topics = issue_raw.get("topics")
    if not isinstance(shared_topics, list) or not shared_topics:
        raise EnrichmentError("Weekly JSON topics must be a non-empty array.")
    shared_titles = [base.require_text(item, "title") for item in shared_topics]
    if len(set(shared_titles)) != len(shared_titles):
        raise EnrichmentError("Weekly JSON topic titles must be unique.")

    topics_raw = raw.get("topics")
    if not isinstance(topics_raw, list):
        raise EnrichmentError("Website enrichment topics must be an array.")

    output: dict[str, WebTopic] = {}
    for index, item in enumerate(topics_raw, start=1):
        name = f"Website topic {index}"
        if not isinstance(item, dict):
            raise EnrichmentError(f"{name} must be an object.")
        title = require_text(item.get("title"), f"{name}.title")
        if title not in shared_titles:
            raise EnrichmentError(f"{name} references unknown weekly topic: {title}")
        if title in output:
            raise EnrichmentError(f"Duplicate website enrichment topic: {title}")
        output[title] = WebTopic(
            title=title,
            english_title=require_text(item.get("englishTitle"), f"{name}.englishTitle"),
            english_context=require_text(item.get("englishContext"), f"{name}.englishContext"),
            interesting_facts=validate_interesting_facts(
                item.get("interestingFacts"), f"{name}.interestingFacts"
            ),
            learn_more=validate_learn_more(item.get("learnMore"), f"{name}.learnMore"),
        )

    missing = [title for title in shared_titles if title not in output]
    extra = [title for title in output if title not in shared_titles]
    if missing or extra:
        raise EnrichmentError(
            f"Website enrichment must cover every weekly topic exactly once. "
            f"Missing: {missing or 'none'}; extra: {extra or 'none'}."
        )
    return output


def render_german_facts(facts: InterestingFacts) -> str:
    if not facts.enabled:
        return ""
    return f'''\n          <aside class="topic-facts" aria-label="Interesting to know">
            <h3>Interesting to know</h3>
            <p>{escape(facts.de or "")}</p>
          </aside>'''


def render_english_panel(web: WebTopic) -> str:
    english_fact = ""
    if web.interesting_facts.enabled:
        english_fact = f'''\n              <h4>Interesting to know</h4>
              <p>{escape(web.interesting_facts.en or "")}</p>'''
    return f'''\n          <details class="topic-language-details">
            <summary>English</summary>
            <div lang="en" class="topic-language-content">
              <h3>{escape(web.english_title)}</h3>
              <p>{escape(web.english_context)}</p>{english_fact}
            </div>
          </details>'''


def render_learn_more(item: LearnMore) -> str:
    if not item.enabled:
        return ""
    return f'''\n          <aside class="topic-connections" aria-label="Learn more">
            <h3>Learn more</h3>
            <a class="text-link text-link-cta" href="{escape(item.url or "")}">{escape(item.title or "")} <span aria-hidden="true">→</span></a>
            <p>{escape(item.summary or "")}</p>
          </aside>'''


def render_topic(topic: base.Topic, web: WebTopic) -> str:
    return f'''        <section class="topic-card">
          <h2>{escape(topic.title)}</h2>
          <div lang="de">
            <p>{escape(topic.whats_happening)}</p>
          </div>{render_german_facts(web.interesting_facts)}{render_english_panel(web)}{render_learn_more(web.learn_more)}
        </section>'''


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate German Buzz HTML from weekly app JSON and website enrichment JSON."
    )
    parser.add_argument("weekly_json", type=Path)
    parser.add_argument("website_enrichment", type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        weekly_path = args.weekly_json.resolve()
        issue_raw = json.loads(weekly_path.read_text(encoding="utf-8"))
        base.normalize_issue(issue_raw)
        enrichment = load_enrichment(args.website_enrichment.resolve(), issue_raw)

        original_render_topic = base.render_topic

        def enriched_render_topic(topic: base.Topic) -> str:
            return render_topic(topic, enrichment[topic.title])

        base.render_topic = enriched_render_topic
        forwarded = [str(weekly_path), "--repo-root", str(args.repo_root)]
        if args.dry_run:
            forwarded.append("--dry-run")
        if args.force:
            forwarded.append("--force")
        original_argv = sys.argv
        sys.argv = [original_argv[0], *forwarded]
        try:
            return base.main()
        finally:
            base.render_topic = original_render_topic
            sys.argv = original_argv
    except (OSError, json.JSONDecodeError, base.ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
