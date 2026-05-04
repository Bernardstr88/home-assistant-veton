"""Data coordinator for the Veton EV Charger integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DOMAIN,
)
from .modbus import VetonConnectionError, VetonData, VetonModbusClient, VetonModbusError

_LOGGER = logging.getLogger(__name__)


class VetonDataUpdateCoordinator(DataUpdateCoordinator[VetonData]):
    """Class to manage fetching Veton data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.client = VetonModbusClient(
            host=entry.data[CONF_HOST],
            port=entry.data.get(CONF_PORT, 502),
            slave_id=entry.data.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID),
        )
        scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> VetonData:
        """Fetch data from the charger."""
        try:
            return await self.hass.async_add_executor_job(self.client.read_all)
        except (VetonConnectionError, VetonModbusError) as err:
            raise UpdateFailed(str(err)) from err

    def close(self) -> None:
        """Close the underlying client."""
        self.client.close()
