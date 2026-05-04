"""Binary sensors for the Veton EV Charger integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VetonDataUpdateCoordinator
from .entity import VetonChargingPointEntity
from .modbus import ChargingPointData

OCCUPIED_STATUSES = {"B1", "B2", "C1", "C2", "D1", "D2"}
CHARGING_STATUSES = {"C1", "C2", "D1", "D2"}


@dataclass(frozen=True, kw_only=True)
class VetonPointBinarySensorDescription(BinarySensorEntityDescription):
    """Charging point binary sensor description."""

    value_fn: Callable[[ChargingPointData], bool | None]


POINT_BINARY_SENSORS: tuple[VetonPointBinarySensorDescription, ...] = (
    VetonPointBinarySensorDescription(
        key="vehicle_connected",
        translation_key="vehicle_connected",
        device_class=BinarySensorDeviceClass.PLUG,
        value_fn=lambda data: data.vehicle_status in OCCUPIED_STATUSES,
    ),
    VetonPointBinarySensorDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.POWER,
        value_fn=lambda data: data.vehicle_status in CHARGING_STATUSES,
    ),
    VetonPointBinarySensorDescription(
        key="error",
        translation_key="error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.error_code not in (None, 0),
    ),
    VetonPointBinarySensorDescription(
        key="modbus_release_mode",
        translation_key="modbus_release_mode",
        value_fn=lambda data: data.release_mode == 5,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Veton binary sensors."""
    coordinator: VetonDataUpdateCoordinator = entry.runtime_data
    async_add_entities(
        VetonPointBinarySensor(coordinator, point, description)
        for point in coordinator.data.points
        for description in POINT_BINARY_SENSORS
    )


class VetonPointBinarySensor(VetonChargingPointEntity, BinarySensorEntity):
    """Charging point binary sensor."""

    entity_description: VetonPointBinarySensorDescription

    def __init__(
        self,
        coordinator: VetonDataUpdateCoordinator,
        point: int,
        description: VetonPointBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, point, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        data = self.coordinator.data.points.get(self.point)
        if data is None:
            return None
        return self.entity_description.value_fn(data)
