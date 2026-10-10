**AI-GENERATED ENGINEERING PROTOTYPE - V2 - HUMAN REVIEW REQUIRED**

# Architecture comparison: Options A, B and C

Independent evaluation of the board partition for the 400 V -> 200 V, 5 kW, 50 kHz SiC
synchronous buck. It is written from the research record
[`../design/research/architecture.json`](../design/research/architecture.json) after applying
the required changes of its two verification reports,
[`verify_pcb_architecture_selection_engineering.json`](../design/research/verify_pcb_architecture_selection_engineering.json)
and
[`verify_pcb_architecture_selection_factcheck.json`](../design/research/verify_pcb_architecture_selection_factcheck.json)
(both present, both "confirmed-with-corrections"), and from the baseline
[`../design/design_decisions.json`](../design/design_decisions.json), which wins wherever it
speaks. The architecture as built is in [`../design/architecture.md`](../design/architecture.md),
the stack-ups in [`../design/pcb_stackup.md`](../design/pcb_stackup.md). Tags: [AC]
analytically checked, [DS] fetched datasheet, [MP] manufacturer page, [SS] search snippet,
[U] unverified, [HR] human review.

## 1 Corrections applied from the verification reports

1. HV area 240 x 140 mm = 33,600 mm2 at 73 % zone utilisation with the record's envelopes
   (the record's 28,800 mm2 / 86 % was an arithmetic slip); the stretch-outline argument is
   re-derived in section 3.
2. Heat-sink envelope replaced: the record's 100 x 40 x 50 mm reservation with "about
   900 cm2 fin area" (unsupported; a taller CR201-50 has 474 cm2) is superseded by the baseline
   Fischer LAM 5 D K 100 12 (CR-06), reservation 175 x 110 mm, 50 mm high; the verify's
   single-width 185 x 60 x 55 mm proposal is itself superseded by CR-06. Height 15 + 2 + 50 =
   67 mm (the baseline mechanical line sums 15 + 2 + 50 = 67 mm (72 mm envelope); the 55 mm sink term is
   unexplained - orchestrator item; both below the 80 mm limit).
3. The record's KR-TH-001 sanity table (0.5 K/W pad, mixed loss corners, 1.1 K/W called
   acceptable) is dropped; the baseline thermal results stand (schema 3, CR-21: R_pad 1.4 K/W):
   T_J,HS about 109 C at 400 V / 25 A, about 130 C at the 360 V / 27.5 A maximum-R corner,
   P_max 41.5 W per device (margin 1.22) [AC].
4. Films and inductor >= 20 mm from the sink, films >= 15 mm from the inductor (baseline
   CR-23); the earlier 10 mm placement figure is superseded.
5. Fan interface fixed by the baseline: fan connector on the power-board SELV strip behind the
   eFuse, FAN_TACH on mezzanine pin 29, 0.5 A budgeted; per-pin current recomputed (0.49 A).
6. Signalling: the KR-GD-008 exclusion ("short on-board links") is extended to the stacked
   mezzanine by analogy; A-21 and the gate-driver record asked for CB-GD-003 RS-422 when the
   boards are separated. Recorded as a human-review conflict; the 100 mm segment and 150 mm
   cable thresholds are agent assumptions, not rule text.
7. Stack-up arithmetic: 4 x 0.07 + 2 x 0.20 + 1.1 = 1.78 mm, not 2.0 mm; a 2.0 mm board
   needs a 1.32 mm core; fabricator confirmation of a 0.20 mm prepreg between two 70 um layers
   is an open item.
8. Option C rejection reworded: KR-PCB-005 constrains how a plug-in card mates (its
   applicability includes plug-in drivers); it does not reject cards. The SKILL-002 "~200 kW+"
   sentence is a scope note about busbar design and is supporting evidence only. KR-PR-001 is
   not a testability basis; the bench-PWM / double-pulse argument rests on A-37 and the
   CGD1700HB2M-UNA verification practice.
9. The HS/LS inter-island copper-free barrier (KR-ISO-001 second clause) is named explicitly.
10. Earthing items placed: single SGND-to-PE bond at a control-board mounting hole or link,
    PGND-to-PE link footprint with 2 x 1 M 500 V and optional Y2 pads at the HV terminals; PE
    keep-out budget for six M4 standoffs raised to about 1,400 mm2.
