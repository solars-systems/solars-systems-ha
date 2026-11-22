"""Config flow for Solars Systems integration."""
from __future__ import annotations

import logging
from typing import Any
import re
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
    PRESET_AXPERT,
    PRESET_CUSTOM,
    CONF_HAS_HA_BMS,
    CONF_BMS_COUNT,
    CONF_HAS_HEAT_PUMP,
    CONF_HP_POWER,
    CONF_HP_ENERGY,
    CONF_HP_TEMP_FLOW,
    CONF_HP_TEMP_RETURN,
    CONF_HP_TEMP_DHW,
    CONF_HP_TEMP_BUFFER,
    CONF_HP_TEMP_OUTDOOR,
    CONF_HP_FLOW_RATE,
    CONF_HP_HEAT_POWER,
    CONF_HP_COP,
    CONF_HP_COMP_FREQ,
    CONF_HP_STATUS,
    CONF_HP_DEFROST,
    CONF_HP_FAULT,
    CONF_UPDATE_INTERVAL,
    CONF_SENSOR_PV_POWER,
    CONF_SENSOR_LOAD_POWER,
    CONF_SENSOR_GRID_POWER,
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
    "solar_assistant", "solarassistant", "axpert", "axpert_max", "voltronic", "easun", "pv_day_meter",
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

            # Class or unit matching (with relaxed fallback for sensors lacking explicit device_class)
            class_match = (device_class and d_class == device_class) or (units and u_meas in units)
            if not class_match:
                if device_class == "current" and (u_meas in ("A", "mA") or any(w in name for w in ("current", "curent", "amp"))):
                    class_match = True
                elif device_class == "voltage" and (u_meas in ("V", "mV") or any(w in name for w in ("volt", "tensiune"))):
                    class_match = True
                elif device_class == "battery" and (u_meas == "%" or any(w in name for w in ("soc", "baterie", "battery"))):
                    class_match = True
                elif device_class == "power" and (u_meas in ("W", "kW") or any(w in name for w in ("power", "putere"))):
                    class_match = True
                elif device_class == "energy" and (u_meas in ("kWh", "Wh") or any(w in name for w in ("energy", "energie", "kwh"))):
                    class_match = True

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


def _auto_detect_bms_pack(hass, p: int) -> dict[str, Any]:
    """Auto-detect BMS entities (electrical, delta, temps) for pack p (v1.0.8 style, enhanced for 16 packs and dual-ESP units)."""
    results: dict[str, Any] = {}
    states = list(hass.states.async_all())
    all_eids = [s.entity_id for s in states]

    base_prefix: str | None = None
    soc_cand: str | None = None
    volt_cand: str | None = None

    esp_idx = (p - 1) // 2 + 1
    sub_idx = (p - 1) % 2 + 1

    geo_macs = [
        ("e465b8719228", "9228"),
        ("e465b871a9f8", "a9f8"),
        ("e465b87197fc", "97fc"),
        ("e465b871aa64", "aa64"),
        ("d8bc38fbae14", "ae14")
    ]
    cur_geo = geo_macs[esp_idx - 1] if esp_idx <= len(geo_macs) else None

    p_patterns = [
        f"banc_{p}_", f"banc{p}_", f"banc_{p:02d}_", f"banc{p:02d}_",
        f"banc_{p}", f"banc{p}",
        f"bms{p}_", f"bms_{p}_", f"bms{p:02d}_", f"bms_{p:02d}_",
        f"battery_{p}_", f"battery{p}_", f"battery_{p:02d}_", f"battery{p:02d}_",
        f"baterie_{p}_", f"baterie{p}_", f"baterie_{p:02d}_", f"baterie{p:02d}_",
        f"pack_{p}_", f"pack{p}_", f"pack_{p:02d}_", f"pack{p:02d}_",
        f"jk_bms_{p}_", f"jk_bms_{p:02d}_", f"jkbms_{p}_", f"jkbms_{p:02d}_",
        f"jk_{p}_", f"jk_{p:02d}_", f"daly_{p}_", f"daly_{p:02d}_",
        f"seplos_{p}_", f"seplos_{p:02d}_", f"pylon_{p}_", f"pylon_{p:02d}_",
        f"bms_{p}", f"bms{p}", f"pack_{p}", f"pack{p}", f"battery_{p}", f"battery{p}", f"baterie_{p}", f"baterie{p}",
        # Dual ESP patterns (esp1_bms1, esp2_bms2, etc.)
        f"esp{esp_idx}_bms{sub_idx}", f"esp_{esp_idx}_bms_{sub_idx}", f"esp{esp_idx}_bms_{sub_idx}",
        f"esp{esp_idx}_pack{sub_idx}", f"esp_{esp_idx}_pack_{sub_idx}",
    ]
    if cur_geo:
        p_patterns.extend([
            f"{cur_geo[0]}_{sub_idx}", f"{cur_geo[1]}_{sub_idx}",
            f"{cur_geo[0]}_bms{sub_idx}", f"{cur_geo[1]}_bms{sub_idx}",
            f"{cur_geo[0]}_bms_{sub_idx}", f"{cur_geo[1]}_bms_{sub_idx}"
        ])

    if p == 1:
        p_patterns.extend(["bms1", "bms_1", "bms_", "jk_bms", "jkbms", "daly", "seplos", "pylon", "banc1", "banc_1"])

    # 1. Search for SOC candidate
    for eid in all_eids:
        low = eid.lower()
        if not low.startswith("sensor."):
            continue
        if any(pat in low for pat in p_patterns):
            if any(k in low for k in ("_state_of_charge", "_soc", "soc", "procent_baterie", "capacity_remaining")) and not any(neg in low for neg in ("invert", "inv", "phone", "ups")):
                soc_cand = eid
                break

    # 2. Search for total voltage candidate
    for eid in all_eids:
        low = eid.lower()
        if not low.startswith("sensor."):
            continue
        if any(pat in low for pat in p_patterns):
            if any(k in low for k in ("_total_voltage", "_battery_voltage", "voltage", "voltaj", "tensiune")) and not any(x in low for x in ("cell", "celula", "min", "max", "delta", "avg", "ac", "grid", "pv", "mppt", "invert", "inv")):
                volt_cand = eid
                break

    base_entity = soc_cand or volt_cand
    if base_entity:
        ent_name = base_entity.split(".", 1)[1]
        for suffix in ("state_of_charge", "total_voltage", "battery_voltage", "pack_voltage", "soc", "voltage", "voltaj", "tensiune"):
            if suffix in ent_name:
                base_prefix = ent_name.split(suffix)[0].rstrip("_")
                break

    all_eids_set = set(all_eids)

    def find_ent(domains: list[str], suffixes: list[str], search_regex: str | None = None) -> str | None:
        if base_prefix:
            for d in domains:
                for suf in suffixes:
                    target = f"{d}.{base_prefix}_{suf}"
                    if target in all_eids_set:
                        return target
                    target_plain = f"{d}.{base_prefix}{suf}"
                    if target_plain in all_eids_set:
                        return target_plain
        if search_regex:
            pat = re.compile(search_regex, re.IGNORECASE)
            for eid in all_eids:
                d = eid.split(".", 1)[0]
                if d in domains and pat.search(eid):
                    return eid
        return None

    prefix_re = rf"(?:bms|battery|baterie|pack|banc|jk_bms|jkbms|jk|daly|seplos|pylon|esp{esp_idx})[_\-\s]*0?{p}(?:_|$)" if p > 1 else rf"(?:(?:bms|battery|baterie|pack|banc|jk_bms|jkbms|jk|daly|seplos|pylon)[_\-\s]*0?1(?:_|$)|bms_|jk_?bms|jkbms|daly|seplos|pylon|banc_)"
    results["soc"] = soc_cand or find_ent(["sensor"], ["state_of_charge", "soc"], rf"{prefix_re}.*(?:state_of_charge|soc)$")
    results["voltage"] = volt_cand or find_ent(["sensor"], ["total_voltage", "battery_voltage", "voltage", "voltaj", "tensiune"], rf"{prefix_re}.*(?:total_voltage|battery_voltage|voltage)$")
    results["current"] = find_ent(["sensor"], ["current", "battery_current", "curent"], rf"{prefix_re}.*(?<!balancing_)(?:battery_)?current$")
    results["power"] = find_ent(["sensor"], ["power", "battery_power", "putere"], rf"{prefix_re}.*(?:battery_)?power$")
    results["cell_delta"] = find_ent(["sensor"], ["delta_cell_voltage", "cell_delta", "delta_voltage", "delta"], rf"{prefix_re}.*delta.*(?:cell_voltage|voltage|delta)$")
    results["t1"] = find_ent(["sensor"], ["temperature_sensor_1", "temp_1", "t1", "temperature_1", "battery_temperature", "temperatura_1"], rf"{prefix_re}.*(?:temperature_sensor_1|temp_?1)$")
    results["tmos"] = find_ent(["sensor"], ["power_tube_temperature", "mosfet_temperature", "tmos", "mosfet_temp", "temperatura_mos"], rf"{prefix_re}.*(?:power_tube_temperature|mosfet_temperature|tmos)$")

    return results

