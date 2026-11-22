"""Solars Systems Home Assistant Integration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    INTEGRATION_VERSION,
    DEFAULT_API_URL,
    CONF_API_KEY,
    CONF_INVERTER_ID,
    CONF_UPDATE_INTERVAL,
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


def _safe_float(val: Any) -> float | None:
    """Helper to convert string/numeric to float safely."""
    if val is None or val in ("unknown", "unavailable", ""):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Solars Systems from a config entry."""
    data = {**entry.data, **entry.options}
    api_key = data[CONF_API_KEY]
    inverter_id = data[CONF_INVERTER_ID]
    update_interval = data.get(CONF_UPDATE_INTERVAL, 30)

    session = async_get_clientsession(hass)
    headers = {
        "x-api-key": api_key,
        "x-integration-version": INTEGRATION_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # 1. Periodic Telemetry Sender
    async def async_send_telemetry(now: datetime | None = None) -> None:
        """Read states from Home Assistant and push to Solars Systems API."""
        payload: dict[str, Any] = {"macid": inverter_id, "integration_version": INTEGRATION_VERSION}

        def get_val(key: str) -> float | None:
            entity_id = data.get(key)
            if not entity_id:
                return None
            state = hass.states.get(entity_id)
            if not state:
                return None
            val = _safe_float(state.state)
            if val is not None:
                unit = state.attributes.get("unit_of_measurement", "")
                if unit == "kW":
                    val = round(val * 1000.0, 1)
                elif unit == "Wh":
                    if key in (CONF_SENSOR_ENERGY_TODAY, CONF_SENSOR_ENERGY_MONTH, CONF_SENSOR_ENERGY_YEAR):
                        val = round(val / 1000.0, 3)
                elif unit == "MWh":
                    if key in (CONF_SENSOR_ENERGY_TODAY, CONF_SENSOR_ENERGY_MONTH, CONF_SENSOR_ENERGY_YEAR):
                        val = round(val * 1000.0, 3)
            # Failsafe: if daily energy value > 1000, it is sent in raw Wh (e.g. 209639 Wh)
            if val is not None and key == CONF_SENSOR_ENERGY_TODAY and val > 1000:
                val = round(val / 1000.0, 2)
            return val

        def get_bool_val(key: str) -> bool | None:
            entity_id = data.get(key)
            if not entity_id:
                return None
            state = hass.states.get(entity_id)
            if not state or state.state in ("unknown", "unavailable", None):
                return None
            return str(state.state).lower() in ("on", "true", "1", "open", "active")

        # Dynamic MPPT Voltages, Currents and Inverter Powers (voltajPV1, voltajPV1_2, curentPV1, curentPV1_2, puterePV1, puterePV1_2...)
        for k, entity_id in data.items():
            if isinstance(k, str) and (k.startswith("voltajPV") or k.startswith("puterePV") or k.startswith("curentPV")):
                val = get_val(k)
                if val is not None:
                    payload[k] = val

        # Auto-alias curentPV{inv}_1 to curentPV{inv} if present
        for inv in range(1, 13):
            if f"curentPV{inv}_1" in payload and f"curentPV{inv}" not in payload:
                payload[f"curentPV{inv}"] = payload[f"curentPV{inv}_1"]

        # Auto-compute curentPV{inv} from puterePV{inv} and voltajPV{inv} if curentPV{inv} is missing (e.g. InfiniSolar)
        for inv in range(1, 13):
            c_key = f"curentPV{inv}"
            p_key = f"puterePV{inv}"
            v_key = f"voltajPV{inv}"
            if c_key not in payload or payload[c_key] is None or payload[c_key] == 0:
                p_val = payload.get(p_key)
                v_val = payload.get(v_key)
                if p_val and v_val and isinstance(p_val, (int, float)) and isinstance(v_val, (int, float)) and v_val > 10:
                    payload[c_key] = round(p_val / v_val, 2)

        # Auto-compute total puterePV{inv} if sub-MPPT powers (puterePV{inv}_1, puterePV{inv}_2...) exist but total puterePV{inv} is not specified
        for inv in range(1, 13):
            sub_mppts = [v for k, v in payload.items() if (k.startswith(f"puterePV{inv}_") and isinstance(v, (int, float)))]
            if sub_mppts and f"puterePV{inv}" not in payload:
                payload[f"puterePV{inv}"] = round(sum(sub_mppts), 1)

        # Total Solar Power
        tot_pv = get_val(CONF_SENSOR_PV_POWER)
        if tot_pv is not None:
            payload["puterePV"] = tot_pv
        elif "puterePV" not in payload:
            sub_powers = [v for k, v in payload.items() if (k.startswith("puterePV") and not "_" in k and isinstance(v, (int, float)))]
            if not sub_powers:
                sub_powers = [v for k, v in payload.items() if k.startswith("puterePV") and isinstance(v, (int, float))]
            if sub_powers:
                payload["puterePV"] = round(sum(sub_powers), 1)

        # Consumption & Grid
        load_power = get_val(CONF_SENSOR_LOAD_POWER)
        grid_power = get_val(CONF_SENSOR_GRID_POWER)
        grid_volt = get_val(CONF_SENSOR_GRID_VOLT)
        ac_out_volt = get_val(CONF_SENSOR_AC_OUT_VOLT)

        if load_power is not None:
            payload["putereConsum"] = load_power
        if grid_power is not None:
            payload["putereAcIn"] = grid_power
        if grid_volt is not None:
            payload["tensiuneAcIn"] = grid_volt
        if ac_out_volt is not None:
            payload["tensiuneAcOut"] = ac_out_volt

        # Battery
        batt_soc = get_val(CONF_SENSOR_BATT_SOC)
        batt_volt = get_val(CONF_SENSOR_BATT_VOLT)
        batt_curr = get_val(CONF_SENSOR_BATT_CURR)
        batt_power = get_val(CONF_SENSOR_BATT_POWER)

        if batt_soc is not None:
            payload["procentBaterie"] = batt_soc
        if batt_volt is not None:
            payload["tensiuneBaterie"] = batt_volt
        if batt_curr is not None:
            payload["curentBaterie"] = batt_curr
        if batt_power is not None:
            payload["putereBaterie"] = batt_power

        # Energy (Today / Month / Year)
        energy_today = get_val(CONF_SENSOR_ENERGY_TODAY)
        energy_month = get_val(CONF_SENSOR_ENERGY_MONTH)
        energy_year = get_val(CONF_SENSOR_ENERGY_YEAR)

        if energy_today is not None:
            payload["energieZi"] = energy_today
        if energy_month is not None:
            payload["energieLuna"] = energy_month
        if energy_year is not None:
            payload["energieAn"] = energy_year

        # Send to API
        try:
            async with session.post(
                f"{DEFAULT_API_URL}/telemetry",
                json=payload,
                headers=headers,
                timeout=10,
            ) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Solars Systems API returned status %s on telemetry", resp.status)
        except Exception as err:
            _LOGGER.debug("Error sending telemetry to Solars Systems: %s", err)

        # Send BMS telemetry if configured
        if data.get(CONF_HAS_HA_BMS):
            bms_count = int(data.get(CONF_BMS_COUNT, 1))
            bms_packs = []
            for p in range(1, bms_count + 1):
                pack_data: dict[str, Any] = {"bms_index": p}
                v = get_val(f"bms_{p}_voltage")
                if v is not None:
                    pack_data["voltage"] = v
                c = get_val(f"bms_{p}_current")
                if c is not None:
                    pack_data["current"] = c
                pw = get_val(f"bms_{p}_power")
                if pw is not None:
                    pack_data["power"] = pw
                s = get_val(f"bms_{p}_soc")
                if s is not None:
                    pack_data["soc"] = s
                cd = get_val(f"bms_{p}_cell_delta")
                if cd is not None:
                    pack_data["cell_delta"] = cd
                cmin = get_val(f"bms_{p}_cell_min")
                if cmin is not None:
                    pack_data["cell_min"] = cmin
                cmax = get_val(f"bms_{p}_cell_max")
                if cmax is not None:
                    pack_data["cell_max"] = cmax

                # Temperatures
                t1 = get_val(f"bms_{p}_t1")
                if t1 is not None:
                    pack_data["t1"] = t1
                t2 = get_val(f"bms_{p}_t2")
                if t2 is not None:
                    pack_data["t2"] = t2
                tmos = get_val(f"bms_{p}_tmos")
                if tmos is not None:
                    pack_data["tmos"] = tmos

                # Switches / binary states
                chg = get_bool_val(f"bms_{p}_charging")
                if chg is not None:
                    pack_data["charge"] = chg
                dis = get_bool_val(f"bms_{p}_discharging")
                if dis is not None:
                    pack_data["discharge"] = dis
                bal = get_bool_val(f"bms_{p}_balancing")
                if bal is not None:
                    pack_data["balance"] = bal
                heat = get_bool_val(f"bms_{p}_heating")
                if heat is not None:
                    pack_data["heating"] = heat

                # Cells 1 to 16
                cells = []
                for cell_idx in range(1, 17):
                    cv = get_val(f"bms_{p}_cell_{cell_idx}")
                    if cv is not None:
                        cells.append(cv)
                if cells:
                    pack_data["cells"] = cells
                    if "cell_min" not in pack_data:
                        pack_data["cell_min"] = min(cells)
                    if "cell_max" not in pack_data:
                        pack_data["cell_max"] = max(cells)
                    if "cell_delta" not in pack_data:
                        pack_data["cell_delta"] = round(max(cells) - min(cells), 3)

                if "voltage" in pack_data or "soc" in pack_data or "current" in pack_data or cells:
                    bms_packs.append(pack_data)

            if bms_packs:
                try:
                    async with session.post(
                        f"{DEFAULT_API_URL}/bms-telemetry",
                        json={"macid": inverter_id, "integration_version": INTEGRATION_VERSION, "packs": bms_packs},
                        headers=headers,
                        timeout=10,
                    ) as bms_resp:
                        if bms_resp.status != 200:
                            _LOGGER.warning("Solars Systems API returned status %s on BMS telemetry", bms_resp.status)
                except Exception as bms_err:
                    _LOGGER.debug("Error sending BMS telemetry to Solars Systems: %s", bms_err)

        # Send Heat Pump telemetry if configured
        if data.get(CONF_HAS_HEAT_PUMP):
            hp_payload: dict[str, Any] = {}
            hp_pwr = get_val(CONF_HP_POWER)
            if hp_pwr is not None:
                hp_payload["putere_el_w"] = hp_pwr
                hp_payload["putere_el_kw"] = round(hp_pwr / 1000.0, 2)
                payload["puterePompa"] = hp_pwr

            hp_en = get_val(CONF_HP_ENERGY)
            if hp_en is not None:
                hp_payload["energie_total_kwh"] = hp_en

            t_tur = get_val(CONF_HP_TEMP_FLOW)
            if t_tur is not None:
                hp_payload["temp_tur"] = t_tur

            t_ret = get_val(CONF_HP_TEMP_RETURN)
            if t_ret is not None:
                hp_payload["temp_retur"] = t_ret

            t_dhw = get_val(CONF_HP_TEMP_DHW)
            if t_dhw is not None:
                hp_payload["temp_boiler"] = t_dhw

            t_buf = get_val(CONF_HP_TEMP_BUFFER)
            if t_buf is not None:
                hp_payload["temp_puffer"] = t_buf

            t_amb = get_val(CONF_HP_TEMP_OUTDOOR)
            if t_amb is not None:
                hp_payload["temp_ambient"] = t_amb

            flow = get_val(CONF_HP_FLOW_RATE)
            if flow is not None:
                hp_payload["debit"] = flow

            heat_pwr = get_val(CONF_HP_HEAT_POWER)
            if heat_pwr is not None:
                hp_payload["putere_term_kw"] = heat_pwr
            elif flow is not None and t_tur is not None and t_ret is not None and t_tur > t_ret:
                # Calcul fizic: Debit (L/min) * 0.06973 * deltaT (kW)
                hp_payload["putere_term_kw"] = round(flow * 0.06973 * (t_tur - t_ret), 2)

            cop_val = get_val(CONF_HP_COP)
            if cop_val is not None:
                hp_payload["cop"] = cop_val
            elif "putere_term_kw" in hp_payload and hp_pwr and hp_pwr > 100:
                hp_payload["cop"] = round(hp_payload["putere_term_kw"] / (hp_pwr / 1000.0), 2)

            comp_hz = get_val(CONF_HP_COMP_FREQ)
            if comp_hz is not None:
                hp_payload["comp_hz"] = int(comp_hz)

            st_eid = data.get(CONF_HP_STATUS)
            if st_eid:
                st_state = hass.states.get(st_eid)
                if st_state and st_state.state not in ("unknown", "unavailable", None):
                    hp_payload["stare"] = str(st_state.state)
                    action = st_state.attributes.get("hvac_action")
                    hp_payload["mode"] = str(action) if action else str(st_state.state)

            defrost_val = get_bool_val(CONF_HP_DEFROST)
            if defrost_val is not None:
                hp_payload["defrost"] = defrost_val

            fault_val = get_bool_val(CONF_HP_FAULT)
            if fault_val is not None:
                hp_payload["fault"] = fault_val
            else:
                fault_eid = data.get(CONF_HP_FAULT)
                if fault_eid:
                    f_st = hass.states.get(fault_eid)
                    if f_st and f_st.state not in ("unknown", "unavailable", "0", "false", "off", "ok", "none", None):
                        hp_payload["fault"] = True
                        hp_payload["fault_code"] = str(f_st.state)

            if hp_payload:
                hp_payload["valid"] = True
                try:
                    async with session.post(
                        f"{DEFAULT_API_URL}/heatpump-telemetry",
                        json={"macid": inverter_id, "integration_version": INTEGRATION_VERSION, "heat_pump": hp_payload},
                        headers=headers,
                        timeout=10,
                    ) as hp_resp:
                        if hp_resp.status != 200:
                            _LOGGER.warning("Solars Systems API returned status %s on heat pump telemetry", hp_resp.status)
                except Exception as hp_err:
                    _LOGGER.debug("Error sending heat pump telemetry to Solars Systems: %s", hp_err)

    # 2. Historical Import Task
    async def async_run_history_import() -> None:
        """Fetch historical statistics from HA and send to Solars Systems."""
        energy_entity = data.get(CONF_SENSOR_ENERGY_TODAY)
        if not energy_entity:
            _LOGGER.info("No energy sensor configured; skipping history import.")
            return

        range_choice = data.get(CONF_HISTORY_RANGE, HISTORY_RANGE_ALL)
        now_dt = dt_util.now()

        if range_choice == HISTORY_RANGE_30_DAYS:
            start_dt = now_dt - timedelta(days=30)
        elif range_choice == HISTORY_RANGE_90_DAYS:
            start_dt = now_dt - timedelta(days=90)
        elif range_choice == HISTORY_RANGE_1_YEAR:
            start_dt = now_dt - timedelta(days=365)
        else:
            start_dt = now_dt - timedelta(days=1825)

        _LOGGER.info("Starting historical import for %s starting from %s", energy_entity, start_dt.date())

        try:
            from homeassistant.components.recorder import get_instance
            from homeassistant.components.recorder.statistics import statistics_during_period

            recorder_instance = get_instance(hass)
            stats = await recorder_instance.async_add_executor_job(
                statistics_during_period,
                hass,
                start_dt,
                now_dt,
                [energy_entity],
                "day",
                None,
                {"change", "state", "max", "min"},
            )

            records: list[dict[str, Any]] = []
            entity_stats = stats.get(energy_entity, [])

            for s in entity_stats:
                start_ts = s.get("start")
                if not start_ts:
                    continue
                dt_record = dt_util.as_local(dt_util.utc_from_timestamp(start_ts))

                kwh = s.get("change")
                if kwh is None or kwh <= 0:
                    kwh = s.get("state")

                val = _safe_float(kwh)
                if val is not None and val > 0:
                    records.append({
                        "date": dt_record.strftime("%d-%m-%Y"),
                        "day": dt_record.day,
                        "month": dt_record.month,
                        "year": dt_record.year,
                        "energieZi": round(val, 2),
                    })

            if not records:
                _LOGGER.info("No historical records found for %s", energy_entity)
                return

            _LOGGER.info("Found %d historical days. Sending to Solars Systems in batches...", len(records))

            batch_size = 100
            total_inserted = 0
            total_updated = 0
            total_skipped = 0

            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                post_payload = {
                    "macid": inverter_id,
                    "records": batch,
                }
                async with session.post(
                    f"{DEFAULT_API_URL}/import-history",
                    json=post_payload,
                    headers=headers,
                    timeout=20,
                ) as resp:
                    if resp.status == 200:
                        res_json = await resp.json()
                        total_inserted += res_json.get("inserted", 0)
                        total_updated += res_json.get("updated", 0)
                        total_skipped += res_json.get("skipped", 0)
                    else:
                        _LOGGER.error("Failed batch import (status %s): %s", resp.status, await resp.text())

            msg = (
                f"✅ **Import istoric finalizat cu succes!**\n\n"
                f"* **{total_inserted}** zile noi adăugate în Solars Systems\n"
                f"* **{total_updated}** zile actualizate cu valori mai complete\n"
                f"* **{total_skipped}** zile păstrate neschimbate\n\n"
                f"Invertor: `{inverter_id}`"
            )
            hass.components.persistent_notification.async_create(
                msg,
                title="Solars Systems - Import Istoric",
                notification_id=f"solars_import_{inverter_id}",
            )

        except Exception as err:
            _LOGGER.exception("Error during historical import: %s", err)

    cancel_timer = async_track_time_interval(
        hass, async_send_telemetry, timedelta(seconds=update_interval)
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "cancel_timer": cancel_timer,
    }

    entry.async_on_unload(entry.add_update_listener(update_listener))

    hass.async_create_task(async_send_telemetry())

    if data.get(CONF_IMPORT_HISTORY, True):
        hass.async_create_task(async_run_history_import())

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)
    if entry_data and "cancel_timer" in entry_data:
        entry_data["cancel_timer"]()

    return True
