"""Der HTTP-Client gegen die TasksSphere-API."""

from __future__ import annotations

import aiohttp
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.taskssphere.api import (
    TasksSphereAuthError,
    TasksSphereClient,
    TasksSphereConnectionError,
)

BASE = "https://tasks.example.org"


@pytest.fixture
async def session(hass):
    """Eine Sitzung, die auf den Mocker zeigt."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    return async_get_clientsession(hass)


async def test_a_list_response_is_parsed(
    hass, aioclient_mock: AiohttpClientMocker, session
) -> None:
    aioclient_mock.get(
        f"{BASE}/api/task-lists",
        json=[{"id": 7, "title": "Einkauf", "type": "checklist"}],
    )

    client = TasksSphereClient(session, BASE, "geheim")

    assert await client.async_get_task_lists() == [
        {"id": 7, "title": "Einkauf", "type": "checklist"}
    ]


async def test_a_response_without_content_length_is_parsed(
    hass, aioclient_mock: AiohttpClientMocker, session
) -> None:
    """Server liefern haeufig keine Laengenangabe.

    Bei gzip oder stueckweiser Uebertragung fehlt Content-Length. Wer daraus
    schliesst, der Koerper sei leer, wirft jede Antwort weg.
    """
    aioclient_mock.get(
        f"{BASE}/api/tasks",
        text='[{"id": 1, "title": "Reifen wechseln"}]',
        headers={"Content-Type": "application/json"},
    )

    client = TasksSphereClient(session, BASE, "geheim")

    assert await client.async_get_tasks() == [{"id": 1, "title": "Reifen wechseln"}]


async def test_the_token_is_sent_as_a_bearer(
    hass, aioclient_mock: AiohttpClientMocker, session
) -> None:
    aioclient_mock.get(f"{BASE}/api/profile", json={"id": 1})

    await TasksSphereClient(session, BASE, "geheim").async_get_profile()

    assert aioclient_mock.mock_calls[0][3]["Authorization"] == "Bearer geheim"


async def test_a_rejected_token_raises_the_auth_error(
    hass, aioclient_mock: AiohttpClientMocker, session
) -> None:
    aioclient_mock.get(f"{BASE}/api/profile", status=401)

    with pytest.raises(TasksSphereAuthError):
        await TasksSphereClient(session, BASE, "falsch").async_get_profile()


async def test_a_server_error_raises_the_connection_error(
    hass, aioclient_mock: AiohttpClientMocker, session
) -> None:
    aioclient_mock.get(f"{BASE}/api/tasks", status=500)

    with pytest.raises(TasksSphereConnectionError):
        await TasksSphereClient(session, BASE, "geheim").async_get_tasks()


async def test_an_empty_body_yields_none(
    hass, aioclient_mock: AiohttpClientMocker, session
) -> None:
    aioclient_mock.delete(f"{BASE}/api/tasks/1", status=204, text="")

    assert await TasksSphereClient(session, BASE, "geheim").async_delete_task(1) is None


async def test_a_broken_connection_raises_the_connection_error(
    hass, aioclient_mock: AiohttpClientMocker, session
) -> None:
    aioclient_mock.get(f"{BASE}/api/tasks", exc=aiohttp.ClientError("weg"))

    with pytest.raises(TasksSphereConnectionError):
        await TasksSphereClient(session, BASE, "geheim").async_get_tasks()


async def test_a_base_url_with_a_path_prefix_is_kept(
    hass, aioclient_mock: AiohttpClientMocker, session
) -> None:
    """Instanzen hinter einem Unterpfad duerfen nicht abgeschnitten werden."""
    aioclient_mock.get("https://example.org/tasks/api/profile", json={"id": 1})

    client = TasksSphereClient(session, "https://example.org/tasks", "geheim")

    assert await client.async_get_profile() == {"id": 1}
