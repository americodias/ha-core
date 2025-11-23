"""The Duosida EV Charger integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from duosida_ev import DuosidaCharger

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .const import CONF_DEVICE_ID, CONF_SWITCH_DEBOUNCE, DEFAULT_SWITCH_DEBOUNCE, DOMAIN
from .coordinator import DuosidaDataUpdateCoordinator
from .discovery import async_discover_devices, async_trigger_discovery

_LOGGER = logging.getLogger(__name__)

# Discovery settings
DISCOVER_SCAN_TIMEOUT = 5
DISCOVERY_INTERVAL = timedelta(minutes=15)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type DuosidaConfigEntry = ConfigEntry[DuosidaDataUpdateCoordinator]

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Duosida EV Charger integration.

    This function runs background discovery to automatically find chargers
    on all networks the system is connected to.
    """

    async def _async_discovery(*_: Any) -> None:
        """Run discovery and trigger config flows for found devices."""
        discovered = await async_discover_devices(hass, DISCOVER_SCAN_TIMEOUT)
        async_trigger_discovery(hass, discovered)

    # Run discovery immediately on startup
    hass.async_create_background_task(
        _async_discovery(), "duosida_ev-initial-discovery"
    )

    # Schedule periodic discovery to find new chargers
    async_track_time_interval(
        hass, _async_discovery, DISCOVERY_INTERVAL, cancel_on_shutdown=True
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: DuosidaConfigEntry) -> bool:
    """Set up Duosida EV Charger from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, 9988)
    device_id = entry.data[CONF_DEVICE_ID]

    switch_debounce = entry.options.get(
        CONF_SWITCH_DEBOUNCE,
        entry.data.get(CONF_SWITCH_DEBOUNCE, DEFAULT_SWITCH_DEBOUNCE),
    )

    charger = DuosidaCharger(
        host=host,
        port=port,
        device_id=device_id,
        debug=False,
    )

    coordinator = DuosidaDataUpdateCoordinator(
        hass,
        entry,
        charger,
        device_id,
        switch_debounce,
    )

    await coordinator.async_load_stored_settings()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: DuosidaConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: DuosidaConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and hasattr(entry, "runtime_data") and entry.runtime_data:
        entry.runtime_data.disconnect()

    return unload_ok
