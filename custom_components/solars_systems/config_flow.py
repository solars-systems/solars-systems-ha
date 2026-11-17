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
    CONF_SENSOR_PV1_VOLT,
    CONF_SENSOR_PV2_VOLT,
    CONF_SENSOR_PV1_POWER,
    CONF_SENSOR_PV2_POWER,
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


def _auto_detect_sensors(hass) -> dict[str, str]:
    """Auto-detect candidate sensors for solar, MPPTs, load, battery and grid."""
    detected: dict[str, str] = {}
    all_states = hass.states.async_all()

    for state in all_states:
        entity_id = state.entity_id
        if not entity_id.startswith("sensor."):
            continue

        name = f"{entity_id} {state.attributes.get('friendly_name', '')}".lower()
        device_class = state.attributes.get("device_class")
        unit = state.attributes.get("unit_of_measurement")

        # 1. Total Solar / PV Power (W / kW)
        if CONF_SENSOR_PV_POWER not in detected and (device_class == "power" or unit in ("W", "kW")):
            if any(k in name for k in ("pv_power", "solar_power", "pv power", "solar power", "total_pv_power", "total pv power")) or (
                any(k in name for k in ("pv", "solar", "panou", "panouri"))
                and not any(neg in name for neg in ("pv1", "pv2", "mppt", "load", "consum", "grid", "retea", "house", "energy", "zi", "daily"))
            ):
                detected[CONF_SENSOR_PV_POWER] = entity_id

        # 1.1 MPPT 1 Voltage & Power
        if CONF_SENSOR_PV1_VOLT not in detected and (device_class == "voltage" or unit == "V"):
            if any(k in name for k in ("pv1_voltage", "pv1_volt", "mppt1_voltage", "mppt1_volt", "pv1 voltage", "mppt 1 voltage", "pv 1 voltage")):
                detected[CONF_SENSOR_PV1_VOLT] = entity_id

        if CONF_SENSOR_PV1_POWER not in detected and (device_class == "power" or unit in ("W", "kW")):
            if any(k in name for k in ("pv1_power", "mppt1_power", "pv1 power", "mppt 1 power", "pv 1 power")):
                detected[CONF_SENSOR_PV1_POWER] = entity_id

        # 1.2 MPPT 2 Voltage & Power
        if CONF_SENSOR_PV2_VOLT not in detected and (device_class == "voltage" or unit == "V"):
            if any(k in name for k in ("pv2_voltage", "pv2_volt", "mppt2_voltage", "mppt2_volt", "pv2 voltage", "mppt 2 voltage", "pv 2 voltage")):
                detected[CONF_SENSOR_PV2_VOLT] = entity_id

        if CONF_SENSOR_PV2_POWER not in detected and (device_class == "power" or unit in ("W", "kW")):
            if any(k in name for k in ("pv2_power", "mppt2_power", "pv2 power", "mppt 2 power", "pv 2 power")):
                detected[CONF_SENSOR_PV2_POWER] = entity_id

        # 2. Load / House Power (W / kW)
        if CONF_SENSOR_LOAD_POWER not in detected and (device_class == "power" or unit in ("W", "kW")):
            if any(k in name for k in ("load_power", "home_power", "house_power", "consum", "consum_casa", "load power")) or (
                any(k in name for k in ("load", "consum", "casa", "house", "home"))
                and not any(neg in name for neg in ("pv", "solar", "panou", "battery", "baterie", "energy", "zi"))
            ):
                detected[CONF_SENSOR_LOAD_POWER] = entity_id

        # 3. Battery SOC (%)
        if CONF_SENSOR_BATT_SOC not in detected and (device_class == "battery" or unit == "%"):
            if any(k in name for k in ("battery", "baterie", "batt", "soc")) and not any(neg in name for neg in ("phone", "telefon", "laptop")):
                detected[CONF_SENSOR_BATT_SOC] = entity_id

        # 4. Energy Today / Daily Solar (kWh)
        if CONF_SENSOR_ENERGY_TODAY not in detected and (device_class == "energy" or unit in ("kWh", "Wh")):
            if (any(k in name for k in ("today", "daily", "zi", "ziua")) and any(k in name for k in ("solar", "pv", "panou", "produc", "energie"))) or (
                any(k in name for k in ("solar_daily_energy", "solar_energy_today", "pv_daily_energy", "energie_zi"))
            ):
                detected[CONF_SENSOR_ENERGY_TODAY] = entity_id

        # 5. Battery Voltage (V)
        if CONF_SENSOR_BATT_VOLT not in detected and (device_class == "voltage" or unit == "V"):
            if any(k in name for k in ("battery_voltage", "batt_volt", "tensiune_baterie", "battery volt")) or (
                any(k in name for k in ("batt", "battery", "baterie")) and "volt" in name
            ):
                detected[CONF_SENSOR_BATT_VOLT] = entity_id

        # 6. Battery Power (W / kW)
        if CONF_SENSOR_BATT_POWER not in detected and (device_class == "power" or unit in ("W", "kW")):
            if any(k in name for k in ("battery_power", "batt_power", "putere_baterie", "battery power")):
                detected[CONF_SENSOR_BATT_POWER] = entity_id

        # 7. Grid Voltage (V)
        if CONF_SENSOR_GRID_VOLT not in detected and (device_class == "voltage" or unit == "V"):
            if any(k in name for k in ("grid_voltage", "ac_voltage", "grid_volt", "tensiune_retea", "grid volt")):
                detected[CONF_SENSOR_GRID_VOLT] = entity_id

    # Fallback for energy today if still not detected
    if CONF_SENSOR_ENERGY_TODAY not in detected:
        for state in all_states:
            if state.entity_id.startswith("sensor.") and state.attributes.get("unit_of_measurement") in ("kWh", "Wh"):
                name = f"{state.entity_id} {state.attributes.get('friendly_name', '')}".lower()
                if any(k in name for k in ("solar", "pv", "produc", "generation")):
                    detected[CONF_SENSOR_ENERGY_TODAY] = state.entity_id
                    break

    return detected


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
        """Step 2: Map inverters and sensors with intelligent auto-detection."""
        errors: dict[str, str] = {}

        if user_input is not None:
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

        # Run auto-detection across Home Assistant entities
        detected = _auto_detect_sensors(self.hass)

        schema_dict = {
            vol.Required(CONF_INVERTER_ID, default=list(device_options.keys())[0]): vol.In(device_options),
            
            vol.Optional(
                CONF_SENSOR_PV_POWER,
                **({"default": detected[CONF_SENSOR_PV_POWER]} if CONF_SENSOR_PV_POWER in detected else {})
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power")
            ),

            vol.Optional(
                CONF_SENSOR_PV1_VOLT,
                **({"default": detected[CONF_SENSOR_PV1_VOLT]} if CONF_SENSOR_PV1_VOLT in detected else {})
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
            ),

            vol.Optional(
                CONF_SENSOR_PV1_POWER,
                **({"default": detected[CONF_SENSOR_PV1_POWER]} if CONF_SENSOR_PV1_POWER in detected else {})
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power")
            ),

            vol.Optional(
                CONF_SENSOR_PV2_VOLT,
                **({"default": detected[CONF_SENSOR_PV2_VOLT]} if CONF_SENSOR_PV2_VOLT in detected else {})
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
            ),

            vol.Optional(
                CONF_SENSOR_PV2_POWER,
                **({"default": detected[CONF_SENSOR_PV2_POWER]} if CONF_SENSOR_PV2_POWER in detected else {})
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power")
            ),
            
            vol.Optional(
                CONF_SENSOR_LOAD_POWER,
                **({"default": detected[CONF_SENSOR_LOAD_POWER]} if CONF_SENSOR_LOAD_POWER in detected else {})
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power")
            ),
            
            vol.Optional(
                CONF_SENSOR_BATT_SOC,
                **({"default": detected[CONF_SENSOR_BATT_SOC]} if CONF_SENSOR_BATT_SOC in detected else {})
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="battery")
            ),
            
            vol.Optional(
                CONF_SENSOR_ENERGY_TODAY,
                **({"default": detected[CONF_SENSOR_ENERGY_TODAY]} if CONF_SENSOR_ENERGY_TODAY in detected else {})
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="energy")
            ),
            
            vol.Optional(
                CONF_SENSOR_BATT_VOLT,
                **({"default": detected[CONF_SENSOR_BATT_VOLT]} if CONF_SENSOR_BATT_VOLT in detected else {})
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
            ),
            
            vol.Optional(
                CONF_SENSOR_BATT_POWER,
                **({"default": detected[CONF_SENSOR_BATT_POWER]} if CONF_SENSOR_BATT_POWER in detected else {})
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="power")
            ),
            
            vol.Optional(
                CONF_SENSOR_GRID_VOLT,
                **({"default": detected[CONF_SENSOR_GRID_VOLT]} if CONF_SENSOR_GRID_VOLT in detected else {})
            ): selector.EntitySelector(
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
        }

        return self.async_show_form(
            step_id="sensors",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )
