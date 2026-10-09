# Engineering Knowledge System V0 — execution status

Recorded 2026-10-09. Branch: `feat/engineering-knowledge-v0`. Host: macOS,
Python 3.9.6 (standard library; no packages installed).

| Milestone | State | Evidence |
|---|---|---|
| Repository inspection, branch | Complete | Existing architecture preserved; new code under `automation/knowledge/`, data under `knowledge/` |
| Reference acquisition | Complete | 25 documents (58.5 MB) from ti.com and wolfspeed.com, all `downloaded` with SHA-256; 13 component datasheets downloaded |
| PRD-04814 located | Complete | Linked from official CGD15SG00D2 and CGD1700HB2M-UNA product pages |
| Inspection | Complete | Archive inventories; PDF text; XLSX→CSV; Allegro netlist (86 nets) and ODB++ connectivity parsed |
| Reference analyses | Complete for V0 | 4 `analysis.md` files, 31 decisions answered with the seven questions |
| Skills | Complete | SKILL-001…006, Markdown + JSON, all `reference-derived` |
| Circuit blocks | Complete | 13 blocks: 7 `analytically-checked`, 6 `reference-derived` |
| Components | Complete | 19 records; datasheet URL status 12 verified-pdf, 3 unverified, 4 not-located |
| Rules | Complete | 43 rules: 11 hard constraints, 2 optimisation objectives, 25 recommendations, 5 human-review; 7 single-reference observations (none hard); conflicts preserved in KR-GD-003/004/005, KR-IS-001 |
| Evidence checks | Passed | 26 checks: 24 pass, 2 computed-for-review, 0 fail (5 netlist checks need the local cache) |
| Validation | Passed | `python -m automation.knowledge.validate`: 0 errors; all 19 part numbers found in the manufacturers' own files |
| Tests | Passed | `python -m unittest discover -s tests`: 40 tests OK (6 existing + 34 new); without the cache: 40 OK, 1 skipped |
| Retrieval demo | Complete | `knowledge/examples/retrieval-demo.md` |
| Buck V1 | Unchanged | Frozen manifest hashes verified by test; no diff against `main` under `examples/buck-48v-24v-1kw` |

## Findings worth human attention

- **Gate-power expression conflict:** TI TIDUES0 Eq.30 uses 2·(V_DD−V_EE)·Q_G·f_s;
  Wolfspeed uses Q_G·f_s·ΔV. Recorded in KR-IS-001 (EC-014).
- **DESAT blanking philosophies differ by >5×** (TI 1 µs vs Wolfspeed ≈46 ns
  + 120 ns deglitch). Recorded in KR-GD-004.
- **TMCS1133:** TI's BOM orderable `TMCS1133B1QDVGR` is not in the current
  datasheet (which lists `TMCS1133B1AQDVGR`), and TI's guide states 1100 VDC
  working voltage versus 1343 VDC reinforced in the 2026 datasheet.
- **Source inconsistencies** are listed per reference (`source_discrepancies`),
  e.g. stale UCC21530 text in TIDUES0F, J15 supply conflict, CGD1700 schematic
  vs 2025 BOM values, PRD-04814 stray paragraph.

## Not done / limitations

- TI Altium binaries not parsed; TI layout knowledge is visual.
- No simulation or hardware validation; nothing is above `analytically-checked`.
- Retrieval is lexical (BM25), not semantic.
- Full AIPE Orchestrator not implemented (only the retrieval API it will call).
