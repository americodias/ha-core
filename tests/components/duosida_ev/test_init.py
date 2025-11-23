"""Test Duosida EV integration setup and unload."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from homeassistant.components.duosida_ev import async_setup_entry
from homeassistant.core import HomeAssistant


async def test_platforms_are_loaded(
    hass: HomeAssistant,
    mock_config_entry: Any,
    mock_duosida_charger: Any,
) -> None:
    """Test that all platforms are loaded."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "homeassistant.components.duosida_ev.DuosidaDataUpdateCoordinator.async_load_stored_settings",
            return_value=None,
        ),
        patch(
            "homeassistant.components.duosida_ev.DuosidaDataUpdateCoordinator.async_config_entry_first_refresh",
            return_value=None,
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=None,
        ) as mock_forward,
    ):
        assert await async_setup_entry(hass, mock_config_entry)
        await hass.async_block_till_done()

        assert mock_forward.called
        loaded_platforms = mock_forward.call_args[0][1]
        assert "sensor" in loaded_platforms
        assert "switch" in loaded_platforms
        assert "number" in loaded_platforms
        assert "button" in loaded_platforms
