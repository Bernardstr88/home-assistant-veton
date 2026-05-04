# Veton EV Charger

Home Assistant custom integration for Veton / Phoenix Contact CHARX SEC based
Modbus TCP EV chargers.

The integration models one Modbus server as a station device and exposes each
configured charging point as a separate Home Assistant device.

## Modbus model

The CHARX/Veton register map has two address areas:

- `0-999`: station-wide registers for the complete charging installation
- `x000-x999`: charging point registers, where `x` is the assigned charging point number

Examples:

| Meaning | Point 1 | Point 2 |
| --- | ---: | ---: |
| Active power `x244` | `1244` | `2244` |
| Charging release `x300` | `1300` | `2300` |
| Maximum current `x301` | `1301` | `2301` |

## Features

- Local polling over Modbus TCP
- UI setup flow
- Station-wide sensors for point counts, total power and total current
- Per charging point sensors for voltage, current, power, energy, status and errors
- Per charging point controls for charging release and maximum charging current

## Requirements

In the CHARX web-based management:

- The Modbus server must be running
- TCP port `502` must be open
- For write control, the charge point release mode must be set to `Modbus`

## Installation with HACS

Until this repository is available as a default HACS repository:

1. Open HACS
2. Add this repository as a custom repository
3. Select category `Integration`
4. Install `Veton EV Charger`
5. Restart Home Assistant
6. Add the integration from Settings > Devices & services

## Configuration

The setup flow asks for:

- Host
- Port, default `502`
- Slave ID, default `1`
- Scan interval, default `10` seconds

## Notes

Controls are only available when the charging point reports release mode `5`
(`Modbus`). Maximum current is constrained to `6-80 A`.

This is an early integration. Validate register behavior on your charger before
using it for unattended control.
