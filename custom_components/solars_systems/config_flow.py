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
    CONF_HP_TEMP_ROOM,
    CONF_HP_TEMP_OUTDOOR,
    CONF_HP_FLOW_RATE,
    CONF_HP_HEAT_POWER,
    CONF_HP_COP,
    CONF_HP_COMP_FREQ,
    CONF_HP_STATUS,
    CONF_HP_DEFROST,
    CONF_HP_FAULT,
    CONF_HAS_HEAT_PUMP_2,
    CONF_HP2_POWER,
    CONF_HP2_ENERGY,
    CONF_HP2_TEMP_FLOW,
    CONF_HP2_TEMP_RETURN,
    CONF_HP2_TEMP_DHW,
    CONF_HP2_TEMP_BUFFER,
    CONF_HP2_TEMP_ROOM,
    CONF_HP2_TEMP_OUTDOOR,
    CONF_HP2_FLOW_RATE,
    CONF_HP2_HEAT_POWER,
    CONF_HP2_COP,
    CONF_HP2_COMP_FREQ,
    CONF_HP2_STATUS,
    CONF_HP2_DEFROST,
    CONF_HP2_FAULT,
    CONF_UPDATE_INTERVAL,
    CONF_SENSOR_PV_POWER,
    CONF_SENSOR_LOAD_POWER,
    CONF_SENSOR_LOAD_ENERGY_TODAY,
    CONF_SENSOR_LOAD_ENERGY_MONTH,
    CONF_UNIT_LOAD_POWER,
    CONF_UNIT_GRID_POWER,
    CONF_UNIT_PV_POWER,
    CONF_UNIT_HP_POWER,
    CONF_UNIT_HP2_POWER,
    POWER_UNIT_AUTO,
    POWER_UNIT_W,
    POWER_UNIT_KW,
    CONF_SENSOR_GRID_POWER,
    CONF_SENSOR_GRID_ENERGY_TODAY,
    CONF_SENSOR_GRID_ENERGY_MONTH,
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

def _sc(hass_or_val: Any, val: Any = None) -> str | None:
    """Sanitize entity ID candidate: must be non-empty string starting with sensor."""
    target = val if val is not None else hass_or_val
    if target and isinstance(target, str) and target.startswith("sensor."):
        return target
    return None

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
    already_used: set[str] | None = None,
) -> str | None:
    """Find a candidate sensor matching criteria with strict non-solar exclusions."""
    # 1. Exact entity_id check first
    for kw in keywords:
        if kw.startswith("sensor."):
            if already_used and kw in already_used:
                continue
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
            if already_used and entity_id in already_used:
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


def _discover_all_bms_clusters(hass) -> list[str]:
    """Find all unique BMS clusters/prefixes in Home Assistant."""
    states = list(hass.states.async_all())
    clusters = []
    seen = set()
    soc_suffixes = ("_state_of_charge", "_soc", "_battery_state_of_charge", "_procent_baterie")
    volt_suffixes = ("_total_voltage", "_battery_voltage", "_pack_voltage")

    for s in states:
        low = s.entity_id.lower()
        if not low.startswith("sensor."):
            continue
        if any(neg in low for neg in ("invert", "inv", "phone", "ups", "telefon", "laptop", "cell", "celula")):
            continue
        for suf in soc_suffixes:
            if suf in low:
                base = low.split(".", 1)[1].split(suf)[0].rstrip("_")
                if base and base not in seen:
                    seen.add(base)
                    clusters.append(base)
                break

    for s in states:
        low = s.entity_id.lower()
        if not low.startswith("sensor."):
            continue
        if any(neg in low for neg in ("invert", "inv", "phone", "ups", "telefon", "laptop", "cell", "celula")):
            continue
        for suf in volt_suffixes:
            if suf in low:
                base = low.split(".", 1)[1].split(suf)[0].rstrip("_")
                if base and base not in seen:
                    seen.add(base)
                    clusters.append(base)
                break

    def natural_sort_key(s: str):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

    clusters.sort(key=natural_sort_key)
    return clusters


def _populate_bms_pack_from_base(hass, base_eid_or_prefix: str, p: int) -> dict[str, str]:
    """Auto-populate all BMS fields for pack p given a single base entity or prefix."""
    states = list(hass.states.async_all())
    # Crucial: BMS inputs strictly belong to the 'sensor' domain
    all_eids = [s.entity_id for s in states if s.entity_id.startswith("sensor.")]

    candidates: list[str] = []

    # 1. Device ID matching from entity registry (highest priority & precision)
    try:
        from homeassistant.helpers import entity_registry as er
        ent_reg = er.async_get(hass)
        entry = ent_reg.async_get(base_eid_or_prefix) if "." in base_eid_or_prefix else None
        if entry and entry.device_id:
            candidates = [
                e.entity_id for e in ent_reg.entities.values()
                if e.device_id == entry.device_id and not e.disabled and e.entity_id.startswith("sensor.")
            ]
    except Exception as ex:
        _LOGGER.debug("Could not resolve device_id for %s: %s", base_eid_or_prefix, ex)

    # 2. Fallback on clean prefix with strict boundary check (prevents bms_1 matching bms_10)
    if not candidates:
        ent_name = base_eid_or_prefix.split(".", 1)[1] if "." in base_eid_or_prefix else base_eid_or_prefix
        for suf in ("_state_of_charge", "_soc", "_total_voltage", "_battery_voltage", "_pack_voltage", "_voltage", "_voltaj", "_current", "_curent"):
            if suf in ent_name:
                ent_name = ent_name.split(suf)[0].rstrip("_")
                break
        pat = re.compile(rf"^sensor\.{re.escape(ent_name.lower())}(?:_|$)", re.IGNORECASE)
        candidates = [e for e in all_eids if pat.match(e.lower())]

    res: dict[str, str] = {}

    def match(keywords, exclude=()):
        for kw in keywords:
            for c in candidates:
                low = c.lower()
                if any(ex in low for ex in exclude):
                    continue
                if kw in low:
                    return c
        return None

    res[f"bms_{p}_soc"] = match(["_state_of_charge", "_soc", "soc", "procent_baterie"])
    res[f"bms_{p}_voltage"] = match(
        ["_total_voltage", "_battery_voltage", "_pack_voltage", "_voltage", "voltaj", "voltage"],
        exclude=["cell", "celula", "delta", "trigger", "calibration", "off", "limit", "setting", "alarm", "min", "max", "protect"]
    )
    res[f"bms_{p}_current"] = match(
        ["_current", "curent", "current"],
        exclude=["balancing", "calibration", "trigger", "limit", "setting", "alarm", "protect"]
    )
    res[f"bms_{p}_power"] = match(
        ["_power", "power", "putere"],
        exclude=["power_off", "power_on", "switch", "factor", "setting", "limit"]
    )
    res[f"bms_{p}_cell_delta"] = match(["delta_cell_voltage", "cell_delta", "delta"])
    res[f"bms_{p}_cell_min"] = match(["cell_voltage_min", "min_cell", "cell_min"])
    res[f"bms_{p}_cell_max"] = match(["cell_voltage_max", "max_cell", "cell_max"])
    res[f"bms_{p}_t1"] = match(["temperature_sensor_1", "temp_1", "t1", "battery_temperature"], exclude=["mos", "power_tube"])
    res[f"bms_{p}_t2"] = match(["temperature_sensor_2", "temp_2", "t2"], exclude=["mos", "power_tube"])
    res[f"bms_{p}_tmos"] = match(["power_tube_temperature", "mosfet_temperature", "tmos", "mosfet_temp"])

    # Cell loop with (?!\d) lookahead boundary (cell_1 never matches cell_10..16)
    for c_idx in range(1, 17):
        cell_re = re.compile(rf"(?:cell_voltage|celula|cell)[_\s]*0?{c_idx}(?!\d)", re.IGNORECASE)
        cv = next((c for c in candidates if cell_re.search(c)), None)
        if cv:
            res[f"bms_{p}_cell_{c_idx}"] = cv

    return {k: v for k, v in res.items() if v and v.startswith("sensor.")}


