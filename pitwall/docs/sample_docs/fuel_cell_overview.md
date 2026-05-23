---
author: Powertrain Department
date: 2024-03-15
---

# Hydrogen fuel cell system overview

## What is a PEM fuel cell

Our car uses a Proton Exchange Membrane (PEM) fuel cell stack. A PEM fuel cell generates electricity through an electrochemical reaction between hydrogen and oxygen. Hydrogen enters at the anode, splits into protons and electrons. The protons pass through the membrane to the cathode; the electrons travel through the external circuit, generating current. At the cathode, protons, electrons, and oxygen combine to form water — the only byproduct.

The overall reaction is: 2H₂ + O₂ → 2H₂O + electricity + heat.

## Our stack: key specifications

- **Supplier:** Ballard Power Systems (FC-Velocity module)
- **Rated power:** 100 kW peak
- **Nominal voltage:** 250-350V DC depending on load
- **Operating temperature:** 60-80°C
- **Coolant:** De-ionised water/glycol mix (conductivity must stay below 5 µS/cm)
- **Hydrogen pressure:** 1.5 bar relative at the anode inlet
- **Air supply:** electric compressor, controlled by embedded software

## Embedded software interface

The fuel cell controller communicates with the main vehicle ECU over CAN bus at 500 kbit/s. The following CAN message IDs are used:

- **0x100** — FC_Status: stack voltage, current, temperature, fault codes
- **0x101** — FC_Control: set-point current request from ECU to FC controller
- **0x102** — Coolant_Status: inlet/outlet temperatures, flow rate
- **0x103** — Air_Status: compressor RPM, inlet pressure, humidity

The embedded software team is responsible for reading 0x100 and 0x102 and writing 0x101. The fuel cell controller firmware handles 0x103 internally.

## Thermal management

Temperature is critical. Above 85°C, the membrane degrades irreversibly. Below 40°C during warm-up, efficiency is poor and condensation builds up. The embedded thermal control loop maintains stack temperature between 65-75°C during operation.

The coolant pump is variable-speed, controlled by a PWM signal from the STM32. The pump speed PID loop runs at 100Hz. If temperature exceeds 82°C, the fault handler immediately drops power demand to 20% and alerts the driver via the dashboard.

## Energy management

The fuel cell is paired with a lithium-ion buffer battery (28 kWh, 400V nominal). The battery handles transient power demands and regenerative braking energy. The energy management system (EMS) — implemented in the SimCon team's code running on the traction processor — decides how to split demand between the fuel cell and battery in real time.

The embedded software team provides the EMS with accurate state-of-charge (SOC) estimates and stack power limits. These are published on CAN every 10ms.

## Common failure modes

**High temperature alarm:** Usually caused by pump failure or blocked coolant circuit. Check coolant level and pump PWM output first.

**Low hydrogen pressure:** Regulator fault or hydrogen supply issue. Never attempt to adjust the hydrogen regulator yourself — contact the safety manager.

**Stack voltage drop:** Normal at high load (polarisation losses), abnormal at low load. If voltage drops below 200V at less than 50kW output, flag to the fuel cell team immediately.

**Compressor surge:** Rare. Happens if air demand changes faster than the compressor can respond. The embedded software includes anti-surge logic — if this triggers repeatedly, review the EMS power ramp rate.

## Safety critical rules

1. Never open the hydrogen circuit while the car is powered
2. The workshop must be ventilated when hydrogen is connected — open the large door and confirm the H2 sensor is active
3. Hydrogen work requires two people present minimum — no solo hydrogen handling
4. All hydrogen connections use TEMA 1 fittings — do not substitute with other fittings
5. In case of hydrogen alarm, evacuate the workshop and call the safety manager immediately
