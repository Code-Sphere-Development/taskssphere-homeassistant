"""Termine als Kalender.

Fragt nicht den Koordinator, sondern die API direkt: Home Assistant gibt beim
Aufruf ein Zeitfenster vor, und genau dafuer gibt es
GET /api/tasks/occurrences - Wiederholungen bereits aufgeloest.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import TasksSphereConfigEntry
from .api import TasksSphereError
from .coordinator import TasksSphereCoordinator
from .entity import TasksSphereEntity
from .util import parse_datetime

# Wie lange ein Termin im Kalender dauert. Aufgaben haben keine Dauer, aber ein
# Kalendereintrag braucht ein Ende.
EVENT_DURATION = timedelta(minutes=30)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TasksSphereConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([TasksSphereCalendar(entry.runtime_data)])


class TasksSphereCalendar(TasksSphereEntity, CalendarEntity):
    """Faellige Termine als Kalender."""

    def __init__(self, coordinator: TasksSphereCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = "Termine"
        self._attr_translation_key = "occurrences"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_calendar"

    @property
    def event(self) -> CalendarEvent | None:
        """Der naechste faellige Termin.

        Aus dem Bestand des Koordinators, damit die Eigenschaft ohne Netzzugriff
        auskommt - Home Assistant fragt sie bei jeder Zustandsaktualisierung ab.
        """
        now = dt_util.now()
        upcoming = sorted(
            (
                (due, task)
                for task in self.coordinator.data.tasks
                if (due := parse_datetime(task.get("due_at"))) is not None
                and due >= now
            ),
            key=lambda pair: pair[0],
        )

        if not upcoming:
            return None

        due, task = upcoming[0]
        return self._to_event(task.get("title", ""), task.get("description"), due)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        try:
            occurrences = await self.coordinator.client.async_get_occurrences(
                start_date, end_date
            )
        except TasksSphereError as err:
            raise HomeAssistantError(str(err)) from err

        events: list[CalendarEvent] = []
        for occurrence in occurrences:
            if occurrence.get("is_completed"):
                continue

            planned_at = parse_datetime(occurrence.get("planned_at"))
            if planned_at is None:
                continue

            task = occurrence.get("task") or {}
            events.append(
                self._to_event(
                    task.get("title", ""), task.get("description"), planned_at
                )
            )

        return events

    @staticmethod
    def _to_event(
        summary: str, description: str | None, start: datetime
    ) -> CalendarEvent:
        return CalendarEvent(
            summary=summary,
            description=description,
            start=start,
            end=start + EVENT_DURATION,
        )