def _populate_heat_pump_from_base(hass, base_eid: str) -> dict[str, str]:
    """Auto-populate all heat pump fields given a single entity belonging to the heat pump."""
    states = list(hass.states.async_all())
    all_eids = [s.entity_id for s in states]

    ent_name = base_eid.split(".", 1)[1] if "." in base_eid else base_eid
    prefix = ""
    for kw in ("sunclima_modbus", "sunclima", "heat_pump", "heatpump", "pompa_caldura", "pompa_de_caldura", "pompa", "altherma", "aquarea", "nibe", "daikin"):
        if kw in ent_name.lower():
            parts = ent_name.lower().split(kw)
            prefix = kw + (parts[1].split("_")[0] if len(parts) > 1 and parts[1].startswith("_") else "")
            break
    if not prefix:
        for s in ("water_outlet", "water_inlet", "outlet", "inlet", "temp", "power", "energy", "flow"):
            if s in ent_name.lower():
                prefix = ent_name.lower().split(s)[0].rstrip("_")
                break
    if not prefix:
        prefix = ent_name.split("_")[0]

    all_hp_cands = [e for e in all_eids if prefix in e.lower()]
    sensor_cands = [e for e in all_hp_cands if e.lower().startswith("sensor.")]

    res: dict[str, str] = {}

    def match(cands, keywords, exclude=()):
        for c in cands:
            low = c.lower()
            if any(ex in low for ex in exclude):
                continue
            if any(kw in low for kw in keywords):
                return c
        return None

    # Temperatures MUST ONLY MATCH sensor_cands (never binary_sensors!)
    res[CONF_HP_TEMP_FLOW] = match(sensor_cands, ["water_outlet", "outlet_t7", "flow_temp", "temp_tur", "tur", "outlet"], exclude=["fan", "status", "switch"])
    res[CONF_HP_TEMP_RETURN] = match(sensor_cands, ["water_inlet", "inlet_t8", "inlet_t6", "return_temp", "temp_retur", "retur", "inlet"], exclude=["fan", "status", "switch"])
    res[CONF_HP_TEMP_DHW] = match(sensor_cands, ["water_tank", "tank_t5", "dhw", "boiler", "acm", "t5"], exclude=["fan", "status", "switch"])
    res[CONF_HP_TEMP_BUFFER] = match(sensor_cands, ["buffer", "puffer", "temp_buffer", "t6"], exclude=["fan", "status", "switch"])
    res[CONF_HP_TEMP_ROOM] = match(sensor_cands, ["room_temp", "indoor_temp", "temp_camera", "camera", "temperatura_camera", "temp_room", "room_temperature", "indoor_temperature", "t1_room"], exclude=["fan", "status", "switch", "binary_sensor"])
    res[CONF_HP_TEMP_OUTDOOR] = match(sensor_cands, ["outdoor_temp", "ambient_temp", "temp_outdoor", "temp_ambient", "exterior_temp", "outdoor_temperature", "temp_t4", "t4", "sc_outdoor", "sc_ambient"], exclude=["fan", "ventilator", "status", "switch", "binary_sensor", "heater", "pump", "health"])
    res[CONF_HP_FLOW_RATE] = match(sensor_cands, ["water_flow", "flow_rate", "debit"], exclude=["health", "index"])
    res[CONF_HP_COMP_FREQ] = match(sensor_cands, ["compressor_freq", "comp_freq", "comp_hz", "frecventa_compresor", "compressor"], exclude=["target", "tracking", "health", "index"])
    res[CONF_HP_COP] = match(sensor_cands, ["_cop", "cop", "instant_cop"], exclude=["health", "index", "target", "tracking"])
    res[CONF_HP_HEAT_POWER] = match(sensor_cands, ["thermal_power", "heat_power", "putere_termica", "thermal"], exclude=["index", "health", "target", "tracking"])
    res[CONF_HP_POWER] = match(sensor_cands, ["running_power", "active_power", "electric_power", "power", "putere"], exclude=["thermal", "heat", "index", "health", "target"])
    res[CONF_HP_ENERGY] = match(sensor_cands, ["energy", "energie", "total_energy", "kwh"], exclude=["index", "health"])
    res[CONF_HP_FAULT] = match(all_hp_cands, ["fault", "error", "eroare", "alarm"])
    res[CONF_HP_DEFROST] = match(all_hp_cands, ["defrost_active", "defrosting", "defrost", "degivrare"], exclude=["health", "time", "interval", "cycle"])
    res[CONF_HP_STATUS] = match(all_hp_cands, ["eco", "mode", "status", "stare", "run_state", "zone1_power", "zone_1_power"], exclude=["fan", "ventilator", "health"])

    return {k: v for k, v in res.items() if v}

