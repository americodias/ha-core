"""Test Duosida EV config flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.components.duosida_ev.const import (
    CONF_DEVICE_ID,
    CONF_SWITCH_DEBOUNCE,
    DEFAULT_PORT,
    DEFAULT_SWITCH_DEBOUNCE,
    DOMAIN,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


async def test_user_step_no_discovery(
    hass: HomeAssistant,
    mock_duosida_charger: Any,
) -> None:
    """Test user step without choosing discovery."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"discovery": False},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"


async def test_manual_step_success(
    hass: HomeAssistant,
    mock_duosida_charger: Any,
) -> None:
    """Test manual configuration step completes successfully."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"discovery": False},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"

    with patch(
        "homeassistant.components.duosida_ev.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 9988,
                CONF_DEVICE_ID: "03123456789012345678",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Duosida 192.168.1.100"
    assert result["data"] == {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 9988,
        CONF_DEVICE_ID: "03123456789012345678",
    }


async def test_manual_step_connection_error(
    hass: HomeAssistant,
) -> None:
    """Test manual configuration with connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"discovery": False},
    )

    with patch(
        "homeassistant.components.duosida_ev.config_flow.DuosidaCharger"
    ) as mock_charger_class:
        mock_charger = mock_charger_class.return_value
        mock_charger.connect.return_value = False

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 9988,
                CONF_DEVICE_ID: "03123456789012345678",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_discovery_step_chargers_found(
    hass: HomeAssistant,
    mock_discover_chargers: Any,
    mock_duosida_charger: Any,
) -> None:
    """Test discovery step when chargers are found."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"discovery": True},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery"
    assert "device" in result["data_schema"].schema

    with patch(
        "homeassistant.components.duosida_ev.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "device": "192.168.1.100",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Duosida 192.168.1.100"
    assert result["data"][CONF_HOST] == "192.168.1.100"
    assert result["data"][CONF_DEVICE_ID] == "03123456789012345678"


async def test_discovery_step_no_chargers_found(
    hass: HomeAssistant,
    mock_duosida_charger: Any,
) -> None:
    """Test discovery step when no chargers are found."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.duosida_ev.config_flow.discover_chargers",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"discovery": True},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_devices_found"}


async def test_already_configured(
    hass: HomeAssistant,
    mock_config_entry: Any,
    mock_duosida_charger: Any,
) -> None:
    """Test we abort if the device is already configured."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"discovery": False},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 9988,
            CONF_DEVICE_ID: "03123456789012345678",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_manual_defaults(
    hass: HomeAssistant,
    mock_duosida_charger: Any,
) -> None:
    """Test manual configuration uses defaults."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"discovery": False},
    )

    with patch(
        "homeassistant.components.duosida_ev.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_DEVICE_ID: "03123456789012345678",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PORT] == DEFAULT_PORT


async def test_options_flow(
    hass: HomeAssistant,
    mock_config_entry: Any,
) -> None:
    """Test options flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SWITCH_DEBOUNCE: DEFAULT_SWITCH_DEBOUNCE,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_SWITCH_DEBOUNCE: DEFAULT_SWITCH_DEBOUNCE,
    }


async def test_options_flow_custom_value(
    hass: HomeAssistant,
    mock_config_entry: Any,
) -> None:
    """Test options flow with existing custom value."""
    mock_config_entry.add_to_hass(hass)

    hass.config_entries.async_update_entry(
        mock_config_entry, options={CONF_SWITCH_DEBOUNCE: 45}
    )

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SWITCH_DEBOUNCE: 60},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_SWITCH_DEBOUNCE: 60}


async def test_integration_discovery_new_device(
    hass: HomeAssistant,
    mock_duosida_charger: Any,
) -> None:
    """Test integration discovery with a new device shows correct flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data={
            "ip_address": "192.168.1.100",
            "device_id": "03123456789012345678",
        },
    )

    # Verify discovery flow shows confirmation form
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    assert result["description_placeholders"]["host"] == "192.168.1.100"
    assert result["description_placeholders"]["device_id"] == "03123456789012345678"


async def test_integration_discovery_already_configured(
    hass: HomeAssistant,
    mock_config_entry: Any,
    mock_duosida_charger: Any,
) -> None:
    """Test integration discovery aborts when device is already configured."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data={
            "ip_address": "192.168.1.100",
            "device_id": "03123456789012345678",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_integration_discovery_updates_host(
    hass: HomeAssistant,
    mock_config_entry: Any,
    mock_duosida_charger: Any,
) -> None:
    """Test integration discovery updates host when device moves to new IP."""
    mock_config_entry.add_to_hass(hass)

    # Simulate device moving to a new IP address
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data={
            "ip_address": "192.168.1.200",  # New IP
            "device_id": "03123456789012345678",  # Same device ID
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"

    # Verify host was updated
    assert mock_config_entry.data[CONF_HOST] == "192.168.1.200"


async def test_integration_discovery_without_device_id(
    hass: HomeAssistant,
    mock_duosida_charger: Any,
) -> None:
    """Test integration discovery when device_id is not in discovery info.

    When device_id is empty, the flow connects to get the device ID.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data={
            "ip_address": "192.168.1.100",
            "device_id": "",  # Empty device ID
        },
    )

    # Should still show confirmation form after connecting to get device ID
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    assert result["description_placeholders"]["host"] == "192.168.1.100"


async def test_integration_discovery_connection_error(
    hass: HomeAssistant,
) -> None:
    """Test integration discovery aborts on connection exception."""
    with patch(
        "homeassistant.components.duosida_ev.config_flow.DuosidaCharger"
    ) as mock_charger_class:
        # Raise an exception during charger creation to trigger abort
        mock_charger_class.side_effect = ConnectionError("Connection failed")

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                "ip_address": "192.168.1.100",
                "device_id": "",  # Empty device ID forces connection attempt
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"
