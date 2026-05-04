"""Sensors for the Veton EV Charger integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VetonDataUpdateCoordinator
from .entity import VetonChargingPointEntity, VetonEntity
from .modbus import ChargingPointData, StationData


def mw_to_kw(value: int | None) -> float | None:
    """Convert mW to kW."""
    return None if value is None else round(value / 1_000_000, 3)


def ma_to_a(value: int | None) -> float | None:
    """Convert mA to A."""
    if value is None or value == -1:
        return None
    return round(value / 1000, 3)


def mv_to_v(value: int | None) -> float | None:
    """Convert mV to V."""
    return None if value is None else round(value / 1000, 1)


@dataclass(frozen=True, kw_only=True)
class VetonStationSensorDescription(SensorEntityDescription):
    """Station sensor description."""

    value_fn: Callable[[StationData], int | float | str | None]


@dataclass(frozen=True, kw_only=True)
class VetonPointSensorDescription(SensorEntityDescription):
    """Charging point sensor description."""

    value_fn: Callable[[ChargingPointData], int | float | str | None]


STATION_SENSORS: tuple[VetonStationSensorDescription, ...] = (
    VetonStationSensorDescription(
        key="charging_point_count",
        translation_key="charging_point_count",
        value_fn=lambda data: data.charging_point_count,
    ),
    VetonStationSensorDescription(
        key="unoccupied_points",
        translation_key="unoccupied_points",
        value_fn=lambda data: data.unoccupied_points,
    ),
    VetonStationSensorDescription(
        key="occupied_points",
        translation_key="occupied_points",
        value_fn=lambda data: data.occupied_points,
    ),
    VetonStationSensorDescription(
        key="active_charging_points",
        translation_key="active_charging_points",
        value_fn=lambda data: data.active_charging_points,
    ),
    VetonStationSensorDescription(
        key="total_power",
        translation_key="total_power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: mw_to_kw(data.total_power_mw),
    ),
    VetonStationSensorDescription(
        key="total_current_l1",
        translation_key="total_current_l1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: ma_to_a(data.total_current_l1_ma),
    ),
    VetonStationSensorDescription(
        key="total_current_l2",
        translation_key="total_current_l2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: ma_to_a(data.total_current_l2_ma),
    ),
    VetonStationSensorDescription(
        key="total_current_l3",
        translation_key="total_current_l3",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: ma_to_a(data.total_current_l3_ma),
    ),
    VetonStationSensorDescription(
        key="dynamic_max_current",
        translation_key="dynamic_max_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        value_fn=lambda data: data.dynamic_max_current_a,
    ),
)

POINT_SENSORS: tuple[VetonPointSensorDescription, ...] = (
    VetonPointSensorDescription(
        key="release_mode",
        translation_key="release_mode",
        value_fn=lambda data: data.release_mode,
    ),
    VetonPointSensorDescription(
        key="vehicle_status",
        translation_key="vehicle_status",
        value_fn=lambda data: data.vehicle_status,
    ),
    VetonPointSensorDescription(
        key="voltage_l1",
        translation_key="voltage_l1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: mv_to_v(data.voltage_l1_mv),
    ),
    VetonPointSensorDescription(
        key="voltage_l2",
        translation_key="voltage_l2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: mv_to_v(data.voltage_l2_mv),
    ),
    VetonPointSensorDescription(
        key="voltage_l3",
        translation_key="voltage_l3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: mv_to_v(data.voltage_l3_mv),
    ),
    VetonPointSensorDescription(
        key="current_l1",
        translation_key="current_l1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: ma_to_a(data.current_l1_ma),
    ),
    VetonPointSensorDescription(
        key="current_l2",
        translation_key="current_l2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: ma_to_a(data.current_l2_ma),
    ),
    VetonPointSensorDescription(
        key="current_l3",
        translation_key="current_l3",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: ma_to_a(data.current_l3_ma),
    ),
    VetonPointSensorDescription(
        key="active_power",
        translation_key="active_power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: mw_to_kw(data.active_power_mw),
    ),
    VetonPointSensorDescription(
        key="active_energy",
        translation_key="active_energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.active_energy_wh,
    ),
    VetonPointSensorDescription(
        key="session_energy",
        translation_key="session_energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.session_energy_wh,
    ),
    VetonPointSensorDescription(
        key="connection_time",
        translation_key="connection_time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda data: data.connection_time_s,
        entity_registry_enabled_default=False,
    ),
    VetonPointSensorDescription(
        key="charging_duration",
        translation_key="charging_duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda data: data.charging_duration_s,
        entity_registry_enabled_default=False,
    ),
    VetonPointSensorDescription(
        key="error_code",
        translation_key="error_code",
        value_fn=lambda data: f"0x{data.error_code:08X}" if data.error_code is not None else None,
    ),
    VetonPointSensorDescription(
        key="offered_current",
        translation_key="offered_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        value_fn=lambda data: data.offered_current_a,
    ),
    VetonPointSensorDescription(
        key="cable_current_capacity",
        translation_key="cable_current_capacity",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        value_fn=lambda data: data.cable_current_capacity_a,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Veton sensors."""
    coordinator: VetonDataUpdateCoordinator = entry.runtime_data

    entities: list[SensorEntity] = [
        VetonStationSensor(coordinator, description) for description in STATION_SENSORS
    ]
    for point in coordinator.data.points:
        entities.extend(
            VetonPointSensor(coordinator, point, description)
            for description in POINT_SENSORS
        )

    async_add_entities(entities)


class VetonStationSensor(VetonEntity, SensorEntity):
    """Station sensor."""

    entity_description: VetonStationSensorDescription

    def __init__(
        self,
        coordinator: VetonDataUpdateCoordinator,
        description: VetonStationSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> int | float | str | None:
        """Return the sensor state."""
        return self.entity_description.value_fn(self.coordinator.data.station)


class VetonPointSensor(VetonChargingPointEntity, SensorEntity):
    """Charging point sensor."""

    entity_description: VetonPointSensorDescription

    def __init__(
        self,
        coordinator: VetonDataUpdateCoordinator,
        point: int,
        description: VetonPointSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, point, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> int | float | str | None:
        """Return the sensor state."""
        data = self.coordinator.data.points.get(self.point)
        if data is None:
            return None
        return self.entity_description.value_fn(data)
