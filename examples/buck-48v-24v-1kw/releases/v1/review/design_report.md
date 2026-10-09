# AIPE 48 V to 24 V / 1 kW - V1 design review

**AI-GENERATED ENGINEERING PROTOTYPE - V1 - HUMAN REVIEW REQUIRED**

V1 is a complete CAD review prototype with a routed integrated power/control
board. It is not a fabrication release, a validated converter, or permission to
energize hardware. No parts were purchased and no hardware was powered.

## Specification and assumptions

The supplied benchmark is a synchronous buck, 48 V nominal input, 24 V output,
1000 W and a preferred TMS320F28335 controller. V1 assumes 36-54 V continuous
input from a current-limited regulated bench source, positive output current,
0-50 C ambient, forced airflow and external insulated heatsinking. Prebiased
startup, reverse energy, battery faults, hotplug and automotive transients are
outside the qualified scope. These are engineering choices, not user-supplied
performance guarantees. See [assumptions](../design/assumptions.md).

## Design and calculations

| Quantity | Design value / interpretation |
|---|---|
| Output current | 41.667 A nominal |
| Input current | 21.93 A at 48 V and an assumed 95% efficiency; 29.24 A at 36 V |
| Switching frequency | 100 kHz, complementary PWM with an initial 200 ns deadtime |
| Duty ratio | 0.444-0.667 ideal over the assumed input range |
| Main inductance | 10 uH; 6.4 uH conservative tolerance-plus-droop scenario |
| Inductor ripple | 12 App nominal; 20.83 App in the 54 V / 6.4 uH scenario |
| Peak current | 52.08 A in that scenario, before fault overshoot |
| Input capacitor bank | 14 x 470 uF / 100 V; 6.58 mF nominal; 24.5 Arms summed rating |
| Output capacitor bank | 4 x 1000 uF / 50 V; 4 mF nominal; 10.22 Arms summed rating |
| Input / output ripple demand | 20.98 Arms input; up to 6.01 Arms output |
| Loss budget | 38.67 W nominal scenario; approximately 96.28% calculated efficiency |
| Sensitivity | Doubling the assumed total loss gives approximately 92.82% efficiency |

[Calculations](../design/calculations.md) and their Python generator expose every
assumption. The 100 ns switching-overlap budget, hot MOSFET resistance factor,
reverse recovery, magnetic core loss and copper loss are estimates. Actual gate
and commutation geometry may produce greater loss. No simulated or measured
efficiency, EMI, loop stability or temperature result is claimed.

## Power stage and component selection

The input M5 terminal feeds a 40 A / 70 V MIDI fuse, SMCJ54A TVS, input bulk bank
and eight 2.2 uF / 100 V ceramic bypass capacitors. Two CSD19536KCS MOSFETs are
paralleled in each half-bridge leg, with individual 4.7 ohm gates and 10 kohm
gate-source resistors. Their 100 V rating leaves 46 V static headroom at 54 V;
switching overshoot and the TVS's pulse conditions still require review.

The Vishay IHXL2000VZEB100M3A inductor feeds a Bourns four-terminal 2 mohm shunt
and the output capacitor bank. The magnetic is rated at 83 A for its specified
temperature-rise and 20% inductance-drop conditions. The shunt dissipates about
3.50 W at full load; its 6 W rating depends on terminal temperature. REDCUBE M5
terminals provide bolted connections, with cable strain relief and support
during torque. The 285 g inductor needs an independent clamp.

[Selection and stress register](../components/component_selection.csv),
[purchasing BOM](../components/bom.csv), and
[manufacturer reference hashes](../components/references.json) are separate
from KiCad's native BOM. There are 220 purchased electronic parts plus twelve
bare test points and eight mounting holes. Hardware, heatsinks, insulation,
cables and the magnetic clamp are not a completed mechanical purchasing BOM.

## Driver, control, sensing and protection

The UCC27211 runs from 12 V with local bootstrap/VDD capacitors. LM5164 generates
12 V using the manufacturer's COT ripple-injection arrangement; TPS54302 then
generates 5 V. TPS767D301 supplies approximately 1.899 V core and 3.3 V I/O.
Core power-good enables the I/O regulator through an NPN stage. Open-drain rail
status and a TPS3808 5 V monitor hold the DSP in reset.

All 176 DSP package pins are explicitly assigned. The design includes a 30 MHz
oscillator, per-supply bypass capacitors, ADC reference capacitors and bias
resistor, reset, flash/SCI boot selection, TI 14-pin JTAG and 3.3 V UART.
GPIO0/1 provide ePWM1A/B, GPIO2 arms the latch, and GPIO12 receives FAULT_N/TZ1.
The [firmware interface contract](../design/firmware_interface.md) defines the
required behavior; no commissioned control-loop firmware is supplied.

