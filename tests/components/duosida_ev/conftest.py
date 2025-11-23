"""Fixtures for Duosida EV integration tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.components.duosida_ev.const import (
    CONF_DEVICE_ID,
    DEFAULT_PORT,
    DOMAIN,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

MOCK_CHARGER_STATUS = {
    "conn_status": 2,
    "cp_voltage": 6.0,
    "voltage": 230.0,
    "voltage_l2": 230.0,
    "voltage_l3": 230.0,
    "current": 16.0,
    "current_l2": 16.0,
    "current_l3": 16.0,
    "power": 11040,
    "temperature_station": 35.0,
    "session_energy": 5.5,
    "session_time": 120,
    "model": "SmartChargePI",
    "manufacturer": "Duosida",
    "firmware": "1.0.0",
}

MOCK_CONFIG_ENTRY_DATA = {
    CONF_HOST: "192.168.1.100",
    CONF_PORT: DEFAULT_PORT,
    CONF_DEVICE_ID: "03123456789012345678",
}

MOCK_DISCOVERED_CHARGER = {
    "ip": "192.168.1.100",
    "port": 9988,
    "device_id": "03123456789012345678",
    "model": "SmartChargePI",
}


class MockDuosidaCharger:
    """Mock DuosidaCharger for testing."""

    def __init__(
        self, host: str, port: int = 9988, device_id: str = "", debug: bool = False
    ) -> None:
        """Initialize mock charger."""
        self.host = host
        self.port = port
        self.device_id = device_id
        self.debug = debug
        self._connected = False
        self._status = MOCK_CHARGER_STATUS.copy()

    def connect(self) -> bool:
        """Mock connect."""
        self._connected = True
        return True

    def disconnect(self) -> None:
        """Mock disconnect."""
        self._connected = False

    def get_status(self) -> MockDuosidaCharger:
        """Mock get_status - returns self (charger object)."""
        if not self._connected:
            raise ConnectionError("Not connected")
        return self

    def to_dict(self) -> dict[str, Any]:
        """Mock to_dict."""
        if not self._connected:
            raise ConnectionError("Not connected")
        return self._status

    def start_charging(self) -> bool:
        """Mock start_charging."""
        if not self._connected:
            return False
        self._status["conn_status"] = 2
        return True

    def stop_charging(self) -> bool:
        """Mock stop_charging."""
        if not self._connected:
            return False
        self._status["conn_status"] = 0
        return True

    def set_max_current(self, current: int) -> bool:
        """Mock set_max_current."""
        if not self._connected:
            return False
        if not 6 <= current <= 32:
            return False
        self._status["current"] = float(current)
        return True

    def set_led_brightness(self, brightness: int) -> bool:
        """Mock set_led_brightness."""
        if not self._connected:
            return False
        if brightness not in (0, 1, 3):
            return False
        return True

    def set_direct_work_mode(self, enabled: bool) -> bool:
        """Mock set_direct_work_mode."""
        return self._connected

    def set_stop_on_disconnect(self, enabled: bool) -> bool:
        """Mock set_stop_on_disconnect."""
        return self._connected

    def set_max_voltage(self, voltage: int) -> bool:
        """Mock set_max_voltage."""
        if not self._connected:
            return False
        return 265 <= voltage <= 290

    def set_min_voltage(self, voltage: int) -> bool:
        """Mock set_min_voltage."""
        if not self._connected:
            return False
        return 70 <= voltage <= 110


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Duosida EV Charger",
        data=MOCK_CONFIG_ENTRY_DATA,
        entry_id="test_entry_id",
        unique_id="03123456789012345678",
    )


@pytest.fixture
def mock_duosida_charger() -> Generator[MagicMock]:
    """Mock the DuosidaCharger class."""
    mock_charger = MockDuosidaCharger(
        host="192.168.1.100",
        port=9988,
        device_id="03123456789012345678",
    )
    with (
        patch(
            "homeassistant.components.duosida_ev.DuosidaCharger",
            return_value=mock_charger,
        ) as mock,
        patch(
            "homeassistant.components.duosida_ev.coordinator.DuosidaCharger",
            return_value=mock_charger,
        ),
        patch(
            "homeassistant.components.duosida_ev.config_flow.DuosidaCharger",
            return_value=mock_charger,
        ),
    ):
        yield mock


@pytest.fixture
def mock_discover_chargers() -> Generator[MagicMock]:
    """Mock discover_chargers function."""
    with patch(
        "homeassistant.components.duosida_ev.config_flow.discover_chargers",
        return_value=[MOCK_DISCOVERED_CHARGER],
    ) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_discovery_in_setup() -> Generator[MagicMock]:
    """Auto-mock discovery functions to prevent socket usage in tests."""
    with (
        patch(
            "homeassistant.components.duosida_ev.async_discover_devices",
            return_value=[],
        ) as mock,
        patch(
            "homeassistant.components.duosida_ev.discovery.discover_chargers",
            return_value=[],
        ),
        # Ensure onboarding returns True so auto-setup doesn't trigger
        patch(
            "homeassistant.components.duosida_ev.config_flow.onboarding.async_is_onboarded",
            return_value=True,
        ),
    ):
        yield mock


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_duosida_charger: MagicMock,
) -> MockConfigEntry:
    """Set up the integration with mocked charger."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "homeassistant.components.duosida_ev.coordinator.Store.async_load",
            return_value=None,
        ),
        patch(
            "homeassistant.components.duosida_ev.coordinator.Store.async_save",
            return_value=None,
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    return mock_config_entry
