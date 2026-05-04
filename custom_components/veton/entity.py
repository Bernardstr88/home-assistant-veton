"""Base entities for the Veton EV Charger integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_CHARGING_POINT, DOMAIN, MANUFACTURER
from .coordinator import VetonDataUpdateCoordinator


class VetonEntity(CoordinatorEntity[VetonDataUpdateCoordinator]):
    """Base station entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: VetonDataUpdateCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return station device info."""
        station = self.coordinator.data.station
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.entry_id)},
            manufacturer=MANUFACTURER,
            name=station.device_designation or "Veton EV Charger",
            sw_version=station.software_version or None,
        )


class VetonChargingPointEntity(CoordinatorEntity[VetonDataUpdateCoordinator]):
    """Base charging point entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VetonDataUpdateCoordinator,
        point: int,
        key: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.point = point
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_point_{point}_{key}"
        self._attr_extra_state_attributes = {ATTR_CHARGING_POINT: point}

    @property
    def device_info(self) -> DeviceInfo:
        """Return charging point device info."""
        point_data = self.coordinator.data.points.get(self.point)
        identifier = (
            point_data.uid
            if point_data is not None and point_data.uid
            else f"{self.coordinator.config_entry.entry_id}_{self.point}"
        )
        return DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            manufacturer=MANUFACTURER,
            name=f"Veton charging point {self.point}",
            via_device=(DOMAIN, self.coordinator.config_entry.entry_id),
        )
