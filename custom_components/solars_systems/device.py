"""Device management for Solars Systems integration."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, INTEGRATION_VERSION, CONF_INVERTER_ID, CONF_HAS_HEAT_PUMP

_LOGGER = logging.getLogger(__name__)


class SolarProDevice:
    """Represents a Solars Systems Inverter / Gateway device in Home Assistant."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the device representation."""
        self.hass = hass
        self.entry = entry
        data = {**entry.data, **entry.options}

        self.inverter_id: str = str(data.get(CONF_INVERTER_ID, "unknown"))
        self.api_key: str = str(data.get("api_key", ""))
        self.has_heat_pump: bool = bool(data.get(CONF_HAS_HEAT_PUMP, False))

        # Device Metadata
        self.manufacturer = "Solars Systems"
        self.model = "SolarPro Gateway (PV + Pompa Caldura)" if self.has_heat_pump else "SolarPro Cloud Gateway"
        self.name = f"SolarPro Gateway ({self.inverter_id})"
        self.sw_version = INTEGRATION_VERSION
        self.configuration_url = "https://solars-systems.eu"

        # Diagnostic state metrics
        self.status: str = "Conectat"
        self.last_telemetry: datetime | None = None
        self.telemetry_count: int = 0
        self.error_count: int = 0
        self.api_latency: float | None = None
        self.last_error: str | None = None

        self._listeners: list[Any] = []
        self.async_send_telemetry: Any = None
        self.device_id: str | None = None

    @property
    def identifiers(self) -> set[tuple[str, str]]:
        """Return unique device identifiers."""
        return {(DOMAIN, self.inverter_id)}

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant DeviceInfo for entities."""
        return DeviceInfo(
            identifiers=self.identifiers,
            name=self.name,
            manufacturer=self.manufacturer,
            model=self.model,
            sw_version=self.sw_version,
            configuration_url=self.configuration_url,
        )

    def async_register(self) -> dr.DeviceEntry:
        """Explicitly register or update the device in the Home Assistant Device Registry."""
        dev_reg = dr.async_get(self.hass)
        device_entry = dev_reg.async_get_or_create(
            config_entry_id=self.entry.entry_id,
            identifiers=self.identifiers,
            name=self.name,
            manufacturer=self.manufacturer,
            model=self.model,
            sw_version=self.sw_version,
            configuration_url=self.configuration_url,
        )
        self.device_id = device_entry.id
        _LOGGER.debug("Registered Solars Systems device %s with ID %s", self.name, self.device_id)
        return device_entry

    def register_listener(self, update_callback: Any) -> None:
        """Register entity update listener."""
        if update_callback not in self._listeners:
            self._listeners.append(update_callback)

    def unregister_listener(self, update_callback: Any) -> None:
        """Unregister entity update listener."""
        if update_callback in self._listeners:
            self._listeners.remove(update_callback)

    def notify_listeners(self) -> None:
        """Notify all listeners that device metrics have changed."""
        for listener in list(self._listeners):
            try:
                listener()
            except Exception as err:
                _LOGGER.debug("Error notifying Solars Systems listener: %s", err)

    def update_telemetry_success(self, latency_ms: float, now: datetime) -> None:
        """Record a successful telemetry transmission."""
        prev_status = self.status
        self.status = "Conectat"
        self.last_telemetry = now
        self.telemetry_count += 1
        self.api_latency = latency_ms
        self.last_error = None

        self.notify_listeners()

        # Fire HA automation events
        if self.device_id:
            self.hass.bus.async_fire(
                f"{DOMAIN}_event",
                {"device_id": self.device_id, "type": "telemetry_sent"},
            )
            if prev_status != "Conectat":
                self.hass.bus.async_fire(
                    f"{DOMAIN}_event",
                    {"device_id": self.device_id, "type": "cloud_connected"},
                )

    def update_telemetry_error(self, error_msg: str) -> None:
        """Record a telemetry error."""
        prev_status = self.status
        self.error_count += 1
        self.status = error_msg or "Eroare Conexiune"
        self.last_error = error_msg

        self.notify_listeners()

        # Fire HA automation events
        if self.device_id and prev_status == "Conectat":
            self.hass.bus.async_fire(
                f"{DOMAIN}_event",
                {"device_id": self.device_id, "type": "cloud_disconnected"},
            )
