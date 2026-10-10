# Knowledge-base feedback from the V2 design run

Recorded 2026-10-10 by the V2 (SiC buck 400 V -> 200 V, 5 kW) autonomous design run.
These are PROPOSALS for the maintainers of the Engineering Knowledge System; nothing
under `knowledge/` was changed by V2. The full audit, including the decisions each item
affected and the verification evidence, is in
[examples/sic-buck-400v-200v-5kw/review/knowledge_utilisation_report.md](../examples/sic-buck-400v-200v-5kw/review/knowledge_utilisation_report.md)
(section 6) and the knowledge-application record
[design/knowledge_application.md](../examples/sic-buck-400v-200v-5kw/design/knowledge_application.md).

## Knowledge-base defects and proposed updates (proposals only; nothing under knowledge/ was changed)

Record corrections.

1. CB-PR-002: add the APWM transfer direction (88 % duty at 0.6 V, 10 % at 4.5 V; D = 0.88 - 0.200/V x (V_AIN - 0.6 V)), the treatment of an unused AIN (tie to COM), a single-owner note and the grounding condition under which the AIN route is wrong.
2. CMP-UCC14141-Q1: attach the conditions to the power ratings (1.5 W at 10.8-13.2 V and TA <= 85 C; 1.0 W at 8-18 V; POUT_VDD_MAX 2.5 W at 25 C; SOA = lower of 1.5 W and the derating curve); add the COM-VEE regulator sink / source path through RLIM with the 0.125 A rms pin limit and 16 % run-time qualification (the fact behind CR-12); reconcile the working-voltage figure (1414 Vpk / 1000 Vrms / 1500 Vrms) from SLUSF10B; record certification status.
3. CMP-TPS2640: add the MODE table and I_CB = 12 / R_ILIM - 0.03 A with the 4 ms timeout and 540 ms retry; "2 A eFuse" is not a threshold.
4. CMP-TMCS1133: replace the non-existent TMCS1133B1QDVGR by the A-suffixed orderables; note the product-page (600 Vrms / 8.1 mm) vs datasheet (950 Vrms / 1343 VDC) discrepancy.
5. CMP-R12P21503D, CB-IS-003, SKILL-004: record from the cached RxxP2xx REV 9-2024 datasheet "working voltage 250 VACrms" and "insulation grade according to 62368-1: basic"; fix the 5.2 / 6.4 kVDC attribution.
6. SKILL-006 and the TIDA analysis: mark C3M0030090K obsolete and CR201-50VE / CLA-TO-21E discontinued (August 2024); state that 0.5 and 0.1 C/W are TI instance values with unrecorded airflow, pressure and test power; note that the Wakefield figure is area-normalised.
7. KR-GD-011 / KR-GD-012: "applies by analogy to discretes; label adapted". KR-GD-008: express the exclusion by link length and noise environment and attach the measurement verification. KR-GD-005: state that a synchronous buck is a half bridge for the exclusion list.
8. KR-ISO-004: add the around-the-slot-end creepage model and the PD2 minimum slot width 1.0 mm after tolerance.
9. KR-ISO-001: add the stacked-PCB case as an explicit condition or exclusion.
10. REF-WS-CGD1700HB2M-UNA: reconcile the board size (50.8 x 61.0 vs 50.8 x 59.69 mm); cite PRD-08296 as its own document or add a reference record.
11. SKILL-005 principle 7 and SKILL-004 principle 6: add the RLIM sink check as a precondition for sharing.
12. SKILL-003: keep the exclusion wording and add the HV buck case explicitly (input dQ = D(1-D) I_o T_s; inductor-defined output ripple plus load-step energy).
13. KR-TH-002 and KR-CAP-003: note that the rules carry no numeric or temperature content (three agents cited them for 4 kV, 5.0 mm, 125 C).
14. KR-PR-001: add "if no withstand time is published, compliance is shown by destructive test"; name PRD-08296 as module-level context only.

Additions.

15. New skill "powder-core DC inductor design" from the inductor and magnetic records (LI^2 selector, permeability / loss / magnetisation fits, still-air model as an own approximation, soft-saturation criterion L(1.3 I_pk) >= 70 % of L(I_o) beside the vendor 30 %-drop I_sat, datasheet-maximum core-loss case); component records for 0058192A2 / C058192A2.
16. Gen-4 device records CMP-C4MS025120K (Rev. 2; -10/+23 V; R_thJC 0.41 K/W typical, no maximum; Q_G 125 nC; no withstand time; Arrow-only stock) and CMP-C3M0021120K; an open check on a Gen-4 750 V TO-247-4 industrial family.
17. A block "DC-link precharge, bypass relay and passive discharge" - the area with no knowledge item and the most part-number errors.
18. Component records for the V2 parts without a record, at the verification level reached: TDK B32776G8206K000 / G4606K000, CGA9P (DC bias open), Bergquist TSP A2000 / 3500, Vishay NTCALUG01A103F, Omron G9EA-1 DC12 (400 V maximum switching voltage), Littelfuse KLKD025.T (I2t missing), Fischer LAM 5 D K 100 12 (distributor-only), Wuerth 744226S, REF3125 / REF3130, TLV1702, OPA2320, SN74LVC1G74 (DCTR / DCUR), SN74LV21A, SN74LV04A, Samtec SSW / TSW, REDCUBE 74651195.
19. SKILL-002 / SKILL-006: record the V2 partition pattern (one barrier line through all eight isolators, device row on the HV side, SELV strip at the edge, stacked control board) once the layout metrics exist.
20. A reference record for IEC 61800-5-1:2022 + COR1:2023 (clause 4.3.11 -> 4.4.9) once a licensed copy is on record.

Tooling and process.

21. query.py: index `automation/verification/pcb_rules.json` (or docs/pcb-design-rules.md) so PE-PCB-001..008 resolve with `--get` (re-checked: `unknown id`), and reconfigure stdout to UTF-8.
22. Component-record cache paths (`.cache/references/datasheets/*.pdf`) do not exist on a host that has not run `acquire`; state that sha256 and resolved URL are the evidence anchor.
23. knowledge_trace.py: split compound ids, recognise `external-method` / `project-precedent` entries as declared sources, and emit a banner and header in knowledge_trace.md.
24. Research-record schema: require `conflicts_preserved` for every rule that carries a `conflicts` list (KR-IS-001 and KR-GD-003 each lost one) and one owner per circuit block (CB-PR-002 was adapted three ways).
25. Validation status: V2 is the first run in which knowledge-derived quantities were simulated. The agreement of the buck applications of KR-CAP-001 / KR-CAP-002 and of KR-GD-009 (dead-time loss) with the ngspice campaign could justify `simulation-verified` for those *applications* after human review, with the caveat that the model has no device physics; the rules themselves stay reference-derived or analytically-checked.
