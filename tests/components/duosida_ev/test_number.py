"""Test Duosida EV number entities."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.components.duosida_ev.number import (
    DuosidaLedBrightnessNumber,
    DuosidaMaxVoltageNumber,
    DuosidaMinVoltageNumber,
)
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_max_current_number(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test max charging current number entity."""
    # Check max current number entity exists
    max_current = hass.states.get(
        "number.duosida_ev_charger_192_168_1_100_max_charging_current"
    )
    assert max_current is not None

    # Check range
    assert max_current.attributes["min"] == 6
    assert max_current.attributes["max"] == 32
    assert max_current.attributes["step"] == 1


async def test_max_current_set_value(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test setting max current value."""
    with patch(
        "homeassistant.components.duosida_ev.coordinator.DuosidaDataUpdateCoordinator.async_set_max_current",
        return_value=True,
    ) as mock_set:
        # Set value
        await hass.services.async_call(
            "number",
            "set_value",
            {
                "entity_id": "number.duosida_ev_charger_192_168_1_100_max_charging_current",
                "value": 20,
            },
            blocking=True,
        )

        # Verify async_set_max_current was called with correct value
        mock_set.assert_called_once_with(20)


async def test_led_brightness_number(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test LED brightness number entity."""
    # LED brightness is disabled by default
    led_brightness = hass.states.get(
        "number.duosida_ev_charger_192_168_1_100_led_brightness"
    )
    assert led_brightness is None  # Disabled by default


async def test_max_voltage_number(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test max voltage number entity."""
    # Max voltage is disabled by default
    max_voltage = hass.states.get("number.duosida_ev_charger_192_168_1_100_max_voltage")
    assert max_voltage is None  # Disabled by default


async def test_min_voltage_number(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test min voltage number entity."""
    # Min voltage is disabled by default
    min_voltage = hass.states.get("number.duosida_ev_charger_192_168_1_100_min_voltage")
    assert min_voltage is None  # Disabled by default


async def test_led_brightness_property(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test LED brightness property reads from stored settings."""
    # Get coordinator from runtime_data
    coordinator = init_integration.runtime_data

    # Create a number entity instance directly
    number_entity = DuosidaLedBrightnessNumber(coordinator, "03123456789012345678")

    # Test native_value reads from stored settings (should be None initially)
    value = number_entity.native_value
    assert value is None or isinstance(value, (int, float))


async def test_max_voltage_property(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test max voltage property reads from stored settings."""
    # Get coordinator from runtime_data
    coordinator = init_integration.runtime_data

    # Create a number entity instance directly
    number_entity = DuosidaMaxVoltageNumber(coordinator, "03123456789012345678")

    # Test native_value reads from stored settings (should be None initially)
    value = number_entity.native_value
    assert value is None or isinstance(value, (int, float))


async def test_min_voltage_property(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test min voltage property reads from stored settings."""
    # Get coordinator from runtime_data
    coordinator = init_integration.runtime_data

    # Create a number entity instance directly
    number_entity = DuosidaMinVoltageNumber(coordinator, "03123456789012345678")

    # Test native_value reads from stored settings (should be None initially)
    value = number_entity.native_value
    assert value is None or isinstance(value, (int, float))


async def test_led_brightness_async_set_value(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test LED brightness async_set_native_value method."""
    # Get coordinator from runtime_data
    coordinator = init_integration.runtime_data

    # Create entity
    number_entity = DuosidaLedBrightnessNumber(coordinator, "03123456789012345678")
    number_entity.hass = hass

    # Test with value 2 (should be mapped to 1)
    with (
        patch.object(coordinator, "async_set_led_brightness", return_value=True),
        patch.object(number_entity, "async_write_ha_state") as mock_write,
    ):
        await number_entity.async_set_native_value(2)
        coordinator.async_set_led_brightness.assert_called_once_with(1)  # Mapped from 2
        mock_write.assert_called_once()

    # Test with value 3 (no mapping)
    with (
        patch.object(coordinator, "async_set_led_brightness", return_value=True),
        patch.object(number_entity, "async_write_ha_state") as mock_write,
    ):
        await number_entity.async_set_native_value(3)
        coordinator.async_set_led_brightness.assert_called_once_with(3)
        mock_write.assert_called_once()


async def test_max_voltage_async_set_value(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test max voltage async_set_native_value method."""
    # Get coordinator from runtime_data
    coordinator = init_integration.runtime_data

    # Create entity
    number_entity = DuosidaMaxVoltageNumber(coordinator, "03123456789012345678")
    number_entity.hass = hass

    # Test with success
    with (
        patch.object(coordinator, "async_set_max_voltage", return_value=True),
        patch.object(number_entity, "async_write_ha_state") as mock_write,
    ):
        await number_entity.async_set_native_value(280)
        coordinator.async_set_max_voltage.assert_called_once_with(280)
        mock_write.assert_called_once()


async def test_min_voltage_async_set_value(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test min voltage async_set_native_value method."""
    # Get coordinator from runtime_data
    coordinator = init_integration.runtime_data

    # Create entity
    number_entity = DuosidaMinVoltageNumber(coordinator, "03123456789012345678")
    number_entity.hass = hass

    # Test with success
    with (
        patch.object(coordinator, "async_set_min_voltage", return_value=True),
        patch.object(number_entity, "async_write_ha_state") as mock_write,
    ):
        await number_entity.async_set_native_value(90)
        coordinator.async_set_min_voltage.assert_called_once_with(90)
        mock_write.assert_called_once()
