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
    DEFAULT_API_URL,
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
    data = entry.data
    api_key = data[CONF_API_KEY]
    inverter_id = data[CONF_INVERTER_ID]
    update_interval = data.get(CONF_UPDATE_INTERVAL, 30)

    session = async_get_clientsession(hass)
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # 1. Periodic Telemetry Sender
    async def async_send_telemetry(now: datetime | None = None) -> None:
        """Read states from Home Assistant and push to Solars Systems API."""
        payload: dict[str, Any] = {"macid": inverter_id}

        def get_val(key: str) -> float | None:
            entity_id = data.get(key)
            if not entity_id:
                return None
            state = hass.states.get(entity_id)
            if not state:
                return None
            return _safe_float(state.state)

        pv_power = get_val(CONF_SENSOR_PV_POWER)
        load_power = get_val(CONF_SENSOR_LOAD_POWER)
        batt_soc = get_val(CONF_SENSOR_BATT_SOC)
        batt_volt = get_val(CONF_SENSOR_BATT_VOLT)
        batt_power = get_val(CONF_SENSOR_BATT_POWER)
        grid_volt = get_val(CONF_SENSOR_GRID_VOLT)
        energy_today = get_val(CONF_SENSOR_ENERGY_TODAY)

        if pv_power is not None:
            payload["puterePV"] = pv_power
        if load_power is not None:
            payload["putereConsum"] = load_power
        if batt_soc is not None:
            payload["procentBaterie"] = batt_soc
        if batt_volt is not None:
            payload["tensiuneBaterie"] = batt_volt
        if batt_power is not None:
            payload["putereBaterie"] = batt_power
        if grid_volt is not None:
            payload["tensiuneAcIn"] = grid_volt
            payload["tensiuneAcOut"] = grid_volt
        if energy_today is not None:
            payload["energieZi"] = energy_today

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
            # All available (last 5 years)
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
                # Format start timestamp as DD-MM-YYYY
                start_ts = s.get("start")
                if not start_ts:
                    continue
                dt_record = dt_util.as_local(dt_util.utc_from_timestamp(start_ts))

                # Energy value for that day
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

            # Send in batches of 100 days
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

            # Notify user in Home Assistant UI
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

    # Schedule recurring telemetry
    cancel_timer = async_track_time_interval(
        hass, async_send_telemetry, timedelta(seconds=update_interval)
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "cancel_timer": cancel_timer,
    }

    # Run immediate initial telemetry
    hass.async_create_task(async_send_telemetry())

    # Run history import in background if enabled
    if data.get(CONF_IMPORT_HISTORY, True):
        hass.async_create_task(async_run_history_import())

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)
    if entry_data and "cancel_timer" in entry_data:
        entry_data["cancel_timer"]()

    return True
