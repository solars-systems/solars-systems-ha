"""Config flow for Solars Systems integration."""
from __future__ import annotations

import logging
from typing import Any
import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    DEFAULT_API_URL,
    DEFAULT_UPDATE_INTERVAL,
    CONF_API_KEY,
    CONF_INVERTER_ID,
    CONF_UPDATE_INTERVAL,
    CONF_SENSOR_PV_POWER,
    CONF_SENSOR_LOAD_POWER,
    CONF_SENSOR_BATT_SOC,
    CONF_SENSOR_BATT_VOLT,
    CONF_SENSOR_BATT_POWER,
    CONF_SENSOR_GRID_VOLT,
    CONF_SENSOR_ENERGY_TODAY,
    CONF_IMPORT_HISTORY,
    CONF_HISTORY_RANGE,
    HISTORY_RANGE_30_DAYS,
    HISTORY_RANGE_90_DAYS,
    HISTORY_RANGE_1_YEAR,
    HISTORY_RANGE_ALL,
)

_LOGGER = logging.getLogger(__name__)


class SolarsSystemsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solars Systems."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._api_key: str | None = None
        self._devices: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1: Authenticate with API Key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            session = async_get_clientsession(self.hass)

            try:
                headers = {"x-api-key": api_key, "Accept": "application/json"}
                async with session.get(
                    f"{DEFAULT_API_URL}/devices", headers=headers, timeout=10
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        devices = data.get("devices", [])
                        if not devices:
                            errors["base"] = "no_inverters_found"
                        else:
                            self._api_key = api_key
                            self._devices = devices
                            return await self.async_step_sensors()
                    elif resp.status in (401, 403):
                        errors["base"] = "invalid_auth"
                    else:
                        errors["base"] = "cannot_connect"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error during authentication: %s", err)
                errors["base"] = "unknown"

        schema = vol.Schema({
            vol.Required(CONF_API_KEY): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2: Map inverters and sensors."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Combine API key with sensor settings
            data = {
                CONF_API_KEY: self._api_key,
                **user_input,
            }
            title = user_input.get(CONF_INVERTER_ID, "Solars Inverter")
            for dev in self._devices:
                if dev.get("macid") == user_input.get(CONF_INVERTER_ID):
                    title = f"Solars - {dev.get('name', dev.get('macid'))}"
                    break

            return self.async_create_entry(title=title, data=data)

        # Build dropdown for inverters
        device_options = {
            dev["macid"]: f"{dev.get('name', dev['macid'])} ({dev['macid']})"
            for dev in self._devices
        }

        schema = vol.Schema({
            vol.Required(CONF_INVERTER_ID, default=list(device_options.keys())[0]): vol.In(device_options),
            vol.Optional(CONF_SENSOR_PV_POWER): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power")
            ),
            vol.Optional(CONF_SENSOR_LOAD_POWER): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power")
            ),
            vol.Optional(CONF_SENSOR_BATT_SOC): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="battery")
            ),
            vol.Optional(CONF_SENSOR_ENERGY_TODAY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy")
            ),
            vol.Optional(CONF_SENSOR_BATT_VOLT): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
            ),
            vol.Optional(CONF_SENSOR_BATT_POWER): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power")
            ),
            vol.Optional(CONF_SENSOR_GRID_VOLT): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
            ),
            vol.Optional(CONF_IMPORT_HISTORY, default=True): bool,
            vol.Optional(CONF_HISTORY_RANGE, default=HISTORY_RANGE_ALL): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        HISTORY_RANGE_30_DAYS,
                        HISTORY_RANGE_90_DAYS,
                        HISTORY_RANGE_1_YEAR,
                        HISTORY_RANGE_ALL,
                    ],
                    translation_key="history_range",
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
                vol.Coerce(int), vol.Range(min=10, max=300)
            ),
        })

        return self.async_show_form(
            step_id="sensors",
            data_schema=schema,
            errors=errors,
        )
