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

from .const import DOMAIN, INTEGRATION_VERSION, CONF_INVERTER_ID, CONF_HAS_HEAT_PUMP


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Solars Systems sensor entities."""
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    coordinator = entry_data.get("coordinator")
    if not coordinator:
        return

    data = {**entry.data, **entry.options}
    inverter_id = data[CONF_INVERTER_ID]
    has_hp = bool(data.get(CONF_HAS_HEAT_PUMP))

    entities: list[SensorEntity] = [
        SolarProCloudStatusSensor(coordinator, inverter_id, has_hp),
        SolarProLastSyncSensor(coordinator, inverter_id, has_hp),
        SolarProPacketsSentSensor(coordinator, inverter_id, has_hp),
        SolarProApiLatencySensor(coordinator, inverter_id, has_hp),
        SolarProTransmissionErrorsSensor(coordinator, inverter_id, has_hp),
    ]

    async_add_entities(entities)


class SolarProBaseSensor(SensorEntity):
    """Base sensor for Solars Systems diagnostic sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: Any, inverter_id: str, has_hp: bool, key: str) -> None:
        """Initialize base sensor."""
        self.coordinator = coordinator
        self._inverter_id = inverter_id
        self._has_hp = has_hp
        self._key = key
        self._attr_unique_id = f"{DOMAIN}_{inverter_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant device info."""
        model_name = "SolarPro Gateway (PV + Pompa Caldura)" if self._has_hp else "SolarPro Cloud Gateway"
        return DeviceInfo(
            identifiers={(DOMAIN, self._inverter_id)},
            name=f"SolarPro Gateway ({self._inverter_id})",
            manufacturer="Solars Systems",
            model=model_name,
            sw_version=INTEGRATION_VERSION,
            configuration_url="https://solars-systems.eu",
        )

    async def async_added_to_hass(self) -> None:
        """Register coordinator update callback."""
        self.coordinator.register_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister coordinator update callback."""
        self.coordinator.unregister_listener(self.async_write_ha_state)


class SolarProCloudStatusSensor(SolarProBaseSensor):
    """Sensor reporting the cloud connection status."""

    _attr_translation_key = "cloud_status"
    _attr_name = "Status Conexiune Cloud"
    if EntityCategory:
        _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: Any, inverter_id: str, has_hp: bool) -> None:
        super().__init__(coordinator, inverter_id, has_hp, "cloud_status")

    @property
    def native_value(self) -> str:
        """Return the current cloud connection status."""
        return self.coordinator.status

    @property
    def icon(self) -> str:
        """Dynamic icon depending on cloud connection status."""
        if self.coordinator.status == "Conectat":
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

    def __init__(self, coordinator: Any, inverter_id: str, has_hp: bool) -> None:
        super().__init__(coordinator, inverter_id, has_hp, "last_sync")

    @property
    def native_value(self) -> Any:
        """Return the timestamp of the last telemetry push."""
        return self.coordinator.last_telemetry


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

    def __init__(self, coordinator: Any, inverter_id: str, has_hp: bool) -> None:
        super().__init__(coordinator, inverter_id, has_hp, "packets_sent")

    @property
    def native_value(self) -> int:
        """Return total packets count."""
        return self.coordinator.telemetry_count


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

    def __init__(self, coordinator: Any, inverter_id: str, has_hp: bool) -> None:
        super().__init__(coordinator, inverter_id, has_hp, "api_latency")

    @property
    def native_value(self) -> float | None:
        """Return the API latency in ms."""
        return self.coordinator.api_latency


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

    def __init__(self, coordinator: Any, inverter_id: str, has_hp: bool) -> None:
        super().__init__(coordinator, inverter_id, has_hp, "transmission_errors")

    @property
    def native_value(self) -> int:
        """Return total transmission errors."""
        return self.coordinator.error_count
