"""Modbus access for Veton / CHARX based EV chargers."""

from __future__ import annotations

from dataclasses import dataclass
import socket
import struct
from typing import Any

from .const import DEFAULT_TIMEOUT, MAX_CHARGING_POINTS


class VetonConnectionError(Exception):
    """Raised when the charger cannot be reached."""


class VetonModbusError(Exception):
    """Raised when a Modbus request fails."""


def point_address(point: int, offset: int) -> int:
    """Return a charging point register address.

    CHARX/Veton uses 0-999 for station-wide data and x000-x999 for charging
    point data, where x is the assigned charging point number.
    """
    return point * 1000 + offset


def decode_u32(words: list[int]) -> int:
    """Decode unsigned 32-bit integer, MSW first."""
    return (words[0] << 16) | words[1]


def decode_s32(words: list[int]) -> int:
    """Decode signed 32-bit integer, MSW first."""
    raw = decode_u32(words)
    return raw - 0x100000000 if raw & 0x80000000 else raw


def decode_u64(words: list[int]) -> int:
    """Decode unsigned 64-bit integer, MSW first."""
    value = 0
    for word in words:
        value = (value << 16) | word
    return value


def decode_s64(words: list[int]) -> int:
    """Decode signed 64-bit integer, MSW first."""
    raw = decode_u64(words)
    return raw - 0x10000000000000000 if raw & 0x8000000000000000 else raw


def decode_ascii(words: list[int]) -> str:
    """Decode register words as ASCII."""
    data = bytearray()
    for word in words:
        data.append((word >> 8) & 0xFF)
        data.append(word & 0xFF)
    return data.decode("ascii", errors="ignore").rstrip("\x00 ").strip()


@dataclass(slots=True)
class StationData:
    """Station-wide Modbus data."""

    device_designation: str
    software_version: str
    charging_point_count: int
    controllers_non_critical_error: int | None
    controllers_error: int | None
    unoccupied_points: int | None
    occupied_points: int | None
    active_charging_points: int | None
    total_power_mw: int | None
    total_current_l1_ma: int | None
    total_current_l2_ma: int | None
    total_current_l3_ma: int | None
    availability: int | None
    dynamic_max_current_a: int | None


@dataclass(slots=True)
class ChargingPointData:
    """Per charging point Modbus data."""

    point: int
    uid: str
    associated_uid: str
    backplane_position: int | None
    release_mode: int | None
    voltage_l1_mv: int | None
    voltage_l2_mv: int | None
    voltage_l3_mv: int | None
    current_l1_ma: int | None
    current_l2_ma: int | None
    current_l3_ma: int | None
    active_power_mw: int | None
    reactive_power_mvar: int | None
    apparent_power_mva: int | None
    active_energy_wh: int | None
    session_energy_wh: int | None
    error_code: int | None
    digital_inputs: int | None
    pwm_duty_cycle: int | None
    offered_current_a: int | None
    cable_current_capacity_a: int | None
    vehicle_status: str
    connection_time_s: int | None
    charging_duration_s: int | None
    charging_release: int | None
    max_current_a: int | None
    availability: int | None
    watchdog_fallback_current_a: int | None
    watchdog_timer_s: int | None


@dataclass(slots=True)
class VetonData:
    """Complete charger data."""

    station: StationData
    points: dict[int, ChargingPointData]


