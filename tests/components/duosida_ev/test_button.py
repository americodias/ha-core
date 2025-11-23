"""Test Duosida EV button entities."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_start_charging_button(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test start charging button."""
    # Start charging button is enabled by default
    start_button = hass.states.get(
        "button.duosida_ev_charger_192_168_1_100_start_charging"
    )
    assert start_button is not None


async def test_stop_charging_button(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test stop charging button."""
    # Stop charging button is enabled by default
    stop_button = hass.states.get(
        "button.duosida_ev_charger_192_168_1_100_stop_charging"
    )
    assert stop_button is not None


async def test_reset_energy_button(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test reset total energy button."""
    # Reset energy button should exist
    reset_button = hass.states.get(
        "button.duosida_ev_charger_192_168_1_100_reset_total_energy"
    )
    assert reset_button is not None


async def test_reset_energy_button_press(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test pressing reset energy button."""
    with patch(
        "homeassistant.components.duosida_ev.coordinator.DuosidaDataUpdateCoordinator.async_reset_total_energy",
        return_value=None,
    ) as mock_reset:
        # Press the button
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.duosida_ev_charger_192_168_1_100_reset_total_energy"},
            blocking=True,
        )

        # Verify async_reset_total_energy was called
        mock_reset.assert_called_once()