11. V1 described correctly: 300 x 220 mm, six layers, 70 um on L1/L3/L4/L6 and 35 um on
    L2/L5; its cost index is quoted with the copper factor used (section 4).
12. Agent metrics labelled as such: <= 15 mm driver-to-device, >= 80 % gate/Kelvin pour
    overlap, <= 100 mm single-ended segment. The 5.0 mm HV-to-sink distance is the standards
    DRC value, not KR-TH-002 content.
13. Component facts upgraded: Samtec SSW insulator 8.51 mm, TSW insulator 2.54 mm, -07 post
    5.84 mm, 6.3 A per pin for SSW+TSW [MP]; C4MS025120K package maxima 16.13 x 23.63 x
    5.21 mm, status Active [DS]; relay coil 0.375 / 0.417 / 0.458 A at 10.8 / 12 / 13.2 V
    [DS]; mass about 1.9 kg [U]; the record's unreproducible "V1 about 24" replaced.
14. The two sensitivity sets whose weights the record did not state are replaced by explicit
    weight vectors (section 5).

## 2 Options

| Option | Boards | Knowledge pattern |
|---|---|---|
| A | one integrated power + control PCB, 70 um on every layer, 4 layers (6 if routing demands, as V1 needed) | V1 project precedent |
| B | power PCB (devices, drivers, bias modules, DC link, inductor, output bank, sensing isolators, fast protection, heatsink) + SELV control PCB (F28335, supplies, PWM/fault logic, comparators, JTAG) on a stacked 2 x 25 mezzanine | REF-TI-TIDA-010054 decision 10 (adapted) |
| C | as B plus one plug-in gate-driver card per switch mating at the device pins | REF-WS-CGD15SG00D2 decision 7, REF-WS-CGD1700HB2M-UNA (adapted, envelopes only) |

## 3 Area, volume and height

Control-section footprints sum to 2,869 mm2; at 30 % utilisation (V1 reached 14-15 % with
loose placement, measured from `placement.json`; TI controlCARDs are denser) a 120 x 80 mm
board follows (2,869 / 0.30 = 9,563 mm2) [AC]. On 70 um copper the same functions need
coarser features: 13,000 mm2 assumed, i.e. 54 mm of depth across 240 mm (agent assumption).

| Metric | A | B | C | V1 |
|---|---|---|---|---|
| Outline(s), mm | 240 x 204 | power 240 x 180 + control 120 x 80 | power 240 x 170 + 2 cards 50 x 30 + control 120 x 80 | 300 x 220 |
| Total PCB area, mm2 | 48,960 | 52,800 | 53,400 | 66,000 |
| Ratio to V1 | 0.74 | 0.80 | 0.81 | 1.00 |
| Occupied plan area, mm2 | 48,960 | 48,000 (control board overhangs 40 mm) | 48,000 | 66,000 |
| Plan bounding box, mm | 240 x 204 | 240 x 220 | 240 x 220 | 300 x 220 |
| Height above baseplate, mm | 67 | 67 (control stack top 38.6) | 67 | not recorded |
| Volume, L (bounding / occupied) | 3.28 / 3.28 | 3.54 / 3.09 | 3.58 / about 3.1 | - |

All figures [AC]; heights 15 mm standoffs + 2.0 mm board + 50 mm sink; A-24 limit 80 mm.
HV zone utilisation with the baseline sink: the exclusive sum (sink body + fan 115 x 110,
inductor with band 6,375, films 5,160, HF tier 560, eight barrier zones 2,000, half-counted
driver islands 1,050, small items and six standoff keep-outs about 5,600) is about
33,400 mm2 = 99 % of 33,600 mm2, 119 % if the 30 mm intake and exhaust corridors (parts
<= 15 mm allowed) are kept empty [AC, this document]. The record's 230 x 170 mm stretch
outline is therefore not credible for any option and the 240 x 180 mm target is at risk for B
exactly as the 240 x 204 mm figure is for A: the comparison between options is unaffected
because all three share the same HV area, but the absolute outlines must be re-derived by
placement (open item in `architecture.md`, section 9). Area estimates carry about +/-15 %.

