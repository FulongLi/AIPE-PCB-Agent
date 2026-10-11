**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

# V2 PCB stack-ups, design rules and reservations

Design stacks, KiCad rule values, copper and via sizing, fabrication minimums and mechanical
reservations for the two boards defined in [`architecture.md`](architecture.md) and chosen in
[`../review/architecture_comparison.md`](../review/architecture_comparison.md). All values come
from the baseline [`design_decisions.json`](design_decisions.json) unless a record is named;
the standards values are [S] secondary-source until a licensed copy of IEC 61800-5-1 /
IEC 60664-1 is on record. These are design stacks, not fabricator quotations. Tags: [AC]
analytically checked, [DS] datasheet, [S] secondary source, [U] unverified, [HR] human
review.

## 1 Power board: 240 x 180 mm, 4 x 70 um, 2.0 mm nominal

Material FR4, Tg >= 150 C, CTI >= 175 V (group IIIa, Isola 370HR class; CTI class
unverified), ENIG, Er about 4.3 (V1 value, [S]).

| Order | Layer / dielectric | Thickness | Function |
|---|---|---|---|
| 1 | F.Cu | 70 um | HF ceramics, VIN+ / SW / VOUT+ pours, TO-247-4 pads, film pads, HV terminals, bleeders, mezzanine socket and SELV-strip top parts |
| | prepreg | 0.20 mm | commutation-loop dielectric (overlapping VIN+/PGND pours) |
| 2 | In1.Cu | 70 um | PGND return pour under the whole commutation loop and bus; GND_CTRL pour under the SELV strip |
| | core | 1.32 mm (baseline CR-22) | |
| 3 | In2.Cu | 70 um | Kelvin-source pours in both driver islands (shield between the gate layer and all other copper, KR-PCB-001); parallel VIN+ / SW / VOUT+ pours (KR-PCB-006); 12 V and 3V3 distribution in the SELV strip |
| | prepreg | 0.20 mm | gate-loop dielectric (gate pour over Kelvin pour) |
| 4 | B.Cu | 70 um | gate pours with the drivers, DESAT networks, rail decoupling and the three bias modules under the device row; parallel PGND / VOUT+ pours; SELV-strip parts |

Thickness note [AC]: 4 x 0.07 + 2 x 0.20 + 1.32 = 2.00 mm. The research record's 1.1 mm core
gave 1.78 mm; the baseline corrected the core to 1.32 mm for the 2.0 mm stack (CR-22). Via
resistance below is computed for 2.0 mm. A 0.20 mm prepreg between
two 70 um layers is at the edge of pooled capability (resin fill of etched 2 oz copper); if
the fabricator needs 0.25-0.30 mm, the KR-PCB-001 gate/Kelvin adjacency is kept and the loop
dielectric grows proportionally [HR]. Two layers are allowed only if the layout agent proves
gate/Kelvin adjacency and the <= 20 nH board loop target with two layers.

Loop targets after layout: commutation loop <= 20 nH on the board (40-60 nH with standing
TO-247 leads); driver to gate pin <= 15 mm; HF capacitor rows within 5 and 15 mm of the
device pins (all agent metrics, not rule values).

## 2 Control board: 120 x 80 mm, 4 x 35 um, 1.6 mm

| Order | Layer / dielectric | Thickness | Function |
|---|---|---|---|
| 1 | F.Cu | 35 um | DSP, logic, comparators, supplies, signals |
| | prepreg | 0.20 mm | |
| 2 | In1.Cu | 35 um | solid GND_CTRL: one ground net, no splits under ADC or PWM tracks |
| | core | 1.06 mm | |
| 3 | In2.Cu | 35 um | 1V9 / 3V3 / 5V / 12V_PROT islands |
| | prepreg | 0.20 mm | |
| 4 | B.Cu | 35 um | signals, JTAG, mezzanine header |

The dielectrics are an added assumption (standard pooled 4-layer 1.6 mm stack: 4 x 0.035 +
2 x 0.20 + 1.06 = 1.60 mm [AC]); the baseline fixes only layers, copper and total thickness.
No controlled impedance is required (30 MHz clock, JTAG, 50 kHz PWM). Default track/clearance
0.20 mm, minimum 0.15 mm (research record; V1 practice), drill >= 0.3 mm; CTRL_SELV is the
only class; PE appears at the single bonded mounting hole.

## 3 Net classes (power board)

