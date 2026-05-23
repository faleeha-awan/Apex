---
author: Operations Team
date: 2024-11-01
---

# Supplier contacts and ordering guide

Always place orders through the operations team unless you have explicit approval for direct purchasing. Keep receipts for everything — we are audited annually.

## Critical suppliers

### Ballard Power Systems (fuel cell stack)
- **Contact:** Dr. Marcus Webb, Technical Account Manager
- **Email:** m.webb@ballard.com
- **Phone:** +1 604 555 0182
- **Lead time:** 8-12 weeks for stack components, 4 weeks for consumables
- **Notes:** We have an academic partnership — always mention "Forze Delft academic program" when ordering. Gives us 30% discount and priority support.

### Saft Batteries (buffer battery cells)
- **Contact:** Ingrid Hoffmann, Academic Sales
- **Email:** i.hoffmann@saft.com
- **Lead time:** 6-8 weeks for cells, 2 weeks for BMS components
- **Notes:** Cells are classified as dangerous goods — requires special shipping documentation. Operations team handles this, never order cells directly.

### STMicroelectronics (microcontrollers)
- **Order via:** DigiKey or Mouser for standard parts. Direct from ST for bulk orders >100 units.
- **STM32H7 (Main ECU):** DigiKey part STM32H743ZIT6
- **STM32F4 (FC/BMS):** DigiKey part STM32F446RET6
- **Lead time:** In stock usually. During chip shortage periods (check Mouser stock first) can be 20+ weeks — order early.
- **Notes:** The NUCLEO dev boards are in the workshop spares cabinet. Take one, log it in the equipment register.

### Kvaser (CAN interfaces)
- **Product:** Kvaser Leaf Light HS v2
- **Order via:** kvaser.com or distributor
- **Lead time:** 1-2 weeks
- **Notes:** We have 4 units. Two are allocated to the HIL bench (do not remove). Two are for portable use — sign them out on the equipment register.

### WEIDMÜLLER (connectors and terminal blocks)
- **Contact:** Bas van der Berg, Sales
- **Email:** b.vanderberg@weidmuller.nl
- **Lead time:** 1-3 days for standard items (they have a warehouse in Rotterdam)
- **Notes:** Preferred supplier for all wiring harness connectors. Ask for the academic catalogue — many items are significantly cheaper.

## Component lead times summary

| Component | Supplier | Typical Lead Time |
|-----------|----------|------------------|
| Fuel cell consumables | Ballard | 4 weeks |
| Microcontrollers (STM32) | DigiKey/Mouser | In stock or 20+ weeks |
| Battery cells | Saft | 6-8 weeks |
| CAN interfaces | Kvaser | 1-2 weeks |
| Wiring connectors | Weidmüller | 1-3 days |
| Pressure sensors | Kistler | 3-4 weeks |
| Temperature sensors (PT100) | RS Components | Next day |

## Ordering process

1. Raise a purchase request in the shared spreadsheet (Operations / Purchase Requests)
2. Include: item, supplier, quantity, estimated cost, justification, urgency
3. Operations lead approves within 2 working days for items under €500
4. Items over €500 require sign-off from the team lead as well
5. Operations places the order and tracks delivery
6. On delivery, check against purchase order and update the equipment register

## Workshop consumables

These can be taken without a formal purchase request — just log usage in the consumables sheet:
- Isopropyl alcohol (cleaning)
- Solder and flux
- Cable ties and heat shrink
- Nitrile gloves
- Safety glasses (replace if scratched — they're free)

Notify the workshop coordinator when any consumable is running low. We aim to never run out during a crunch period.
