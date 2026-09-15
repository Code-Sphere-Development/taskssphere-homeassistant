"""Der Einrichtungsdialog."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.taskssphere.api import (
    TasksSphereAuthError,
    TasksSphereConnectionError,
)
from custom_components.taskssphere.const import CONF_BASE_URL, CONF_TOKEN, DOMAIN

VALID_INPUT = {CONF_BASE_URL: "https://tasks.example.org", CONF_TOKEN: "geheim"}


def _profile(**overrides):
    return {"id": 1, "name": "Collin Ilgner", **overrides}


async def _start(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_form_is_shown_first(hass: HomeAssistant) -> None:
    result = await _start(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_valid_input_creates_the_entry(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.taskssphere.config_flow.TasksSphereClient.async_get_profile",
        AsyncMock(return_value=_profile()),
    ):
        result = await hass.config_entries.flow.async_configure(
            (await _start(hass))["flow_id"], VALID_INPUT
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Collin Ilgner"
    assert result["data"][CONF_BASE_URL] == "https://tasks.example.org"
    assert result["data"][CONF_TOKEN] == "geheim"


async def test_a_rejected_token_is_reported_on_the_token_field(
    hass: HomeAssistant,
) -> None:
    with patch(
        "custom_components.taskssphere.config_flow.TasksSphereClient.async_get_profile",
        AsyncMock(side_effect=TasksSphereAuthError("nope")),
    ):
        result = await hass.config_entries.flow.async_configure(
            (await _start(hass))["flow_id"], VALID_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TOKEN: "invalid_auth"}


async def test_an_unreachable_server_is_reported(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.taskssphere.config_flow.TasksSphereClient.async_get_profile",
        AsyncMock(side_effect=TasksSphereConnectionError("weg")),
    ):
        result = await hass.config_entries.flow.async_configure(
            (await _start(hass))["flow_id"], VALID_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


@pytest.mark.parametrize("address", ["tasks.example.org", "ftp://tasks.example.org"])
async def test_an_address_without_a_scheme_is_refused(
    hass: HomeAssistant, address: str
) -> None:
    result = await hass.config_entries.flow.async_configure(
        (await _start(hass))["flow_id"], {**VALID_INPUT, CONF_BASE_URL: address}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_BASE_URL: "invalid_url"}


async def test_the_same_account_cannot_be_added_twice(hass: HomeAssistant) -> None:
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="https://tasks.example.org::1",
        data=VALID_INPUT,
    ).add_to_hass(hass)

    with patch(
        "custom_components.taskssphere.config_flow.TasksSphereClient.async_get_profile",
        AsyncMock(return_value=_profile()),
    ):
        result = await hass.config_entries.flow.async_configure(
            (await _start(hass))["flow_id"], VALID_INPUT
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_a_trailing_slash_is_stripped(hass: HomeAssistant) -> None:
    with patch(
        "custom_components.taskssphere.config_flow.TasksSphereClient.async_get_profile",
        AsyncMock(return_value=_profile()),
    ):
        result = await hass.config_entries.flow.async_configure(
            (await _start(hass))["flow_id"],
            {**VALID_INPUT, CONF_BASE_URL: "https://tasks.example.org/"},
        )
        await hass.async_block_till_done()

    assert result["data"][CONF_BASE_URL] == "https://tasks.example.org"
