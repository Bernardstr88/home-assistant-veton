"""Switch entities for the Veton EV Charger integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VetonDataUpdateCoordinator
from .entity import VetonChargingPointEntity
from .modbus import ChargingPointData


@dataclass(frozen=True, kw_only=True)
class VetonPointSwitchDescription(SwitchEntityDescription):
    """Charging point switch description."""

    value_fn: Callable[[ChargingPointData], bool | None]
    set_fn: Callable[[VetonDataUpdateCoordinator, int, bool], None]


def _set_charging_release(
    coordinator: VetonDataUpdateCoordinator,
    point: int,
    enabled: bool,
) -> None:
    coordinator.client.set_charging_release(point, enabled)


def _set_available(
    coordinator: VetonDataUpdateCoordinator,
    point: int,
    enabled: bool,
) -> None:
    coordinator.client.set_point_available(point, enabled)


POINT_SWITCHES: tuple[VetonPointSwitchDescription, ...] = (
    VetonPointSwitchDescription(
        key="charging_release",
        translation_key="charging_release",
        value_fn=lambda data: None
        if data.charging_release is None
        else data.charging_release == 1,
        set_fn=_set_charging_release,
    ),
    VetonPointSwitchDescription(
        key="available",
        translation_key="available",
        value_fn=lambda data: None if data.availability is None else data.availability == 1,
        set_fn=_set_available,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Veton switches."""
    coordinator: VetonDataUpdateCoordinator = entry.runtime_data
    async_add_entities(
        VetonPointSwitch(coordinator, point, description)
        for point in coordinator.data.points
        for description in POINT_SWITCHES
    )


class VetonPointSwitch(VetonChargingPointEntity, SwitchEntity):
    """Charging point switch."""

    entity_description: VetonPointSwitchDescription

    def __init__(
        self,
        coordinator: VetonDataUpdateCoordinator,
        point: int,
        description: VetonPointSwitchDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, point, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        data = self.coordinator.data.points.get(self.point)
        if data is None:
            return None
        return self.entity_description.value_fn(data)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        data = self.coordinator.data.points.get(self.point)
        return super().available and data is not None and data.release_mode == 5

    async def async_turn_on(self, **kwargs: object) -> None:
        """Turn the switch on."""
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Turn the switch off."""
        await self._async_set_state(False)

    async def _async_set_state(self, enabled: bool) -> None:
        """Set switch state."""
        await self.hass.async_add_executor_job(
            self.entity_description.set_fn,
            self.coordinator,
            self.point,
            enabled,
        )
        await self.coordinator.async_request_refresh()
