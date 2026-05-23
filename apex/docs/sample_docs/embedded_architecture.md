---
author: Embedded Systems Department
date: 2024-06-10
---

# Embedded systems architecture

## Overview

The Forze IX embedded system consists of five Electronic Control Units (ECUs) connected over a dual CAN bus network. The main ECU coordinates all subsystems. Redundant CAN buses (CAN-A and CAN-B) ensure that a single bus failure does not take down the car.

All firmware is written in C using the STM32 HAL library and FreeRTOS. The toolchain is STM32CubeIDE with GCC ARM. Version control is on GitHub — never commit directly to main, always use feature branches with pull request review.

## ECU overview

| ECU | MCU | Role |
|-----|-----|------|
| Main ECU | STM32H7 | Vehicle coordinator, CAN gateway, driver interface |
| FC Controller | STM32F4 | Fuel cell stack management, thermal control |
| BMS | STM32F4 | Battery cell monitoring, protection, SOC |
| Traction | STM32F7 | Motor controller interface, EMS, regen |
| Dashboard | STM32F1 | Driver display, steering wheel inputs |

## CAN bus topology

CAN-A (500 kbit/s) — high priority: safety messages, fault flags, power limits
CAN-B (250 kbit/s) — low priority: telemetry, dashboard, logging

All ECUs listen to both buses. Safety-critical messages are transmitted on CAN-A only. If CAN-A is silent for more than 100ms, every ECU enters safe mode independently: fuel cell power drops to zero, traction cuts off, driver alarm activates.

## Software task structure (FreeRTOS)

Each ECU runs FreeRTOS with the following task priorities (higher number = higher priority):

**Main ECU tasks:**
- `task_can_rx` (priority 8) — receive and route all CAN messages
- `task_safety_monitor` (priority 7) — watchdog, fault detection
- `task_ecu_coordinator` (priority 5) — request arbitration between subsystems
- `task_telemetry` (priority 2) — log data to SD card
- `task_dashboard_tx` (priority 1) — send display data

**Timing requirements:**
- Safety monitor: must run every 10ms maximum
- CAN RX: interrupt-driven, no task delay
- Telemetry: 100ms interval acceptable

## CAN message definitions

All message definitions live in `forze_ix.dbc` in the firmware repository. Always use the DBC file as the single source of truth. Never hardcode CAN IDs in source files — use the generated header `can_ids.h` which is auto-generated from the DBC file via `scripts/gen_can_headers.py`.

Key message IDs:
- 0x001 — Heartbeat (all ECUs transmit, 100ms period)
- 0x010 — VehicleState (Main ECU → all)
- 0x020 — PowerRequest (Main ECU → Traction)
- 0x100 through 0x103 — Fuel cell (see fuel cell doc)
- 0x200 through 0x204 — BMS messages
- 0x300 through 0x302 — Traction messages
- 0x7F0 — FaultFlags (any ECU, safety-critical, CAN-A only)

## Development workflow

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Write code + unit tests. Tests live in `tests/` next to the module they test.
3. Run the test suite: `make test`. All tests must pass before PR.
4. Open a pull request. Minimum one review from another embedded team member.
5. Merge to main only after review approval.

Never flash untested firmware to the car. Use the hardware-in-the-loop (HIL) test bench in the workshop for any changes to safety-critical code before connecting to the real car.

## Coding standards

We follow MISRA-C guidelines loosely — the goal is readable, predictable code, not bureaucracy. Key rules we enforce:

- No dynamic memory allocation (no malloc/free) — use static allocation only
- All functions return an error code; use `FC_OK` / `FC_ERROR` enum defined in `common/errors.h`
- All shared variables accessed from multiple tasks must be protected by a mutex or accessed only from a single task
- Interrupt service routines (ISRs) must be short — set a flag or push to a queue, then return. Never block in an ISR.
- Every hardware register write must have a comment explaining what it does and why

## Getting started for new embedded members

1. Clone the firmware repo: `git clone https://github.com/forze-delft/forze-ix-firmware`
2. Install STM32CubeIDE from st.com (free)
3. Install the GCC ARM toolchain (included in CubeIDE)
4. Open the project in CubeIDE, build it, confirm zero errors
5. Your first task: pick any driver in `drivers/` that has a TODO comment and implement it
6. Ask the department lead for access to a Nucleo development board — all new members get one to use during their tenure
