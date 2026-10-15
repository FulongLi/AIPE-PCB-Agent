# Architecture selection before placement

This is a new placement problem. No V2.2 coordinates are input to V3 placement.

| Criterion | A: integrated PCB | B: power + control PCBs | C: power + driver + control PCBs |
|---|---|---|---|
| Gate and commutation loops | Can be local | Local on power PCB | Extra gate/source connector transition unless driver boards mount directly at devices |
| DSP analogue return | Shares large board with switching fields | Separate continuous control ground plane | Separate control plane |
| Insulation boundary | Long shared PCB boundary | Local certified barrier components on power PCB; low-voltage harness | Additional isolated mechanical interfaces and inter-board creepage checks |
| Mechanical support | Large PCB with heavy power parts | Four-point support for both PCBs; heavy magnetics/contactors on chassis | Additional supported driver assemblies |
| Service and verification | One board replacement | Power and control verified independently | Most interconnects and assembly tolerances |
| Manufacturing | Large 4-layer board; expensive scrap | 4-layer power and 4-layer control; different copper weights | Three PCB families; connector BOM and assembly cost |
| Main risk | Noise, mixed geometry and unsupported heavy parts | Harness EMC and fail-safe disconnection | Gate connector parasitics and Kelvin discontinuities |

**Select B.** Power switches, HF link capacitors, both gate drivers, gate bias and isolated voltage acquisition remain on the power PCB. The DSP, reference, ADC filters, timing/interlocks and communications live on a separately supported control PCB placed beside the power board. This prevents the unsupported V2.2 mezzanine overhang. The current transducer, output choke, input fuse/contactors and precharge resistor mount to the chassis with explicit harness connections. They remain part of the complete system circuit and assembly BOM.

Control/power signals use a short, keyed cable with paired returns and default-low receiving enables. No high-current gate or Kelvin-source path crosses that cable. Loss of the cable or control supply must force gate disable. A contactor is an energy isolation device, not a microsecond short-circuit protection device; the asynchronous PWM inhibit and gate-driver short-circuit protection act first.

Power PCB initially uses four 70 um copper layers; control PCB four 35 um layers, one continuous ground plane. These are engineering starting points, not claims that current or routing gates already pass. Layer count may only change after measured routing/return-path evidence. Target assembly envelope is developed from real parts before final placement, with independent A/B floorplan candidates.

The scores above are qualitative. Board dimensions, copper resistance, critical-loop closed-path geometry and assembly volume will be measured from the generated candidates, then the selection will be revisited before final routing.
