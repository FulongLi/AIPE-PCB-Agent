# V1 design assumptions

AI-GENERATED ENGINEERING PROTOTYPE - V1 - HUMAN REVIEW REQUIRED

The user supplied 48 V nominal input, 24 V output, 1000 W, synchronous buck,
F28335 preferred, and one integrated PCB. The following are engineering choices,
not additional user requirements.

| Topic | V1 assumption and consequence |
|---|---|
| Input | 36-54 V continuous from a current-limited regulated bench supply; no battery reverse-polarity or automotive surge qualification |
| Output | 24 V / 41.667 A continuous design target; positive-current operation; no prebiased-output start or reverse energy acceptance |
| Frequency | 100 kHz, complementary ePWM1A/B, 200 ns initial dead time |
| Environment | 0-50 C ambient; forced airflow and externally supported insulated MOSFET heatsink required |
| Load behavior | 20 A / 100 us illustrative load step; no guaranteed dynamic specification |
| Board | Final 300 x 220 mm, six copper layers, 2.0 mm total; expanded from the initial 300 x 200 mm estimate for placement/routing |
| Copper | L1/L3/L4/L6 70 um finished copper, L2/L5 35 um; PCB vendor must confirm manufacturability and fine-pitch process |
| Power connection | M5 REDCUBE solder terminals, ring lugs, cable strain relief; 2.2 Nm terminal torque only with mechanical support |
| Main inductor | 285 g part requires a separate mechanical clamp/support; solder joints must not carry shock loads |
| Startup | Controlled supply ramp; input-capacitor inrush is not actively limited on this board |
| Software | Hardware design and firmware interface contract; no energized firmware commissioning or validated closed-loop controller in this task |
| Fault protection | Hardware latch inhibits both gates; not a safety-rated function and not a proven hard-short interruption system |
| Development | No purchases, fabrication or physical power-up; full CAD checks plus human review before any later physical work |

The 36-54 V input range is deliberately recorded here because the original task
specified only the nominal voltage. It is not evidence that the board withstands
arbitrary 48 V-bus transients. Transient suppression and measured switch-node
overshoot require review before fabrication.
