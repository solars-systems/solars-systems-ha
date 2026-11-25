"""Button platform for Solars Systems integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device import SolarProDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Solars Systems button entities."""
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    device: SolarProDevice | None = entry_data.get("device")
    if not device:
        return

    async_add_entities([SolarProSyncNowButton(device)])


class SolarProSyncNowButton(ButtonEntity):
    """Button to force an immediate telemetry push to Solars Systems cloud."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:cloud-sync"
    _attr_translation_key = "sync_now"
    _attr_name = "Sincronizeaza Acum"

    def __init__(self, device: SolarProDevice) -> None:
        """Initialize button."""
        self.device = device
        self._attr_unique_id = f"{DOMAIN}_{device.inverter_id}_sync_now"

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant device info."""
        return self.device.device_info

    async def async_press(self) -> None:
        """Handle button press to force an immediate telemetry sync."""
        if self.device.async_send_telemetry:
            await self.device.async_send_telemetry()
