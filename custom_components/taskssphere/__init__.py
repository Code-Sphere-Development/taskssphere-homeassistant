"""Die TasksSphere-Integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TasksSphereClient
from .const import (
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_TOKEN,
    DEFAULT_SCAN_INTERVAL,
)
from .coordinator import TasksSphereCoordinator

PLATFORMS: list[Platform] = [Platform.TODO, Platform.SENSOR, Platform.CALENDAR]

type TasksSphereConfigEntry = ConfigEntry[TasksSphereCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: TasksSphereConfigEntry
) -> bool:
    """Einen eingerichteten Eintrag hochfahren."""
    client = TasksSphereClient(
        session=async_get_clientsession(hass),
        base_url=entry.data[CONF_BASE_URL],
        token=entry.data[CONF_TOKEN],
    )

    minutes = entry.options.get(CONF_SCAN_INTERVAL_MINUTES)
    interval = timedelta(minutes=minutes) if minutes else DEFAULT_SCAN_INTERVAL

    coordinator = TasksSphereCoordinator(hass, entry, client, interval)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: TasksSphereConfigEntry
) -> bool:
    """Einen Eintrag wieder abraeumen."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(
    hass: HomeAssistant, entry: TasksSphereConfigEntry
) -> None:
    """Nach geaenderten Einstellungen neu laden, damit das Intervall greift."""
    await hass.config_entries.async_reload(entry.entry_id)
