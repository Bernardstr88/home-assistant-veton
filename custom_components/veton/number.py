"""Number entities for the Veton EV Charger integration."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MAX_CHARGING_CURRENT, MIN_CHARGING_CURRENT
from .coordinator import VetonDataUpdateCoordinator
from .entity import VetonChargingPointEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Veton numbers."""
    coordinator: VetonDataUpdateCoordinator = entry.runtime_data
    async_add_entities(
        VetonMaxCurrentNumber(coordinator, point) for point in coordinator.data.points
    )


class VetonMaxCurrentNumber(VetonChargingPointEntity, NumberEntity):
    """Maximum charging current control."""

    _attr_translation_key = "max_current"
    _attr_native_min_value = MIN_CHARGING_CURRENT
    _attr_native_max_value = MAX_CHARGING_CURRENT
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: VetonDataUpdateCoordinator, point: int) -> None:
        """Initialize the number."""
        super().__init__(coordinator, point, "max_current")

    @property
    def native_value(self) -> int | None:
        """Return the current value."""
        data = self.coordinator.data.points.get(self.point)
        return None if data is None else data.max_current_a

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        data = self.coordinator.data.points.get(self.point)
        return super().available and data is not None and data.release_mode == 5

    async def async_set_native_value(self, value: float) -> None:
        """Set maximum charging current."""
        current = round(value)
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_max_current,
            self.point,
            current,
        )
        await self.coordinator.async_request_refresh()
