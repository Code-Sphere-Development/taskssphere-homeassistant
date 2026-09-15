"""Aufbau des Eintrags und die Entitaeten, die dabei entstehen."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.taskssphere.const import CONF_BASE_URL, CONF_TOKEN, DOMAIN

CHECKLIST = {
    "id": 7,
    "title": "Einkauf",
    "type": "checklist",
    "items": [
        {"id": 71, "title": "Milch", "note": "fettarm", "is_completed": False},
        {"id": 72, "title": "Brot", "note": None, "is_completed": True},
    ],
}


def _task(task_id: int, title: str, due_at: str | None) -> dict:
    return {
        "id": task_id,
        "title": title,
        "description": None,
        "due_at": due_at,
        "recurrence_rule": None,
    }


# Feste Zeitpunkte statt "jetzt plus X": Die Fixture liefe sonst vor dem
# Setzen der Zeitzone durch Home Assistant, schriebe die Zeitstempel also in
# einer anderen Zone als sie spaeter gelesen werden - der Test haenge an der
# Uhrzeit des Rechners.
FROZEN_NOW = "2026-09-15 10:00:00"
OVERDUE = "2026-09-14 09:00:00"
LATER_TODAY = "2026-09-15 18:00:00"
NEXT_WEEK = "2026-09-22 09:00:00"
COMPLETED_AT = "2026-09-15 09:30:00"


@pytest.fixture(autouse=True)
def frozen_clock(freezer):
    """Alle Zeitvergleiche gegen einen festen Zeitpunkt."""
    freezer.move_to(FROZEN_NOW)
    return freezer


@pytest.fixture
def api():
    """Ein Klient, der feste Daten liefert."""
    with patch(
        "custom_components.taskssphere.TasksSphereClient", autospec=True
    ) as client_class:
        client = client_class.return_value
        client.async_get_profile = AsyncMock(return_value={"id": 1, "name": "Zuhause"})
        client.async_get_task_lists = AsyncMock(
            return_value=[
                {"id": 7, "title": "Einkauf", "type": "checklist"},
                {"id": 8, "title": "Projekte", "type": "tasks"},
            ]
        )
        client.async_get_task_list = AsyncMock(return_value=CHECKLIST)
        client.async_get_tasks = AsyncMock(
            return_value=[
                _task(1, "Reifen wechseln", OVERDUE),
                _task(2, "Müll rausbringen", LATER_TODAY),
                _task(3, "Versicherung kündigen", NEXT_WEEK),
            ]
        )
        client.async_get_completed = AsyncMock(
            return_value=[
                {
                    "id": 90,
                    "planned_at": OVERDUE,
                    "completed_at": COMPLETED_AT,
                    "task": _task(4, "Paket abholen", OVERDUE),
                }
            ]
        )
        client.async_create_item = AsyncMock(return_value={})
        client.async_update_item = AsyncMock(return_value={})
        client.async_delete_item = AsyncMock(return_value=None)
        client.async_complete_task = AsyncMock(return_value={})
        client.async_uncomplete_task = AsyncMock(return_value={})
        yield client


@pytest.fixture
async def entry(hass: HomeAssistant, api) -> MockConfigEntry:
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Zuhause",
        unique_id="https://tasks.example.org::1",
        data={CONF_BASE_URL: "https://tasks.example.org", CONF_TOKEN: "geheim"},
    )
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    return config_entry


async def test_the_entry_loads(hass: HomeAssistant, entry) -> None:
    assert entry.state is ConfigEntryState.LOADED


async def test_a_todo_list_exists_per_checklist(hass: HomeAssistant, entry) -> None:
    state = hass.states.get("todo.zuhause_einkauf")

    assert state is not None
    # Home Assistant zaehlt in diesem Zustand die offenen Eintraege.
    assert state.state == "1"


async def test_the_task_list_exists(hass: HomeAssistant, entry) -> None:
    state = hass.states.get("todo.zuhause_aufgaben")

    assert state is not None
    assert state.state == "3"


async def test_the_counters_are_right(hass: HomeAssistant, entry) -> None:
    assert hass.states.get("sensor.zuhause_overdue").state == "1"
    assert hass.states.get("sensor.zuhause_due_today").state == "1"
    assert hass.states.get("sensor.zuhause_completed_today").state == "1"


async def test_the_calendar_exists(hass: HomeAssistant, entry) -> None:
    state = hass.states.get("calendar.zuhause_termine")

    assert state is not None


async def test_checking_a_checklist_item_reaches_the_api(
    hass: HomeAssistant, entry, api
) -> None:
    await hass.services.async_call(
        "todo",
        "update_item",
        {"item": "Milch", "status": "completed"},
        target={"entity_id": "todo.zuhause_einkauf"},
        blocking=True,
    )

    api.async_update_item.assert_awaited_once()
    args, kwargs = api.async_update_item.await_args
    assert args[0] == 7
    assert args[1] == 71
    assert kwargs["is_completed"] is True


async def test_checking_a_task_calls_complete(hass: HomeAssistant, entry, api) -> None:
    await hass.services.async_call(
        "todo",
        "update_item",
        {"item": "Reifen wechseln", "status": "completed"},
        target={"entity_id": "todo.zuhause_aufgaben"},
        blocking=True,
    )

    api.async_complete_task.assert_awaited_once()
    assert api.async_complete_task.await_args[0][0] == 1


async def test_unchecking_a_completed_occurrence_calls_uncomplete(
    hass: HomeAssistant, entry, api
) -> None:
    await hass.services.async_call(
        "todo",
        "update_item",
        {"item": "Paket abholen", "status": "needs_action"},
        target={"entity_id": "todo.zuhause_aufgaben"},
        blocking=True,
    )

    api.async_uncomplete_task.assert_awaited_once()
    task_id, planned_at = api.async_uncomplete_task.await_args[0]
    assert task_id == 4
    assert planned_at is not None


async def test_the_entry_unloads_again(hass: HomeAssistant, entry) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    # Home Assistant behaelt den Eintrag im Zustandsspeicher und markiert ihn
    # als nicht verfuegbar, statt ihn zu entfernen.
    assert hass.states.get("todo.zuhause_einkauf").state == "unavailable"
