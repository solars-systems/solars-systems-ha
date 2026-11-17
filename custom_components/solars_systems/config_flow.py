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
    CONF_INVERTER_COUNT,
    CONF_MPPT_PER_INVERTER,
    CONF_UPDATE_INTERVAL,
    CONF_SENSOR_PV_POWER,
    CONF_SENSOR_LOAD_POWER,
    CONF_SENSOR_BATT_SOC,
    CONF_SENSOR_BATT_VOLT,
    CONF_SENSOR_BATT_CURR,
    CONF_SENSOR_BATT_POWER,
    CONF_SENSOR_GRID_VOLT,
    CONF_SENSOR_AC_OUT_VOLT,
    CONF_SENSOR_ENERGY_TODAY,
    CONF_SENSOR_ENERGY_MONTH,
    CONF_SENSOR_ENERGY_YEAR,
    CONF_IMPORT_HISTORY,
    CONF_HISTORY_RANGE,
    HISTORY_RANGE_30_DAYS,
    HISTORY_RANGE_90_DAYS,
    HISTORY_RANGE_1_YEAR,
    HISTORY_RANGE_ALL,
)

_LOGGER = logging.getLogger(__name__)


COMMON_NON_SOLAR_KEYWORDS = (
    "tablet", "tableta", "ipad", "telefon", "phone", "mobile", "laptop",
    "pompa", "heat_pump", "caldura", "clima", "ac_", "aer_conditionat",
    "boiler", "priza", "plug", "socket", "smart_plug", "releu", "relay",
    "shelly", "sonoff", "tuya", "bec", "light", "lumina", "tv", "frigider",
    "masina_spalat", "cuptor", "aspirator", "ups", "watch", "ceas", "smartwatch",
    "temperatura", "temp_", "humidity", "umiditate", "motion", "door", "window",
)

SOLAR_CONTEXT_KEYWORDS = (
    "solar", "pv", "panou", "invert", "inv_", "inverter", "mppt", "bms", "jk",
    "lifepo4", "pylon", "byd", "victron", "storage", "acumulator", "baterie_solara",
    "fotovolt", "yield", "solarpro", "solars", "deye", "growatt", "huawei", "solis",
)


def _auto_detect_candidate(
    hass,
    domain: str,
    device_class: str | None,
    units: tuple[str, ...],
    keywords: tuple[str, ...],
    negative_keywords: tuple[str, ...] = (),
    require_solar_context: bool = False,
) -> str | None:
    """Find a candidate sensor matching criteria with strict non-solar exclusions."""
    for state in hass.states.async_all():
        entity_id = state.entity_id
        if not entity_id.startswith(f"{domain}."):
            continue

        d_class = state.attributes.get("device_class")
        u_meas = state.attributes.get("unit_of_measurement")
        name = f"{entity_id} {state.attributes.get('friendly_name', '')}".lower()

        # Class or unit matching
        class_match = (device_class and d_class == device_class) or (units and u_meas in units)
        if not class_match:
            continue

        # Global exclusion of household appliances, phones, tablets, heat pumps
        if any(neg in name for neg in COMMON_NON_SOLAR_KEYWORDS):
            continue

        # Specific negative keywords matching
        if any(neg in name for neg in negative_keywords):
            continue

        # If solar context is required, must contain at least one solar keyword
        if require_solar_context and not any(sc in name for sc in SOLAR_CONTEXT_KEYWORDS):
            continue

        if any(kw in name for kw in keywords):
            return entity_id

    return None


class SolarsSystemsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solars Systems."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._api_key: str | None = None
        self._devices: list[dict[str, Any]] = []
        self._layout: dict[str, Any] = {}

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
                            return await self.async_step_layout()
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

    async def async_step_layout(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2: Configure System Layout (Inverters and MPPT count)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._layout = user_input
            return await self.async_step_sensors()

        device_options = {
            dev["macid"]: f"{dev.get('name', dev['macid'])} ({dev['macid']})"
            for dev in self._devices
        }

        schema = vol.Schema({
            vol.Required(CONF_INVERTER_ID, default=list(device_options.keys())[0]): vol.In(device_options),
            vol.Required(CONF_INVERTER_COUNT, default=1): vol.In({
                1: "1 Invertor (Standard)",
                2: "2 Invertoare în paralel",
                3: "3 Invertoare în paralel",
                4: "4 Invertoare în paralel",
                5: "5 Invertoare în paralel",
                6: "6 Invertoare în paralel",
            }),
            vol.Required(CONF_MPPT_PER_INVERTER, default=2): vol.In({
                1: "1 MPPT (1 String)",
                2: "2 MPPT-uri (Dual MPPT)",
                3: "3 MPPT-uri",
                4: "4 MPPT-uri",
            }),
        })

        return self.async_show_form(
            step_id="layout",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 3: Map sensors dynamically based on chosen layout."""
        errors: dict[str, str] = {}
        inv_count = int(self._layout.get(CONF_INVERTER_COUNT, 1))
        mppt_count = int(self._layout.get(CONF_MPPT_PER_INVERTER, 2))
        inverter_id = self._layout.get(CONF_INVERTER_ID, "")

        if user_input is not None:
            data = {
                CONF_API_KEY: self._api_key,
                CONF_INVERTER_ID: inverter_id,
                CONF_INVERTER_COUNT: inv_count,
                CONF_MPPT_PER_INVERTER: mppt_count,
                **user_input,
            }
            title = inverter_id
            for dev in self._devices:
                if dev.get("macid") == inverter_id:
                    title = f"Solars - {dev.get('name', dev.get('macid'))}"
                    break

            return self.async_create_entry(title=title, data=data)

        schema_dict: dict[Any, Any] = {}

        # 1. Generate dynamic MPPT Voltage fields for each inverter
        for inv in range(1, inv_count + 1):
            for m in range(1, mppt_count + 1):
                # Standard Solars Systems key convention:
                # Inverter 1: voltajPV1, voltajPV1_2, voltajPV1_3...
                # Inverter 2: voltajPV2, voltajPV2_2, voltajPV2_3...
                key = f"voltajPV{inv}" if m == 1 else f"voltajPV{inv}_{m}"
                
                # Auto-detect candidates
                kw_list = [f"pv{m}", f"pv_{m}", f"mppt{m}", f"mppt_{m}"]
                if inv_count > 1:
                    kw_list = [f"inv{inv}_{k}" for k in kw_list] + [f"inverter_{inv}_{k}" for k in kw_list] + [f"inverter {inv} {k}" for k in kw_list]
                
                cand = _auto_detect_candidate(
                    self.hass, "sensor", "voltage", ("V",), tuple(kw_list), ("batt", "battery", "ac", "grid")
                )

                field_opts = {"default": cand} if cand else {}
                schema_dict[vol.Optional(key, **field_opts)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
                )

            # Optional Power per Inverter (puterePV1, puterePV2...) if multiple inverters
            if inv_count > 1:
                p_key = f"puterePV{inv}"
                p_cand = _auto_detect_candidate(
                    self.hass, "sensor", "power", ("W", "kW"), (f"inv{inv}_power", f"inverter_{inv}_power", f"inverter {inv} power"), ("consum", "load")
                )
                p_opts = {"default": p_cand} if p_cand else {}
                schema_dict[vol.Optional(p_key, **p_opts)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="power")
                )

        # 2. Total Solar Power
        tot_pv_cand = _auto_detect_candidate(
            self.hass, "sensor", "power", ("W", "kW"), ("solar_power", "total_pv", "total_panouri", "putere_pv", "pv_power"), ("consum", "load", "battery"), require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_PV_POWER, **({"default": tot_pv_cand} if tot_pv_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        # 3. Consumption / Load Power
        load_cand = _auto_detect_candidate(
            self.hass, "sensor", "power", ("W", "kW"), ("load_power", "consum", "house_power", "home_power"), ("solar", "pv", "battery")
        )
        schema_dict[vol.Optional(CONF_SENSOR_LOAD_POWER, **({"default": load_cand} if load_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        # 4. Battery Sensors
        soc_cand = _auto_detect_candidate(
            self.hass, "sensor", "battery", ("%",), ("battery_soc", "bms_soc", "baterie_soc", "soc"), ("phone", "telefon", "laptop"), require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_BATT_SOC, **({"default": soc_cand} if soc_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="battery")
        )

        batt_v_cand = _auto_detect_candidate(
            self.hass, "sensor", "voltage", ("V",), ("battery_voltage", "voltaj_baterie", "batt_volt", "battery_volt", "bms_voltage"), (), require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_BATT_VOLT, **({"default": batt_v_cand} if batt_v_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
        )

        batt_c_cand = _auto_detect_candidate(
            self.hass, "sensor", "current", ("A",), ("battery_current", "curent_baterie", "batt_current", "bms_current"), (), require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_BATT_CURR, **({"default": batt_c_cand} if batt_c_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="current")
        )

        batt_p_cand = _auto_detect_candidate(
            self.hass, "sensor", "power", ("W", "kW"), ("battery_power", "putere_baterie", "batt_power", "bms_power"), (), require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_BATT_POWER, **({"default": batt_p_cand} if batt_p_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        # 5. Grid Voltages
        grid_cand = _auto_detect_candidate(
            self.hass, "sensor", "voltage", ("V",), ("grid_voltage", "tensiune_retea", "ac_in_voltage", "grid_volt"), ()
        )
        schema_dict[vol.Optional(CONF_SENSOR_GRID_VOLT, **({"default": grid_cand} if grid_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
        )

        ac_out_cand = _auto_detect_candidate(
            self.hass, "sensor", "voltage", ("V",), ("output_voltage", "ac_out_voltage", "tensiune_ac_out", "inverter_out_voltage"), ()
        )
        schema_dict[vol.Optional(CONF_SENSOR_AC_OUT_VOLT, **({"default": ac_out_cand} if ac_out_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
        )

        # 6. Energy Sensors
        e_today_cand = _auto_detect_candidate(
            self.hass, "sensor", "energy", ("kWh", "Wh"), ("energy_today", "daily_energy", "productie_zi", "energie_zi", "solar_today"), ("consum", "load", "pompa", "heat_pump", "retea", "grid"), require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_TODAY, **({"default": e_today_cand} if e_today_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        )

        e_month_cand = _auto_detect_candidate(
            self.hass, "sensor", "energy", ("kWh", "Wh"), ("monthly_energy", "energy_month", "productie_luna", "energie_luna"), ("consum", "load", "pompa", "heat_pump", "retea", "grid"), require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_MONTH, **({"default": e_month_cand} if e_month_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        )

        e_year_cand = _auto_detect_candidate(
            self.hass, "sensor", "energy", ("kWh", "Wh"), ("yearly_energy", "energy_year", "productie_an", "energie_an"), ("consum", "load", "pompa", "heat_pump", "retea", "grid"), require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_YEAR, **({"default": e_year_cand} if e_year_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        )

        # 7. History import and intervals
        schema_dict[vol.Optional(CONF_IMPORT_HISTORY, default=True)] = bool
        schema_dict[vol.Optional(CONF_HISTORY_RANGE, default=HISTORY_RANGE_ALL)] = selector.SelectSelector(
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
        )
        schema_dict[vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL)] = vol.All(
            vol.Coerce(int), vol.Range(min=10, max=300)
        )

        return self.async_show_form(
            step_id="sensors",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )
