"""Data update coordinator for Duosida EV Charger."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import timedelta
from functools import partial
import logging
from typing import TYPE_CHECKING, Any

from duosida_ev import DuosidaCharger

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    INITIAL_RETRY_DELAY,
    MAX_RETRY_ATTEMPTS,
    MAX_RETRY_DELAY,
    RETRY_BACKOFF_MULTIPLIER,
)

if TYPE_CHECKING:
    from . import DuosidaConfigEntry

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


class DuosidaDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Duosida data."""

    config_entry: DuosidaConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        charger: DuosidaCharger,
        device_id: str,
        switch_debounce: int = 30,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

        self.charger = charger
        self.switch_debounce = switch_debounce
        self._device_id = device_id

        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{device_id}",
        )

        self._stored_settings: dict[str, Any] = {
            "max_current": None,
            "led_brightness": None,
            "direct_mode": None,
            "stop_on_disconnect": None,
            "max_voltage": None,
            "min_voltage": None,
            "total_energy": 0.0,
            "last_power": 0.0,
            "last_update_time": None,
        }

        self._settings_synced_this_session = False
        self._unavailable_logged = False

    async def async_load_stored_settings(self) -> None:
        """Load stored settings from Home Assistant storage."""
        stored = await self._store.async_load()
        if stored:
            self._stored_settings.update(stored)

    async def _async_save_stored_settings(self) -> None:
        """Save current settings to Home Assistant storage."""
        await self._store.async_save(self._stored_settings)

    async def _async_sync_settings_to_charger(self) -> None:
        """Sync stored settings to the charger on first connection."""
        settings_to_sync: list[tuple[str, Any, Callable[[Any], bool]]] = [
            (
                "max_current",
                self._stored_settings.get("max_current"),
                self.charger.set_max_current,
            ),
            (
                "led_brightness",
                self._stored_settings.get("led_brightness"),
                self.charger.set_led_brightness,
            ),
            (
                "direct_mode",
                self._stored_settings.get("direct_mode"),
                self.charger.set_direct_work_mode,
            ),
            (
                "stop_on_disconnect",
                self._stored_settings.get("stop_on_disconnect"),
                self.charger.set_stop_on_disconnect,
            ),
            (
                "max_voltage",
                self._stored_settings.get("max_voltage"),
                self.charger.set_max_voltage,
            ),
            (
                "min_voltage",
                self._stored_settings.get("min_voltage"),
                self.charger.set_min_voltage,
            ),
        ]

        for name, value, setter in settings_to_sync:
            if value is not None:
                await self.hass.async_add_executor_job(setter, value)
                _LOGGER.debug("Synced %s: %s", name, value)

    def get_stored_setting(self, key: str) -> Any:
        """Get a stored setting value."""
        return self._stored_settings.get(key)

    async def _async_connect_with_retry(self) -> bool:
        """Connect to charger with exponential backoff retry logic."""
        retry_delay = INITIAL_RETRY_DELAY

        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            try:
                connected = await self.hass.async_add_executor_job(self.charger.connect)

                if connected:
                    return True

                if attempt < MAX_RETRY_ATTEMPTS:
                    _LOGGER.debug(
                        "Connection attempt %d/%d failed, retrying in %.1fs",
                        attempt,
                        MAX_RETRY_ATTEMPTS,
                        retry_delay,
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(
                        retry_delay * RETRY_BACKOFF_MULTIPLIER, MAX_RETRY_DELAY
                    )

            except Exception as err:  # noqa: BLE001
                if attempt < MAX_RETRY_ATTEMPTS:
                    _LOGGER.debug(
                        "Connection error on attempt %d/%d: %s",
                        attempt,
                        MAX_RETRY_ATTEMPTS,
                        err,
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(
                        retry_delay * RETRY_BACKOFF_MULTIPLIER, MAX_RETRY_DELAY
                    )
                else:
                    _LOGGER.warning(
                        "Connection failed after %d attempts", MAX_RETRY_ATTEMPTS
                    )

        return False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the charger."""
        connected = await self._async_connect_with_retry()

        if not connected:
            if not self._unavailable_logged:
                _LOGGER.info(
                    "Duosida charger %s is unavailable",
                    self.charger.host,
                )
                self._unavailable_logged = True
            raise UpdateFailed(
                f"Failed to connect to charger after {MAX_RETRY_ATTEMPTS} attempts"
            )

        # Log recovery if we were previously unavailable
        if self._unavailable_logged:
            _LOGGER.info(
                "Duosida charger %s is back online",
                self.charger.host,
            )
            self._unavailable_logged = False

        try:
            await asyncio.sleep(0.3)

            if not self._settings_synced_this_session:
                await self._async_sync_settings_to_charger()
                self._settings_synced_this_session = True

            status = await self.hass.async_add_executor_job(self.charger.get_status)

            if not status:
                raise UpdateFailed("Failed to get status from charger")

            data = status.to_dict()

            # Integrate power over time for total energy calculation
            current_power = data.get("power", 0.0) or 0.0
            current_time = self.hass.loop.time()

            last_power = self._stored_settings.get("last_power", 0.0) or 0.0
            last_time = self._stored_settings.get("last_update_time")
            total_energy = self._stored_settings.get("total_energy", 0.0) or 0.0

            if last_time is not None and current_time > last_time:
                time_delta_hours = (current_time - last_time) / 3600.0
                average_power = (current_power + last_power) / 2.0
                energy_delta = (average_power * time_delta_hours) / 1000.0

                if 0 < energy_delta < 100:
                    total_energy += energy_delta

            self._stored_settings["total_energy"] = total_energy
            self._stored_settings["last_power"] = current_power
            self._stored_settings["last_update_time"] = current_time

            self.hass.async_create_task(self._async_save_stored_settings())

            data["total_energy"] = total_energy
            return data

        finally:
            await self.hass.async_add_executor_job(self.charger.disconnect)

    async def _async_send_command(
        self, command_func: Callable[[], bool], command_name: str
    ) -> bool:
        """Send a command to the charger with connect/disconnect."""
        try:
            connected = await self._async_connect_with_retry()
            if not connected:
                return False

            try:
                await asyncio.sleep(0.3)
                return await self.hass.async_add_executor_job(command_func)
            finally:
                await self.hass.async_add_executor_job(self.charger.disconnect)

        except Exception:
            _LOGGER.exception("Error in %s", command_name)
            return False

    async def async_start_charging(self) -> bool:
        """Start charging the vehicle."""
        result = await self._async_send_command(
            self.charger.start_charging, "start charging"
        )

        if result:
            await asyncio.sleep(1.0)
            await self.async_request_refresh()

        return result

    async def async_stop_charging(self) -> bool:
        """Stop charging the vehicle."""
        result = await self._async_send_command(
            self.charger.stop_charging, "stop charging"
        )

        if result:
            await asyncio.sleep(1.0)
            await self.async_request_refresh()

        return result

    async def async_set_max_current(self, current: int) -> bool:
        """Set the maximum charging current."""
        result = await self._async_send_command(
            partial(self.charger.set_max_current, current),
            f"set max current to {current}A",
        )

        if result:
            self._stored_settings["max_current"] = current
            await self._async_save_stored_settings()
            await asyncio.sleep(0.5)
            await self.async_request_refresh()

        return result

    async def async_set_led_brightness(self, level: int) -> bool:
        """Set LED/screen brightness level."""
        result = await self._async_send_command(
            partial(self.charger.set_led_brightness, level),
            f"set LED brightness to {level}",
        )

        if result:
            self._stored_settings["led_brightness"] = level
            await self._async_save_stored_settings()

        return result

    async def async_set_direct_mode(self, enabled: bool) -> bool:
        """Set direct work mode (plug and charge)."""
        state = "enabled" if enabled else "disabled"
        result = await self._async_send_command(
            partial(self.charger.set_direct_work_mode, enabled),
            f"set direct mode to {state}",
        )

        if result:
            self._stored_settings["direct_mode"] = enabled
            await self._async_save_stored_settings()

        return result

    async def async_set_stop_on_disconnect(self, enabled: bool) -> bool:
        """Set whether to stop transaction when EV side disconnects."""
        state = "enabled" if enabled else "disabled"
        result = await self._async_send_command(
            partial(self.charger.set_stop_on_disconnect, enabled),
            f"set stop on disconnect to {state}",
        )

        if result:
            self._stored_settings["stop_on_disconnect"] = enabled
            await self._async_save_stored_settings()

        return result

    async def async_set_max_voltage(self, voltage: int) -> bool:
        """Set maximum working voltage."""
        result = await self._async_send_command(
            partial(self.charger.set_max_voltage, voltage),
            f"set max voltage to {voltage}V",
        )

        if result:
            self._stored_settings["max_voltage"] = voltage
            await self._async_save_stored_settings()

        return result

    async def async_set_min_voltage(self, voltage: int) -> bool:
        """Set minimum working voltage."""
        result = await self._async_send_command(
            partial(self.charger.set_min_voltage, voltage),
            f"set min voltage to {voltage}V",
        )

        if result:
            self._stored_settings["min_voltage"] = voltage
            await self._async_save_stored_settings()

        return result

    async def async_reset_total_energy(self) -> None:
        """Reset the total energy counter to zero."""
        self._stored_settings["total_energy"] = 0.0
        self._stored_settings["last_power"] = 0.0
        self._stored_settings["last_update_time"] = None
        await self._async_save_stored_settings()
        await self.async_request_refresh()

    def disconnect(self) -> None:
        """Disconnect from the charger."""