INA240A1 senses separate shunt Kelvin terminals. Voltage dividers and LM61
temperature sensing feed TLV9004 buffers, ADC RC networks and rail clamps.
The ADC full-scale range is 0-3 V, not 3.3 V. LM61 measures local board
temperature, not MOSFET junction temperature.

LM2903B comparators collect approximately 60 A overcurrent, 27.5 V overvoltage,
90 C board temperature and 34.5 V input undervoltage faults. Fault/reset/12 V
power-good clear the hardware latch; restart requires a new ARM edge. XOR/AND
logic inhibits simultaneous PWM commands, but does not replace DSP deadtime or
prove freedom from propagation-delay hazards. The INA240/comparator path is
not proven fast enough to save MOSFETs during a hard short. At 54 V / 6.4 uH,
short-circuit current can rise about 8.44 A/us.

## PCB implementation

The 300 x 220 x 2.0 mm board has six copper layers. L1/L3/L4/L6 use 70 um copper;
L2/L5 use 35 um ground planes. Power occupies the upper region, driver and
sensing the middle, and DSP/auxiliary supplies the lower region. The layer
order, material assumptions, drill treatment and assembly constraints are in
[stack-up and assembly notes](../design/pcb_stackup.md).

Routing contains 3491 track segments and 720 through vias. VIN uses F.Cu and
In2.Cu; the main switch node uses F.Cu, In3.Cu and B.Cu. The dedicated inner SW
region connects the power copper across interruptions caused by gate routing.
Inductor/shunt/output force paths use both outer layers. Each side of the
surface-mount shunt has 32 large current-transfer vias. Signals use the two
internal signal layers and the back, with top-layer escapes where necessary.
Ground is one electrical net, with two planes and outer copper pours. Plane
windows reduce overlap beneath the extended switch-node region.

## Separate engineering self-review

The review found and corrected an incompatible first package choice for small
logic, undersized driver/regulator exposed-pad geometry, a bootstrap/SW copper
disconnection, duplicate/closely spaced vias, incomplete JTAG routing, exposed-
pad thermal-via omissions, a boot jumper arrangement that could short the rail,
and overlapping connector silkscreen. A separate layer-image inspection found
and corrected a polygon API indexing error that had made a large unintended
ground-plane cutout despite a passing DRC; an area/window invariant now guards
against recurrence. These corrections were followed by new
native checks. Historical failed reports are retained as development evidence.

The final CAD is connected, but its power layout is not optimized or qualified:
driver-to-gate straight-line distances are 8.74-16.17 mm; the LO branch network
has 59.75 mm total track length. HF capacitor-to-drain pad distances are 11 mm
for the upper devices and 16 mm for the lower devices. Switch-node copper is
approximately 508/606/546 mm2 on F.Cu/In3.Cu/B.Cu. These dimensions warrant
overshoot, gate ringing and EMI review. They are not a minimized-loop claim.

The sense paths are true Kelvin nets but are not length-matched differential
pairs. DSP bypass pad distances range up to 6.86 mm. The input bank has only
about 17% summed ripple-rating margin before unequal sharing and temperature.
The [rule-by-rule review](../verification/pcb_rule_review.md) answers all task
review questions and identifies the limits of automated geometry checks.

## Verification and handoff

KiCad 10.0.7 native ERC and DRC, with all severities and schematic parity,
returned zero findings. DRC reports zero unintentionally unrouted connections.
An independently exported XML netlist matches all 645 assigned pins on 85 named
nets; board pads and footprints match the model. All eleven export commands
completed, and export/source hashes are checked. Six automation-wrapper tests
and the original automation smoke example also pass. See
[verification summary](../verification/verification-summary.json).

The review directory contains schematic/layout PDFs and three board views.
Manufacturing contains six copper Gerbers, masks/paste, silkscreen, outline,
drills, coordinates, BOM and STEP. They are review artifacts, not a released
fabrication order. V1 is frozen with a SHA-256 manifest; it must not be edited
for V2. GitHub upload requires repository write access for the authenticated
account; local completion does not imply a remote branch or PR exists.

Priority human decisions are the switching-loop quality, short-circuit strategy,
thermal/mechanical design, input inrush/ripple life, auxiliary rail sequencing
and closed-loop firmware. Read [known issues](../verification/known_issues.md)
before approving any physical work.
