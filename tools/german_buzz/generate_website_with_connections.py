#!/usr/bin/env python3
"""Generate German Buzz pages with editorial links into Life Areas.

The weekly German Buzz JSON remains focused on current topics. Knowledge Units
are maintained separately in tools/life_areas/knowledge_units.json and provide
the single source of truth for each topic's Life Area destination.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from typing import Any

import generate_website as base

KNOWLEDGE_UNITS_FILE = Path(__file__).parents[1] / "life_areas" / "knowledge_units.json"


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def find_json_argument(arguments: list[str]) -> Path:
    for argument in arguments:
        if not argument.startswith("-"):
            return Path(argument).resolve()
    raise base.ValidationError("Missing weekly German Buzz JSON file argument.")


def require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise base.ValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def load_topic_destinations(issue_id: str) -> dict[str, dict[str, str]]:
    if not KNOWLEDGE_UNITS_FILE.exists():
        raise base.ValidationError(
            f"Knowledge Unit source not found: {KNOWLEDGE_UNITS_FILE}"
        )

    raw = json.loads(KNOWLEDGE_UNITS_FILE.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise base.ValidationError("knowledge_units.json must contain an array.")

    destinations: dict[str, dict[str, str]] = {}
    for unit_index, unit in enumerate(raw, start=1):
        if not isinstance(unit, dict):
            raise base.ValidationError(f"Knowledge Unit {unit_index} must be an object.")

        unit_id = require_text(unit.get("id"), f"Knowledge Unit {unit_index} id")
        life_area = require_text(
            unit.get("lifeArea"), f"Knowledge Unit {unit_index} lifeArea"
        )
        title = require_text(unit.get("title"), f"Knowledge Unit {unit_index} title")
        summary = require_text(
            unit.get("summary"), f"Knowledge Unit {unit_index} summary"
        )
        experiences = unit.get("experiences", [])
        if not isinstance(experiences, list):
            raise base.ValidationError(
                f"Knowledge Unit {unit_index} experiences must be an array."
            )

        for experience_index, experience in enumerate(experiences, start=1):
            if not isinstance(experience, dict):
                raise base.ValidationError(
                    f"Knowledge Unit {unit_index} experience {experience_index} must be an object."
                )
            experience_issue = require_text(
                experience.get("issueId"),
                f"Knowledge Unit {unit_index} experience {experience_index} issueId",
            )
            if experience_issue != issue_id:
                continue

            topic = require_text(
                experience.get("topic"),
                f"Knowledge Unit {unit_index} experience {experience_index} topic",
            )
            if topic in destinations:
                raise base.ValidationError(
                    f"Topic '{topic}' in {issue_id} is assigned to more than one Knowledge Unit."
                )

            destinations[topic] = {
                "type": "Mehr dazu",
                "label": title,
                "description": summary,
                "url": f"/mygermanfreund/life-areas/{life_area}/#{unit_id}",
            }

    return destinations


def render_connection(item: dict[str, str]) -> str:
    return (
        '            <li class="topic-connection">'
        f'<span class="topic-connection-type">{escape(item["type"])}</span>'
        f'<a href="{escape(item["url"])}">{escape(item["label"])}</a>'
        f'<p>{escape(item["description"])}</p>'
        '</li>'
    )


def main() -> int:
    try:
        json_path = find_json_argument(sys.argv[1:])
        issue_raw = json.loads(json_path.read_text(encoding="utf-8"))
        issue_id = base.require_text(issue_raw, "id")
        destinations = load_topic_destinations(issue_id)

        original_render_topic = base.render_topic

        def render_topic(topic: base.Topic) -> str:
            topic_html = original_render_topic(topic)
            destination = destinations.get(topic.title)
            if destination is None:
                return topic_html

            block = (
                '\n          <aside class="topic-connections" aria-label="Mehr dazu">'
                '<h3>Mehr dazu</h3>'
                f'<ul>{render_connection(destination)}</ul>'
                '</aside>'
            )
            return topic_html.replace(
                "\n        </section>", block + "\n        </section>"
            )

        base.render_topic = render_topic
        return base.main()
    except (OSError, json.JSONDecodeError, base.ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
