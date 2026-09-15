"""Einrichtung und Einstellungen."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    TasksSphereAuthError,
    TasksSphereClient,
    TasksSphereConnectionError,
)
from .const import (
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_TOKEN,
    DOMAIN,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
        vol.Required(CONF_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


class TasksSphereConfigFlow(ConfigFlow, domain=DOMAIN):
    """Fragt Adresse und Token ab und prueft beides."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = user_input[CONF_BASE_URL].strip()
            token = user_input[CONF_TOKEN].strip()

            if not base_url.startswith(("http://", "https://")):
                errors[CONF_BASE_URL] = "invalid_url"
            else:
                client = TasksSphereClient(
                    async_get_clientsession(self.hass), base_url, token
                )
                try:
                    profile = await client.async_get_profile()
                except TasksSphereAuthError:
                    errors[CONF_TOKEN] = "invalid_auth"
                except TasksSphereConnectionError:
                    errors["base"] = "cannot_connect"
                else:
                    # Ein Konto je Instanz: Adresse und Konto-Id zusammen.
                    await self.async_set_unique_id(
                        f"{base_url.rstrip('/')}::{profile.get('id')}"
                    )
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=profile.get("name") or "TasksSphere",
                        data={CONF_BASE_URL: base_url.rstrip("/"), CONF_TOKEN: token},
                    )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> TasksSphereOptionsFlow:
        return TasksSphereOptionsFlow()


class TasksSphereOptionsFlow(OptionsFlow):
    """Erlaubt, das Abrufintervall zu aendern."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(CONF_SCAN_INTERVAL_MINUTES, 5)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL_MINUTES, default=current
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL_MINUTES,
                            max=MAX_SCAN_INTERVAL_MINUTES,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="min",
                        )
                    )
                }
            ),
        )