| Class | Reference | Members |
|---|---|---|
| CTRL_SELV | GND_CTRL (SGND, PE-bonded at one point, A-23 HR) | mezzanine nets, 12V_PROT, 3V3_PWRBOARD, driver and bias-module primaries, CM chokes, OPA2320 / REF3125 strip, relay coil, fan, test points |
| HV_VIN | PGND | VIN+, VIN_PRE (relay-contact and PTC terminals), DC-link positive, HF-tier positive, input bleeder chain |
| HV_SW | PGND | SW, HS power source, LS drain, inductor input, snubber node |
| HV_PGND | PGND | PGND, LS power source, DC-link and output negative, PGND-to-PE link pads |
| HV_VOUT | PGND | VOUT+, TMCS1133 conductor, output bank, output bleeder chain |
| DRV_HS | KS_HS = SW | HS gate, HS Kelvin source, VDD_HS / COM_HS / VEE_HS, HS driver and bias secondaries, HS probe loop |
| DRV_LS | KS_LS (PGND potential, separate net) | LS gate, LS Kelvin source, LS rails, LS driver and bias secondaries |
| DESAT_HS, DESAT_LS | floating, full bus when the device is off | nodes between each DESAT diode and its driver (R and C network) |
| SENSE_ISO | PGND | 5V_ISO, sensing-module secondary, AMC1311 VDD1 / IN / GND1 nets, divider taps |
| PE | earth | PE stud, heatsink, clips, standoffs, Y2 PE pads, NTC lug |

## 4 Clearance and keep-out rules (KiCad custom rules, copper gap)

| Pair / item | Value | Basis |
|---|---|---|
| HV_*, DRV_*, DESAT_*, SENSE_ISO to CTRL_SELV, all layers | 9.0 mm | reinforced, 440 V DC working, 6 kV impulse; standard minimum 5.5 mm clearance / 8.8-10.0 mm creepage in the "other insulators" IIIa column [S]; the strict column is adopted (HR: board area) |
| ISO_BARRIER rule area, all copper layers, full board length | 10.0 mm wide, no copper, via or pour | KR-ISO-001 |
| HV_*, DRV_*, DESAT_*, SENSE_ISO to PE (sink outline, clips, standoffs, PE stud, mounting holes) | 5.0 mm (3.0 mm absolute minimum) | basic, 4 kV impulse [S] |
| HV functional pairs (HV_VIN / HV_SW / HV_PGND / HV_VOUT; DRV_HS to DRV_LS and to the other-reference HV classes; DESAT_* to everything except its own drain) | 3.0 mm outer layers, 1.0 mm inner layers | functional at 4 kV / 530 V recurring peak; copper-free HS/LS inter-island band (KR-ISO-001 second clause) |
| Same-reference pairs (DRV_HS-HV_SW, DRV_LS-HV_PGND, SENSE_ISO-HV_PGND, intra-island) | 0.3 mm | <= 25 V functional |
| CTRL_SELV intra-class (power board) | 0.2 mm | fabrication minimum at 70 um |
| HV copper to board edge | 1.0 mm (5.0 mm where an earthed wall or the baseplate edge can touch) | |
| TO-247-4 pin field (2.54 mm pitch cannot meet 3.0 mm) | per-package rule from the pad geometry; the rule applies outside the land pattern | creepage review item (HR), together with the lead-to-sink-face air gap |
| Solder mask | not credited as insulation; no conformal coating assumed (PD2 kept) | |

The DESAT diode bodies and midpoint nets keep the full 3.0 mm outer distance to every other
group; drain runs short (KR-ISO-002). HV test points are recessed safety sockets or probe
loops >= 9.0 mm from SELV copper; hand-probing points only on the SELV side.

## 5 Slots under barrier parts

Every barrier part whose land gap g between HV-side and SELV-side pads is below 9.0 mm sits
over a non-plated slot: 3 x UCC14141 DWN-36, 2 x UCC21710 SOIC-16 DW, 2 x AMC1311 DWV, the
TMCS1133 DVG. Slot width 1.2 mm nominal, >= 1.0 mm after routing tolerance (the IEC 60664-1 X
value at PD2 is 1.0 mm, so a narrower gap would be bridged when creepage is measured; the
CGD1700HB2M-UNA 0.76 mm slot is not reusable). For a through-slot the walls lead nowhere, so
the only surface path runs around the slot ends:

    path = 2 x sqrt((g / 2)^2 + e^2) >= 9.0 mm,  e = slot extension beyond the outermost pad edges

| g (mm) | e = 1.0 mm | e = 2.5 mm | e = 3.0 mm (baseline) | minimum e for 9.0 mm |
|---|---|---|---|---|
| 7.6 | 7.86 | 9.10 | 9.68 | 2.41 |
| 8.0 | 8.25 | 9.43 | 10.00 | 2.06 |
| 8.5 | 8.73 | 9.86 | 10.40 | 1.48 |

