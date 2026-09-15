"""Zaehler fuer Automationen und Wandtafeln."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import TasksSphereConfigEntry
from .coordinator import TasksSphereCoordinator, TasksSphereData
from .entity import TasksSphereEntity
from .util import parse_datetime


def _overdue(data: TasksSphereData) -> int:
    now = dt_util.now()
    return sum(
        1
        for task in data.tasks
        if (due := parse_datetime(task.get("due_at"))) is not None and due < now
    )


def _due_today(data: TasksSphereData) -> int:
    today = dt_util.now().date()
    return sum(
        1
        for task in data.tasks
        if (due := parse_datetime(task.get("due_at"))) is not None
        and due.date() == today
    )


def _completed_today(data: TasksSphereData) -> int:
    today = dt_util.now().date()
    return sum(
        1
        for completion in data.completed
        if (done := parse_datetime(completion.get("completed_at"))) is not None
        and done.date() == today
    )


@dataclass(frozen=True, kw_only=True)
class TasksSphereSensorDescription(SensorEntityDescription):
    """Beschreibt einen Zaehler samt seiner Rechenvorschrift."""

    value_fn: Callable[[TasksSphereData], int]


SENSORS: tuple[TasksSphereSensorDescription, ...] = (
    TasksSphereSensorDescription(
        key="overdue",
        translation_key="overdue",
        icon="mdi:alert-circle-outline",
        native_unit_of_measurement="Aufgaben",
        value_fn=_overdue,
    ),
    TasksSphereSensorDescription(
        key="due_today",
        translation_key="due_today",
        icon="mdi:calendar-today",
        native_unit_of_measurement="Aufgaben",
        value_fn=_due_today,
    ),
    TasksSphereSensorDescription(
        key="completed_today",
        translation_key="completed_today",
        icon="mdi:check-circle-outline",
        native_unit_of_measurement="Aufgaben",
        value_fn=_completed_today,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TasksSphereConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        TasksSphereSensor(coordinator, description) for description in SENSORS
    )


class TasksSphereSensor(TasksSphereEntity, SensorEntity):
    """Ein einzelner Zaehler."""

    entity_description: TasksSphereSensorDescription

    def __init__(
        self,
        coordinator: TasksSphereCoordinator,
        description: TasksSphereSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{description.key}"
        )

    @property
    def native_value(self) -> int:
        return self.entity_description.value_fn(self.coordinator.data)
