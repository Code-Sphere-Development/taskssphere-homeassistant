"""Gemeinsame Grundlage aller Entitaeten."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BASE_URL, DOMAIN
from .coordinator import TasksSphereCoordinator


class TasksSphereEntity(CoordinatorEntity[TasksSphereCoordinator]):
    """Haengt alle Entitaeten an ein gemeinsames Geraet."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TasksSphereCoordinator) -> None:
        super().__init__(coordinator)

        entry = coordinator.config_entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            entry_type=DeviceEntryType.SERVICE,
            name=entry.title,
            manufacturer="Code-Sphere",
            model="TasksSphere",
            configuration_url=entry.data.get(CONF_BASE_URL),
        )
