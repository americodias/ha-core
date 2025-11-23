"""Constants for the Duosida EV Charger integration."""

from typing import Final

DOMAIN: Final = "duosida_ev"
NAME: Final = "Duosida EV Charger"

# Configuration keys
CONF_DEVICE_ID: Final = "device_id"
CONF_SWITCH_DEBOUNCE: Final = "switch_debounce"

# Default values
DEFAULT_PORT: Final = 9988
DEFAULT_SCAN_INTERVAL: Final = 10
DEFAULT_SWITCH_DEBOUNCE: Final = 30

# Connection retry settings
MAX_RETRY_ATTEMPTS: Final = 3
INITIAL_RETRY_DELAY: Final = 1.0
RETRY_BACKOFF_MULTIPLIER: Final = 2.0
MAX_RETRY_DELAY: Final = 10.0

# Charger connection status codes
STATUS_CODES: Final[dict[int, str]] = {
    0: "Available",
    1: "Preparing",
    2: "Charging",
    3: "Cooling",
    4: "SuspendedEV",
    5: "Finished",
    6: "Holiday",
}
