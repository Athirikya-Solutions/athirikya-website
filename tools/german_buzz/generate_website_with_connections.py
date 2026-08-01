#!/usr/bin/env python3
"""Generate German Buzz pages with explicit editorial knowledge connections.

This wrapper uses the normal local generator, then adds curated per-topic links
from topic_connections.json. It performs no automatic matching or web search.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from typing import Any

import generate_website as base

DEFAULT_CONNECTIONS = Path(__file__).with_name("topic_connections.json")


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def find_json_argument(arguments: list[str]) -> Path:
    for argument in arguments:
        if not argument.startswith("-"):
            return Path(argument).resolve()
    raise base.ValidationError("Missing weekly German Buzz JSON file argument.")


def load_connections(issue_id: str) -> dict[str, list[dict[str, Any]]]:
    if not DEFAULT_CONNECTIONS.exists():
        return {}
    raw = json.loads(DEFAULT_CONNECTIONS.read_text(encoding="utf-8"))
    issue_connections = raw.get(issue_id, {})
    if not isinstance(issue_connections, dict):
        raise base.ValidationError(f"Connections for {issue_id} must be an object.")
    return issue_connections


def render_connection(item: dict[str, Any]) -> str:
    label = item.get("label")
    description = item.get("description")
    url = item.get("url")
    item_type = item.get("type", "Related guide")
    if not all(isinstance(value, str) and value.strip() for value in (label, description, url)):
        raise base.ValidationError("Each topic connection needs label, description and url.")

    external = bool(item.get("external"))
    target = ' target="_blank" rel="noopener noreferrer"' if external else ""
    source_note = " <span aria-hidden=\"true\">↗</span>" if external else ""
    return (
        '            <li class="topic-connection">'
        f'<span class="topic-connection-type">{escape(str(item_type))}</span>'
        f'<a href="{escape(url)}"{target}>{escape(label)}{source_note}</a>'
        f'<p>{escape(description)}</p>'
        '</li>'
    )


def main() -> int:
    try:
        json_path = find_json_argument(sys.argv[1:])
        issue_raw = json.loads(json_path.read_text(encoding="utf-8"))
        issue_id = base.require_text(issue_raw, "id")
        connections = load_connections(issue_id)

        original_render_topic = base.render_topic

        def render_topic(topic: base.Topic) -> str:
            topic_html = original_render_topic(topic)
            items = connections.get(topic.title, [])
            if not items:
                return topic_html
            if not isinstance(items, list):
                raise base.ValidationError(f"Connections for topic '{topic.title}' must be an array.")
            rendered = "\n".join(render_connection(item) for item in items[:2])
            block = (
                '\n          <aside class="topic-connections" aria-label="Mehr dazu">'
                '<h3>Mehr dazu</h3>'
                f'<ul>{rendered}</ul>'
                '</aside>'
            )
            return topic_html.replace("\n        </section>", block + "\n        </section>")

        base.render_topic = render_topic
        return base.main()
    except (OSError, json.JSONDecodeError, base.ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
