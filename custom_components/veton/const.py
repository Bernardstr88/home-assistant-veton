"""Constants for the Veton EV Charger integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "veton"

DEFAULT_NAME = "Veton EV Charger"
DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 1
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_TIMEOUT = 5

MIN_SCAN_INTERVAL = 5
MAX_CHARGING_CURRENT = 80
MIN_CHARGING_CURRENT = 6
MAX_CHARGING_POINTS = 48

CONF_SLAVE_ID = "slave_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

ATTR_CHARGING_POINT = "charging_point"

MANUFACTURER = "Phoenix Contact / Veton"
