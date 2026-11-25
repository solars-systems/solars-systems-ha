"""Sensor platform for Solars Systems integration."""
from __future__ import annotations

from typing import Any
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

try:
    from homeassistant.const import EntityCategory
except ImportError:
    try:
        from homeassistant.helpers.entity import EntityCategory
    except ImportError:
        EntityCategory = None

from .const import DOMAIN
from .device import SolarProDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Solars Systems sensor entities."""
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    device: SolarProDevice | None = entry_data.get("device")
    if not device:
        return

    entities: list[SensorEntity] = [
        SolarProCloudStatusSensor(device),
        SolarProLastSyncSensor(device),
        SolarProPacketsSentSensor(device),
        SolarProApiLatencySensor(device),
        SolarProTransmissionErrorsSensor(device),
    ]

    async_add_entities(entities)


class SolarProBaseSensor(SensorEntity):
    """Base sensor for Solars Systems diagnostic sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: SolarProDevice, key: str) -> None:
        """Initialize base sensor."""
        self.device = device
        self._key = key
        self._attr_unique_id = f"{DOMAIN}_{device.inverter_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant device info."""
        return self.device.device_info

    async def async_added_to_hass(self) -> None:
        """Register device update callback."""
        self.device.register_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister device update callback."""
        self.device.unregister_listener(self.async_write_ha_state)


class SolarProCloudStatusSensor(SolarProBaseSensor):
    """Sensor reporting the cloud connection status."""

    _attr_translation_key = "cloud_status"
    _attr_name = "Status Conexiune Cloud"
    if EntityCategory:
        _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device: SolarProDevice) -> None:
        super().__init__(device, "cloud_status")

    @property
    def native_value(self) -> str:
        """Return the current cloud connection status."""
        return self.device.status

    @property
    def icon(self) -> str:
        """Dynamic icon depending on cloud connection status."""
        if self.device.status == "Conectat":
            return "mdi:cloud-check"
        return "mdi:cloud-alert"


class SolarProLastSyncSensor(SolarProBaseSensor):
    """Sensor reporting the timestamp of the last successful telemetry push."""

    _attr_translation_key = "last_sync"
    _attr_name = "Ultima Sincronizare"
    _attr_icon = "mdi:clock-check-outline"
    if SensorDeviceClass:
        _attr_device_class = SensorDeviceClass.TIMESTAMP
    if EntityCategory:
        _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device: SolarProDevice) -> None:
        super().__init__(device, "last_sync")

    @property
    def native_value(self) -> Any:
        """Return the timestamp of the last telemetry push."""
        return self.device.last_telemetry


class SolarProPacketsSentSensor(SolarProBaseSensor):
    """Sensor reporting total telemetry packets sent."""

    _attr_translation_key = "packets_sent"
    _attr_name = "Pachete Telemetrie Trimise"
    _attr_icon = "mdi:upload-network"
    _attr_native_unit_of_measurement = "pachete"
    if SensorStateClass:
        _attr_state_class = SensorStateClass.TOTAL_INCREASING
    if EntityCategory:
        _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device: SolarProDevice) -> None:
        super().__init__(device, "packets_sent")

    @property
    def native_value(self) -> int:
        """Return total packets count."""
        return self.device.telemetry_count


class SolarProApiLatencySensor(SolarProBaseSensor):
    """Sensor reporting the round-trip API latency."""

    _attr_translation_key = "api_latency"
    _attr_name = "Latenta Raspuns Cloud"
    _attr_icon = "mdi:timer-outline"
    _attr_native_unit_of_measurement = "ms"
    if SensorStateClass:
        _attr_state_class = SensorStateClass.MEASUREMENT
    if EntityCategory:
        _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device: SolarProDevice) -> None:
        super().__init__(device, "api_latency")

    @property
    def native_value(self) -> float | None:
        """Return the API latency in ms."""
        return self.device.api_latency


class SolarProTransmissionErrorsSensor(SolarProBaseSensor):
    """Sensor reporting total transmission errors encountered."""

    _attr_translation_key = "errors_count"
    _attr_name = "Erori Transmisie Cloud"
    _attr_icon = "mdi:alert-circle-outline"
    _attr_native_unit_of_measurement = "erori"
    if SensorStateClass:
        _attr_state_class = SensorStateClass.TOTAL_INCREASING
    if EntityCategory:
        _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device: SolarProDevice) -> None:
        super().__init__(device, "transmission_errors")

    @property
    def native_value(self) -> int:
        """Return total transmission errors."""
        return self.device.error_count
