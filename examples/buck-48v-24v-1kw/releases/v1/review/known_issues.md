# V1 known issues and review limits

**AI-GENERATED ENGINEERING PROTOTYPE - V1 - HUMAN REVIEW REQUIRED**

Native ERC/DRC and netlist checks pass. The following engineering issues remain;
a zero CAD finding count does not resolve them.

| ID | Priority | Issue / evidence | Review needed |
|---|---|---|---|
| V1-01 | Before fabrication | Gate and commutation paths are long for a 1 kW switcher: driver-pad distances 8.74-16.17 mm, LO network sum 59.75 mm, ceramic-to-drain distances 11/16 mm | Power engineer review of complete outgoing and return paths; estimate/measure inductance and ringing; determine whether layout revision is required |
| V1-02 | Before energization | 60 A comparator threshold is not guaranteed short-circuit protection; current can rise 8.44 A/us in the conservative fault scenario | Worst-case delay, MOSFET SOA, fuse coordination and source current-limit review; consider a faster dedicated trip strategy |
| V1-03 | Before fabrication | Four live TO-220 tabs, approximately 285 g inductor, fuse bolts and high-current cables need an engineered assembly | Heatsink, insulation, clamp, fastener drawings, torque and clearance review; envelope STEP is insufficient |
| V1-04 | Before fabrication | Input bank has only about 17% summed ripple-rating margin; parallel sharing and capacitor temperature are unknown | Current sharing, cooling, service-life and derating evaluation |
| V1-05 | Before energization | No active inrush, reverse-polarity, prebias, reverse-energy or automotive surge qualification | Restrict initial system requirements to the documented bench-source assumptions; review capacitor charge energy and fuse/TVS coordination |
| V1-06 | Before energization | No validated firmware or compensator; combinational overlap gating has propagation skew | Implement and review the firmware contract, deadtime, startup, synchronous-current policy, trip behavior and loop stability |
| V1-07 | Before energization | Core-first sequence exists, but power-down hold-up, LDO ESR/stability and reset timing have not been measured | Review all ramp/brownout cases, regulator combined thermal limits and actual DSP load |
| V1-08 | Before fabrication | Sense routes are Kelvin-connected but not tightly coupled or length matched; maximum DSP bypass pad distance 6.86 mm | Analog coupling, sample settling and high-frequency decoupling review |
| V1-09 | Before fabrication | Six-layer heavy-copper build contains fine-pitch DSP/logic, plated slots and exposed-pad vias | Fabricator DFM and assembly feedback; confirm mask/paste, plating and via treatment without changing net connectivity |
| V1-10 | Before purchasing | Exact passive order-code availability, MLCC DC-bias curves and some supplier package/lifetime details remain to be confirmed; Taiyo Yuden lists TMK325B7226KMHT as Non-preferred (checked 2026-10-09) | Independent BOM sourcing review; do not substitute by capacitance or footprint alone |
| V1-11 | Performance qualification | Estimated 38.67 W loss / 96.28% efficiency depends on unmeasured transitions, core loss and thermal assumptions | Simulation and measured waveform/temperature validation; no continuous 1 kW rating is established |
| V1-12 | Review handoff | The authenticated GitHub account initially had pull but no push access | Grant write access to the existing repository, push the prepared branch and open the prepared PR |

No fabricated-board, EMC, insulation, lifetime, functional-safety, thermal-rise
or control-loop test results exist. No exclusion/waiver was used to hide an ERC,
DRC or unconnected-net finding. The next design generation requires human
feedback; do not silently alter the frozen V1 files.
