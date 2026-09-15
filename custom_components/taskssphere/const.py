"""Konstanten der TasksSphere-Integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "taskssphere"

CONF_BASE_URL: Final = "base_url"
CONF_TOKEN: Final = "token"
CONF_SCAN_INTERVAL_MINUTES: Final = "scan_interval_minutes"

DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=5)
MIN_SCAN_INTERVAL_MINUTES: Final = 1
MAX_SCAN_INTERVAL_MINUTES: Final = 120

# Der Listentyp entscheidet, wie eine Liste in Home Assistant erscheint:
# Checklisten kennen keine Faelligkeit, Aufgabenlisten schon.
LIST_TYPE_CHECKLIST: Final = "checklist"
LIST_TYPE_TASKS: Final = "tasks"
