"""Config flow for Duosida EV Charger integration."""

from __future__ import annotations

import logging
from typing import Any

from duosida_ev import DuosidaCharger, discover_chargers
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import onboarding
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow

from .const import (
    CONF_DEVICE_ID,
    CONF_SWITCH_DEBOUNCE,
    DEFAULT_PORT,
    DEFAULT_SWITCH_DEBOUNCE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class DuosidaLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Duosida EV Charger."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: list[dict[str, Any]] = []
        self._discovered_ip: str | None = None
        self._discovered_device_id: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow handler for this integration."""
        return OptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            if user_input.get("discovery"):
                return await self.async_step_discovery()
            return await self.async_step_manual()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("discovery", default=True): bool}),
        )

    async def async_step_integration_discovery(
        self, discovery_info: dict[str, str]
    ) -> ConfigFlowResult:
        """Handle integration discovery (auto-discovered devices)."""
        self._discovered_ip = discovery_info["ip_address"]
        self._discovered_device_id = discovery_info.get("device_id", "")

        # Set unique ID and check if already configured
        if self._discovered_device_id:
            await self.async_set_unique_id(self._discovered_device_id)
            self._abort_if_unique_id_configured(
                updates={CONF_HOST: self._discovered_ip}
            )
        else:
            # Try to connect to get the device ID
            try:
                charger = await self.hass.async_add_executor_job(
                    lambda: DuosidaCharger(
                        host=self._discovered_ip,
                        port=DEFAULT_PORT,
                        device_id="discover",
                        debug=False,
                    )
                )
                connected = await self.hass.async_add_executor_job(charger.connect)
                if connected:
                    status = await self.hass.async_add_executor_job(charger.get_status)
                    if status:
                        self._discovered_device_id = charger.device_id
                    await self.hass.async_add_executor_job(charger.disconnect)
            except Exception:  # noqa: BLE001
                _LOGGER.debug(
                    "Failed to connect to discovered charger at %s",
                    self._discovered_ip,
                )
                raise AbortFlow("cannot_connect") from None

            if self._discovered_device_id:
                await self.async_set_unique_id(self._discovered_device_id)
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: self._discovered_ip}
                )

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovered device."""
        if user_input is not None or not onboarding.async_is_onboarded(self.hass):
            return self.async_create_entry(
                title=f"Duosida {self._discovered_ip}",
                data={
                    CONF_HOST: self._discovered_ip,
                    CONF_PORT: DEFAULT_PORT,
                    CONF_DEVICE_ID: self._discovered_device_id,
                },
            )

        self._set_confirm_only()
        placeholders = {
            "host": self._discovered_ip,
            "device_id": self._discovered_device_id or "Unknown",
        }
        self.context["title_placeholders"] = placeholders
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders=placeholders,
        )

    async def async_step_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the discovery step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected = user_input["device"]

            for device in self._discovered_devices:
                if device["ip"] == selected:
                    await self.async_set_unique_id(device["device_id"])
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Duosida {device['ip']}",
                        data={
                            CONF_HOST: device["ip"],
                            CONF_PORT: DEFAULT_PORT,
                            CONF_DEVICE_ID: device["device_id"],
                        },
                    )

        self._discovered_devices = await self.hass.async_add_executor_job(
            discover_chargers, 5
        )

        if not self._discovered_devices:
            return self.async_show_form(
                step_id="discovery",
                errors={"base": "no_devices_found"},
            )

        devices = {
            device["ip"]: f"{device['ip']} ({device.get('device_id', 'Unknown')})"
            for device in self._discovered_devices
        }

        return self.async_show_form(
            step_id="discovery",
            data_schema=vol.Schema({vol.Required("device"): vol.In(devices)}),
            errors=errors,
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            device_id = user_input.get(CONF_DEVICE_ID)

            try:
                charger = await self.hass.async_add_executor_job(
                    lambda: DuosidaCharger(
                        host=host,
                        port=port,
                        device_id=device_id or "test",
                        debug=False,
                    )
                )

                connected = await self.hass.async_add_executor_job(charger.connect)

                if not connected:
                    errors["base"] = "cannot_connect"
                else:
                    if not device_id:
                        status = await self.hass.async_add_executor_job(
                            charger.get_status
                        )
                        if status:
                            device_id = charger.device_id
                        else:
                            errors["base"] = "cannot_connect"

                    await self.hass.async_add_executor_job(charger.disconnect)

                    if not errors:
                        await self.async_set_unique_id(device_id)
                        self._abort_if_unique_id_configured()

                        return self.async_create_entry(
                            title=f"Duosida {host}",
                            data={
                                CONF_HOST: host,
                                CONF_PORT: port,
                                CONF_DEVICE_ID: device_id,
                            },
                        )

            except AbortFlow:
                raise
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Optional(CONF_DEVICE_ID): str,
                }
            ),
            errors=errors,
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Duosida EV Charger."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_switch_debounce = self.config_entry.options.get(
            CONF_SWITCH_DEBOUNCE,
            self.config_entry.data.get(CONF_SWITCH_DEBOUNCE, DEFAULT_SWITCH_DEBOUNCE),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SWITCH_DEBOUNCE,
                        default=current_switch_debounce,
                    ): vol.All(int, vol.Range(min=5, max=120)),
                }
            ),
        )
