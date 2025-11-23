"""The Duosida EV Charger integration discovery."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from duosida_ev import discover_chargers

from homeassistant import config_entries
from homeassistant.components import network
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import discovery_flow

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DISCOVER_TIMEOUT = 5


@dataclass
class DiscoveredCharger:
    """Represent a discovered Duosida charger."""

    ip_address: str
    device_id: str


async def async_discover_devices(
    hass: HomeAssistant, timeout: int = DISCOVER_TIMEOUT
) -> list[DiscoveredCharger]:
    """Discover Duosida chargers on all networks.

    This scans all IPv4 broadcast addresses to find chargers
    across all networks the system is connected to.
    """
    broadcast_addrs = await network.async_get_ipv4_broadcast_addresses(hass)
    _LOGGER.debug("Scanning for Duosida chargers on %s networks", len(broadcast_addrs))

    # Discover chargers using the library's broadcast discovery
    # The library uses UDP broadcast on port 9988
    discovered: list[dict[str, Any]] = await hass.async_add_executor_job(
        discover_chargers, timeout
    )

    chargers = [
        DiscoveredCharger(
            ip_address=device["ip"],
            device_id=device.get("device_id", ""),
        )
        for device in discovered
    ]

    _LOGGER.debug("Discovered %s Duosida charger(s)", len(chargers))
    return chargers


@callback
def async_trigger_discovery(
    hass: HomeAssistant,
    discovered_devices: list[DiscoveredCharger],
) -> None:
    """Trigger config flows for discovered devices."""
    for device in discovered_devices:
        discovery_flow.async_create_flow(
            hass,
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                "ip_address": device.ip_address,
                "device_id": device.device_id,
            },
        )