def _auto_detect_bms_pack(hass, p: int) -> dict[str, Any]:
    """Auto-detect BMS entities for pack p (cluster-aware)."""
    clusters = _discover_all_bms_clusters(hass)
    if p <= len(clusters):
        pop = _populate_bms_pack_from_base(hass, clusters[p - 1], p)
        return {
            "soc": pop.get(f"bms_{p}_soc"),
            "voltage": pop.get(f"bms_{p}_voltage"),
            "current": pop.get(f"bms_{p}_current"),
            "power": pop.get(f"bms_{p}_power"),
            "cell_delta": pop.get(f"bms_{p}_cell_delta"),
            "t1": pop.get(f"bms_{p}_t1"),
            "tmos": pop.get(f"bms_{p}_tmos")
        }

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


    # Check whether multiple numbered BMS packs exist in the system (2..16)
    has_multiple_bms = False
    for eid in all_eids:
        if any(re.search(rf"(?:bms|battery|baterie|pack|jk|jkbms|seplos|daly|banc)[_\-\s]*0?{other_p}(?!\d)", eid.lower()) for other_p in range(2, 17)):
            has_multiple_bms = True
            break

    # Boundary regex matching for pack p (prevents pack 1 matching pack 10..16)
    pack_re = re.compile(rf"(?:banc|bms|battery|baterie|pack|jk_bms|jkbms|jk|daly|seplos|pylon|esp\d+_bms|esp_\d+_bms)[_\-\s]*0?{p}(?!\d)", re.IGNORECASE)
    geo_re = re.compile(rf"(?:{cur_geo[0]}|{cur_geo[1]})[_\-\s]*(?:bms[_\-\s]*)?0?{sub_idx}(?!\d)", re.IGNORECASE) if cur_geo else None
    generic_re = re.compile(r"(?:bms|jk_bms|jkbms|daly|seplos|pylon|banc)", re.IGNORECASE) if (p == 1 and not has_multiple_bms) else None

    def match_pack(low_str: str) -> bool:
        if pack_re.search(low_str):
            return True
        if geo_re and geo_re.search(low_str):
            return True
        if generic_re and generic_re.search(low_str):
            return True
        return False

    # 1. Search for SOC candidate
    for eid in all_eids:
        low = eid.lower()
        if not low.startswith("sensor."):
            continue
        if match_pack(low):
            if any(k in low for k in ("_state_of_charge", "_soc", "soc", "procent_baterie", "capacity_remaining")) and not any(neg in low for neg in ("invert", "inv", "phone", "ups")):
                soc_cand = eid
                break

    # 2. Search for total voltage candidate
    for eid in all_eids:
        low = eid.lower()
        if not low.startswith("sensor."):
            continue
        if match_pack(low):
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
    states = list(hass.states.async_all())
    # 1. First check if any sunclima or heatpump entity exists
    for s in states:
        low = s.entity_id.lower()
        if any(hp_k in low for hp_k in ("sunclima", "heat_pump", "heatpump", "pompa_caldura", "pompa_de_caldura", "altherma", "aquarea")):
            pop = _populate_heat_pump_from_base(hass, s.entity_id)
            if pop.get(CONF_HP_TEMP_FLOW) or pop.get(CONF_HP_POWER) or pop.get(CONF_HP_TEMP_RETURN):
                return {
                    "power": pop.get(CONF_HP_POWER),
                    "energy": pop.get(CONF_HP_ENERGY),
                    "temp_flow": pop.get(CONF_HP_TEMP_FLOW),
                    "temp_return": pop.get(CONF_HP_TEMP_RETURN),
                    "temp_dhw": pop.get(CONF_HP_TEMP_DHW),
                    "temp_buffer": pop.get(CONF_HP_TEMP_BUFFER),
                    "temp_room": pop.get(CONF_HP_TEMP_ROOM),
                    "temp_outdoor": pop.get(CONF_HP_TEMP_OUTDOOR),
                    "flow_rate": pop.get(CONF_HP_FLOW_RATE),
                    "heat_power": pop.get(CONF_HP_HEAT_POWER),
                    "cop": pop.get(CONF_HP_COP),
                    "comp_freq": pop.get(CONF_HP_COMP_FREQ),
                    "status": pop.get(CONF_HP_STATUS),
                    "defrost": pop.get(CONF_HP_DEFROST),
                    "fault": pop.get(CONF_HP_FAULT),
                }

    results: dict[str, Any] = {}

    hp_keywords = (
        "heat_pump", "heatpump", "pompa_caldura", "pompa_de_caldura",
        "nibe", "daikin", "midea", "sunclima", "lg_therma", "therma_v",
        "panasonic_aquarea", "aquarea", "altherma", "vaillant", "chiller", "termopompa"
    )

    def find_hp_sensor(domain: str, keywords: tuple[str, ...], device_class: str | None = None) -> str | None:
        if device_class:
            for s in states:
                eid = s.entity_id.lower()
                if not eid.startswith(f"{domain}."):
                    continue
                if s.attributes.get("device_class") == device_class and any(hp_k in eid for hp_k in hp_keywords):
                    if any(kw in eid for kw in keywords):
                        return s.entity_id
        for s in states:
            eid = s.entity_id.lower()
            if not eid.startswith(f"{domain}."):
                continue
            if any(hp_k in eid for hp_k in hp_keywords):
                if any(kw in eid for kw in keywords):
                    return s.entity_id
        for s in states:
            eid = s.entity_id.lower()
            if not eid.startswith(f"{domain}."):
                continue
            if any(kw in eid for kw in keywords):
                return s.entity_id
        return None

    results["power"] = find_hp_sensor("sensor", ("power", "putere", "active_power", "consum"), device_class="power")
    results["energy"] = find_hp_sensor("sensor", ("energy", "energie", "total_energy"), device_class="energy")
    results["temp_flow"] = find_hp_sensor("sensor", ("water_outlet", "outlet_temp", "flow_temp", "tur_apa", "temp_tur", "supply_temp", "leaving_water", "water_outlet_t7"))
    results["temp_return"] = find_hp_sensor("sensor", ("water_inlet", "inlet_temp", "return_temp", "retur_apa", "temp_retur", "entering_water", "water_inlet_t8"))
    results["temp_dhw"] = find_hp_sensor("sensor", ("water_tank", "tank_temp", "dhw_temp", "temp_dhw", "boiler_temp", "temp_boiler", "acm_temp", "temp_acm"))
    results["temp_buffer"] = find_hp_sensor("sensor", ("buffer_tank", "buffer_temp", "temp_buffer", "puffer_temp", "temp_puffer"))
    results["temp_room"] = find_hp_sensor("sensor", ("room_temp", "indoor_temp", "temp_camera", "camera", "temperatura_camera", "temp_room", "room_temperature", "indoor_temperature"))
    results["temp_outdoor"] = find_hp_sensor("sensor", ("outdoor_temp", "temp_outdoor", "ambient_temp", "temp_ambient", "exterior_temp", "temp_exterior"))
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


def _populate_heat_pump_2_from_base(hass, base_eid: str) -> dict[str, str]:
    """Auto-populate heat pump 2 fields given a base entity."""
    pop = _populate_heat_pump_from_base(hass, base_eid)
    key_map = {
        CONF_HP_POWER: CONF_HP2_POWER,
        CONF_HP_ENERGY: CONF_HP2_ENERGY,
        CONF_HP_TEMP_FLOW: CONF_HP2_TEMP_FLOW,
        CONF_HP_TEMP_RETURN: CONF_HP2_TEMP_RETURN,
        CONF_HP_TEMP_DHW: CONF_HP2_TEMP_DHW,
        CONF_HP_TEMP_BUFFER: CONF_HP2_TEMP_BUFFER,
        CONF_HP_TEMP_ROOM: CONF_HP2_TEMP_ROOM,
        CONF_HP_TEMP_OUTDOOR: CONF_HP2_TEMP_OUTDOOR,
        CONF_HP_FLOW_RATE: CONF_HP2_FLOW_RATE,
        CONF_HP_HEAT_POWER: CONF_HP2_HEAT_POWER,
        CONF_HP_COP: CONF_HP2_COP,
        CONF_HP_COMP_FREQ: CONF_HP2_COMP_FREQ,
        CONF_HP_STATUS: CONF_HP2_STATUS,
        CONF_HP_DEFROST: CONF_HP2_DEFROST,
        CONF_HP_FAULT: CONF_HP2_FAULT,
    }
    return {key_map[k]: v for k, v in pop.items() if k in key_map and v}