def _auto_detect_heat_pump(hass) -> dict[str, Any]:
    """Auto-detect heat pump sensors (power, energy, temps, debit, cop, state, faults)."""
    results: dict[str, Any] = {}
    states = list(hass.states.async_all())

    hp_keywords = (
        "heat_pump", "heatpump", "pompa_caldura", "pompa_de_caldura",
        "nibe", "daikin", "midea", "sunclima", "lg_therma", "therma_v",
        "panasonic_aquarea", "aquarea", "altherma", "vaillant", "chiller", "termopompa"
    )

    def find_hp_sensor(domain: str, keywords: tuple[str, ...], device_class: str | None = None) -> str | None:
        for s in states:
            eid = s.entity_id.lower()
            if not eid.startswith(f"{domain}."):
                continue
            if device_class and s.attributes.get("device_class") != device_class:
                continue
            if any(hp_k in eid for hp_k in hp_keywords):
                if any(kw in eid for kw in keywords):
                    return s.entity_id

        for s in states:
            eid = s.entity_id.lower()
            if not eid.startswith(f"{domain}."):
                continue
            if device_class and s.attributes.get("device_class") != device_class:
                continue
            if any(kw in eid for kw in keywords):
                return s.entity_id
        return None

    results["power"] = find_hp_sensor("sensor", ("power", "putere", "active_power"), device_class="power")
    results["energy"] = find_hp_sensor("sensor", ("energy", "energie", "total_energy"), device_class="energy")
    results["temp_flow"] = find_hp_sensor("sensor", ("water_outlet", "outlet_temp", "flow_temp", "tur_apa", "temp_tur", "supply_temp", "leaving_water"), device_class="temperature")
    results["temp_return"] = find_hp_sensor("sensor", ("water_inlet", "inlet_temp", "return_temp", "retur_apa", "temp_retur", "entering_water"), device_class="temperature")
    results["temp_dhw"] = find_hp_sensor("sensor", ("water_tank", "tank_temp", "dhw_temp", "temp_dhw", "boiler_temp", "temp_boiler", "acm_temp", "temp_acm"), device_class="temperature")
    results["temp_buffer"] = find_hp_sensor("sensor", ("buffer_tank", "buffer_temp", "temp_buffer", "puffer_temp", "temp_puffer"), device_class="temperature")
    results["temp_outdoor"] = find_hp_sensor("sensor", ("outdoor_temp", "temp_outdoor", "ambient_temp", "temp_ambient", "exterior_temp", "temp_exterior"), device_class="temperature")
    results["flow_rate"] = find_hp_sensor("sensor", ("flow_rate", "water_flow", "debit_apa", "debit"))
    results["heat_power"] = find_hp_sensor("sensor", ("thermal_power", "heat_power", "output_heat", "putere_termica", "putere_term"))
    results["cop"] = find_hp_sensor("sensor", ("cop", "instant_cop", "performance_coefficient"))
    results["comp_freq"] = find_hp_sensor("sensor", ("compressor_freq", "comp_hz", "compresor_freq", "frecventa_compresor"))

    climate_cand = None
    for s in states:
        if s.entity_id.startswith("climate."):
            if any(hp_k in s.entity_id.lower() for hp_k in hp_keywords):
                climate_cand = s.entity_id
                break
    if not climate_cand:
        for s in states:
            if s.entity_id.startswith("climate."):
                climate_cand = s.entity_id
                break
    results["status"] = climate_cand or find_hp_sensor("sensor", ("mode", "status", "stare", "heatpump_state"))

    results["defrost"] = find_hp_sensor("binary_sensor", ("defrost", "dezghetare"))
    results["fault"] = find_hp_sensor("binary_sensor", ("fault", "error", "avarie")) or find_hp_sensor("sensor", ("fault_code", "error_code", "avarie"))

    return results


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
        """Step 2: Configure System Layout (Inverter selection, count, battery presence)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._layout = user_input
            return await self.async_step_mppt_layout()

        device_options = {
            dev["macid"]: f"{dev.get('name', dev['macid'])} ({dev['macid']})"
            for dev in self._devices
        }

        schema = vol.Schema({
            vol.Required(CONF_INVERTER_ID, default=list(device_options.keys())[0]): vol.In(device_options),
            vol.Required(CONF_PRESET, default=PRESET_SOLAR_ASSISTANT): vol.In({
                PRESET_SOLAR_ASSISTANT: "SolarAssistant (Detectare automată / Auto-detect)",
                PRESET_AXPERT: "Axpert / Voltronic / Easun (Auto-detectare / Auto-detect)",
                PRESET_CUSTOM: "Personalizat / Alte sisteme / Custom (Deye, Growatt, Huawei, Victron)",
            }),
            vol.Optional(CONF_HAS_HA_BMS, default=False): bool,
            vol.Optional(CONF_HAS_HEAT_PUMP, default=False): bool,
            vol.Required(CONF_INVERTER_COUNT, default=1): vol.In({
                1: "1 Invertor (Standard) / 1 Inverter",
                2: "2 Invertoare în paralel / 2 Parallel Inverters",
                3: "3 Invertoare în paralel / 3 Parallel Inverters",
                4: "4 Invertoare în paralel / 4 Parallel Inverters",
                5: "5 Invertoare în paralel / 5 Parallel Inverters",
                6: "6 Invertoare în paralel / 6 Parallel Inverters",
            }),
            vol.Required(CONF_HAS_BATTERY, default=True): bool,
        })

        return self.async_show_form(
            step_id="layout",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_mppt_layout(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2b: Configure MPPT count per Inverter individually."""
        errors: dict[str, str] = {}
        inv_count = int(self._layout.get(CONF_INVERTER_COUNT, 1))

        if user_input is not None:
            self._layout.update(user_input)
            return await self.async_step_solar()

        schema_dict: dict[Any, Any] = {}
        for inv in range(1, inv_count + 1):
            schema_dict[vol.Required(f"mppt_inv_{inv}", default=1)] = vol.In({
                1: "1 MPPT (1 String)",
                2: "2 MPPT-uri (Dual MPPT)",
                3: "3 MPPT-uri",
                4: "4 MPPT-uri",
            })

        return self.async_show_form(
            step_id="mppt_layout",
            data_schema=vol.Schema(schema_dict),
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
            if self._layout.get(CONF_HAS_HA_BMS, False):
                return await self.async_step_bms()
            if self._layout.get(CONF_HAS_HEAT_PUMP, False):
                return await self.async_step_heat_pump()
            return await self.async_step_grid()

        schema_dict: dict[Any, Any] = {}

        # 1. Total Solar Power (e.g. sensor.total_pv_power, sensor.pv_power, sensor.total_panouri)
        tot_pv_cand = _auto_detect_candidate(
            self.hass, "sensor", "power", ("W", "kW"),
            ("sensor.total_pv_power", "sensor.pv_power", "sensor.axpert_max_pv_power_1", "total_pv_power", "pv_power", "axpert_max_pv_power_1", "axpert_max_pv_power", "voltronic_pv_power", "total_panouri", "total_pv", "putere_pv", "solar_power", "total solar"),
            ("consum", "load", "battery", "baterie"),
            require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_PV_POWER, **({"default": tot_pv_cand} if tot_pv_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        # 2. Dynamic MPPT Voltage, Current & Power fields for each inverter
        for inv in range(1, inv_count + 1):
            inv_mppt_count = int(self._layout.get(f"mppt_inv_{inv}", 1))
            for m in range(1, inv_mppt_count + 1):
                # 2.1 Voltage per MPPT
                v_key = f"voltajPV{inv}" if m == 1 else f"voltajPV{inv}_{m}"
                v_kw = [
                    f"sensor.inverter_{inv}_pv_voltage_{m}",
                    f"inverter_{inv}_pv_voltage_{m}",
                    f"inverter_{inv}_pv_{m}",
                    f"inv{inv}_pv{m}",
                    f"inv{inv}_pv_{m}",
                    f"pv{inv}_{m}",
                    f"pv{m}",
                    f"mppt{m}",
                    f"mppt_{m}",
                    f"growatt_vpv{m}",
                    f"growatt_pv{m}",
                    f"vpv{m}",
                    f"growatt_voltaj",
                    f"pv{inv}",
                    f"sensor.axpert_max_pv_voltage_{m}",
                    f"axpert_max_pv_voltage_{m}",
                    f"axpert_pv_voltage_{m}",
                    f"voltronic_pv_voltage_{m}",
                ]
                v_cand = _auto_detect_candidate(
                    self.hass, "sensor", "voltage", ("V",),
                    tuple(v_kw),
                    ("batt", "baterie", "ac", "grid", "cell")
                )
                v_opts = {"default": v_cand} if v_cand else {}
                schema_dict[vol.Optional(v_key, **v_opts)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
                )

                # 2.2 Current per MPPT
                c_key = f"curentPV{inv}" if m == 1 else f"curentPV{inv}_{m}"
                c_kw = [
                    f"sensor.inverter_{inv}_pv_current_{m}",
                    f"inverter_{inv}_pv_current_{m}",
                    f"inverter_{inv}_pv_{m}_current",
                    f"inverter_{inv}_pv{m}_current",
                    f"inv{inv}_pv{m}_current",
                    f"inv{inv}_pv_{m}_current",
                    f"pv{inv}_current_{m}",
                    f"pv{m}_current",
                    f"pv_{m}_current",
                    f"pv{inv}_{m}_current",
                    f"mppt{m}_current",
                    f"mppt_{m}_current",
                    f"curent_pv{m}",
                    f"curent_pv_{m}",
                    f"curent_pv{inv}_{m}",
                    f"pv{m}_curent",
                    f"growatt_ipv{m}",
                    f"ipv{m}",
                    f"axpert_pv_current_{m}",
                    f"axpert_max_pv_current_{m}",
                    f"solar_assistant_pv{m}_current",
                    f"solarassistant_pv_{m}_current",
                    f"curent_string_{m}",
                    f"string_{m}_current",
                ]
                c_cand = _auto_detect_candidate(
                    self.hass, "sensor", "current", ("A", "mA"),
                    tuple(c_kw),
                    ("batt", "baterie", "ac", "grid")
                )
                c_opts = {"default": c_cand} if c_cand else {}
                schema_dict[vol.Optional(c_key, **c_opts)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                )

                # 2.3 Power per MPPT (if inverter has 2+ MPPTs)
                if inv_mppt_count > 1:
                    p_mppt_key = f"puterePV{inv}_{m}"
                    p_mppt_kw = [
                        f"sensor.inverter_{inv}_pv_power_{m}",
                        f"inverter_{inv}_pv_power_{m}",
                        f"inverter_{inv}_pv_{m}_power",
                        f"inv{inv}_pv{m}_power",
                        f"inv{inv}_pv_{m}_power",
                        f"pv{inv}_power_{m}",
                        f"pv{m}_power",
                        f"mppt{m}_power",
                        f"mppt_{m}_power",
                        f"putere_pv{m}",
                        f"putere_pv{inv}_{m}",
                        f"growatt_ppv{m}",
                        f"ppv{m}",
                    ]
                    p_mppt_cand = _auto_detect_candidate(
                        self.hass, "sensor", "power", ("W", "kW"),
                        tuple(p_mppt_kw),
                        ("consum", "load", "batt", "baterie")
                    )
                    p_mppt_opts = {"default": p_mppt_cand} if p_mppt_cand else {}
                    schema_dict[vol.Optional(p_mppt_key, **p_mppt_opts)] = selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor", device_class="power")
                    )

            # 2.4 Total Power per Inverter if multiple inverters
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
            ("sensor.solar_energy_today", "sensor.energy_today", "sensor.pv_day_meter", "solar_energy_today", "energy_today", "pv_day_meter", "pv_day_energy", "productie_zi", "energie_zi", "daily_energy", "solar_today", "today_energy"),
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
            if self._layout.get(CONF_HAS_HA_BMS, False):
                return await self.async_step_bms()
            if self._layout.get(CONF_HAS_HEAT_PUMP, False):
                return await self.async_step_heat_pump()
            return await self.async_step_grid()

        schema_dict: dict[Any, Any] = {}

        # 1. Battery SOC (%)
        soc_cand = _auto_detect_candidate(
            self.hass, "sensor", "battery", ("%",),
            ("sensor.battery_state_of_charge", "sensor.axpert_max_battery_state_of_charge", "battery_state_of_charge", "axpert_max_battery_state_of_charge", "voltaj_total_baterie_soc", "baterie_soc", "battery_soc", "bms_soc", "procent_baterie", "procentbaterie", "soc"),
            ("phone", "telefon", "laptop", "tablet"),
            require_solar_context=True,
            exclude_cells=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_BATT_SOC, **({"default": soc_cand} if soc_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        # 2. Battery Voltage (V) - STRICT anti-cell filter to eliminate 160+ cell voltage sensors!
        batt_v_cand = _auto_detect_candidate(
            self.hass, "sensor", "voltage", ("V",),
            ("sensor.battery_voltage", "sensor.axpert_max_battery_voltage", "battery_voltage", "axpert_max_battery_voltage", "voltaj_total_baterie", "tensiune_total_baterie", "voltaj_baterie", "tensiune_baterie", "batt_volt", "bms_voltage", "total_voltage"),
            ("ac", "grid", "retea", "pv", "mppt"),
            require_solar_context=True,
            exclude_cells=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_BATT_VOLT, **({"default": batt_v_cand} if batt_v_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        # 3. Battery Current (A) - aggregate or total
        batt_c_cand = _auto_detect_candidate(
            self.hass, "sensor", "current", ("A",),
            ("sensor.battery_current", "sensor.axpert_max_battery_current", "battery_current", "axpert_max_battery_current", "curent_total_baterie", "curent_baterie", "batt_current", "bms_current", "total_current"),
            ("ac", "grid", "retea", "pv"),
            require_solar_context=True,
            exclude_cells=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_BATT_CURR, **({"default": batt_c_cand} if batt_c_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        # 4. Battery Power (W/kW)
        batt_p_cand = _auto_detect_candidate(
            self.hass, "sensor", "power", ("W", "kW"),
            ("sensor.total_battery_power", "sensor.battery_power", "sensor.battery_power_voltronic", "total_battery_power", "putere_baterie", "battery_power", "battery_power_voltronic", "batt_power", "bms_power", "puterebaterie"),
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

    async def async_step_bms(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 4b: Home Assistant BMS Packs Configuration."""
        errors: dict[str, str] = {}
        bms_count = int(self._collected_data.get(CONF_BMS_COUNT, self._layout.get(CONF_BMS_COUNT, 1)))

        if user_input is not None:
            self._collected_data.update(user_input)
            new_count = int(user_input.get(CONF_BMS_COUNT, bms_count))
            if new_count != bms_count:
                return await self.async_step_bms()
            if self._layout.get(CONF_HAS_HEAT_PUMP, False):
                return await self.async_step_heat_pump()
            return await self.async_step_grid()

        # Auto-detect number of BMS packs if not yet customized (support up to 16 packs)
        if CONF_BMS_COUNT not in self._collected_data and CONF_BMS_COUNT not in self._layout:
            detected_count = 1
            all_eids = [s.entity_id.lower() for s in self.hass.states.async_all()]
            for p_chk in range(2, 17):
                pat = re.compile(rf"(?:bms|battery|baterie|pack|jk|jkbms|seplos|daly)[_\-\s]*0?{p_chk}(?:_|$)")
                if any(pat.search(eid) for eid in all_eids):
                    detected_count = max(detected_count, p_chk)
            bms_count = detected_count

        schema_dict: dict[Any, Any] = {
            vol.Required(CONF_BMS_COUNT, default=bms_count): vol.In({
                i: f"{i} Pachete BMS / {i} BMS Packs" if i > 1 else "1 Pachet BMS / 1 BMS Pack"
                for i in range(1, 17)
            })
        }

        for p in range(1, bms_count + 1):
            det = _auto_detect_bms_pack(self.hass, p)

            # SOC & Electrical (v1.0.8 style)
            schema_dict[vol.Optional(f"bms_{p}_soc", **({"default": det["soc"]} if det.get("soc") else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )
            schema_dict[vol.Optional(f"bms_{p}_voltage", **({"default": det["voltage"]} if det.get("voltage") else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )
            schema_dict[vol.Optional(f"bms_{p}_current", **({"default": det["current"]} if det.get("current") else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )
            schema_dict[vol.Optional(f"bms_{p}_power", **({"default": det["power"]} if det.get("power") else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            # Cell Diagnostics
            schema_dict[vol.Optional(f"bms_{p}_cell_delta", **({"default": det["cell_delta"]} if det.get("cell_delta") else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            # Temperatures
            schema_dict[vol.Optional(f"bms_{p}_t1", **({"default": det["t1"]} if det.get("t1") else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            )
            schema_dict[vol.Optional(f"bms_{p}_tmos", **({"default": det["tmos"]} if det.get("tmos") else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            )

        return self.async_show_form(
            step_id="bms",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def async_step_heat_pump(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 4c: Heat Pump & HVAC Configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._collected_data.update(user_input)
            return await self.async_step_grid()

        det = _auto_detect_heat_pump(self.hass)
        schema_dict: dict[Any, Any] = {}

        schema_dict[vol.Optional(CONF_HP_POWER, **({"default": det["power"]} if det.get("power") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )
        schema_dict[vol.Optional(CONF_HP_ENERGY, **({"default": det["energy"]} if det.get("energy") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        )
        schema_dict[vol.Optional(CONF_HP_TEMP_FLOW, **({"default": det["temp_flow"]} if det.get("temp_flow") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
        )
        schema_dict[vol.Optional(CONF_HP_TEMP_RETURN, **({"default": det["temp_return"]} if det.get("temp_return") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
        )
        schema_dict[vol.Optional(CONF_HP_TEMP_DHW, **({"default": det["temp_dhw"]} if det.get("temp_dhw") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
        )
        schema_dict[vol.Optional(CONF_HP_TEMP_BUFFER, **({"default": det["temp_buffer"]} if det.get("temp_buffer") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
        )
        schema_dict[vol.Optional(CONF_HP_TEMP_OUTDOOR, **({"default": det["temp_outdoor"]} if det.get("temp_outdoor") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
        )
        schema_dict[vol.Optional(CONF_HP_FLOW_RATE, **({"default": det["flow_rate"]} if det.get("flow_rate") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP_HEAT_POWER, **({"default": det["heat_power"]} if det.get("heat_power") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP_COP, **({"default": det["cop"]} if det.get("cop") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP_COMP_FREQ, **({"default": det["comp_freq"]} if det.get("comp_freq") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP_STATUS, **({"default": det["status"]} if det.get("status") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["climate", "sensor"])
        )
        schema_dict[vol.Optional(CONF_HP_DEFROST, **({"default": det["defrost"]} if det.get("defrost") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "switch"])
        )
        schema_dict[vol.Optional(CONF_HP_FAULT, **({"default": det["fault"]} if det.get("fault") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"])
        )

        return self.async_show_form(
            step_id="heat_pump",
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
                CONF_HAS_HA_BMS: self._layout.get(CONF_HAS_HA_BMS, False),
                CONF_HAS_HEAT_PUMP: self._layout.get(CONF_HAS_HEAT_PUMP, False),
                CONF_PRESET: self._layout.get(CONF_PRESET, PRESET_SOLAR_ASSISTANT),
                **self._collected_data,
            }

            title = inverter_id
            for dev in self._devices:
                if dev.get("macid") == inverter_id:
                    title = f"Solars - {dev.get('name', dev.get('macid'))}"
                    break

            return self.async_create_entry(title=title, data=final_data)

        schema_dict: dict[Any, Any] = {}

        # 1. Consumption / Load Power
        load_cand = _auto_detect_candidate(
            self.hass, "sensor", "power", ("W", "kW"),
            ("sensor.total_load_power", "sensor.load_power", "sensor.axpert_max_load_power", "total_load_power", "load_power", "axpert_max_load_power", "putere_consum", "consum", "house_power", "home_power", "infinisolar_v_x_3_load_power"),
            ("solar", "pv", "battery", "baterie")
        )
        schema_dict[vol.Optional(CONF_SENSOR_LOAD_POWER, **({"default": load_cand} if load_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        # 1.1 Grid / AC In Power (for Hybrid inverters, Smart Meters, Feed-In / Import)
        grid_pwr_cand = _auto_detect_candidate(
            self.hass, "sensor", "power", ("W", "kW"),
            (
                "sensor.grid_power", "sensor.inverter_1_grid_power", "sensor.solar_assistant_grid_power",
                "sensor.ac_input_power", "sensor.grid_active_power", "sensor.total_grid_power",
                "grid_power", "ac_input_power", "grid_active_power", "putere_retea", "putereacin",
                "infinisolar_v_x_3_grid_power", "axpert_max_grid_power", "deye_grid_power"
            ),
            ("battery", "baterie", "pv", "load", "consum", "cell")
        )
        schema_dict[vol.Optional(CONF_SENSOR_GRID_POWER, **({"default": grid_pwr_cand} if grid_pwr_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        # 2. Grid AC Voltage
        grid_cand = _auto_detect_candidate(
            self.hass, "sensor", "voltage", ("V",),
            ("sensor.inverter_1_grid_voltage", "sensor.grid_voltage", "sensor.axpert_max_grid_voltage", "inverter_1_grid_voltage", "grid_voltage", "axpert_max_grid_voltage", "tensiune_retea", "tensiuneacin", "ac_in_voltage", "grid_volt", "infinisolar_v_x_3_grid_voltage"),
            ("battery", "baterie", "pv", "cell")
        )
        schema_dict[vol.Optional(CONF_SENSOR_GRID_VOLT, **({"default": grid_cand} if grid_cand else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
        )

        # 3. AC Output Voltage
        ac_out_cand = _auto_detect_candidate(
            self.hass, "sensor", "voltage", ("V",),
            ("sensor.inverter_1_ac_output_voltage", "sensor.ac_output_voltage", "sensor.axpert_max_ac_output_voltage", "inverter_1_ac_output_voltage", "ac_output_voltage", "axpert_max_ac_output_voltage", "output_voltage", "tensiune_ac_out", "tensiuneacout", "inverter_out_voltage"),
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
    ) -> SolarsSystemsOptionsFlowHandler:
        """Create the options flow."""
        return SolarsSystemsOptionsFlowHandler()


class SolarsSystemsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for modifying mapped sensors and settings without reinstalling."""

    def __init__(self) -> None:
        """Initialize options flow."""
        super().__init__()
        self._collected_data: dict[str, Any] = {}

    def _val(self, key: str, default: Any = None) -> Any:
        combined = {}
        if hasattr(self, "config_entry") and self.config_entry:
            combined = {**dict(self.config_entry.data), **dict(self.config_entry.options)}
        return combined.get(key, default)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Step 1: Architecture & Layout Options."""
        if user_input is not None:
            self._collected_data.update(user_input)
            return await self.async_step_mppt_layout()

        try:
            cur_inv = int(self._val(CONF_INVERTER_COUNT, 1))
        except (ValueError, TypeError):
            cur_inv = 1
        if cur_inv not in (1, 2, 3, 4, 5, 6):
            cur_inv = 1

        schema = vol.Schema({
            vol.Required(CONF_INVERTER_COUNT, default=cur_inv): vol.In({
                1: "1 Invertor (Standard) / 1 Inverter",
                2: "2 Invertoare în paralel / 2 Parallel Inverters",
                3: "3 Invertoare în paralel / 3 Parallel Inverters",
                4: "4 Invertoare în paralel / 4 Parallel Inverters",
                5: "5 Invertoare în paralel / 5 Parallel Inverters",
                6: "6 Invertoare în paralel / 6 Parallel Inverters",
            }),
            vol.Required(CONF_HAS_BATTERY, default=bool(self._val(CONF_HAS_BATTERY, True))): bool,
            vol.Optional(CONF_HAS_HA_BMS, default=bool(self._val(CONF_HAS_HA_BMS, False))): bool,
            vol.Optional(CONF_HAS_HEAT_PUMP, default=bool(self._val(CONF_HAS_HEAT_PUMP, False))): bool,
        })

        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_mppt_layout(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Step 1b: Architecture & MPPT count per Inverter."""
        inv_count = int(self._collected_data.get(CONF_INVERTER_COUNT, self._val(CONF_INVERTER_COUNT, 1)))

        if user_input is not None:
            self._collected_data.update(user_input)
            return await self.async_step_solar()

        schema_dict: dict[Any, Any] = {}
        for inv in range(1, inv_count + 1):
            cur_mppt = 1
            try:
                cur_mppt = int(self._val(f"mppt_inv_{inv}", 1))
            except (ValueError, TypeError):
                cur_mppt = 1
            if cur_mppt not in (1, 2, 3, 4):
                cur_mppt = 1

            schema_dict[vol.Required(f"mppt_inv_{inv}", default=cur_mppt)] = vol.In({
                1: "1 MPPT (1 String)",
                2: "2 MPPT-uri (Dual MPPT)",
                3: "3 MPPT-uri",
                4: "4 MPPT-uri",
            })

        return self.async_show_form(step_id="mppt_layout", data_schema=vol.Schema(schema_dict))

    async def async_step_solar(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Step 2: Solar PV Panels & Energy Production."""
        if user_input is not None:
            self._collected_data.update(user_input)
            has_batt = self._collected_data.get(CONF_HAS_BATTERY, self._val(CONF_HAS_BATTERY, True))
            if has_batt:
                return await self.async_step_battery()
            has_bms = self._collected_data.get(CONF_HAS_HA_BMS, self._val(CONF_HAS_HA_BMS, False))
            if has_bms:
                return await self.async_step_bms()
            has_hp = self._collected_data.get(CONF_HAS_HEAT_PUMP, self._val(CONF_HAS_HEAT_PUMP, False))
            if has_hp:
                return await self.async_step_heat_pump()
            return await self.async_step_grid()

        inv_count = int(self._collected_data.get(CONF_INVERTER_COUNT, self._val(CONF_INVERTER_COUNT, 1)))

        schema_dict: dict[Any, Any] = {}

        # 1. Total Solar Power
        cur_pv = self._val(CONF_SENSOR_PV_POWER)
        pv_opts = {"default": cur_pv} if cur_pv else {}
        schema_dict[vol.Optional(CONF_SENSOR_PV_POWER, **pv_opts)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        # 2. Dynamic MPPT Voltages, Currents and Inverter Powers
        for inv in range(1, inv_count + 1):
            inv_mppt_count = int(self._collected_data.get(f"mppt_inv_{inv}", self._val(f"mppt_inv_{inv}", 1)))
            for m in range(1, inv_mppt_count + 1):
                # Voltage
                v_key = f"voltajPV{inv}" if m == 1 else f"voltajPV{inv}_{m}"
                cur_v = self._val(v_key)
                f_opts = {"default": cur_v} if cur_v else {}
                schema_dict[vol.Optional(v_key, **f_opts)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="voltage")
                )

                # Current
                c_key = f"curentPV{inv}" if m == 1 else f"curentPV{inv}_{m}"
                cur_c = self._val(c_key)
                c_opts = {"default": cur_c} if cur_c else {}
                schema_dict[vol.Optional(c_key, **c_opts)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                )

                # Power per MPPT
                if inv_mppt_count > 1:
                    p_mppt_key = f"puterePV{inv}_{m}"
                    cur_p_mppt = self._val(p_mppt_key)
                    p_mppt_opts = {"default": cur_p_mppt} if cur_p_mppt else {}
                    schema_dict[vol.Optional(p_mppt_key, **p_mppt_opts)] = selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor", device_class="power")
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
    ) -> Any:
        """Step 3: Battery & Storage Sensors."""
        if user_input is not None:
            self._collected_data.update(user_input)
            has_bms = self._collected_data.get(CONF_HAS_HA_BMS)
            if has_bms is None:
                has_bms = self._val(CONF_HAS_HA_BMS, False)
            if has_bms:
                return await self.async_step_bms()
            has_hp = self._collected_data.get(CONF_HAS_HEAT_PUMP)
            if has_hp is None:
                has_hp = self._val(CONF_HAS_HEAT_PUMP, False)
            if has_hp:
                return await self.async_step_heat_pump()
            return await self.async_step_grid()

        schema_dict: dict[Any, Any] = {}

        cur_soc = self._val(CONF_SENSOR_BATT_SOC)
        schema_dict[vol.Optional(CONF_SENSOR_BATT_SOC, **({"default": cur_soc} if cur_soc else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_volt = self._val(CONF_SENSOR_BATT_VOLT)
        schema_dict[vol.Optional(CONF_SENSOR_BATT_VOLT, **({"default": cur_volt} if cur_volt else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_curr = self._val(CONF_SENSOR_BATT_CURR)
        schema_dict[vol.Optional(CONF_SENSOR_BATT_CURR, **({"default": cur_curr} if cur_curr else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_pow = self._val(CONF_SENSOR_BATT_POWER)
        schema_dict[vol.Optional(CONF_SENSOR_BATT_POWER, **({"default": cur_pow} if cur_pow else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        return self.async_show_form(step_id="battery", data_schema=vol.Schema(schema_dict))

    async def async_step_bms(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Step 4b: Options for BMS Packs."""
        bms_count = int(self._collected_data.get(CONF_BMS_COUNT, self._val(CONF_BMS_COUNT, 0) or 1))

        if user_input is not None:
            self._collected_data.update(user_input)
            new_count = int(user_input.get(CONF_BMS_COUNT, bms_count))
            if new_count != bms_count:
                return await self.async_step_bms()
            has_hp = self._collected_data.get(CONF_HAS_HEAT_PUMP)
            if has_hp is None:
                has_hp = self._val(CONF_HAS_HEAT_PUMP, False)
            if has_hp:
                return await self.async_step_heat_pump()
            return await self.async_step_grid()

        # Auto-detect number of BMS packs if not yet customized (support up to 16 packs)
        if CONF_BMS_COUNT not in self._collected_data and not self._val(CONF_BMS_COUNT):
            detected_count = 1
            all_eids = [s.entity_id.lower() for s in self.hass.states.async_all()]
            for p_chk in range(2, 17):
                pat = re.compile(rf"(?:bms|battery|baterie|pack|jk|jkbms|seplos|daly)[_\-\s]*0?{p_chk}(?:_|$)")
                if any(pat.search(eid) for eid in all_eids):
                    detected_count = max(detected_count, p_chk)
            bms_count = detected_count

        schema_dict: dict[Any, Any] = {
            vol.Required(CONF_BMS_COUNT, default=bms_count): vol.In({
                i: f"{i} Pachete BMS / {i} BMS Packs" if i > 1 else "1 Pachet BMS / 1 BMS Pack"
                for i in range(1, 17)
            })
        }

        for p in range(1, bms_count + 1):
            det = _auto_detect_bms_pack(self.hass, p)

            # SOC & Electrical (v1.0.8 style)
            cur_soc = self._val(f"bms_{p}_soc") or det.get("soc")
            schema_dict[vol.Optional(f"bms_{p}_soc", **({"default": cur_soc} if cur_soc else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            cur_v = self._val(f"bms_{p}_voltage") or det.get("voltage")
            schema_dict[vol.Optional(f"bms_{p}_voltage", **({"default": cur_v} if cur_v else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            cur_c = self._val(f"bms_{p}_current") or det.get("current")
            schema_dict[vol.Optional(f"bms_{p}_current", **({"default": cur_c} if cur_c else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            cur_p = self._val(f"bms_{p}_power") or det.get("power")
            schema_dict[vol.Optional(f"bms_{p}_power", **({"default": cur_p} if cur_p else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            # Cell Diagnostics
            cur_delta = self._val(f"bms_{p}_cell_delta") or det.get("cell_delta")
            schema_dict[vol.Optional(f"bms_{p}_cell_delta", **({"default": cur_delta} if cur_delta else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            # Temperatures
            cur_t1 = self._val(f"bms_{p}_t1") or det.get("t1")
            schema_dict[vol.Optional(f"bms_{p}_t1", **({"default": cur_t1} if cur_t1 else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            )

            cur_tmos = self._val(f"bms_{p}_tmos") or det.get("tmos")
            schema_dict[vol.Optional(f"bms_{p}_tmos", **({"default": cur_tmos} if cur_tmos else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            )

        return self.async_show_form(
            step_id="bms",
            data_schema=vol.Schema(schema_dict)
        )

    async def async_step_heat_pump(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Step 4c: Options for Heat Pump & HVAC."""
        if user_input is not None:
            self._collected_data.update(user_input)
            return await self.async_step_grid()

        det = _auto_detect_heat_pump(self.hass)
        schema_dict: dict[Any, Any] = {}

        cur_pwr = self._val(CONF_HP_POWER) or det.get("power")
        schema_dict[vol.Optional(CONF_HP_POWER, **({"default": cur_pwr} if cur_pwr else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        cur_en = self._val(CONF_HP_ENERGY) or det.get("energy")
        schema_dict[vol.Optional(CONF_HP_ENERGY, **({"default": cur_en} if cur_en else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="energy")
        )

        cur_flow = self._val(CONF_HP_TEMP_FLOW) or det.get("temp_flow")
        schema_dict[vol.Optional(CONF_HP_TEMP_FLOW, **({"default": cur_flow} if cur_flow else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
        )

        cur_ret = self._val(CONF_HP_TEMP_RETURN) or det.get("temp_return")
        schema_dict[vol.Optional(CONF_HP_TEMP_RETURN, **({"default": cur_ret} if cur_ret else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
        )

        cur_dhw = self._val(CONF_HP_TEMP_DHW) or det.get("temp_dhw")
        schema_dict[vol.Optional(CONF_HP_TEMP_DHW, **({"default": cur_dhw} if cur_dhw else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
        )

        cur_buf = self._val(CONF_HP_TEMP_BUFFER) or det.get("temp_buffer")
        schema_dict[vol.Optional(CONF_HP_TEMP_BUFFER, **({"default": cur_buf} if cur_buf else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
        )

        cur_out = self._val(CONF_HP_TEMP_OUTDOOR) or det.get("temp_outdoor")
        schema_dict[vol.Optional(CONF_HP_TEMP_OUTDOOR, **({"default": cur_out} if cur_out else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
        )

        cur_fr = self._val(CONF_HP_FLOW_RATE) or det.get("flow_rate")
        schema_dict[vol.Optional(CONF_HP_FLOW_RATE, **({"default": cur_fr} if cur_fr else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_hp = self._val(CONF_HP_HEAT_POWER) or det.get("heat_power")
        schema_dict[vol.Optional(CONF_HP_HEAT_POWER, **({"default": cur_hp} if cur_hp else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_cop = self._val(CONF_HP_COP) or det.get("cop")
        schema_dict[vol.Optional(CONF_HP_COP, **({"default": cur_cop} if cur_cop else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_cf = self._val(CONF_HP_COMP_FREQ) or det.get("comp_freq")
        schema_dict[vol.Optional(CONF_HP_COMP_FREQ, **({"default": cur_cf} if cur_cf else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_st = self._val(CONF_HP_STATUS) or det.get("status")
        schema_dict[vol.Optional(CONF_HP_STATUS, **({"default": cur_st} if cur_st else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["climate", "sensor"])
        )

        cur_def = self._val(CONF_HP_DEFROST) or det.get("defrost")
        schema_dict[vol.Optional(CONF_HP_DEFROST, **({"default": cur_def} if cur_def else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "switch"])
        )

        cur_flt = self._val(CONF_HP_FAULT) or det.get("fault")
        schema_dict[vol.Optional(CONF_HP_FAULT, **({"default": cur_flt} if cur_flt else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"])
        )

        return self.async_show_form(
            step_id="heat_pump",
            data_schema=vol.Schema(schema_dict)
        )

    async def async_step_grid(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Step 4: Grid, Consumption & Update Interval."""
        if user_input is not None:
            self._collected_data.update(user_input)
            final_options = {**dict(self.config_entry.data), **dict(self.config_entry.options), **self._collected_data}
            return self.async_create_entry(data=final_options)

        schema_dict: dict[Any, Any] = {}

        cur_load = self._val(CONF_SENSOR_LOAD_POWER)
        schema_dict[vol.Optional(CONF_SENSOR_LOAD_POWER, **({"default": cur_load} if cur_load else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor", device_class="power")
        )

        cur_grid_pwr = self._val(CONF_SENSOR_GRID_POWER)
        schema_dict[vol.Optional(CONF_SENSOR_GRID_POWER, **({"default": cur_grid_pwr} if cur_grid_pwr else {}))] = selector.EntitySelector(
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
