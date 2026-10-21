# DAB-V1 requirements and evidence contract

The source request is the AIPE 10 kW DAB workflow task of 2026-10-21; the reference facts are the TI TIDA-010054
fact sheet and the SiC device shortlist in `AIPE-Workflows/examples/dab-10kw/references` (hashed in `baseline.json`).
`specification.yaml` separates user requirements from engineering assumptions, derived operating points and unverified
design targets. A manufacturer rating is not a measurement; a KiCad check result is not a qualification. Everything
generated from these files is **engineering prototype review material**.

## Application and environment (assumed)

Enclosed laboratory / industrial DC-DC converter, pollution degree 2, overvoltage category II, altitude <= 2000 m, 40 C
ambient, forced air on two PE-bonded heat sinks per board with insulating pads under the TO-247-4 devices. The user
did not name a certifiable product or an installation standard. IEC 60664-1 table values are used as **reference
inputs** for the spacing rules; the applicable standard, the laminate CTI certificate (CTI >= 600 assumed), the
impulse basis (4 kV functional / 6 kV reinforced on the 800 V primary, 2.5 / 4 kV on the 400 V secondary) and the
heat-sink insulation system are review prerequisites, not established facts.

## Electrical envelopes

Primary bus 700-800 V (working voltage 800 V used for spacing), secondary 350-450 V (450 V), 10 kW, 100 kHz single
phase shift, turns ratio 2, 35 uH external series inductance in the primary AC path, 9.4 uF DC-blocking capacitance
on the primary AC_B terminal. Transient envelopes of 1000 V / 600 V are handled by the over-voltage trips only; the
boards contain no surge clamp and the source must be a controlled DC supply. Reverse power flow is a control-mode
decision; uncontrolled back-feeding above the envelopes is outside the design basis.

## Devices and reference values carried over

- Gate rails +15 / -4 V and 2 ohm / 2 ohm gate resistors from TIDUES0 for the same driver and devices.
- DESAT, bias-module feedback and sensing-supply network values from the repository's reviewed V3 design; the
  trip level and blanking are to be re-tuned (TIDUES0 used 6.4 V / 1 us).
- Wolfspeed TO-247-4 lead order (drain, source, driver source, gate) as recorded in the repository for the
  C4MS025120K outline; to be confirmed for C3M0075120K and C3M0030090K.
- Film-capacitor, DC-blocking-capacitor and heat-sink dimensions are reserved envelopes (datasheets not located or
  not read); the AIPE isolation footprints keep >= 8.0 mm land gaps and must be compared with the package creepage.

## Controller interface

The TMS320F280039C controlCARD contact map in `interfaces.yaml` is an assumption modelled on the common 180-contact
C2000 controlCARD layout. The task calls the interface "HSEC8-160"; the card has 180 contacts, which is Samtec's
HSEC8-190 size. Both facts are recorded; the map and the socket orderable must be verified before any board is made.

## Auxiliary power and harnesses

External isolated regulated 12 V (about 5 A) into the control board only; the power boards receive 12V_E and 3V3
through 40-way keyed SELV harnesses with signal/return pairs. The harness carries no gate current and no hazardous
potential. Contact current (two 12V_E contacts for about 1 A per board) and SDFM clock integrity over 160 mm are
review items.

## What the automation claims and does not claim

- Claims: the three KiCad projects were generated from these files; native ERC and DRC were run with the recorded
  settings and results; exports were produced with hashed manifests; pad/net equality between model, schematic and
  board was checked; layout and routing metrics were measured as geometry.
- Does not claim: electrical safety, insulation compliance, EMC, thermal adequacy, loop inductance, current
  capacity, component fit (envelopes), firmware behaviour, or manufacturability. No hardware exists; nothing was
  simulated by this package (the AIPE simulation workflow owns that evidence).

Reference URLs and the retrieval status of every manufacturer document are in `source_manifest.json`; cached copies
stay in the ignored `.cache/dab-datasheets` and are not redistributed.
