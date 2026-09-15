"""Zugriff auf die TasksSphere-API.

Duenne Huelle um die REST-Schnittstelle. Bewusst ohne eigene Zwischenspeicherung
und ohne Kenntnis von Home Assistant, damit sie sich einzeln testen laesst.
"""

from __future__ import annotations

from datetime import datetime
from json import JSONDecodeError
from json import loads as json_loads
from typing import Any

import aiohttp
from yarl import URL


class TasksSphereError(Exception):
    """Basisfehler dieser Integration."""


class TasksSphereAuthError(TasksSphereError):
    """Der Token wurde abgelehnt."""


class TasksSphereConnectionError(TasksSphereError):
    """Der Server war nicht erreichbar oder hat unerwartet geantwortet."""


class TasksSphereClient:
    """Spricht mit einer TasksSphere-Instanz."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        token: str,
    ) -> None:
        self._session = session
        self._base = URL(base_url.rstrip("/") + "/")
        self._token = token

    # -- Lesen ---------------------------------------------------------------

    async def async_get_profile(self) -> dict[str, Any]:
        """Konto zum Token. Dient auch als Pruefung bei der Einrichtung."""
        return await self._request("GET", "api/profile")

    async def async_get_task_lists(self) -> list[dict[str, Any]]:
        return await self._request("GET", "api/task-lists")

    async def async_get_task_list(self, list_id: int) -> dict[str, Any]:
        """Eine Liste samt ihrer Eintraege beziehungsweise Aufgaben."""
        return await self._request("GET", f"api/task-lists/{list_id}")

    async def async_get_tasks(self) -> list[dict[str, Any]]:
        """Offene, nicht archivierte Aufgaben."""
        return await self._request("GET", "api/tasks")

    async def async_get_completed(self) -> list[dict[str, Any]]:
        """Die letzten Erledigungen.

        Der Endpunkt liefert hoechstens zehn Eintraege; das ist serverseitig
        fest verdrahtet und keine Einstellung dieser Integration.
        """
        return await self._request("GET", "api/tasks/completed")

    async def async_get_occurrences(
        self, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        """Termine im Zeitfenster, Wiederholungen bereits aufgeloest."""
        return await self._request(
            "GET",
            "api/tasks/occurrences",
            params={
                "start": start.strftime("%Y-%m-%d %H:%M:%S"),
                "end": end.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )

    # -- Checklisten-Eintraege ------------------------------------------------

    async def async_create_item(
        self, list_id: int, title: str, note: str | None = None
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"api/task-lists/{list_id}/items",
            json={"title": title, "note": note},
        )

    async def async_update_item(
        self, list_id: int, item_id: int, **fields: Any
    ) -> dict[str, Any]:
        return await self._request(
            "PUT", f"api/task-lists/{list_id}/items/{item_id}", json=fields
        )

    async def async_delete_item(self, list_id: int, item_id: int) -> None:
        await self._request("DELETE", f"api/task-lists/{list_id}/items/{item_id}")

    # -- Aufgaben -------------------------------------------------------------

    async def async_create_task(self, **fields: Any) -> dict[str, Any]:
        return await self._request("POST", "api/tasks", json=fields)

    async def async_update_task(self, task_id: int, **fields: Any) -> dict[str, Any]:
        return await self._request("PUT", f"api/tasks/{task_id}", json=fields)

    async def async_delete_task(self, task_id: int) -> None:
        await self._request("DELETE", f"api/tasks/{task_id}")

    async def async_complete_task(
        self, task_id: int, planned_at: str | None = None
    ) -> dict[str, Any]:
        return await self._request(
            "POST", f"api/tasks/{task_id}/complete", json={"planned_at": planned_at}
        )

    async def async_uncomplete_task(
        self, task_id: int, planned_at: str | None = None
    ) -> dict[str, Any]:
        return await self._request(
            "POST", f"api/tasks/{task_id}/uncomplete", json={"planned_at": planned_at}
        )

    # -- Innereien ------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        url = self._base.join(URL(path))
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

        try:
            async with self._session.request(
                method, url, headers=headers, json=json, params=params
            ) as response:
                if response.status in (401, 403):
                    raise TasksSphereAuthError(
                        f"Zugriff verweigert ({response.status})"
                    )

                if response.status >= 400:
                    raise TasksSphereConnectionError(
                        f"Unerwartete Antwort {response.status} von {url}"
                    )

                if response.status == 204:
                    return None

                # Bewusst ueber den Text und nicht ueber Content-Length: sobald
                # der Server gzip oder stueckweise Uebertragung nutzt, fehlt die
                # Laengenangabe. Wer daraus schliesst, der Koerper sei leer,
                # wirft jede groessere Antwort weg.
                body = await response.text()

                if not body.strip():
                    return None

                try:
                    # json_loads, nicht json.loads: der Parameter json verdeckt
                    # das Modul innerhalb dieser Methode.
                    return json_loads(body)
                except JSONDecodeError as err:
                    raise TasksSphereConnectionError(
                        f"Antwort von {url} war kein JSON: {body[:200]}"
                    ) from err
        except aiohttp.ClientError as err:
            raise TasksSphereConnectionError(str(err)) from err