def _auto_detect_heat_pump_2(hass) -> dict[str, Any]:
    """Auto-detect second heat pump sensors."""
    states = list(hass.states.async_all())
    for s in states:
        low = s.entity_id.lower()
        if any(hp2_k in low for hp2_k in ("sunclima_2", "sunclima2", "heat_pump_2", "heatpump_2", "heat_pump2", "heatpump2", "pompa_caldura_2", "pompa2", "pompa_2", "altherma_2", "aquarea_2")):
            pop = _populate_heat_pump_2_from_base(hass, s.entity_id)
            if pop.get(CONF_HP2_TEMP_FLOW) or pop.get(CONF_HP2_POWER) or pop.get(CONF_HP2_TEMP_RETURN):
                return {
                    "power": pop.get(CONF_HP2_POWER),
                    "energy": pop.get(CONF_HP2_ENERGY),
                    "temp_flow": pop.get(CONF_HP2_TEMP_FLOW),
                    "temp_return": pop.get(CONF_HP2_TEMP_RETURN),
                    "temp_dhw": pop.get(CONF_HP2_TEMP_DHW),
                    "temp_buffer": pop.get(CONF_HP2_TEMP_BUFFER),
                    "temp_room": pop.get(CONF_HP2_TEMP_ROOM),
                    "temp_outdoor": pop.get(CONF_HP2_TEMP_OUTDOOR),
                    "flow_rate": pop.get(CONF_HP2_FLOW_RATE),
                    "heat_power": pop.get(CONF_HP2_HEAT_POWER),
                    "cop": pop.get(CONF_HP2_COP),
                    "comp_freq": pop.get(CONF_HP2_COMP_FREQ),
                    "status": pop.get(CONF_HP2_STATUS),
                    "defrost": pop.get(CONF_HP2_DEFROST),
                    "fault": pop.get(CONF_HP2_FAULT),
                }

    results: dict[str, Any] = {}
    hp2_keywords = ("pompa_2", "pompa2", "heatpump2", "heat_pump_2", "heat_pump2", "zone_2", "zone2", "hp2", "hp_2")

    def find_hp2_sensor(domain: str, keywords: tuple[str, ...], device_class: str | None = None) -> str | None:
        for s in states:
            eid = s.entity_id.lower()
            if not eid.startswith(f"{domain}."):
                continue
            if any(hp_k in eid for hp_k in hp2_keywords):
                if any(kw in eid for kw in keywords):
                    return s.entity_id
        return None

    results["power"] = find_hp2_sensor("sensor", ("power", "putere", "active_power", "consum"), device_class="power")
    results["energy"] = find_hp2_sensor("sensor", ("energy", "energie", "total_energy"), device_class="energy")
    results["temp_flow"] = find_hp2_sensor("sensor", ("water_outlet", "outlet_temp", "flow_temp", "tur_apa", "temp_tur", "supply_temp", "leaving_water"))
    results["temp_return"] = find_hp2_sensor("sensor", ("water_inlet", "inlet_temp", "return_temp", "retur_apa", "temp_retur", "entering_water"))
    results["temp_dhw"] = find_hp2_sensor("sensor", ("water_tank", "tank_temp", "dhw_temp", "temp_dhw", "boiler_temp", "temp_boiler", "acm_temp"))
    results["temp_buffer"] = find_hp2_sensor("sensor", ("buffer_tank", "buffer_temp", "temp_buffer", "puffer_temp", "temp_puffer"))
    results["temp_room"] = find_hp2_sensor("sensor", ("room_temp", "indoor_temp", "temp_camera", "camera", "temperatura_camera", "temp_room"))
    results["temp_outdoor"] = find_hp2_sensor("sensor", ("outdoor_temp", "temp_outdoor", "ambient_temp", "temp_ambient", "exterior_temp"))
    results["flow_rate"] = find_hp2_sensor("sensor", ("flow_rate", "water_flow", "debit_apa", "debit"))
    results["heat_power"] = find_hp2_sensor("sensor", ("thermal_power", "heat_power", "output_heat", "putere_termica"))
    results["cop"] = find_hp2_sensor("sensor", ("cop", "instant_cop"))
    results["comp_freq"] = find_hp2_sensor("sensor", ("compressor_freq", "comp_hz", "compresor_freq"))
    results["status"] = find_hp2_sensor("climate", ("mode", "zone2", "zone_2")) or find_hp2_sensor("sensor", ("mode", "status", "stare"))
    results["defrost"] = find_hp2_sensor("binary_sensor", ("defrost", "dezghetare"))
    results["fault"] = find_hp2_sensor("binary_sensor", ("fault", "error", "avarie")) or find_hp2_sensor("sensor", ("fault_code", "error_code", "avarie"))

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
            vol.Required(CONF_PRESET, default=PRESET_SOLAR_ASSISTANT): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[PRESET_SOLAR_ASSISTANT, PRESET_AXPERT, PRESET_CUSTOM],
                    translation_key="system_preset",
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_HAS_HA_BMS, default=False): bool,
            vol.Optional(CONF_HAS_HEAT_PUMP, default=False): bool,
            vol.Optional(CONF_HAS_HEAT_PUMP_2, default=False): bool,
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

        if user_input is not None:
            self._collected_data.update(user_input)
            if self._layout.get(CONF_HAS_BATTERY, True):
                return await self.async_step_battery()
            if self._layout.get(CONF_HAS_HA_BMS, False):
                return await self.async_step_bms()
            if self._layout.get(CONF_HAS_HEAT_PUMP, False):
                return await self.async_step_heat_pump()
            if self._layout.get(CONF_HAS_HEAT_PUMP_2, False):
                return await self.async_step_heat_pump_2()
            return await self.async_step_grid()

        schema_dict: dict[Any, Any] = {}
        used_in_step: set[str] = set()

        # 1. Total Solar Power (e.g. sensor.total_pv_power, sensor.pv_power, sensor.total_panouri)
        tot_pv_cand = _auto_detect_candidate(
            self.hass, "sensor", "power", ("W", "kW"),
            ("sensor.total_pv_power", "sensor.pv_power", "sensor.axpert_max_pv_power_1", "total_pv_power", "pv_power", "axpert_max_pv_power_1", "axpert_max_pv_power", "voltronic_pv_power", "total_panouri", "total_pv", "putere_pv", "solar_power", "total solar"),
            ("consum", "load", "battery", "baterie"),
            require_solar_context=True,
            already_used=used_in_step
        )
        if tot_pv_cand:
            used_in_step.add(tot_pv_cand)
        schema_dict[vol.Optional(CONF_SENSOR_PV_POWER, **({"default": _sc(self.hass, tot_pv_cand)} if _sc(self.hass, tot_pv_cand) else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
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
                    ("batt", "baterie", "ac", "grid", "cell"),
                    already_used=used_in_step
                )
                if v_cand:
                    used_in_step.add(v_cand)
                v_opts = {"default": _sc(self.hass, v_cand)} if _sc(self.hass, v_cand) else {}
                schema_dict[vol.Optional(v_key, **v_opts)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
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
                    ("batt", "baterie", "ac", "grid"),
                    already_used=used_in_step
                )
                # If current not found by keywords, try deriving from detected voltage entity!
                if not c_cand and v_cand:
                    for v_word, c_word in (("voltage", "current"), ("voltaj", "curent"), ("volt", "current"), ("_v_", "_c_"), ("_v", "_c")):
                        if v_word in v_cand:
                            der_c = v_cand.replace(v_word, c_word)
                            if der_c not in used_in_step and self.hass.states.get(der_c) is not None:
                                c_cand = der_c
                                break
                if c_cand:
                    used_in_step.add(c_cand)
                c_opts = {"default": _sc(self.hass, c_cand)} if _sc(self.hass, c_cand) else {}
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
                        ("consum", "load", "batt", "baterie"),
                        already_used=used_in_step
                    )
                    if p_mppt_cand:
                        used_in_step.add(p_mppt_cand)
                    p_mppt_opts = {"default": _sc(self.hass, p_mppt_cand)} if _sc(self.hass, p_mppt_cand) else {}
                    schema_dict[vol.Optional(p_mppt_key, **p_mppt_opts)] = selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    )

            # 2.4 Total Power per Inverter if multiple inverters
            if inv_count > 1:
                p_key = f"puterePV{inv}"
                p_cand = _auto_detect_candidate(
                    self.hass, "sensor", "power", ("W", "kW"),
                    (f"sensor.inverter_{inv}_pv_power", f"inverter_{inv}_pv_power", f"inv{inv}_power", f"inverter_{inv}_power", f"inverter {inv} power", f"putere_inv{inv}"),
                    ("consum", "load", "batt", "baterie"),
                    already_used=used_in_step
                )
                if p_cand:
                    used_in_step.add(p_cand)
                p_opts = {"default": _sc(self.hass, p_cand)} if _sc(self.hass, p_cand) else {}
                schema_dict[vol.Optional(p_key, **p_opts)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                )

        # 3. Energy Production Sensors (Daily, Monthly, Yearly)
        e_today_cand = _auto_detect_candidate(
            self.hass, "sensor", "energy", ("kWh", "Wh"),
            ("sensor.solar_energy_today", "sensor.energy_today", "sensor.pv_day_meter", "solar_energy_today", "energy_today", "pv_day_meter", "pv_day_energy", "productie_zi", "energie_zi", "daily_energy", "solar_today", "today_energy"),
            ("consum", "load", "pompa", "heat_pump", "retea", "grid"),
            require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_TODAY, **({"default": _sc(self.hass, e_today_cand)} if _sc(self.hass, e_today_cand) else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        e_month_cand = _auto_detect_candidate(
            self.hass, "sensor", "energy", ("kWh", "Wh"),
            ("sensor.solar_energy_this_month", "solar_energy_this_month", "productie_panouri_lunar", "productie_luna", "energie_luna", "monthly_energy", "energy_month"),
            ("consum", "load", "pompa", "heat_pump", "retea", "grid"),
            require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_MONTH, **({"default": _sc(self.hass, e_month_cand)} if _sc(self.hass, e_month_cand) else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        e_year_cand = _auto_detect_candidate(
            self.hass, "sensor", "energy", ("kWh", "Wh"),
            ("sensor.solar_energy_this_year", "solar_energy_this_year", "productie_anuala", "productie_an", "energie_an", "yearly_energy", "energy_year"),
            ("consum", "load", "pompa", "heat_pump", "retea", "grid"),
            require_solar_context=True
        )
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_YEAR, **({"default": _sc(self.hass, e_year_cand)} if _sc(self.hass, e_year_cand) else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
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
            if self._layout.get(CONF_HAS_HEAT_PUMP_2, False):
                return await self.async_step_heat_pump_2()
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
            selector.EntitySelectorConfig(domain="sensor")
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
            for p_idx in range(1, bms_count + 1):
                ref_eid = user_input.get(f"bms_{p_idx}_soc") or user_input.get(f"bms_{p_idx}_voltage")
                init_ref = getattr(self, "_initial_bms_ref", {}).get(p_idx)
                user_changed_anchor = bool(ref_eid and init_ref and ref_eid != init_ref)
                if ref_eid:
                    pack_pop = _populate_bms_pack_from_base(self.hass, ref_eid, p_idx)
                    for k, v in pack_pop.items():
                        if v and v.startswith("sensor."):
                            if user_changed_anchor or not user_input.get(k):
                                user_input[k] = v
            self._collected_data.update(user_input)
            new_count = int(user_input.get(CONF_BMS_COUNT, bms_count))
            if new_count != bms_count:
                return await self.async_step_bms()
            if self._layout.get(CONF_HAS_HEAT_PUMP, False):
                return await self.async_step_heat_pump()
            if self._layout.get(CONF_HAS_HEAT_PUMP_2, False):
                return await self.async_step_heat_pump_2()
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

        def _sc(val):
            return val if (val and isinstance(val, str) and val.startswith("sensor.")) else None

        self._initial_bms_ref: dict[int, str] = {}
        for p in range(1, bms_count + 1):
            det = _auto_detect_bms_pack(self.hass, p)
            init_val = det.get("soc") or det.get("voltage")
            if init_val:
                self._initial_bms_ref[p] = init_val

            # SOC & Electrical (strictly sensor domain)
            d_soc = _sc(det.get("soc"))
            schema_dict[vol.Optional(f"bms_{p}_soc", **({"default": d_soc} if d_soc else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )
            d_v = _sc(det.get("voltage"))
            schema_dict[vol.Optional(f"bms_{p}_voltage", **({"default": d_v} if d_v else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )
            d_c = _sc(det.get("current"))
            schema_dict[vol.Optional(f"bms_{p}_current", **({"default": d_c} if d_c else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )
            d_p = _sc(det.get("power"))
            schema_dict[vol.Optional(f"bms_{p}_power", **({"default": d_p} if d_p else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            # Cell Diagnostics
            d_delta = _sc(det.get("cell_delta"))
            schema_dict[vol.Optional(f"bms_{p}_cell_delta", **({"default": d_delta} if d_delta else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            # Temperatures
            d_t1 = _sc(det.get("t1"))
            schema_dict[vol.Optional(f"bms_{p}_t1", **({"default": d_t1} if d_t1 else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )
            d_tmos = _sc(det.get("tmos"))
            schema_dict[vol.Optional(f"bms_{p}_tmos", **({"default": d_tmos} if d_tmos else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
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
            ref_eid = user_input.get(CONF_HP_TEMP_FLOW) or user_input.get(CONF_HP_POWER)
            init_ref = getattr(self, "_initial_hp_ref", None)
            user_changed_hp = bool(ref_eid and init_ref and ref_eid != init_ref)
            if ref_eid:
                hp_pop = _populate_heat_pump_from_base(self.hass, ref_eid)
                for k, v in hp_pop.items():
                    if v and (user_changed_hp or not user_input.get(k)):
                        user_input[k] = v
            self._collected_data.update(user_input)
            if user_input.get(CONF_HAS_HEAT_PUMP_2) or self._layout.get(CONF_HAS_HEAT_PUMP_2):
                self._layout[CONF_HAS_HEAT_PUMP_2] = True
                return await self.async_step_heat_pump_2()
            return await self.async_step_grid()

        det = _auto_detect_heat_pump(self.hass)
        self._initial_hp_ref = det.get("temp_flow") or det.get("power")
        schema_dict: dict[Any, Any] = {}

        schema_dict[vol.Optional(CONF_HP_POWER, **({"default": det["power"]} if det.get("power") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_UNIT_HP_POWER, default=POWER_UNIT_AUTO)] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value="auto", label="Auto (detectare automată din HA)"),
                    selector.SelectOptionDict(value="w", label="Wați (W)"),
                    selector.SelectOptionDict(value="kw", label="Kilowați (kW - multiplică x1000)"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="unit_power",
            )
        )
        schema_dict[vol.Optional(CONF_HP_ENERGY, **({"default": det["energy"]} if det.get("energy") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP_TEMP_FLOW, **({"default": det["temp_flow"]} if det.get("temp_flow") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP_TEMP_RETURN, **({"default": det["temp_return"]} if det.get("temp_return") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP_TEMP_DHW, **({"default": det["temp_dhw"]} if det.get("temp_dhw") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP_TEMP_BUFFER, **({"default": det["temp_buffer"]} if det.get("temp_buffer") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP_TEMP_ROOM, **({"default": det["temp_room"]} if det.get("temp_room") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP_TEMP_OUTDOOR, **({"default": det["temp_outdoor"]} if det.get("temp_outdoor") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
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
            selector.EntitySelectorConfig(domain=["climate", "sensor", "switch", "select", "binary_sensor", "input_select", "input_boolean"])
        )
        schema_dict[vol.Optional(CONF_HP_DEFROST, **({"default": det["defrost"]} if det.get("defrost") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "switch", "sensor"])
        )
        schema_dict[vol.Optional(CONF_HP_FAULT, **({"default": det["fault"]} if det.get("fault") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"])
        )
        has_hp2_default = bool(self._collected_data.get(CONF_HAS_HEAT_PUMP_2, self._layout.get(CONF_HAS_HEAT_PUMP_2, False)))
        schema_dict[vol.Optional(CONF_HAS_HEAT_PUMP_2, default=has_hp2_default)] = bool

        return self.async_show_form(
            step_id="heat_pump",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def async_step_heat_pump_2(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 4d: Second Heat Pump & HVAC Configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            ref_eid = user_input.get(CONF_HP2_TEMP_FLOW) or user_input.get(CONF_HP2_POWER)
            init_ref = getattr(self, "_initial_hp2_ref", None)
            user_changed_hp = bool(ref_eid and init_ref and ref_eid != init_ref)
            if ref_eid:
                hp2_pop = _populate_heat_pump_2_from_base(self.hass, ref_eid)
                for k, v in hp2_pop.items():
                    if v and (user_changed_hp or not user_input.get(k)):
                        user_input[k] = v
            self._collected_data.update(user_input)
            return await self.async_step_grid()

        det = _auto_detect_heat_pump_2(self.hass)
        self._initial_hp2_ref = det.get("temp_flow") or det.get("power")
        schema_dict: dict[Any, Any] = {}

        schema_dict[vol.Optional(CONF_HP2_POWER, **({"default": det["power"]} if det.get("power") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_UNIT_HP2_POWER, default=POWER_UNIT_AUTO)] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value="auto", label="Auto (detectare automată din HA)"),
                    selector.SelectOptionDict(value="w", label="Wați (W)"),
                    selector.SelectOptionDict(value="kw", label="Kilowați (kW - multiplică x1000)"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="unit_power",
            )
        )
        schema_dict[vol.Optional(CONF_HP2_ENERGY, **({"default": det["energy"]} if det.get("energy") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP2_TEMP_FLOW, **({"default": det["temp_flow"]} if det.get("temp_flow") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP2_TEMP_RETURN, **({"default": det["temp_return"]} if det.get("temp_return") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP2_TEMP_DHW, **({"default": det["temp_dhw"]} if det.get("temp_dhw") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP2_TEMP_BUFFER, **({"default": det["temp_buffer"]} if det.get("temp_buffer") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP2_TEMP_ROOM, **({"default": det["temp_room"]} if det.get("temp_room") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP2_TEMP_OUTDOOR, **({"default": det["temp_outdoor"]} if det.get("temp_outdoor") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP2_FLOW_RATE, **({"default": det["flow_rate"]} if det.get("flow_rate") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP2_HEAT_POWER, **({"default": det["heat_power"]} if det.get("heat_power") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP2_COP, **({"default": det["cop"]} if det.get("cop") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP2_COMP_FREQ, **({"default": det["comp_freq"]} if det.get("comp_freq") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_HP2_STATUS, **({"default": det["status"]} if det.get("status") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["climate", "sensor", "switch", "select", "binary_sensor", "input_select", "input_boolean"])
        )
        schema_dict[vol.Optional(CONF_HP2_DEFROST, **({"default": det["defrost"]} if det.get("defrost") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "switch", "sensor"])
        )
        schema_dict[vol.Optional(CONF_HP2_FAULT, **({"default": det["fault"]} if det.get("fault") else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"])
        )

        return self.async_show_form(
            step_id="heat_pump_2",
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
            max_mppt = max(
                [int(self._layout.get(f"mppt_inv_{inv}", 1)) for inv in range(1, inv_count + 1)] or [1]
            )
            inverter_id = self._layout.get(CONF_INVERTER_ID, "")

            final_data = {
                CONF_API_KEY: self._api_key,
                CONF_INVERTER_ID: inverter_id,
                CONF_INVERTER_COUNT: inv_count,
                CONF_MPPT_PER_INVERTER: max_mppt,
                CONF_HAS_BATTERY: self._layout.get(CONF_HAS_BATTERY, True),
                CONF_HAS_HA_BMS: self._layout.get(CONF_HAS_HA_BMS, False),
                CONF_HAS_HEAT_PUMP: self._layout.get(CONF_HAS_HEAT_PUMP, False),
                CONF_HAS_HEAT_PUMP_2: bool(self._layout.get(CONF_HAS_HEAT_PUMP_2, False) or self._collected_data.get(CONF_HAS_HEAT_PUMP_2, False)),
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
        schema_dict[vol.Optional(CONF_SENSOR_LOAD_POWER, **({"default": _sc(self.hass, load_cand)} if _sc(self.hass, load_cand) else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_UNIT_LOAD_POWER, default=POWER_UNIT_AUTO)] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value="auto", label="Auto (detectare automată din HA)"),
                    selector.SelectOptionDict(value="w", label="Wați (W)"),
                    selector.SelectOptionDict(value="kw", label="Kilowați (kW - multiplică x1000)"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="unit_power",
            )
        )

        # 1.1 House Consumption Energy Today (kWh, Optional)
        load_energy_cand = _auto_detect_candidate(
            self.hass, "sensor", "energy", ("kWh", "Wh", "MWh"),
            (
                "sensor.load_energy_today", "sensor.daily_load_energy", "sensor.home_consumption_today",
                "sensor.house_consumption_today", "sensor.energy_consumed_today", "sensor.total_load_energy_today",
                "sensor.daily_energy_consumption", "sensor.axpert_max_load_energy_today", "sensor.solar_assistant_daily_load_energy",
                "load_energy_today", "energy_consumed_today", "daily_load_energy", "house_consumption_today", "consum_zi", "energie_consum_zi"
            ),
            ("solar", "pv", "grid", "retea", "battery", "baterie", "export")
        )
        schema_dict[vol.Optional(CONF_SENSOR_LOAD_ENERGY_TODAY, **({"default": _sc(self.hass, load_energy_cand)} if _sc(self.hass, load_energy_cand) else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        # 1.2 Grid / AC In Power (for Hybrid inverters, Smart Meters, Feed-In / Import)
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
        schema_dict[vol.Optional(CONF_SENSOR_GRID_POWER, **({"default": _sc(self.hass, grid_pwr_cand)} if _sc(self.hass, grid_pwr_cand) else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_UNIT_GRID_POWER, default=POWER_UNIT_AUTO)] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value="auto", label="Auto (detectare automată din HA)"),
                    selector.SelectOptionDict(value="w", label="Wați (W)"),
                    selector.SelectOptionDict(value="kw", label="Kilowați (kW - multiplică x1000)"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="unit_power",
            )
        )

        # 1.3 Grid Energy Imported Today (kWh, Optional)
        grid_energy_cand = _auto_detect_candidate(
            self.hass, "sensor", "energy", ("kWh", "Wh", "MWh"),
            (
                "sensor.grid_energy_today", "sensor.daily_grid_energy", "sensor.daily_grid_import",
                "sensor.energy_imported_today", "sensor.grid_import_today", "sensor.grid_energy_in_today",
                "sensor.solar_assistant_daily_grid_energy", "grid_energy_today", "energy_imported_today",
                "retea_zi", "energie_retea_zi"
            ),
            ("export", "solar", "pv", "battery", "baterie", "load", "consum")
        )
        schema_dict[vol.Optional(CONF_SENSOR_GRID_ENERGY_TODAY, **({"default": _sc(self.hass, grid_energy_cand)} if _sc(self.hass, grid_energy_cand) else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        # 2. Grid AC Voltage
        grid_cand = _auto_detect_candidate(
            self.hass, "sensor", "voltage", ("V",),
            ("sensor.inverter_1_grid_voltage", "sensor.grid_voltage", "sensor.axpert_max_grid_voltage", "inverter_1_grid_voltage", "grid_voltage", "axpert_max_grid_voltage", "tensiune_retea", "tensiuneacin", "ac_in_voltage", "grid_volt", "infinisolar_v_x_3_grid_voltage"),
            ("battery", "baterie", "pv", "cell")
        )
        schema_dict[vol.Optional(CONF_SENSOR_GRID_VOLT, **({"default": _sc(self.hass, grid_cand)} if _sc(self.hass, grid_cand) else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        # 3. AC Output Voltage
        ac_out_cand = _auto_detect_candidate(
            self.hass, "sensor", "voltage", ("V",),
            ("sensor.inverter_1_ac_output_voltage", "sensor.ac_output_voltage", "sensor.axpert_max_ac_output_voltage", "inverter_1_ac_output_voltage", "ac_output_voltage", "axpert_max_ac_output_voltage", "output_voltage", "tensiune_ac_out", "tensiuneacout", "inverter_out_voltage"),
            ("battery", "baterie", "pv", "grid", "retea", "cell")
        )
        schema_dict[vol.Optional(CONF_SENSOR_AC_OUT_VOLT, **({"default": _sc(self.hass, ac_out_cand)} if _sc(self.hass, ac_out_cand) else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
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
        return SolarsSystemsOptionsFlowHandler(config_entry)


class SolarsSystemsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for modifying mapped sensors and settings without reinstalling."""

    def __init__(self, config_entry: config_entries.ConfigEntry | None = None) -> None:
        """Initialize options flow."""
        super().__init__()
        self._config_entry = config_entry
        self._collected_data: dict[str, Any] = {}

    def _val(self, key: str, default: Any = None) -> Any:
        entry = getattr(self, "_config_entry", None)
        if not entry:
            try:
                entry = self.config_entry
            except Exception:
                entry = None
        combined = {}
        if entry:
            combined = {**dict(entry.data or {}), **dict(entry.options or {})}
        if key in self._collected_data:
            return self._collected_data[key]
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
            vol.Optional(CONF_HAS_HEAT_PUMP_2, default=bool(self._val(CONF_HAS_HEAT_PUMP_2, False))): bool,
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
            has_hp2 = self._collected_data.get(CONF_HAS_HEAT_PUMP_2, self._val(CONF_HAS_HEAT_PUMP_2, False))
            if has_hp2:
                return await self.async_step_heat_pump_2()
            return await self.async_step_grid()

        inv_count = int(self._collected_data.get(CONF_INVERTER_COUNT, self._val(CONF_INVERTER_COUNT, 1)))

        schema_dict: dict[Any, Any] = {}

        # 1. Total Solar Power
        cur_pv = self._val(CONF_SENSOR_PV_POWER)
        pv_opts = {"default": cur_pv} if cur_pv else {}
        schema_dict[vol.Optional(CONF_SENSOR_PV_POWER, **pv_opts)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
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
                    selector.EntitySelectorConfig(domain="sensor")
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
                        selector.EntitySelectorConfig(domain="sensor")
                    )

            if inv_count > 1:
                p_key = f"puterePV{inv}"
                cur_p = self._val(p_key)
                p_opts = {"default": cur_p} if cur_p else {}
                schema_dict[vol.Optional(p_key, **p_opts)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                )

        # 3. Energy Production Sensors
        cur_e_today = self._val(CONF_SENSOR_ENERGY_TODAY)
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_TODAY, **({"default": cur_e_today} if _sc(self.hass, cur_e_today) else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_e_month = self._val(CONF_SENSOR_ENERGY_MONTH)
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_MONTH, **({"default": cur_e_month} if _sc(self.hass, cur_e_month) else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_e_year = self._val(CONF_SENSOR_ENERGY_YEAR)
        schema_dict[vol.Optional(CONF_SENSOR_ENERGY_YEAR, **({"default": cur_e_year} if _sc(self.hass, cur_e_year) else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
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
            has_hp2 = self._collected_data.get(CONF_HAS_HEAT_PUMP_2)
            if has_hp2 is None:
                has_hp2 = self._val(CONF_HAS_HEAT_PUMP_2, False)
            if has_hp2:
                return await self.async_step_heat_pump_2()
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
            selector.EntitySelectorConfig(domain="sensor")
        )

        return self.async_show_form(step_id="battery", data_schema=vol.Schema(schema_dict))

    async def async_step_bms(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Step 4b: Options for BMS Packs."""
        bms_count = int(self._collected_data.get(CONF_BMS_COUNT, self._val(CONF_BMS_COUNT, 0) or 1))

        if user_input is not None:
            for p_idx in range(1, bms_count + 1):
                ref_eid = user_input.get(f"bms_{p_idx}_soc") or user_input.get(f"bms_{p_idx}_voltage")
                init_ref = getattr(self, "_initial_bms_ref", {}).get(p_idx)
                user_changed_anchor = bool(ref_eid and init_ref and ref_eid != init_ref)
                if ref_eid:
                    pack_pop = _populate_bms_pack_from_base(self.hass, ref_eid, p_idx)
                    for k, v in pack_pop.items():
                        if v and v.startswith("sensor."):
                            if user_changed_anchor or not user_input.get(k):
                                user_input[k] = v
            self._collected_data.update(user_input)
            new_count = int(user_input.get(CONF_BMS_COUNT, bms_count))
            if new_count != bms_count:
                return await self.async_step_bms()
            has_hp = self._collected_data.get(CONF_HAS_HEAT_PUMP)
            if has_hp is None:
                has_hp = self._val(CONF_HAS_HEAT_PUMP, False)
            if has_hp:
                return await self.async_step_heat_pump()
            has_hp2 = self._collected_data.get(CONF_HAS_HEAT_PUMP_2)
            if has_hp2 is None:
                has_hp2 = self._val(CONF_HAS_HEAT_PUMP_2, False)
            if has_hp2:
                return await self.async_step_heat_pump_2()
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

        self._initial_bms_ref = {}
        for p in range(1, bms_count + 1):
            saved_soc = self._val(f"bms_{p}_soc")
            saved_v = self._val(f"bms_{p}_voltage")
            saved_c = self._val(f"bms_{p}_current")
            saved_p = self._val(f"bms_{p}_power")
            saved_delta = self._val(f"bms_{p}_cell_delta")
            saved_t1 = self._val(f"bms_{p}_t1")
            saved_tmos = self._val(f"bms_{p}_tmos")

            def _sc(val):
                return val if (val and isinstance(val, str) and val.startswith("sensor.")) else None

            det = {}
            if not (saved_soc or saved_v):
                det = _auto_detect_bms_pack(self.hass, p)

            cur_soc = _sc(saved_soc or det.get("soc"))
            if cur_soc:
                self._initial_bms_ref[p] = cur_soc
            schema_dict[vol.Optional(f"bms_{p}_soc", **({"default": cur_soc} if cur_soc else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            cur_v = _sc(saved_v or det.get("voltage"))
            schema_dict[vol.Optional(f"bms_{p}_voltage", **({"default": cur_v} if cur_v else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            cur_c = _sc(saved_c or det.get("current"))
            schema_dict[vol.Optional(f"bms_{p}_current", **({"default": cur_c} if cur_c else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            cur_p = _sc(saved_p or det.get("power"))
            schema_dict[vol.Optional(f"bms_{p}_power", **({"default": cur_p} if cur_p else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            cur_delta = _sc(saved_delta or det.get("cell_delta"))
            schema_dict[vol.Optional(f"bms_{p}_cell_delta", **({"default": cur_delta} if cur_delta else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            cur_t1 = _sc(saved_t1 or det.get("t1"))
            schema_dict[vol.Optional(f"bms_{p}_t1", **({"default": cur_t1} if cur_t1 else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            )

            cur_tmos = _sc(saved_tmos or det.get("tmos"))
            schema_dict[vol.Optional(f"bms_{p}_tmos", **({"default": cur_tmos} if cur_tmos else {}))] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
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
            ref_eid = user_input.get(CONF_HP_TEMP_FLOW) or user_input.get(CONF_HP_POWER)
            init_ref = getattr(self, "_initial_hp_ref", None)
            user_changed_hp = bool(ref_eid and init_ref and ref_eid != init_ref)
            if ref_eid:
                hp_pop = _populate_heat_pump_from_base(self.hass, ref_eid)
                for k, v in hp_pop.items():
                    if v and (user_changed_hp or not user_input.get(k)):
                        user_input[k] = v
            self._collected_data.update(user_input)
            if user_input.get(CONF_HAS_HEAT_PUMP_2) or self._val(CONF_HAS_HEAT_PUMP_2):
                return await self.async_step_heat_pump_2()
            return await self.async_step_grid()

        saved_flow = self._val(CONF_HP_TEMP_FLOW)
        saved_pwr = self._val(CONF_HP_POWER)
        saved_ret = self._val(CONF_HP_TEMP_RETURN)

        det = {}
        if not (saved_flow or saved_pwr or saved_ret):
            det = _auto_detect_heat_pump(self.hass)
        self._initial_hp_ref = saved_flow or saved_pwr or det.get("temp_flow") or det.get("power")

        schema_dict: dict[Any, Any] = {}

        cur_pwr = saved_pwr or det.get("power")
        schema_dict[vol.Optional(CONF_HP_POWER, **({"default": cur_pwr} if cur_pwr else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_UNIT_HP_POWER, default=self._val(CONF_UNIT_HP_POWER, POWER_UNIT_AUTO))] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value="auto", label="Auto (detectare automată din HA)"),
                    selector.SelectOptionDict(value="w", label="Wați (W)"),
                    selector.SelectOptionDict(value="kw", label="Kilowați (kW - multiplică x1000)"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="unit_power",
            )
        )

        cur_en = self._val(CONF_HP_ENERGY) or det.get("energy")
        schema_dict[vol.Optional(CONF_HP_ENERGY, **({"default": cur_en} if cur_en else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_flow = self._val(CONF_HP_TEMP_FLOW) or det.get("temp_flow")
        schema_dict[vol.Optional(CONF_HP_TEMP_FLOW, **({"default": cur_flow} if cur_flow else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_ret = self._val(CONF_HP_TEMP_RETURN) or det.get("temp_return")
        schema_dict[vol.Optional(CONF_HP_TEMP_RETURN, **({"default": cur_ret} if cur_ret else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_dhw = self._val(CONF_HP_TEMP_DHW) or det.get("temp_dhw")
        schema_dict[vol.Optional(CONF_HP_TEMP_DHW, **({"default": cur_dhw} if cur_dhw else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_buf = self._val(CONF_HP_TEMP_BUFFER) or det.get("temp_buffer")
        schema_dict[vol.Optional(CONF_HP_TEMP_BUFFER, **({"default": cur_buf} if cur_buf else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_room = self._val(CONF_HP_TEMP_ROOM) or det.get("temp_room")
        schema_dict[vol.Optional(CONF_HP_TEMP_ROOM, **({"default": cur_room} if cur_room else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_out = self._val(CONF_HP_TEMP_OUTDOOR) or det.get("temp_outdoor")
        schema_dict[vol.Optional(CONF_HP_TEMP_OUTDOOR, **({"default": cur_out} if cur_out else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
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
            selector.EntitySelectorConfig(domain=["climate", "sensor", "switch", "select", "binary_sensor", "input_select", "input_boolean"])
        )

        cur_def = self._val(CONF_HP_DEFROST) or det.get("defrost")
        schema_dict[vol.Optional(CONF_HP_DEFROST, **({"default": cur_def} if cur_def else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "switch", "sensor"])
        )

        cur_flt = self._val(CONF_HP_FAULT) or det.get("fault")
        schema_dict[vol.Optional(CONF_HP_FAULT, **({"default": cur_flt} if cur_flt else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"])
        )

        has_hp2_default = bool(self._collected_data.get(CONF_HAS_HEAT_PUMP_2, self._val(CONF_HAS_HEAT_PUMP_2, False)))
        schema_dict[vol.Optional(CONF_HAS_HEAT_PUMP_2, default=has_hp2_default)] = bool

        return self.async_show_form(
            step_id="heat_pump",
            data_schema=vol.Schema(schema_dict)
        )

    async def async_step_heat_pump_2(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Step 4d: Options for Second Heat Pump & HVAC."""
        if user_input is not None:
            ref_eid = user_input.get(CONF_HP2_TEMP_FLOW) or user_input.get(CONF_HP2_POWER)
            init_ref = getattr(self, "_initial_hp2_ref", None)
            user_changed_hp = bool(ref_eid and init_ref and ref_eid != init_ref)
            if ref_eid:
                hp2_pop = _populate_heat_pump_2_from_base(self.hass, ref_eid)
                for k, v in hp2_pop.items():
                    if v and (user_changed_hp or not user_input.get(k)):
                        user_input[k] = v
            self._collected_data.update(user_input)
            return await self.async_step_grid()

        saved_flow = self._val(CONF_HP2_TEMP_FLOW)
        saved_pwr = self._val(CONF_HP2_POWER)
        saved_ret = self._val(CONF_HP2_TEMP_RETURN)

        det = {}
        if not (saved_flow or saved_pwr or saved_ret):
            det = _auto_detect_heat_pump_2(self.hass)
        self._initial_hp2_ref = saved_flow or saved_pwr or det.get("temp_flow") or det.get("power")

        schema_dict: dict[Any, Any] = {}

        cur_pwr = saved_pwr or det.get("power")
        schema_dict[vol.Optional(CONF_HP2_POWER, **({"default": cur_pwr} if cur_pwr else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_UNIT_HP2_POWER, default=self._val(CONF_UNIT_HP2_POWER, POWER_UNIT_AUTO))] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value="auto", label="Auto (detectare automată din HA)"),
                    selector.SelectOptionDict(value="w", label="Wați (W)"),
                    selector.SelectOptionDict(value="kw", label="Kilowați (kW - multiplică x1000)"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="unit_power",
            )
        )

        cur_en = self._val(CONF_HP2_ENERGY) or det.get("energy")
        schema_dict[vol.Optional(CONF_HP2_ENERGY, **({"default": cur_en} if cur_en else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_flow = self._val(CONF_HP2_TEMP_FLOW) or det.get("temp_flow")
        schema_dict[vol.Optional(CONF_HP2_TEMP_FLOW, **({"default": cur_flow} if cur_flow else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_ret = self._val(CONF_HP2_TEMP_RETURN) or det.get("temp_return")
        schema_dict[vol.Optional(CONF_HP2_TEMP_RETURN, **({"default": cur_ret} if cur_ret else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_dhw = self._val(CONF_HP2_TEMP_DHW) or det.get("temp_dhw")
        schema_dict[vol.Optional(CONF_HP2_TEMP_DHW, **({"default": cur_dhw} if cur_dhw else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_buf = self._val(CONF_HP2_TEMP_BUFFER) or det.get("temp_buffer")
        schema_dict[vol.Optional(CONF_HP2_TEMP_BUFFER, **({"default": cur_buf} if cur_buf else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_room = self._val(CONF_HP2_TEMP_ROOM) or det.get("temp_room")
        schema_dict[vol.Optional(CONF_HP2_TEMP_ROOM, **({"default": cur_room} if cur_room else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_out = self._val(CONF_HP2_TEMP_OUTDOOR) or det.get("temp_outdoor")
        schema_dict[vol.Optional(CONF_HP2_TEMP_OUTDOOR, **({"default": cur_out} if cur_out else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_fr = self._val(CONF_HP2_FLOW_RATE) or det.get("flow_rate")
        schema_dict[vol.Optional(CONF_HP2_FLOW_RATE, **({"default": cur_fr} if cur_fr else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_hp = self._val(CONF_HP2_HEAT_POWER) or det.get("heat_power")
        schema_dict[vol.Optional(CONF_HP2_HEAT_POWER, **({"default": cur_hp} if cur_hp else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_cop = self._val(CONF_HP2_COP) or det.get("cop")
        schema_dict[vol.Optional(CONF_HP2_COP, **({"default": cur_cop} if cur_cop else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_cf = self._val(CONF_HP2_COMP_FREQ) or det.get("comp_freq")
        schema_dict[vol.Optional(CONF_HP2_COMP_FREQ, **({"default": cur_cf} if cur_cf else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_st = self._val(CONF_HP2_STATUS) or det.get("status")
        schema_dict[vol.Optional(CONF_HP2_STATUS, **({"default": cur_st} if cur_st else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["climate", "sensor", "switch", "select", "binary_sensor", "input_select", "input_boolean"])
        )

        cur_def = self._val(CONF_HP2_DEFROST) or det.get("defrost")
        schema_dict[vol.Optional(CONF_HP2_DEFROST, **({"default": cur_def} if cur_def else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "switch", "sensor"])
        )

        cur_flt = self._val(CONF_HP2_FAULT) or det.get("fault")
        schema_dict[vol.Optional(CONF_HP2_FAULT, **({"default": cur_flt} if cur_flt else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["binary_sensor", "sensor"])
        )

        return self.async_show_form(
            step_id="heat_pump_2",
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
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_UNIT_LOAD_POWER, default=self._val(CONF_UNIT_LOAD_POWER, POWER_UNIT_AUTO))] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value="auto", label="Auto (detectare automată din HA)"),
                    selector.SelectOptionDict(value="w", label="Wați (W)"),
                    selector.SelectOptionDict(value="kw", label="Kilowați (kW - multiplică x1000)"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="unit_power",
            )
        )

        cur_load_energy = self._val(CONF_SENSOR_LOAD_ENERGY_TODAY)
        schema_dict[vol.Optional(CONF_SENSOR_LOAD_ENERGY_TODAY, **({"default": cur_load_energy} if cur_load_energy else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_grid_pwr = self._val(CONF_SENSOR_GRID_POWER)
        schema_dict[vol.Optional(CONF_SENSOR_GRID_POWER, **({"default": cur_grid_pwr} if cur_grid_pwr else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )
        schema_dict[vol.Optional(CONF_UNIT_GRID_POWER, default=self._val(CONF_UNIT_GRID_POWER, POWER_UNIT_AUTO))] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value="auto", label="Auto (detectare automată din HA)"),
                    selector.SelectOptionDict(value="w", label="Wați (W)"),
                    selector.SelectOptionDict(value="kw", label="Kilowați (kW - multiplică x1000)"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="unit_power",
            )
        )

        cur_grid_energy = self._val(CONF_SENSOR_GRID_ENERGY_TODAY)
        schema_dict[vol.Optional(CONF_SENSOR_GRID_ENERGY_TODAY, **({"default": cur_grid_energy} if cur_grid_energy else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_grid = self._val(CONF_SENSOR_GRID_VOLT)
        schema_dict[vol.Optional(CONF_SENSOR_GRID_VOLT, **({"default": cur_grid} if cur_grid else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        cur_ac_out = self._val(CONF_SENSOR_AC_OUT_VOLT)
        schema_dict[vol.Optional(CONF_SENSOR_AC_OUT_VOLT, **({"default": cur_ac_out} if cur_ac_out else {}))] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        schema_dict[vol.Optional(CONF_UPDATE_INTERVAL, default=self._val(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))] = vol.All(
            vol.Coerce(int), vol.Range(min=10, max=300)
        )

        return self.async_show_form(step_id="grid", data_schema=vol.Schema(schema_dict))