## 4 Cost index and DFM: LQFP-176 on 70 um copper

    cost index = sum over boards of area [dm2] x layer factor (2L 1.0, 4L 1.8, 6L 2.8)
                 x copper factor (70 um 1.5, 35 um 1.0)      (pooled-fabrication structure,
                                                            relative only, no NRE per board)

| Build | A | B | C | V1 |
|---|---|---|---|---|
| 4-layer power section | 13.2 | 13.4 + 1 connector pair | 13.3 + 3 connector sets + 3 assemblies | - |
| 2-layer power section | - | 8.2 | 8.4 | - |
| 6-layer | 20.6 | - | - | 27.7 (all-70 um factor) / 18.5 (35 um) / 24.6 (blended 4 x 70 + 2 x 35 um) |

The raw board cost of A and B is equal at four layers [AC]; the per-board tooling, stencil and
assembly set-up that the index omits favours A slightly. The decisive difference is
manufacturability. The LQFP-176 has 0.5 mm pitch and 0.28 mm pads, a 0.22 mm nominal gap:

| Copper | Fabricator minimum space [SS] | Margin of the 0.22 mm gap | Mask dam (0.22 - 2 x 0.05 expansion) vs minimum dam |
|---|---|---|---|
| 70 um outer | 0.20 mm (0.25 preferred, A-33) | 10 % | 0.12 mm vs >= 0.15 mm at 2 oz: no dam possible, gang-mask opening, bridging risk |
| 35 um outer | 0.15 mm | 47 % | 0.12 mm vs about 0.10 mm absolute minimum: dam possible |

