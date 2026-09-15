"""To-do-Listen aus TasksSphere.

Zwei Arten, weil das Datenmodell zwei kennt: Checklisten haben keine
Faelligkeit, Aufgaben schon. Die Faehigkeiten werden deshalb je Art gemeldet,
statt ein Feld anzubieten, das hinterher nicht ankommt.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TasksSphereConfigEntry
from .api import TasksSphereError
from .coordinator import TasksSphereCoordinator
from .entity import TasksSphereEntity
from .util import parse_datetime, to_api_datetime

# Eine erledigte Wiederholung wird als "<Aufgabe>@<Termin>" gefuehrt, damit das
# Zuruecknehmen weiss, welcher Termin gemeint ist.
_OCCURRENCE_SEPARATOR = "@"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TasksSphereConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data

    entities: list[TodoListEntity] = [TasksSphereTaskList(coordinator)]
    entities.extend(
        TasksSphereChecklist(coordinator, checklist["id"], checklist.get("title", ""))
        for checklist in coordinator.data.checklists
    )

    async_add_entities(entities)


class TasksSphereChecklist(TasksSphereEntity, TodoListEntity):
    """Eine Checkliste. Kein Datum, dafuer eine Notiz je Eintrag."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(
        self, coordinator: TasksSphereCoordinator, list_id: int, title: str
    ) -> None:
        super().__init__(coordinator)
        self._list_id = list_id
        self._attr_name = title
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_list_{list_id}"

    @property
    def _list(self) -> dict[str, Any] | None:
        return next(
            (
                entry
                for entry in self.coordinator.data.checklists
                if entry["id"] == self._list_id
            ),
            None,
        )

    @property
    def available(self) -> bool:
        return super().available and self._list is not None

    @property
    def todo_items(self) -> list[TodoItem] | None:
        task_list = self._list
        if task_list is None:
            return None

        return [
            TodoItem(
                uid=str(item["id"]),
                summary=item.get("title", ""),
                description=item.get("note"),
                status=(
                    TodoItemStatus.COMPLETED
                    if item.get("is_completed")
                    else TodoItemStatus.NEEDS_ACTION
                ),
            )
            for item in task_list.get("items", [])
        ]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        await self._call(
            self.coordinator.client.async_create_item(
                self._list_id, item.summary or "", item.description
            )
        )

    async def async_update_todo_item(self, item: TodoItem) -> None:
        await self._call(
            self.coordinator.client.async_update_item(
                self._list_id,
                int(item.uid),
                title=item.summary,
                note=item.description,
                is_completed=item.status == TodoItemStatus.COMPLETED,
            )
        )

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        for uid in uids:
            await self._call(
                self.coordinator.client.async_delete_item(self._list_id, int(uid))
            )

    async def _call(self, awaitable: Any) -> None:
        try:
            await awaitable
        except TasksSphereError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()


class TasksSphereTaskList(TasksSphereEntity, TodoListEntity):
    """Alle offenen Aufgaben, dazu die letzten Erledigungen."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DUE_DATETIME_ON_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(self, coordinator: TasksSphereCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = "Aufgaben"
        self._attr_translation_key = "tasks"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_tasks"

    @property
    def todo_items(self) -> list[TodoItem] | None:
        items = [
            TodoItem(
                uid=str(task["id"]),
                summary=task.get("title", ""),
                description=task.get("description"),
                due=parse_datetime(task.get("due_at")),
                status=TodoItemStatus.NEEDS_ACTION,
            )
            for task in self.coordinator.data.tasks
        ]

        # GET /api/tasks liefert ausschliesslich Offenes. Damit ein Haken
        # ueberhaupt wieder entfernt werden kann, kommen die juengsten
        # Erledigungen dazu - serverseitig auf zehn begrenzt.
        for completion in self.coordinator.data.completed:
            task = completion.get("task")
            if not task:
                continue

            planned_at = completion.get("planned_at")
            uid = str(task["id"])
            if planned_at:
                uid = f"{uid}{_OCCURRENCE_SEPARATOR}{planned_at}"

            items.append(
                TodoItem(
                    uid=uid,
                    summary=task.get("title", ""),
                    description=task.get("description"),
                    due=parse_datetime(planned_at),
                    status=TodoItemStatus.COMPLETED,
                )
            )

        return items

    async def async_create_todo_item(self, item: TodoItem) -> None:
        await self._call(
            self.coordinator.client.async_create_task(
                title=item.summary or "",
                description=item.description,
                due_at=to_api_datetime(item.due),
            )
        )

    async def async_update_todo_item(self, item: TodoItem) -> None:
        task_id, planned_at = self._split(item.uid or "")
        client = self.coordinator.client

        if item.status == TodoItemStatus.COMPLETED:
            await self._call(client.async_complete_task(task_id, planned_at))
            return

        if planned_at is not None:
            # Der Eintrag stammt aus der Erledigt-Liste und wird zurueckgenommen.
            await self._call(client.async_uncomplete_task(task_id, planned_at))
            return

        await self._call(
            client.async_update_task(
                task_id,
                title=item.summary,
                description=item.description,
                due_at=to_api_datetime(item.due),
            )
        )

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        for uid in uids:
            task_id, _ = self._split(uid)
            await self._call(self.coordinator.client.async_delete_task(task_id))

    @staticmethod
    def _split(uid: str) -> tuple[int, str | None]:
        if _OCCURRENCE_SEPARATOR in uid:
            task_id, planned_at = uid.split(_OCCURRENCE_SEPARATOR, 1)
            return int(task_id), planned_at
        return int(uid), None

    async def _call(self, awaitable: Any) -> None:
        try:
            await awaitable
        except TasksSphereError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
