"""Ein Abruf fuer alle Entitaeten."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TasksSphereAuthError, TasksSphereClient, TasksSphereError
from .const import DOMAIN, LIST_TYPE_CHECKLIST

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TasksSphereData:
    """Was ein Abrufzyklus zutage foerdert."""

    checklists: list[dict[str, Any]] = field(default_factory=list)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    completed: list[dict[str, Any]] = field(default_factory=list)


class TasksSphereCoordinator(DataUpdateCoordinator[TasksSphereData]):
    """Haelt den Zustand fuer To-do-Listen, Sensoren und Kalender."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: TasksSphereClient,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> TasksSphereData:
        try:
            lists = await self.client.async_get_task_lists()

            # Die Uebersicht liefert die Eintraege nicht mit, deshalb je
            # Checkliste ein weiterer Abruf. Im Haushaltsmassstab sind das eine
            # Handvoll Anfragen; bei sehr vielen Listen waere ein Sammelendpunkt
            # in TasksSphere die bessere Antwort.
            checklists: list[dict[str, Any]] = []
            for task_list in lists:
                if task_list.get("type") != LIST_TYPE_CHECKLIST:
                    continue
                checklists.append(await self.client.async_get_task_list(task_list["id"]))

            return TasksSphereData(
                checklists=checklists,
                tasks=await self.client.async_get_tasks(),
                completed=await self.client.async_get_completed(),
            )
        except TasksSphereAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except TasksSphereError as err:
            raise UpdateFailed(str(err)) from err
