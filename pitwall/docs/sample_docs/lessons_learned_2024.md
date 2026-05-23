---
author: Chief Embedded Systems
date: 2024-08-22
---

# Lessons learned — Forze IX testing season 2024

This document captures key failures and learnings from the 2024 testing season at Circuit Zandvoort and the Lelystad airstrip tests. Read this before working on any of these subsystems.

## CAN bus timeout incident (Lelystad, June 2024)

**What happened:** During a high-speed run, the car entered safe mode unexpectedly. The driver had to coast to a stop. No physical damage.

**Root cause:** The telemetry task (lowest priority) was starving the CAN TX task by holding the SPI bus to the SD card for too long. When CAN TX was delayed, the heartbeat message from the Main ECU stopped. All other ECUs saw CAN silence and correctly entered safe mode.

**Fix:** Added a separate RTOS task specifically for SD card writes, with a queue buffer so CAN TX never waits for SD. Also reduced SD write frequency from 10Hz to 2Hz for non-critical data.

**Lesson:** Telemetry is never worth losing the car. Always protect safety-critical tasks from interference by lower-priority work. Use task profiling (FreeRTOS runtime stats) regularly to check task execution times.

## Coolant conductivity failure (Zandvoort, July 2024)

**What happened:** Stack voltage started dropping during lap 3 of a 5-lap test. Post-run analysis showed coolant conductivity had risen to 18 µS/cm. Spec is under 5 µS/cm.

**Root cause:** Someone refilled the coolant circuit with tap water instead of de-ionised water after a maintenance session. Tap water contains ions that become conductive and can short internal fuel cell membranes.

**Fix:** The coolant reservoir is now labelled with a red warning sticker. De-ionised water is stored in a clearly marked blue container next to the car. Conductivity is now measured before every test session and logged.

**Lesson:** Label everything. Write it in the pre-run checklist. The person who made the mistake was experienced — it was end of a long day. Checklists exist precisely for that situation.

## Embedded software watchdog timer not triggering (March 2024)

**What happened:** During a bench test, the main ECU firmware entered an infinite loop (bug in prototype code). The hardware watchdog should have reset the MCU within 500ms. It did not.

**Root cause:** The watchdog was being fed by an ISR (Timer interrupt) independently of the main task loop. So even though the main program was stuck, the watchdog kept being satisfied.

**Fix:** Watchdog is now fed only from the `task_safety_monitor` task, which itself monitors the liveness of all other critical tasks via a heartbeat flag mechanism. If any task stops running, `task_safety_monitor` stops feeding the watchdog, and the hardware resets the MCU.

**Lesson:** A watchdog that can be fed independently of the logic it is supposed to watch is worse than no watchdog — it gives false confidence. The watchdog must be fed by code that actually proves the system is healthy.

## Hydrogen pressure sensor calibration drift (ongoing)

**What happened:** Across multiple test sessions, we noticed the hydrogen pressure readings were consistently 0.08 bar higher than the reference gauge.

**Root cause:** The analog pressure sensors drift over time and temperature cycles. Our calibration was done at room temperature but the sensors operate up to 70°C near the stack.

**Current status:** We now recalibrate sensors before every competition. A calibration procedure is in `docs/procedures/sensor_calibration.md`. The embedded software applies a temperature-compensated correction factor stored in flash.

**Lesson:** Analog sensors lie. Always cross-check critical measurements against a known reference. Digital sensors with I2C/SPI output are more reliable for high-stakes measurements.

## Things that went well

- The FreeRTOS task architecture handled all the complexity we threw at it. No deadlocks in the entire season.
- The DBC-based CAN approach made adding new messages trivial — zero coordination overhead between teams.
- Unit tests caught three bugs before they reached hardware. Testing is worth the time.
- The HIL bench saved us twice — once prevented a BMS software bug from reaching the real battery pack.
