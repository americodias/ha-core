"""Binary sensor platform for Duosida EV Charger."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DuosidaConfigEntry
from .const import CONF_DEVICE_ID
from .coordinator import DuosidaDataUpdateCoordinator
from .entity import DuosidaEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DuosidaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Duosida binary sensors."""
    coordinator = entry.runtime_data
    device_id = entry.data[CONF_DEVICE_ID]

    async_add_entities([DuosidaChargingBinarySensor(coordinator, device_id)])


class DuosidaChargingBinarySensor(DuosidaEntity, BinarySensorEntity):
    """Binary sensor indicating charging status."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    _attr_translation_key = "charging"

    def __init__(
        self,
        coordinator: DuosidaDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the charging binary sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_charging"

    @property
    def is_on(self) -> bool:
        """Return true if charging is active."""
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("conn_status") == 2
