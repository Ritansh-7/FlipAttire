from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EVENTS_PATH = Path("data/events/events.jsonl")


def append_event(payload: dict[str, Any]) -> None:
    """Append an event to the local durable event log used by both UIs.

    Kafka remains the production transport when configured; this JSONL mirror
    keeps the local admin console live even when Kafka is not running.
    """
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def read_events(limit: int = 5000) -> list[dict[str, Any]]:
    if not EVENTS_PATH.exists():
        return []
    try:
        lines = EVENTS_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    events: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events
