#!/usr/bin/env python3
"""Generate German Buzz pages with curated context-aware resources.

This wrapper keeps the canonical app JSON unchanged. It reuses the existing
website generator and adds recommendations from recommendations.json.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path
from typing import Any

import generate_website as base

RULES_PATH = Path(__file__).with_name("recommendations.json")
MAX_RESOURCES_PER_TOPIC = 2


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _load_rules() -> list[dict[str, Any]]:
    if not RULES_PATH.exists():
        return []
    raw = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    rules = raw.get("rules") if isinstance(raw, dict) else None
    if not isinstance(rules, list):
        raise base.ValidationError("recommendations.json must contain a rules array.")
    return rules


RULES = _load_rules()


def _match_resources(topic: base.Topic) -> list[dict[str, str]]:
    haystack = _normalise(f"{topic.title} {topic.whats_happening}")
    matches: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for rule in RULES:
        if not isinstance(rule, dict):
            continue
        keywords = rule.get("keywords", [])
        resources = rule.get("resources", [])
        if not isinstance(keywords, list) or not isinstance(resources, list):
            continue
        if not any(_normalise(str(keyword)) in haystack for keyword in keywords):
            continue

        for resource in resources:
            if not isinstance(resource, dict):
                continue
            required = ("title", "description", "url", "source")
            if not all(isinstance(resource.get(key), str) and resource[key].strip() for key in required):
                continue
            url = resource["url"].strip()
            if not url.startswith("https://") or url in seen_urls:
                continue
            matches.append({key: resource[key].strip() for key in required})
            seen_urls.add(url)
            if len(matches) >= MAX_RESOURCES_PER_TOPIC:
                return matches

    return matches


def _render_resources(resources: list[dict[str, str]]) -> str:
    if not resources:
        return ""

    items = "\n".join(
        f'''            <li>
              <a href="{_escape(resource['url'])}" target="_blank" rel="noopener noreferrer">{_escape(resource['title'])} <span aria-hidden="true">↗</span></a>
              <p>{_escape(resource['description'])}</p>
              <small>Source: {_escape(resource['source'])}</small>
            </li>'''
        for resource in resources
    )

    return f'''\n          <aside class="topic-resources" aria-label="Helpful resources for this topic">
            <h3>Helpful resources for this topic</h3>
            <ul>
{items}
            </ul>
          </aside>'''


def render_topic_with_recommendations(topic: base.Topic) -> str:
    resources = _match_resources(topic)
    return f'''        <section class="topic-card">
          <h2>{_escape(topic.title)}</h2>
          <h3>Worum geht es?</h3>
          <p>{_escape(topic.whats_happening)}</p>
          <p><strong>Satz zum Thema:</strong> {_escape(topic.sentence)}</p>{_render_resources(resources)}
        </section>'''


def main() -> int:
    base.render_topic = render_topic_with_recommendations
    matched_topics: list[str] = []
    original_normalize = base.normalize_issue

    def normalize_with_report(raw: dict[str, Any]) -> base.Issue:
        issue = original_normalize(raw)
        matched_topics.extend(topic.title for topic in issue.topics if _match_resources(topic))
        return issue

    base.normalize_issue = normalize_with_report
    result = base.main()
    if result == 0:
        print(f"Recommendation matches: {len(matched_topics)} topic(s).")
        for title in matched_topics:
            print(f"  - {title}")
    return result


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, base.ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