The record's "effective gap" method (0.22 - 2 x etch allowance = 0.10 mm on 70 um, 0.16 mm on
35 um) double-counts the fabricator's etch compensation, as the verify noted, but the
conclusion holds: a 0.5 mm pitch LQFP on 2 oz outer copper is marginal in space and
impossible in mask dam, which is V1 known issue V1-09 ("six-layer heavy-copper build contains
fine-pitch DSP/logic, plated slots and exposed-pad vias"). Mixed copper weights did not help
V1 because the DSP sits on an outer 70 um layer. Heat conduction across the copper-free
barrier is irrelevant to the choice: R_th = 0.010 / (0.3 x 0.24 x 0.002) = 69 K/W through-plane
(21 K/W in-plane) [AC], so only exhaust air and radiation couple the sections.

## 5 Weighted scoring

Weights (engineering judgement anchored on the V1 failure mode and the knowledge rules):
manufacturing cost and DFM 0.20; EMI loop integrity 0.15 and isolation barrier / grounding
0.15 (hard-switched 400 V SiC; KR-PCB-004, KR-ISO-001); testability 0.10 (A-37 nine-step
commissioning; power stage driven by a bench PWM source at the mezzanine for double-pulse
tests, control board by a simulator); total area 0.10; 0.05 each for volume, cooling
interaction, connector reliability, modularity, layout complexity and future redesign.

| Criterion (weight) | A | B | C |
|---|---|---|---|
| Manufacturing cost and DFM (0.20) | 2 | 4 | 3 |
| EMI: commutation and gate loops, CM coupling (0.15) | 3 | 4 | 2 |
| Isolation barrier and grounding (0.15) | 3 | 4 | 3 |
| Ease of testing (0.10) | 2 | 4 | 4 |
| Total PCB area (0.10) | 4 | 4 | 3 |
| Assembly volume (0.05) | 4 | 4 | 4 |
| Cooling interaction (0.05) | 3 | 4 | 3 |
| Connector reliability (0.05) | 5 | 4 | 2 |
| Modularity / reuse (0.05) | 1 | 4 | 5 |
| Layout complexity (0.05) | 2 | 4 | 3 |
| Future redesign (0.05) | 2 | 4 | 4 |
| Weighted total | 2.75 | 4.00 | 3.10 |

Sensitivity sets with explicit weights (order as in the table) [AC]:

| Set | Weights | A | B | C |
|---|---|---|---|---|
| Baseline | 0.20 / 0.15 / 0.15 / 0.10 / 0.10 / 6 x 0.05 | 2.75 | 4.00 | 3.10 |
| Equal | 11 x 1/11 | 2.82 | 4.00 | 3.27 |
| Area/volume-heavy | 0.15 / 0.10 / 0.10 / 0.05 / 0.25 / 0.15 / 0.05 / 0.05 / 0.05 / 0.025 / 0.025 | 3.15 | 4.00 | 3.18 |
| Modularity/test-heavy | 0.10 / 0.10 / 0.10 / 0.20 / 0.05 / 0.05 / 0.025 / 0.025 / 0.20 / 0.05 / 0.10 | 2.30 | 4.00 | 3.63 |
| Cost-heavy | 0.40 / 0.10 / 0.10 / 0.10 / 0.10 / 4 x 0.04 / 2 x 0.02 | 2.60 | 4.00 | 3.10 |
| Baseline, B penalised to 3 on area and volume (8 % larger than A) | as baseline | 2.75 | 3.85 | 3.10 |

B leads in every set by at least 0.37; C approaches it only when modularity and test are
weighted at 0.40 together, which a two-device 5 kW prototype does not justify. The scores
are integer judgements; the ranking, not the decimals, is the result.

## 6 Knowledge applied

| Item | Status | How it entered the comparison |
|---|---|---|
| KR-PCB-005 (driver adjacent to its switch; plug-in boards mate at the gate/source pins; V_GS probe) | direct, as a constraint | B keeps both UCC21710 on the power board under the device row; C must mate at the pins and still adds a connector to each gate loop (rule rationale: connectors often dominate). The rule rejects nothing; the "<= 15 mm" target is an agent metric |
| KR-PCB-004 (commutation loop first) | direct | HF ceramic columns and the F.Cu/In1.Cu VIN+/PGND pair are planned before the driver islands; in B and C only logic-level signals cross a connector, so connector inductance is outside both loops |
| KR-ISO-001 (no copper across a barrier on any layer; also between driver channels) | direct, hard constraint | B has one barrier instance (eight parts on one line) plus the HS/LS inter-island barrier; A the same on a board shared with the switch node; C one per driver card plus the control barrier. The inter-board "no control copper above HV copper" is an agent extension handed to the standards review |
| KR-ISO-002 (distances per standard) | HR | 9.0 / 5.5 / 5.0 / 3.0 / 1.0 mm applied as geometry from the standards record; stacked-board air gap 11.05-14.9 mm surfaced for review |
| KR-ISO-003 (classes by potential) | direct | eleven classes on the power board; CTRL_SELV only on the control board, which is why B's control-board DRC is trivial |
| KR-ISO-004 (slots) | direct | 1.2 mm slots under eight barrier parts with the around-the-end path formula |
| SKILL-002 principle 4 (driver beside switch; connectors dominate inductance) | direct | the EMI and layout-complexity scores of C; principles 1, 2, 5-8 drive the 4-layer stack-up, barrier and class concept. The "~200 kW+" scope note is supporting evidence only |
| REF-TI-TIDA-010054 decision 10 (power board + control card, drivers bottom-side beside each TO-247-4, LV along the edge) | adapted | pattern for B and the 300 x 180 mm size benchmark; evidence is visual only, no TI value copied |
| REF-WS-CGD1700HB2M-UNA decisions 4, 6 | adapted | 25.4 x 30.5 mm island sections calibrate the 30 x 35 mm driver-island envelope; on-board single-ended links acceptable with buffering and RC |
| REF-WS-CGD15SG00D2 decision 7 | adapted | 47.6 x 17.8 mm card gives the 50 x 30 mm Option C card envelope; three 1 mm slots cross-check; its 8 mm creepage is not generalised |
| KR-PCB-001 / 002 / 003 / 006 | direct | the argument for four layers: gate pour B.Cu over Kelvin pour In2.Cu, decoupling inside the gate loop, Kelvin never merged, parallel bus pours (KR-PCB-006 low confidence; sizing from IPC-2221) |
| KR-GD-008 | adapted, HR | mezzanine single-ended with RC at every receiving pin; conflict with A-21 recorded |
| CB-GD-003 (RS-422) | not applied | fallback for any cabled variant |
| KR-PR-003 / CB-PR-001 | adapted, HR | eFuse at the 12 V entry on the control board; protected 12 V over three mezzanine pins |
| KR-TH-002 | direct | rated pads on the shared PE-bonded sink; the rule carries no distance |
| KR-TH-001 | not re-derived | thermal record owns it; the record's sanity table is withdrawn |
| KR-PR-001 | direct, hard constraint | protection response versus withstand time; not a testability argument |
| SKILL-006 principle 4 / step 3 | direct / adapted and flagged | drivers under the device row; films and magnetics out of the exhaust is an "AIPE recommendation without source evidence" |
| PE-PCB-001..008 | direct, evidence human review | PE-PCB-007 is implemented by the partition itself |
| V1 precedent and V1-09 | adapted | the quantitative baseline that A would repeat |

## 7 Why V1's integrated architecture was not repeated

V1 put the F28335, its supplies and logic on the same 300 x 220 mm heavy-copper board as the
power stage and needed six layers to route it. The consequences are recorded as V1-09
(fine-pitch DSP on 70 um outer copper, plated slots and exposed-pad vias in one fabrication
lot), as the 15 % utilisation of the control section, and as a control ground that had to be
managed on a board carrying the switch node. At 400 V the same architecture would also put
the reinforced HV-to-SELV barrier on the board with the highest dv/dt and the largest
outline, so every change to either domain respins a 2 oz four- or six-layer panel and the
power stage cannot be tested without the DSP. B removes the fine-pitch part from the heavy
copper, gives the control board a continuous 35 um ground plane (PE-PCB-007/008), allows
bench PWM drive of the power stage at the mezzanine and reuses the control board for a later
power stage. This does not deny A's advantages, which the scores record: no connector, 8 %
less area, fewer assemblies.

## 8 Why Option C was not chosen

C is the module-driver pattern of CGD15SG00D2 and CGD1700HB2M-UNA applied to two discrete
TO-247-4 devices. For this converter it adds two connectors inside the gate loops that
KR-PCB-005's rationale warns about, two more assemblies and connector sets, and a reinforced
barrier instance on each card (KR-ISO-001) that each needs its own 9.0 mm clearance, slots
and DRC. It gains modularity that nothing in the programme uses: the driver circuit is fixed
by the device and the bias module, and double-pulse tuning is possible on the power board.
C stays available for a module-based >= 50 kW variant, where it must mate at the gate pins
and carry its own barrier per card.

## 9 Residual risks of Option B

The mezzanine is a single-ended link across two boards in a 400 V / 50 kHz environment (HR,
test by common-mode injection and open-connector test); the stacked control board relies on
a through-air clearance argument at pollution degree 2 (HR); the 240 x 180 mm outline is at
99-119 % zone utilisation with the baseline sink and may have to grow (section 3); the
Samtec stack height and the WR-PHD 50-pin code are unverified; the 12 V pins carry 0.49 A
each at relay pull-in against 4.7 A (SSW/TSM) or 3 A (WR-PHD) ratings [MP], above the
record's 0.4 A target but with > 6x margin.

## Verification status and open items

- Analytically checked: all areas, ratios, heights, volumes, cost indices, scores and the
  five sensitivity sets, the LQFP gap and mask-dam arithmetic, the barrier conduction, the
  zone-sum utilisation with the baseline sink.
- Fetched datasheet / manufacturer page: TO-247-4 envelope, TDK film envelopes, Omron relay,
  Samtec catalogue values, TI controlCARD practice.
- Search snippet / unverified: fabricator capability figures (0.20 / 0.15 mm space, mask
  dams), Fischer LAM 5 D K 100 12 data, Samtec seating depth, WR-PHD 50-pin orderability,
  control-board utilisation 30 %, 70 um density assumption, cost factors, mass.
- Simulated: nothing.
- Human review: scoring weights; 2 versus 4 power-board layers (2 layers only if gate/Kelvin
  adjacency and the <= 20 nH loop target are proven); the single-ended mezzanine versus
  A-21; stacked-board clearance; the outline growth needed to fit the baseline heat-sink
  reservation; 0.20 mm prepreg between 70 um layers.
