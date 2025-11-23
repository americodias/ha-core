"""Test Duosida EV discovery module."""

from __future__ import annotations

from ipaddress import IPv4Address
from unittest.mock import patch

from homeassistant.components.duosida_ev.discovery import (
    DiscoveredCharger,
    async_discover_devices,
    async_trigger_discovery,
)
from homeassistant.core import HomeAssistant


async def test_async_discover_devices(hass: HomeAssistant) -> None:
    """Test discovering devices on the network."""
    mock_discovered = [
        {"ip": "192.168.1.100", "device_id": "device123"},
        {"ip": "192.168.1.101", "device_id": "device456"},
    ]

    with (
        patch(
            "homeassistant.components.duosida_ev.discovery.network.async_get_ipv4_broadcast_addresses",
            return_value={IPv4Address("192.168.1.255")},
        ),
        patch(
            "homeassistant.components.duosida_ev.discovery.discover_chargers",
            return_value=mock_discovered,
        ),
    ):
        result = await async_discover_devices(hass, timeout=5)

    assert len(result) == 2
    assert isinstance(result[0], DiscoveredCharger)
    assert result[0].ip_address == "192.168.1.100"
    assert result[0].device_id == "device123"
    assert result[1].ip_address == "192.168.1.101"
    assert result[1].device_id == "device456"


async def test_async_discover_devices_empty(hass: HomeAssistant) -> None:
    """Test discovering no devices on the network."""
    with (
        patch(
            "homeassistant.components.duosida_ev.discovery.network.async_get_ipv4_broadcast_addresses",
            return_value={IPv4Address("192.168.1.255")},
        ),
        patch(
            "homeassistant.components.duosida_ev.discovery.discover_chargers",
            return_value=[],
        ),
    ):
        result = await async_discover_devices(hass, timeout=5)

    assert len(result) == 0


async def test_async_discover_devices_missing_device_id(hass: HomeAssistant) -> None:
    """Test discovering devices with missing device_id."""
    mock_discovered = [
        {"ip": "192.168.1.100"},  # No device_id
    ]

    with (
        patch(
            "homeassistant.components.duosida_ev.discovery.network.async_get_ipv4_broadcast_addresses",
            return_value={IPv4Address("192.168.1.255")},
        ),
        patch(
            "homeassistant.components.duosida_ev.discovery.discover_chargers",
            return_value=mock_discovered,
        ),
    ):
        result = await async_discover_devices(hass, timeout=5)

    assert len(result) == 1
    assert result[0].ip_address == "192.168.1.100"
    assert result[0].device_id == ""  # Default to empty string


async def test_async_trigger_discovery(hass: HomeAssistant) -> None:
    """Test triggering discovery flows."""
    discovered = [
        DiscoveredCharger(ip_address="192.168.1.100", device_id="device123"),
        DiscoveredCharger(ip_address="192.168.1.101", device_id="device456"),
    ]

    with patch(
        "homeassistant.components.duosida_ev.discovery.discovery_flow.async_create_flow"
    ) as mock_create_flow:
        async_trigger_discovery(hass, discovered)

    assert mock_create_flow.call_count == 2
    # Check first call
    call_args = mock_create_flow.call_args_list[0]
    assert call_args[0][0] == hass
    assert call_args[0][1] == "duosida_ev"
    assert call_args[1]["data"]["ip_address"] == "192.168.1.100"
    assert call_args[1]["data"]["device_id"] == "device123"


async def test_async_trigger_discovery_empty(hass: HomeAssistant) -> None:
    """Test triggering discovery with no devices."""
    with patch(
        "homeassistant.components.duosida_ev.discovery.discovery_flow.async_create_flow"
    ) as mock_create_flow:
        async_trigger_discovery(hass, [])

    assert mock_create_flow.call_count == 0


async def test_discovered_charger_dataclass() -> None:
    """Test DiscoveredCharger dataclass."""
    charger = DiscoveredCharger(ip_address="192.168.1.100", device_id="test123")
    assert charger.ip_address == "192.168.1.100"
    assert charger.device_id == "test123"
