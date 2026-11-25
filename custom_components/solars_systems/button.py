"""Button platform for Solars Systems integration."""
from __future__ import annotations

from typing import Any
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, INTEGRATION_VERSION, CONF_INVERTER_ID, CONF_HAS_HEAT_PUMP


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Solars Systems button entities."""
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    coordinator = entry_data.get("coordinator")
    if not coordinator:
        return

    data = {**entry.data, **entry.options}
    inverter_id = data[CONF_INVERTER_ID]
    has_hp = bool(data.get(CONF_HAS_HEAT_PUMP))

    async_add_entities([SolarProSyncNowButton(coordinator, inverter_id, has_hp)])


class SolarProSyncNowButton(ButtonEntity):
    """Button to force an immediate telemetry push to Solars Systems cloud."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:cloud-sync"
    _attr_translation_key = "sync_now"
    _attr_name = "Sincronizeaza Acum"

    def __init__(self, coordinator: Any, inverter_id: str, has_hp: bool) -> None:
        """Initialize button."""
        self.coordinator = coordinator
        self._inverter_id = inverter_id
        self._has_hp = has_hp
        self._attr_unique_id = f"{DOMAIN}_{inverter_id}_sync_now"

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

    async def async_press(self) -> None:
        """Handle button press to force an immediate telemetry sync."""
        if self.coordinator.async_send_telemetry:
            await self.coordinator.async_send_telemetry()
