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
    CONF_HAS_BATTERY,
    CONF_PRESET,
    PRESET_SOLAR_ASSISTANT,
    PRESET_CUSTOM,
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
    # Dispozitive mobile & Tablete perete
    "tablet", "tableta", "ipad", "telefon", "phone", "mobile", "laptop",
    "wallpanel", "fully_kiosk", "fullykiosk", "fire_hd", "kindle",
    "galaxy_tab", "sm_t", "tab_a", "mobile_app", "companion",
    # Pompe de caldura & Climatizare
    "pompa", "heat_pump", "heatpump", "caldura", "clima", "ac_", "aer_conditionat",
    "daikin", "nibe", "panasonic", "aquarea", "mitsubishi", "termopompa", "chiller",
    "compresor", "compressor", "incalzire", "heating", "puffer", "acm", "dhw",
    # Electrocasnice & Prize
    "boiler", "priza", "plug", "socket", "smart_plug", "releu", "relay",
    "shelly", "sonoff", "tuya", "bec", "light", "lumina", "tv", "frigider",
    "masina_spalat", "cuptor", "aspirator", "ups", "watch", "ceas", "smartwatch",
    "temperatura", "temp_", "humidity", "umiditate", "motion", "door", "window",
    # Statie incarcare auto (EV)
    "evse", "wallbox", "charger", "masina", "car_",
)

BATTERY_CELL_EXCLUSIONS = (
    "cell_", "celula_", "_cell", "cell ", "celula ", "bms_cell",
    "c1_", "c2_", "c3_", "c4_", "c5_", "c6_", "c7_", "c8_",
    "c9_", "c10_", "c11_", "c12_", "c13_", "c14_", "c15_", "c16_",
    "c17_", "c18_", "c19_", "c20_", "c21_", "c22_", "c23_", "c24_",
    "cell1", "cell2", "cell3", "cell4", "cell5", "cell6", "cell7", "cell8",
    "cell9", "cell10", "cell11", "cell12", "cell13", "cell14", "cell15", "cell16",
    "celula1", "celula2", "celula3", "celula4", "celula5", "celula6", "celula7",
)

SOLAR_CONTEXT_KEYWORDS = (
    "solar", "pv", "panou", "invert", "inv_", "inverter", "mppt", "bms", "jk",
    "lifepo4", "pylon", "byd", "victron", "storage", "acumulator", "baterie_solara",
    "fotovolt", "yield", "solarpro", "solars", "deye", "growatt", "huawei", "solis",
    "infinisolar", "fronius", "goodwe", "solax", "total_panouri", "total_baterie",
    "solar_assistant", "solarassistant",
)


def _auto_detect_candidate(
    hass,
    domain: str,
    device_class: str | None,
    units: tuple[str, ...],
    keywords: tuple[str, ...],
    negative_keywords: tuple[str, ...] = (),
    require_solar_context: bool = False,
    exclude_cells: bool = False,
) -> str | None:
    """Find a candidate sensor matching criteria with strict non-solar exclusions."""
    # 1. Exact entity_id check first
    for kw in keywords:
        if kw.startswith("sensor."):
            state = hass.states.get(kw)
            if state is not None:
                return kw

    # 2. Iterate through states in priority order of keywords
    all_states = list(hass.states.async_all())

    for kw in keywords:
        for state in all_states:
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

            # Global exclusion of household appliances, phones, heat pumps
            if any(neg in name for neg in COMMON_NON_SOLAR_KEYWORDS):
                continue

            # Anti-cell filter for battery packs
            if exclude_cells and any(cell in name for cell in BATTERY_CELL_EXCLUSIONS):
                continue

            # Specific negative keywords matching
            if any(neg in name for neg in negative_keywords):
                continue

            # If solar context is required, must contain at least one solar keyword
            if require_solar_context and not any(sc in name for sc in SOLAR_CONTEXT_KEYWORDS):
                continue

            if kw in name:
                return entity_id

    return None


class SolarsSystemsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a multi-step, user-friendly config flow for Solars Systems."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._api_key: str | None = None
        self._devices: list[dict[str, Any]] = []
        self._layout: dict[str, Any] = {}
        self._collected_data: dict[str, Any] = {}

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
        """Step 2: Configure System Layout (Inverters, MPPT count, Preset, Battery presence)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._layout = user_input
            return await self.async_step_solar()

        device_options = {
            dev["macid"]: f"{dev.get('name', dev['macid'])} ({dev['macid']})"
            for dev in self._devices
        }

        schema = vol.Schema({
            vol.Required(CONF_INVERTER_ID, default=list(device_options.keys())[0]): vol.In(device_options),
            vol.Required(CONF_PRESET, default=PRESET_SOLAR_ASSISTANT): vol.In({
                PRESET_SOLAR_ASSISTANT: "SolarAssistant (Detectare automată)",
                PRESET_CUSTOM: "Personalizat / Alte sisteme (Deye, Growatt, Huawei, Victron)",
            }),
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
            vol.Required(CONF_HAS_BATTERY, default=True): bool,
        })

        return self.async_show_form(
            step_id="layout",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_solar(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 3: Solar PV Panels & Energy Production."""
        errors: dict[str, str] = {}
        inv_count = int(self._layout.get(CONF_INVERTER_COUNT, 1))
        mppt_count = int(self._layout.get(CONF_MPPT_PER_INVERTER, 2))

        if user_input is not None:
            self._collected_data.update(user_input)
            if self._layout.get(CONF_HAS_BATTERY, True):
                return await self.async_step_battery()
            return await self.async_step_grid()

        schema_dict: dict[Any, Any] = {}

        # 1. Total Solar Power (e.g. sensor.total_pv_power, sensor.pv_power, sensor.total_panouri)
        tot_pv_cand = _auto_detect_candidate(
            self.hass, "sensor", "power", ("W", "kW"),
            ("sensor.total_pv_power", "sensor.pv_power", "total_pv_power", "pv_power", "total_panouri", "total_pv", "putere_pv", "solar_power", "total solar"),
            ("consum", "load", "battery", "baterie"),
            require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_PV_POWER, **({"default": tot_pv_cand} if tot_pv_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        # 2. Dynamic MPPT Voltage fields for each inverter
        for inv in range(1, inv_count + 1):
            for m in range(1, mppt_count + 1):
                key = f"voltajPV{inv}" if m == 1 else f"voltajPV{inv}_{m}"
                
                kw_list = [
                    f"sensor.inverter_{inv}_pv_voltage_{m}",
                    f"inverter_{inv}_pv_voltage_{m}",
                    f"inverter_{inv}_pv_{m}",
                    f"inv{inv}_pv{m}",
                    f"inv{inv}_pv_{m}",
                    f"pv{inv}_{m}",
                    f"pv{m}",
                    f"mppt{m}",
                    f"mppt_{m}",
                    f"growatt_voltaj" if inv == 5 else f"pv{inv}",
                ]
                
                cand = _auto_detect_candidate(
                    self.hass, "sensor", "voltage", ("V",),
                    tuple(kw_list),
                    ("batt", "baterie", "ac", "grid", "cell")
                )

                field_opts = {"default": cand} if cand else {}
                schema_dict[vol.Optional(key, **field_opts)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
                )

            # Optional Power per Inverter if multiple inverters
            if inv_count > 1:
                p_key = f"puterePV{inv}"
                p_cand = _auto_detect_candidate(
                    self.hass, "sensor", "power", ("W", "kW"),
                    (f"sensor.inverter_{inv}_pv_power", f"inverter_{inv}_pv_power", f"inv{inv}_power", f"inverter_{inv}_power", f"inverter {inv} power", f"putere_inv{inv}"),
                    ("consum", "load", "batt", "baterie")
                )
                p_opts = {"default": p_cand} if p_cand else {}
                schema_dict[vol.Optional(p_key, **p_opts)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="power")
                )

        # 3. Energy Production Sensors (Daily, Monthly, Yearly)
        e_today_cand = _auto_detect_candidate(
            self.hass, "sensor", "energy", ("kWh", "Wh"),
            ("sensor.solar_energy_today", "sensor.energy_today", "solar_energy_today", "energy_today", "productie_zi", "energie_zi", "daily_energy", "solar_today", "today_energy"),
            ("consum", "load", "pompa", "heat_pump", "retea", "grid"),
            require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_TODAY, **({"default": e_today_cand} if e_today_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        )

        e_month_cand = _auto_detect_candidate(
            self.hass, "sensor", "energy", ("kWh", "Wh"),
            ("sensor.solar_energy_this_month", "solar_energy_this_month", "productie_panouri_lunar", "productie_luna", "energie_luna", "monthly_energy", "energy_month"),
            ("consum", "load", "pompa", "heat_pump", "retea", "grid"),
            require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_MONTH, **({"default": e_month_cand} if e_month_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        )

        e_year_cand = _auto_detect_candidate(
            self.hass, "sensor", "energy", ("kWh", "Wh"),
            ("sensor.solar_energy_this_year", "solar_energy_this_year", "productie_anuala", "productie_an", "energie_an", "yearly_energy", "energy_year"),
            ("consum", "load", "pompa", "heat_pump", "retea", "grid"),
            require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_YEAR, **({"default": e_year_cand} if e_year_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        )

        return self.async_show_form(
            step_id="solar",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def async_step_battery(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 4: Battery & Storage Sensors (filtered, excluding individual cells)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._collected_data.update(user_input)
            return await self.async_step_grid()

        schema_dict: dict[Any, Any] = {}

        # 1. Battery SOC (%)
        soc_cand = _auto_detect_candidate(
            self.hass, "sensor", "battery", ("%",),
            ("sensor.battery_state_of_charge", "battery_state_of_charge", "voltaj_total_baterie_soc", "baterie_soc", "battery_soc", "bms_soc", "procent_baterie", "procentbaterie", "soc"),
            ("phone", "telefon", "laptop", "tablet"),
            require_solar_context=True,
            exclude_cells=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_BATT_SOC, **({"default": soc_cand} if soc_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="battery")
        )

        # 2. Battery Voltage (V) - STRICT anti-cell filter to eliminate 160+ cell voltage sensors!
        batt_v_cand = _auto_detect_candidate(
            self.hass, "sensor", "voltage", ("V",),
            ("sensor.battery_voltage", "battery_voltage", "voltaj_total_baterie", "tensiune_total_baterie", "voltaj_baterie", "tensiune_baterie", "batt_volt", "bms_voltage", "total_voltage"),
            ("ac", "grid", "retea", "pv", "mppt"),
            require_solar_context=True,
            exclude_cells=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_BATT_VOLT, **({"default": batt_v_cand} if batt_v_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
        )

        # 3. Battery Current (A) - aggregate or total
        batt_c_cand = _auto_detect_candidate(
            self.hass, "sensor", "current", ("A",),
            ("sensor.battery_current", "battery_current", "curent_total_baterie", "curent_baterie", "batt_current", "bms_current", "total_current"),
            ("ac", "grid", "retea", "pv"),
            require_solar_context=True,
            exclude_cells=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_BATT_CURR, **({"default": batt_c_cand} if batt_c_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="current")
        )

        # 4. Battery Power (W/kW)
        batt_p_cand = _auto_detect_candidate(
            self.hass, "sensor", "power", ("W", "kW"),
            ("sensor.total_battery_power", "sensor.battery_power", "total_battery_power", "putere_baterie", "battery_power", "batt_power", "bms_power", "puterebaterie"),
            ("consum", "load", "pv", "grid", "retea"),
            require_solar_context=True,
            exclude_cells=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_BATT_POWER, **({"default": batt_p_cand} if batt_p_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        return self.async_show_form(
            step_id="battery",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def async_step_grid(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 5: Grid & Load Power, History Import, and Live Interval."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._collected_data.update(user_input)
            
            # Combine all collected data into final entry
            inv_count = int(self._layout.get(CONF_INVERTER_COUNT, 1))
            mppt_count = int(self._layout.get(CONF_MPPT_PER_INVERTER, 2))
            inverter_id = self._layout.get(CONF_INVERTER_ID, "")

            final_data = {
                CONF_API_KEY: self._api_key,
                CONF_INVERTER_ID: inverter_id,
                CONF_INVERTER_COUNT: inv_count,
                CONF_MPPT_PER_INVERTER: mppt_count,
                CONF_HAS_BATTERY: self._layout.get(CONF_HAS_BATTERY, True),
                CONF_PRESET: self._layout.get(CONF_PRESET, PRESET_SOLAR_ASSISTANT),
                **self._collected_data,
            }

            title = inverter_id
            for dev in self._devices:
                if dev.get("macid") == inverter_id:
                    title = f"Solars - {dev.get('name', dev.get('macid'))}"
                    break

            if self.context.get("source") == config_entries.SOURCE_RECONFIGURE:
                entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                return self.async_update_reload_and_abort(entry, data=final_data)

            return self.async_create_entry(title=title, data=final_data)

        schema_dict: dict[Any, Any] = {}

        # 1. Consumption / Load Power
        load_cand = _auto_detect_candidate(
            self.hass, "sensor", "power", ("W", "kW"),
            ("sensor.total_load_power", "sensor.load_power", "total_load_power", "load_power", "putere_consum", "consum", "house_power", "home_power", "infinisolar_v_x_3_load_power"),
            ("solar", "pv", "battery", "baterie")
        )
        schema_dict[vol.Optional(CONF_SENSOR_LOAD_POWER, **({"default": load_cand} if load_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        # 2. Grid AC Voltage
        grid_cand = _auto_detect_candidate(
            self.hass, "sensor", "voltage", ("V",),
            ("sensor.inverter_1_grid_voltage", "sensor.grid_voltage", "inverter_1_grid_voltage", "grid_voltage", "tensiune_retea", "tensiuneacin", "ac_in_voltage", "grid_volt", "infinisolar_v_x_3_grid_voltage"),
            ("battery", "baterie", "pv", "cell")
        )
        schema_dict[vol.Optional(CONF_SENSOR_GRID_VOLT, **({"default": grid_cand} if grid_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
        )

        # 3. AC Output Voltage
        ac_out_cand = _auto_detect_candidate(
            self.hass, "sensor", "voltage", ("V",),
            ("sensor.inverter_1_ac_output_voltage", "sensor.ac_output_voltage", "inverter_1_ac_output_voltage", "ac_output_voltage", "output_voltage", "tensiune_ac_out", "tensiuneacout", "inverter_out_voltage"),
            ("battery", "baterie", "pv", "grid", "retea", "cell")
        )
        schema_dict[vol.Optional(CONF_SENSOR_AC_OUT_VOLT, **({"default": ac_out_cand} if ac_out_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
        )

        # 4. History Import & Live Update Interval
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
            step_id="grid",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return SolarsSystemsOptionsFlowHandler(config_entry)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle re-configuration request from Home Assistant UI."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        self._api_key = entry.data[CONF_API_KEY]
        self._layout = {
            CONF_INVERTER_ID: entry.data[CONF_INVERTER_ID],
            CONF_INVERTER_COUNT: entry.data.get(CONF_INVERTER_COUNT, 1),
            CONF_MPPT_PER_INVERTER: entry.data.get(CONF_MPPT_PER_INVERTER, 2),
            CONF_HAS_BATTERY: entry.data.get(CONF_HAS_BATTERY, True),
            CONF_PRESET: entry.data.get(CONF_PRESET, PRESET_SOLAR_ASSISTANT),
        }
        return await self.async_step_layout()


class SolarsSystemsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for modifying mapped sensors and settings without reinstalling."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._combined: dict[str, Any] = {**dict(config_entry.data), **dict(config_entry.options)}
        self._collected_data: dict[str, Any] = {}

    def _val(self, key: str, default: Any = None) -> Any:
        return self._combined.get(key, default)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1: Architecture & Layout Options."""
        if user_input is not None:
            self._combined.update(user_input)
            return await self.async_step_solar()

        schema = vol.Schema({
            vol.Required(CONF_INVERTER_COUNT, default=self._val(CONF_INVERTER_COUNT, 1)): vol.In({
                1: "1 Invertor (Standard)",
                2: "2 Invertoare în paralel",
                3: "3 Invertoare în paralel",
                4: "4 Invertoare în paralel",
                5: "5 Invertoare în paralel",
                6: "6 Invertoare în paralel",
            }),
            vol.Required(CONF_MPPT_PER_INVERTER, default=self._val(CONF_MPPT_PER_INVERTER, 2)): vol.In({
                1: "1 MPPT (1 String)",
                2: "2 MPPT-uri (Dual MPPT)",
                3: "3 MPPT-uri",
                4: "4 MPPT-uri",
            }),
            vol.Required(CONF_HAS_BATTERY, default=self._val(CONF_HAS_BATTERY, True)): bool,
        })

        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_solar(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2: Solar PV Panels & Energy Production."""
        if user_input is not None:
            self._collected_data.update(user_input)
            if self._val(CONF_HAS_BATTERY, True):
                return await self.async_step_battery()
            return await self.async_step_grid()

        inv_count = int(self._val(CONF_INVERTER_COUNT, 1))
        mppt_count = int(self._val(CONF_MPPT_PER_INVERTER, 2))

        schema_dict: dict[Any, Any] = {}

        # 1. Total Solar Power
        cur_pv = self._val(CONF_SENSOR_PV_POWER)
        pv_opts = {"default": cur_pv} if cur_pv else {}
        schema_dict[vol.Optional(CONF_SENSOR_PV_POWER, **pv_opts)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        # 2. Dynamic MPPT Voltages and Inverter Powers
        for inv in range(1, inv_count + 1):
            for m in range(1, mppt_count + 1):
                key = f"voltajPV{inv}" if m == 1 else f"voltajPV{inv}_{m}"
                cur_v = self._val(key)
                f_opts = {"default": cur_v} if cur_v else {}
                schema_dict[vol.Optional(key, **f_opts)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
                )

            if inv_count > 1:
                p_key = f"puterePV{inv}"
                cur_p = self._val(p_key)
                p_opts = {"default": cur_p} if cur_p else {}
                schema_dict[vol.Optional(p_key, **p_opts)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="power")
                )

        # 3. Energy Production Sensors
        cur_e_today = self._val(CONF_SENSOR_ENERGY_TODAY)
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_TODAY, **({"default": cur_e_today} if cur_e_today else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        )

        cur_e_month = self._val(CONF_SENSOR_ENERGY_MONTH)
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_MONTH, **({"default": cur_e_month} if cur_e_month else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        )

        cur_e_year = self._val(CONF_SENSOR_ENERGY_YEAR)
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_YEAR, **({"default": cur_e_year} if cur_e_year else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        )

        return self.async_show_form(step_id="solar", data_schema=vol.Schema(schema_dict))

    async def async_step_battery(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 3: Battery & Storage Sensors."""
        if user_input is not None:
            self._collected_data.update(user_input)
            return await self.async_step_grid()

        schema_dict: dict[Any, Any] = {}

        cur_soc = self._val(CONF_SENSOR_BATT_SOC)
        schema_dict[vol.Optional(CONF_SENSOR_BATT_SOC, **({"default": cur_soc} if cur_soc else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="battery")
        )

        cur_volt = self._val(CONF_SENSOR_BATT_VOLT)
        schema_dict[vol.Optional(CONF_SENSOR_BATT_VOLT, **({"default": cur_volt} if cur_volt else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
        )

        cur_curr = self._val(CONF_SENSOR_BATT_CURR)
        schema_dict[vol.Optional(CONF_SENSOR_BATT_CURR, **({"default": cur_curr} if cur_curr else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="current")
        )

        cur_pow = self._val(CONF_SENSOR_BATT_POWER)
        schema_dict[vol.Optional(CONF_SENSOR_BATT_POWER, **({"default": cur_pow} if cur_pow else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        return self.async_show_form(step_id="battery", data_schema=vol.Schema(schema_dict))

    async def async_step_grid(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 4: Grid, Consumption & Update Interval."""
        if user_input is not None:
            self._collected_data.update(user_input)
            final_options = {**self._combined, **self._collected_data}
            return self.async_create_entry(title="", data=final_options)

        schema_dict: dict[Any, Any] = {}

        cur_load = self._val(CONF_SENSOR_LOAD_POWER)
        schema_dict[vol.Optional(CONF_SENSOR_LOAD_POWER, **({"default": cur_load} if cur_load else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        cur_grid = self._val(CONF_SENSOR_GRID_VOLT)
        schema_dict[vol.Optional(CONF_SENSOR_GRID_VOLT, **({"default": cur_grid} if cur_grid else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
        )

        cur_ac_out = self._val(CONF_SENSOR_AC_OUT_VOLT)
        schema_dict[vol.Optional(CONF_SENSOR_AC_OUT_VOLT, **({"default": cur_ac_out} if cur_ac_out else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
        )

        schema_dict[vol.Optional(CONF_UPDATE_INTERVAL, default=self._val(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))] = vol.All(
            vol.Coerce(int), vol.Range(min=10, max=300)
        )

        return self.async_show_form(step_id="grid", data_schema=vol.Schema(schema_dict))