class VetonModbusClient:
    """Small synchronous Modbus TCP client for CHARX/Veton chargers."""

    def __init__(
        self,
        host: str,
        port: int,
        slave_id: int,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.timeout = timeout
        self._socket: socket.socket | None = None
        self._transaction_id = 0

    def close(self) -> None:
        """Close the Modbus connection."""
        if self._socket is not None:
            try:
                self._socket.close()
            finally:
                self._socket = None

    def _ensure_socket(self) -> socket.socket:
        """Return a connected socket."""
        if self._socket is None:
            try:
                self._socket = socket.create_connection(
                    (self.host, self.port),
                    timeout=self.timeout,
                )
                self._socket.settimeout(self.timeout)
            except OSError as err:
                raise VetonConnectionError(
                    f"Could not connect to {self.host}:{self.port}"
                ) from err
        return self._socket

    def read_registers(self, address: int, count: int = 1) -> list[int]:
        """Read holding registers."""
        payload = self._request(0x03, struct.pack(">HH", address, count))
        if len(payload) < 1 or payload[0] != count * 2:
            raise VetonModbusError(f"Invalid read response for address {address}")
        data = payload[1:]
        return [
            struct.unpack(">H", data[index : index + 2])[0]
            for index in range(0, len(data), 2)
        ]

    def write_register(self, address: int, value: int) -> None:
        """Write one holding register."""
        payload = self._request(0x06, struct.pack(">HH", address, value))
        if payload != struct.pack(">HH", address, value):
            raise VetonModbusError(f"Invalid write response for address {address}")

    def _request(self, function_code: int, payload: bytes) -> bytes:
        """Send one Modbus/TCP request and return the response payload."""
        self._transaction_id = (self._transaction_id + 1) % 0x10000
        pdu = bytes([function_code]) + payload
        header = struct.pack(
            ">HHHB",
            self._transaction_id,
            0,
            len(pdu) + 1,
            self.slave_id,
        )
        sock = self._ensure_socket()
        try:
            sock.sendall(header + pdu)
            response_header = self._recv_exact(7)
            transaction_id, protocol_id, length, unit_id = struct.unpack(
                ">HHHB",
                response_header,
            )
            if transaction_id != self._transaction_id or protocol_id != 0:
                raise VetonModbusError("Invalid Modbus/TCP response header")
            response_pdu = self._recv_exact(length - 1)
        except OSError as err:
            self.close()
            raise VetonConnectionError(str(err)) from err

        if unit_id != self.slave_id:
            raise VetonModbusError("Invalid Modbus unit id in response")
        if not response_pdu:
            raise VetonModbusError("Empty Modbus response")
        response_function = response_pdu[0]
        if response_function == function_code + 0x80:
            code = response_pdu[1] if len(response_pdu) > 1 else 0
            raise VetonModbusError(f"Modbus exception {code}")
        if response_function != function_code:
            raise VetonModbusError("Unexpected Modbus function code in response")
        return response_pdu[1:]

    def _recv_exact(self, size: int) -> bytes:
        """Receive exactly size bytes from the socket."""
        sock = self._ensure_socket()
        chunks = bytearray()
        while len(chunks) < size:
            chunk = sock.recv(size - len(chunks))
            if not chunk:
                self.close()
                raise VetonConnectionError("Connection closed by remote host")
            chunks.extend(chunk)
        return bytes(chunks)

    def read_station(self) -> StationData:
        """Read station-wide registers."""
        point_count = self.read_registers(114, 1)[0]
        point_count = min(max(point_count, 0), MAX_CHARGING_POINTS)

        return StationData(
            device_designation=decode_ascii(self.read_registers(100, 10)),
            software_version=decode_ascii(self.read_registers(110, 4)),
            charging_point_count=point_count,
            controllers_non_critical_error=self._read_u16_or_none(147),
            controllers_error=self._read_u16_or_none(148),
            unoccupied_points=self._read_u16_or_none(149),
            occupied_points=self._read_u16_or_none(150),
            active_charging_points=self._read_u16_or_none(151),
            total_power_mw=self._read_u32_or_none(152),
            total_current_l1_ma=self._read_s32_or_none(158),
            total_current_l2_ma=self._read_s32_or_none(160),
            total_current_l3_ma=self._read_s32_or_none(162),
            availability=self._read_u16_or_none(164),
            dynamic_max_current_a=self._read_u16_or_none(167),
        )

    def read_point(self, point: int) -> ChargingPointData:
        """Read registers for one charging point."""
        return ChargingPointData(
            point=point,
            uid=decode_ascii(self.read_registers(point_address(point, 113), 3)),
            associated_uid=decode_ascii(self.read_registers(point_address(point, 116), 3)),
            backplane_position=self._read_point_u16_or_none(point, 119),
            release_mode=self._read_point_u16_or_none(point, 120),
            voltage_l1_mv=self._read_point_u32_or_none(point, 232),
            voltage_l2_mv=self._read_point_u32_or_none(point, 234),
            voltage_l3_mv=self._read_point_u32_or_none(point, 236),
            current_l1_ma=self._read_point_u32_or_none(point, 238),
            current_l2_ma=self._read_point_u32_or_none(point, 240),
            current_l3_ma=self._read_point_u32_or_none(point, 242),
            active_power_mw=self._read_point_u32_or_none(point, 244),
            reactive_power_mvar=self._read_point_s32_or_none(point, 246),
            apparent_power_mva=self._read_point_u32_or_none(point, 248),
            active_energy_wh=self._read_point_u64_or_none(point, 250),
            session_energy_wh=self._read_point_u64_or_none(point, 289),
            error_code=self._read_point_u32_or_none(point, 293),
            digital_inputs=self._read_point_u16_or_none(point, 295),
            pwm_duty_cycle=self._read_point_u16_or_none(point, 296),
            offered_current_a=self._read_point_u16_or_none(point, 297),
            cable_current_capacity_a=self._read_point_u16_or_none(point, 298),
            vehicle_status=decode_ascii(self.read_registers(point_address(point, 299), 1)),
            connection_time_s=self._read_point_u32_or_none(point, 285),
            charging_duration_s=self._read_point_u32_or_none(point, 287),
            charging_release=self._read_point_u16_or_none(point, 300),
            max_current_a=self._read_point_u16_or_none(point, 301),
            availability=self._read_point_u16_or_none(point, 304),
            watchdog_fallback_current_a=self._read_point_u16_or_none(point, 306),
            watchdog_timer_s=self._read_point_u16_or_none(point, 307),
        )

    def read_all(self) -> VetonData:
        """Read station data and all configured charging points."""
        station = self.read_station()
        points: dict[int, ChargingPointData] = {}
        for point in range(1, station.charging_point_count + 1):
            try:
                points[point] = self.read_point(point)
            except VetonModbusError:
                continue
        return VetonData(station=station, points=points)

    def set_charging_release(self, point: int, enabled: bool) -> None:
        """Enable or disable charging release for one point."""
        self.write_register(point_address(point, 300), 1 if enabled else 0)

    def set_point_available(self, point: int, available: bool) -> None:
        """Set charging point availability."""
        self.write_register(point_address(point, 304), 1 if available else 0)

    def set_max_current(self, point: int, current: int) -> None:
        """Set maximum charging current for one point."""
        self.write_register(point_address(point, 301), current)

    def _read_u16_or_none(self, address: int) -> int | None:
        return self._read_or_none(address, 1, lambda words: words[0])

    def _read_u32_or_none(self, address: int) -> int | None:
        return self._read_or_none(address, 2, decode_u32)

    def _read_s32_or_none(self, address: int) -> int | None:
        return self._read_or_none(address, 2, decode_s32)

    def _read_point_u16_or_none(self, point: int, offset: int) -> int | None:
        return self._read_u16_or_none(point_address(point, offset))

    def _read_point_u32_or_none(self, point: int, offset: int) -> int | None:
        return self._read_u32_or_none(point_address(point, offset))

    def _read_point_s32_or_none(self, point: int, offset: int) -> int | None:
        return self._read_s32_or_none(point_address(point, offset))

    def _read_point_u64_or_none(self, point: int, offset: int) -> int | None:
        return self._read_or_none(point_address(point, offset), 4, decode_u64)

    def _read_or_none(
        self,
        address: int,
        count: int,
        decoder: Any,
    ) -> int | None:
        try:
            return decoder(self.read_registers(address, count))
        except VetonModbusError:
            return None
