"""Kleine Helfer, die mehrere Plattformen brauchen."""

from __future__ import annotations

from datetime import date, datetime

from homeassistant.util import dt as dt_util

# TasksSphere serialisiert Zeitpunkte als "Y-m-d H:i:s" ohne Zonenangabe
# (App\Models\Task::serializeDate). Der Wert ist Wanduhrzeit in der Zeitzone der
# Aufgabe. Ohne Marker im String bleibt nur, ihn in der Zeitzone von Home
# Assistant zu verankern - im Haushalt ist das dieselbe.
_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S")


def parse_datetime(value: str | None) -> datetime | None:
    """Einen Zeitpunkt der API in eine zonenbehaftete datetime wandeln."""
    if not value:
        return None

    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        for fmt in _FORMATS:
            try:
                parsed = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue

    if parsed is None:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)

    return parsed


def to_api_datetime(value: datetime | date | None) -> str | None:
    """Einen Zeitpunkt in der Schreibweise abliefern, die die API erwartet."""
    if value is None:
        return None

    if isinstance(value, datetime):
        local = dt_util.as_local(value) if value.tzinfo else value
        return local.strftime("%Y-%m-%d %H:%M:%S")

    return f"{value.isoformat()} 00:00:00"