The "gap + 2 x board thickness" model of the standards record is wrong for through-slots and
is not used [AC]. Where e >= 3 mm does not fit, the local fallback is the standard-minimum
PWB creepage of 5.5 mm, recorded per instance for review. Slots between DRV_HS and DRV_LS
are needed only if 3.0 mm cannot be held around the TO-247-4 pin field.

## 6 Copper widths and via arrays

IPC-2221 formula I = k x dT^0.44 x A^0.725 (A in mil2; k = 0.048 external, 0.024 internal),
dT = 20 K, 70 um copper, 25 um via plating, rho = 1.72e-8 ohm m; conservative relative to
IPC-2152, whose charts were not obtained [S].

| Item | IPC-2221 minimum [AC] | Design value (baseline) |
|---|---|---|
| 25 A, outer 70 um | 8.4 mm (0.585 mm2) | >= 12 mm pours for VIN+, PGND, SW, VOUT+ |
| 25 A, inner 70 um | 21.7 mm | >= 22 mm, or two parallel inner pours each <= 12.5 A (>= 8.4 mm) |
| 27.5 A overload, outer | 9.5 mm (24.8 K steady state, never reached in 10 s) | covered by 12 mm |
| 32 A worst peak (information) | 11.7 mm outer | - |
| 0.3 mm via, 2.0 mm board | 1.29 A, 1.35 mohm | 24 vias per 25 A layer transition: 31 A capacity, 0.056 mohm, 0.035 W at 25 A |
| 0.5 mm via, 2.0 mm board | 1.83 A, 0.83 mohm | alternative 21 vias: 38 A capacity, 0.040 mohm, 0.025 W |
| DRC proxy | | >= 1 via per 1.5 A of layer-transfer current, staggered arrays at >= 1.0 mm pitch |

Inductor terminals: 3.2 mm PTH with 6.0 mm pads on all layers, no thermal relief, solder-filled
from both sides; SW and VOUT+ pours >= 10 mm wide on two paralleled layers at the terminals
with >= 30 x 0.3 mm vias (inductor record). TMCS1133 IN+/IN- bar pads: wide copper on both
sides, via-stitched, no thermal reliefs, no other high-current trace under the package
(sensing record). Switch-node copper area is limited to what 29-32 A peak and spreading
require, to limit dv/dt-coupled common-mode current (MOSFET record).

## 7 Fabrication minimums (70 um pooled process, confirm with the fabricator [S])

| Feature | Minimum | Preferred / note |
|---|---|---|
| Track / space, 2 oz outer and inner | 0.20 mm | 0.25 mm preferred (A-33, baseline correction); 0.20 mm only with fabricator confirmation |
| Solder-mask dam / expansion | >= 0.15 mm (0.10 absolute) / 0.05 mm | |
| Drill | 0.3 mm | annular ring >= 0.20 mm at 2 oz |
| Plated slot | >= 0.5-0.6 mm wide | none planned on the power board |
| Non-plated routed slot | >= 0.8-1.0 mm | barrier slots 1.2 mm nominal, 1.0 mm minimum after tolerance |
| Via plating | 25 um nominal (IPC-6012 class 2 average >= 20 um) | sizing basis in section 6 |
| Copper to edge | 0.5 mm (HV 1.0 / 5.0 mm) | |
| Large holes | film pads drill 1.6 mm / pad 3.0 mm; inductor 3.2 mm PTH; 4 x 4.3 mm NPTH; REDCUBE THR M5 pattern | custom footprints (capacitor and inductor records) |
| Thickness | 2.0 mm (1.32 mm core, CR-22) | 0.20 mm prepreg between 70 um layers to confirm |
| Control board | 0.15 mm track/space, 0.3 mm drill, 1.6 mm, 35 um | standard pooled stack |

## 8 Reservations and footprints

- Heatsink Fischer LAM 5 D K 100 12 (CR-06; ~100 x 100 mm plan, 50 mm high, integrated 12 V
  fan, 0.30 K/W distributor figure [U]): reservation 175 x 110 mm including the fan allowance
  and 30 mm intake and exhaust corridors, which may hold parts <= 15 mm tall; HV copper
  keep-out >= 5 mm around outline, clips and earthed mounting pins; both TO-247-4 against one
  face at 28 mm pitch, lead row 3-5 mm from the face (thermal record; lead-to-sink air gap is a
  review item), bodies 20-25 mm above the board; custom-cut Sil-Pad TSP A2000 28 x 32 mm per
  device without hole, pad overhang >= 5 mm, clip force >= 40 N to verify, clip metal >= 3 mm
  from the leads; M3 thread-forming NTC hole on the sink top face beside the HS footprint;
  flat thermocouple spots beside each device; PE bonding pad and wire on the PE net.
