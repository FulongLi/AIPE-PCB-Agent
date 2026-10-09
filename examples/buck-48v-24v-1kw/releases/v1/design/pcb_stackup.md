# V1 PCB stack-up and assembly basis

AI-GENERATED ENGINEERING PROTOTYPE - V1 - HUMAN REVIEW REQUIRED

Final outline: 300 x 220 mm, rectangular, eight 3.2 mm NPTH support holes,
2.0 mm nominal total thickness. The board is larger than the initial estimate
to accommodate the input ripple-current bank and power/control separation.

| Order | Layer / dielectric | Thickness | Function |
|---|---|---|---|
| 1 | F.Cu | 70 um | Components, gate escapes, VIN/SW/force/output and ground pours |
| | Prepreg | 0.18 mm | FR4 nominal Er 4.3 |
| 2 | In1.Cu | 35 um | Ground, with window beneath extended SW |
| | Core | 0.30 mm | FR4 |
| 3 | In2.Cu | 70 um | VIN and routed signals |
| | Center prepreg | 0.69 mm | FR4 |
| 4 | In3.Cu | 70 um | Routed signals and localized SW power bridge |
| | Core | 0.30 mm | FR4 |
| 5 | In4.Cu | 35 um | Ground, with window beneath extended SW |
| | Prepreg | 0.18 mm | FR4 |
| 6 | B.Cu | 70 um | Power force/output/SW, signals and ground |

Copper totals 0.35 mm and dielectric totals 1.65 mm. ENIG is the proposed
finish. This is a design stack, not a fabricator quotation. The fabricator must
confirm achievable dielectric thicknesses, finished copper, fine-pitch pad
clearance, solder-mask registration and plated-slot quality.

Ordinary signals are 0.2 mm with 0.2 mm clearance. Default vias are 0.6/0.3 mm
diameter/drill. Minimum checks retain 0.15 mm copper clearance/track width,
0.25 mm drilled-hole separation, and 0.5 mm copper-to-edge clearance. Local
power-zone clearance is 0.5 mm. No meaningful DRC category is disabled.

Main copper transfer at each shunt force terminal uses 32 vias, 1.0 mm diameter,
0.5 mm finished drill, 1.5 mm pitch. The analytical barrel estimate assumes
25 um plating and uniform sharing. It is a resistance/loss estimate, not a
certified current rating. At 41.67 A, the two 32-via arrays must be reviewed
with the shunt-pad bottleneck and hot terminal temperature. Main switch-node
copper uses a third 70 um layer to maintain a continuous power connection
through the gate-routing region.

U1/U2 have five grounded exposed-pad vias each; U4 has nine. Vias under exposed
pads require fabrication/assembly agreement on filling, plugging or tenting to
control solder loss. Ground pours connect directly to pads; large through-hole
power joints will need a qualified soldering process and thermal profile.

## Mechanical and assembly review

- L1 uses two plated 8.5 x 3.0 mm slots at 32.51 mm center spacing. This follows
  the 10 uH Figure B lead geometry, not a generic two-pin inductor. Provide a
  clamp/bracket using the support region; do not rely on solder joints for its
  285 g mass. Its upright envelope is about 55 mm tall.
- R9 uses distinct force and sense pads. Do not bridge the sense pads to force
  copper during footprint cleanup. Orient its two sense terminals toward the
  top of the board as shown in the assembly drawing.
- F1 is a 40 A / 70 V MIDI fuse on 30 mm M6 centers. Its PCB pad/hole geometry
  is a proposal; the insulating support, fasteners, torque and replacement
  clearance require a mechanical drawing and fuse-datasheet review.
- J1-J4 are M5 REDCUBE terminals. Support the terminal during tightening and
  restrain the cable. The vendor's 20 C current rating is conditional on the
  complete PCB/cable assembly and cannot be carried unchanged to hot operation.
- Q1/Q2 tabs are VIN; Q3/Q4 tabs are SW. An external common heatsink requires
  insulating pads and shoulder washers with verified thermal and dielectric
  performance. Clearance for the actual heatsink is not proven by the STEP.
- J7 is a TI 14-pin JTAG header; remove pin 6 or use a keyed equivalent. J8
  jumper 1-2 selects SCI boot; 2-3 or open selects Flash. J9 is 3.3 V UART only.
- Custom L1/R9/F1/U1/U2/U4/Y1 3D shapes are dimensioned envelope models, not
  manufacturer-certified mechanical CAD. Slots/threads, exact lead bends,
  clamps, cables, insulation and heatsinks are not fully modeled. Stock
  capacitor models can also differ in exact height from the selected MPN.

See the F.Fab page in pcb_layout.pdf for designators. Test points are identified
in the schematic and the generated test-point map. Mask and paste outputs are
provided for review; no stencil thickness or final reflow process is specified.