- Inductor: keep-out circle 75 mm, height 48 mm; 2 x PTH 3.2 mm at 25.4 mm pitch; 4 x 4.3 mm
  NPTH on 60 x 60 mm with 8 mm copper-free annulus for the cup standoffs (metal hardware tied
  to PGND would need >= 4 mm to SW/VOUT copper); terminals >= 4 mm from other nets; no
  feedback, sense, gate or control trace within 10 mm of the keep-out; in the fan stream
  >= 20 mm from the sink and >= 15 mm from the film capacitors (baseline CR-23).
- Film capacitors: C_IN pads at (+/-18.75, +/-5.10) mm, C_OUT at (+/-18.75, +/-10.15) mm,
  drill 1.6 mm, pad 3.0 mm, courtyards 28 x 42 and 30 x 45 mm, heights 37 and 45 mm; >= 20 mm
  from the sink, outside the exhaust; all four pins tied to both pour layers.
- Barrier line: eight parts in one straight row at the HV edge of the ISO_BARRIER band, HV
  pins toward the device row, SELV pins into the strip; slots per section 5; CM chokes and
  input capacitors at the UCC14141 VIN pins on the SELV side; UCC14141 DWN footprint is custom
  (no KiCad library part); TMCS1133 custom DVG footprint with fused IN+/IN- bar pads.
- HF tier: 10 x 2220 in two rows within 5 and 15 mm of the HS drain and LS source pins, both
  sides of the device row, rated >= 125 C; VIN+ and PGND as overlapping F.Cu / In1.Cu pours
  beneath them.
- Terminals: 6 x REDCUBE THR M5 (VIN+, PGND_IN, VOUT+, PGND_OUT, two relay contacts) and the
  PTC footprint at the input and output ends; M4 PE stud pad; PGND-to-PE link, 2 x 1 M 500 V
  and Y2 footprints at the HV terminals (DNP); input and output bleeder chains as straight
  2512 rows with <= 160 V per element and the LED indicator chains at the board edge.
- Mezzanine: SSW-125-01-G-D socket on the SELV strip with four M3 standoff holes; TSW-125-07-G-D
  header on the control board; stack 11.05 mm derived [U]; nothing taller than 8 mm under the
  control board.

## 9 Mounting

Power board on 6 x M4 x 15 mm standoffs to the PE-bonded baseplate (PE keep-out about
17 mm circle each, 5.0 mm rule); control board on 4 x M3 standoffs reaching the baseplate
(two through clearance holes in the SELV strip, nothing cantilevered), overhanging the power
board edge by about 40 mm, no control copper above HV copper (air gap >= 11 mm); inductor
cup on 4 x M4 standoffs, mass never on the solder joints; heatsink mounting hardware from the
Fischer drawing (not accessible [U]), PE-bonded, HV copper >= 5 mm from it; total height
15 + 2 + 50 = 67 mm (limit 80 mm; the baseline mechanical line sums 15 + 2 + 50 = 67 mm (72 mm envelope) -
orchestrator item); mass about 1.9 kg [U]. Labels reserved on silkscreen / enclosure:
IEC 60417-5036 + 60 s, ISO 7010 W012, IEC 60417-5019 at the PE stud, hot surface.

## Verification status and open items

- Analytically checked: stack thickness arithmetic, slot-path table, IPC-2221 widths, via
  current and resistance at 2.0 mm, control-board stack arithmetic, air gap.
- Datasheet: isolator package creepage > 8 mm (UCC21710-Q1, UCC14141-Q1, AMC1311, TMCS1133);
  TO-247-4 package maxima; film and relay envelopes.
- Secondary source: all IEC 61800-5-1 / 60664-1 table values (licensed copy not on record),
  IPC-2221B Table 6-1, fabricator capability figures, Er.
- Unverified: Fischer LAM 5 D K 100 12 dimensions, R_th, mass and mounting; Samtec seating
  depth; isolator land gaps g (to be read from the final footprints); 0.20 mm prepreg
  feasibility; CTI class of the chosen laminate.
- Simulated: nothing.
- Human review: 9.0 mm all-layer rule versus 5.5 mm minimum (board area); 4 kV versus 2.5 kV
  impulse basis; TO-247-4 pin-field exception and
  lead-to-sink air gap; pad rating versus impulse basis; stacked-board clearance at PD2;
  inductor and film spacing (20 mm to the sink, 15 mm film-to-inductor, CR-23) at layout;
  2-layer power-board option; PE bonding
  of the single mounting hole (A-23).
